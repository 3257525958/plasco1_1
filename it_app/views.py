from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from decimal import Decimal
from django.db.models import Max, Sum
from django.http import JsonResponse
from django.core.cache import cache
import time
import uuid

from dashbord_app.models import Invoice, InvoiceItem
from cantact_app.models import Branch
from account_app.models import InventoryCount, ProductPricing


# کلاس برای مدیریت وضعیت پیشرفت
class ProgressTracker:
    def __init__(self, task_id):
        self.task_id = task_id

    def update(self, message, percentage, details=None):
        progress_data = {
            'message': message,
            'percentage': percentage,
            'details': details or [],
            'timestamp': time.time()
        }
        cache.set(f'progress_{self.task_id}', progress_data, 300)  # 5 دقیقه

    def get(self):
        return cache.get(f'progress_{self.task_id}')


def invoice_list(request):
    """
    نمایش لیست فاکتورها
    """
    invoices = Invoice.objects.all().prefetch_related('items')

    for invoice in invoices:
        total_remaining = invoice.items.aggregate(
            total_remaining=Sum('remaining_quantity')
        )['total_remaining'] or 0
        invoice.total_remaining = total_remaining

        total_quantity = invoice.items.aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0
        invoice.total_quantity = total_quantity

    return render(request, 'invoice_list.html', {'invoices': invoices})


@require_POST
def reset_remaining_quantity(request):
    """
    ریست کردن تعداد باقیمانده فاکتورهای انتخاب شده
    """
    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        messages.warning(request, 'هیچ فاکتوری انتخاب نشده است.')
        return redirect('invoice_list')

    try:
        selected_items = InvoiceItem.objects.filter(invoice_id__in=selected_invoice_ids)
        updated_count = 0

        for item in selected_items:
            if item.remaining_quantity != item.quantity:
                item.remaining_quantity = item.quantity
                item.save(update_fields=['remaining_quantity'])
                updated_count += 1

        if updated_count > 0:
            messages.success(
                request,
                f'تعداد باقیمانده برای {updated_count} آیتم با موفقیت بروزرسانی شد.'
            )
        else:
            messages.info(request, 'همه آیتم‌ها قبلاً بروزرسانی شده بودند.')

    except Exception as e:
        messages.error(request, f'خطا در بروزرسانی: {str(e)}')

    return redirect('invoice_list')


@require_POST
@transaction.atomic
def distribute_inventory(request):
    """
    توزیع موجودی با قابلیت پیشرفت واقعی و bulk operations
    """
    task_id = str(uuid.uuid4())
    tracker = ProgressTracker(task_id)

    print(f"🎬 شروع فرآیند توزیع موجودی - Task ID: {task_id}")
    tracker.update('آماده‌سازی برای توزیع...', 0, [])

    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        tracker.update('هیچ فاکتوری انتخاب نشده است.', 100)
        time.sleep(1)
        cache.delete(f'progress_{task_id}')
        return JsonResponse({
            'success': False,
            'error': 'هیچ فاکتوری انتخاب نشده است.'
        })

    try:
        # مرحله 1: دریافت اطلاعات شعب
        tracker.update('دریافت اطلاعات شعب...', 5, ['در حال بارگذاری اطلاعات شعب'])
        branches = list(Branch.objects.all())
        if not branches:
            tracker.update('هیچ شعبه‌ای تعریف نشده است.', 100)
            time.sleep(1)
            cache.delete(f'progress_{task_id}')
            return JsonResponse({
                'success': False,
                'error': 'هیچ شعبه‌ای تعریف نشده است.'
            })

        branch_count = len(branches)
        tracker.update(f'تعداد شعب: {branch_count}', 10, [f'تعداد شعب: {branch_count}'])

        # مرحله 2: دریافت آیتم‌های فاکتور
        tracker.update('دریافت آیتم‌های فاکتور...', 15, ['در حال بارگذاری آیتم‌های فاکتور'])
        all_items = InvoiceItem.objects.filter(
            invoice_id__in=selected_invoice_ids,
            remaining_quantity__gt=0
        ).select_related('invoice')

        total_items = all_items.count()
        tracker.update(f'تعداد کل آیتم‌ها: {total_items}', 20, [f'تعداد آیتم‌ها: {total_items}'])

        if not all_items:
            tracker.update('هیچ کالایی با تعداد باقیمانده یافت نشد.', 100)
            time.sleep(1)
            cache.delete(f'progress_{task_id}')
            return JsonResponse({
                'success': False,
                'error': 'هیچ کالایی با تعداد باقیمانده برای توزیع یافت نشد.'
            })

        # مرحله 3: گروه‌بندی کالاها
        tracker.update('گروه‌بندی کالاها...', 25, ['در حال گروه‌بندی کالاها'])
        product_summary = {}
        processed_items = 0

        for item in all_items.iterator(chunk_size=500):
            key = f"{item.product_name}|{item.product_type}"
            if key not in product_summary:
                product_summary[key] = {
                    'name': item.product_name,
                    'type': item.product_type,
                    'total_remaining': 0,
                    'max_selling_price': item.selling_price or item.unit_price,
                    'is_new': item.product_type == 'new',
                    'source_items': []
                }

            product_summary[key]['total_remaining'] += item.remaining_quantity
            product_summary[key]['max_selling_price'] = max(
                product_summary[key]['max_selling_price'],
                item.selling_price or item.unit_price
            )
            product_summary[key]['source_items'].append(item.id)

            processed_items += 1
            if processed_items % 50 == 0:
                progress_percent = 25 + (processed_items / total_items * 15)
                details = [
                    f'تعداد آیتم‌های پردازش شده: {processed_items}/{total_items}',
                    f'تعداد محصولات منحصربه‌فرد: {len(product_summary)}'
                ]
                tracker.update(
                    f'گروه‌بندی کالاها: {processed_items}/{total_items} آیتم',
                    progress_percent,
                    details
                )

        products_to_distribute = []
        for key, data in product_summary.items():
            if data['total_remaining'] > 0:
                products_to_distribute.append(data)

        if not products_to_distribute:
            tracker.update('هیچ کالایی برای توزیع یافت نشد.', 100)
            time.sleep(1)
            cache.delete(f'progress_{task_id}')
            return JsonResponse({
                'success': False,
                'error': 'هیچ کالایی با تعداد باقیمانده معتبر برای توزیع یافت نشد.'
            })

        tracker.update(
            f'تعداد محصولات برای توزیع: {len(products_to_distribute)}',
            40,
            [f'تعداد محصولات: {len(products_to_distribute)}']
        )

        # مرحله 4: به‌روزرسانی قیمت‌گذاری محصولات
        tracker.update('به‌روزرسانی قیمت‌گذاری محصولات...', 45, ['در حال به‌روزرسانی قیمت‌گذاری'])
        pricing_updates = []
        for product in products_to_distribute:
            product_name = product['name']

            try:
                highest_purchase = InvoiceItem.objects.filter(
                    product_name=product_name,
                    invoice_id__in=selected_invoice_ids
                ).aggregate(max_price=Max('unit_price'))['max_price'] or Decimal('0')

                standard_price = product['max_selling_price']

                pricing_updates.append(
                    ProductPricing(
                        product_name=product_name,
                        highest_purchase_price=highest_purchase,
                        standard_price=standard_price
                    )
                )

            except Exception as e:
                print(f"⚠️ خطا در ProductPricing برای {product_name}: {str(e)}")
                continue

        if pricing_updates:
            try:
                ProductPricing.objects.bulk_create(
                    pricing_updates,
                    update_conflicts=True,
                    update_fields=['highest_purchase_price', 'standard_price'],
                    unique_fields=['product_name']
                )
                tracker.update(
                    f'قیمت‌گذاری {len(pricing_updates)} محصول به‌روزرسانی شد',
                    50,
                    [f'قیمت‌گذاری: {len(pricing_updates)} محصول']
                )
            except Exception as e:
                print(f"⚠️ خطا در bulk_create قیمت‌گذاری: {str(e)}")

        # مرحله 5: توزیع کالاها به شعب
        tracker.update('شروع توزیع کالاها بین شعب...', 55, ['شروع توزیع بین شعب'])
        total_distributed = 0
        distribution_details = []
        inventory_updates = []
        inventory_creates = []

        # دریافت موجودی‌های فعلی برای bulk update
        tracker.update('دریافت موجودی‌های فعلی...', 60, ['دریافت موجودی‌های فعلی'])
        existing_inventories = {}
        product_names = [p['name'] for p in products_to_distribute]
        for inv in InventoryCount.objects.filter(product_name__in=product_names):
            key = f"{inv.product_name}_{inv.branch_id}_{inv.is_new}"
            existing_inventories[key] = inv

        product_count = len(products_to_distribute)
        for idx, product in enumerate(products_to_distribute):
            total_remaining = product['total_remaining']
            product_distributed = 0

            progress_percent = 60 + (idx / product_count * 35)
            details = [
                f'محصول: {product["name"]}',
                f'تعداد باقیمانده: {total_remaining}',
                f'پیشرفت: {idx + 1}/{product_count}'
            ]
            tracker.update(
                f'توزیع محصول {product["name"]} ({idx + 1}/{product_count})',
                progress_percent,
                details
            )

            # منطق توزیع
            if total_remaining < 3:
                for branch in branches:
                    qty_for_branch = 1
                    key = f"{product['name']}_{branch.id}_{product['is_new']}"

                    if key in existing_inventories:
                        inv = existing_inventories[key]
                        inv.quantity += qty_for_branch
                        inv.selling_price = max(
                            inv.selling_price or 0,
                            product['max_selling_price']
                        )
                        inventory_updates.append(inv)
                    else:
                        inventory_creates.append(InventoryCount(
                            product_name=product['name'],
                            branch=branch,
                            is_new=product['is_new'],
                            quantity=qty_for_branch,
                            counter=request.user,
                            selling_price=product['max_selling_price'],
                            profit_percentage=Decimal('70.00')
                        ))

                    product_distributed += qty_for_branch
                    total_distributed += qty_for_branch
            else:
                base_per_branch = total_remaining // branch_count
                remainder = total_remaining % branch_count

                for i, branch in enumerate(branches):
                    qty_for_branch = base_per_branch
                    if i < remainder:
                        qty_for_branch += 1

                    if qty_for_branch > 0:
                        key = f"{product['name']}_{branch.id}_{product['is_new']}"

                        if key in existing_inventories:
                            inv = existing_inventories[key]
                            inv.quantity += qty_for_branch
                            inv.selling_price = max(
                                inv.selling_price or 0,
                                product['max_selling_price']
                            )
                            inventory_updates.append(inv)
                        else:
                            inventory_creates.append(InventoryCount(
                                product_name=product['name'],
                                branch=branch,
                                is_new=product['is_new'],
                                quantity=qty_for_branch,
                                counter=request.user,
                                selling_price=product['max_selling_price'],
                                profit_percentage=Decimal('70.00')
                            ))

                        product_distributed += qty_for_branch
                        total_distributed += qty_for_branch

            distribution_details.append(
                f"{product['name']} ({product['type']}): {product_distributed} عدد"
            )

        # مرحله 6: ذخیره‌سازی bulk
        tracker.update('ذخیره‌سازی تغییرات در دیتابیس...', 95, ['ذخیره‌سازی در دیتابیس'])

        if inventory_creates:
            InventoryCount.objects.bulk_create(inventory_creates, batch_size=1000)
            tracker.update(
                f'{len(inventory_creates)} رکورد جدید انبار ایجاد شد',
                96,
                [f'ایجاد: {len(inventory_creates)} رکورد']
            )

        if inventory_updates:
            InventoryCount.objects.bulk_update(
                inventory_updates,
                ['quantity', 'selling_price', 'profit_percentage'],
                batch_size=1000
            )
            tracker.update(
                f'{len(inventory_updates)} رکورد انبار به‌روزرسانی شد',
                97,
                [f'به‌روزرسانی: {len(inventory_updates)} رکورد']
            )

        # مرحله 7: صفر کردن remaining_quantity
        tracker.update('صفر کردن تعداد باقیمانده...', 98, ['صفر کردن تعداد باقیمانده'])
        zeroed_count = all_items.update(remaining_quantity=0)

        # مرحله 8: تکمیل عملیات
        tracker.update('تکمیل عملیات...', 99, ['تکمیل نهایی'])

        # ذخیره نتیجه نهایی
        final_details = [
            f'تعداد کل کالاهای توزیع شده: {total_distributed} عدد',
            f'تعداد کالاهای منحصربه‌فرد: {len(products_to_distribute)} مورد',
            f'تعداد شعب: {branch_count} شعبه',
            f'آیتم‌های به‌روزرسانی شده: {zeroed_count} مورد'
        ]

        # ذخیره پیام موفقیت در session برای نمایش بعدی
        request.session['distribution_success_message'] = {
            'total_distributed': total_distributed,
            'unique_products': len(products_to_distribute),
            'branch_count': branch_count,
            'updated_items': zeroed_count,
            'details': distribution_details[:10]  # فقط 10 آیتم اول
        }

        tracker.update('✅ توزیع با موفقیت انجام شد!', 100, final_details)

        # کمی تأخیر برای نمایش آخرین وضعیت
        time.sleep(2)
        cache.delete(f'progress_{task_id}')

        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'message': 'توزیع با موفقیت انجام شد',
            'data': {
                'total_distributed': total_distributed,
                'unique_products': len(products_to_distribute),
                'branch_count': branch_count,
                'updated_items': zeroed_count
            }
        })

    except Exception as e:
        print(f"❌ خطای بحرانی در توزیع کالاها: {str(e)}")
        import traceback
        traceback.print_exc()

        tracker.update(f'❌ خطا: {str(e)}', 100, ['خطا در عملیات'])
        cache.delete(f'progress_{task_id}')

        return JsonResponse({
            'success': False,
            'error': f'خطا در توزیع کالاها: {str(e)}'
        })


def check_distribution_progress(request):
    """
    بررسی وضعیت پیشرفت توزیع
    """
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({
            'status': 'error',
            'message': 'شناسه کار ارائه نشده است'
        })

    progress = cache.get(f'progress_{task_id}')

    if progress:
        return JsonResponse({
            'status': 'in_progress',
            'message': progress['message'],
            'percentage': progress['percentage'],
            'details': progress.get('details', []),
            'timestamp': progress['timestamp']
        })
    else:
        # بررسی اگر عملیات کامل شده باشد
        if 'distribution_success_message' in request.session:
            success_data = request.session.pop('distribution_success_message', None)
            if success_data:
                return JsonResponse({
                    'status': 'completed',
                    'message': '✅ توزیع با موفقیت انجام شد!',
                    'percentage': 100,
                    'details': [
                        f'تعداد کل کالاهای توزیع شده: {success_data["total_distributed"]} عدد',
                        f'تعداد کالاهای منحصربه‌فرد: {success_data["unique_products"]} مورد',
                        f'تعداد شعب: {success_data["branch_count"]} شعبه',
                        f'آیتم‌های به‌روزرسانی شده: {success_data["updated_items"]} مورد'
                    ]
                })

        return JsonResponse({
            'status': 'not_found',
            'message': 'وضعیت پیشرفت یافت نشد',
            'percentage': 0
        })


@require_http_methods(["GET", "POST"])
def delete_all_product_pricing(request):
    """
    ویو برای حذف تمام رکوردهای ProductPricing با تأیید کاربر
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'confirm':
            record_count = ProductPricing.objects.count()

            if record_count == 0:
                messages.warning(request, '❌ هیچ رکوردی برای حذف وجود ندارد.')
                return redirect('delete_all_product_pricing')

            try:
                deleted_count, deleted_details = ProductPricing.objects.all().delete()
                messages.success(request, f'✅ با موفقیت {deleted_count} رکورد قیمت‌گذاری حذف شد.')

            except Exception as e:
                error_msg = f'❌ خطا در حذف رکوردها: {str(e)}'
                messages.error(request, error_msg)

            return redirect('delete_all_product_pricing')

        elif action == 'cancel':
            messages.info(request, '🔒 عملیات حذف لغو شد.')
            return redirect('delete_all_product_pricing')
        else:
            messages.error(request, '❌ عمل نامعتبر!')
            return redirect('delete_all_product_pricing')

    # GET request
    record_count = ProductPricing.objects.count()
    context = {
        'record_count': record_count,
        'page_title': 'حذف تمام اطلاعات قیمت‌گذاری',
    }
    return render(request, 'delete_all_product_pricing.html', context)


@require_POST
def clear_inventory(request):
    """
    پاک کردن تمام رکوردهای مدل InventoryCount پس از تأیید کاربر
    """
    try:
        record_count = InventoryCount.objects.count()

        if record_count == 0:
            messages.warning(request, "در حال حاضر هیچ داده‌ای در انبار وجود ندارد.")
        else:
            deleted_count = InventoryCount.objects.all().delete()[0]
            messages.success(request, f"✅ تمام داده‌های انبار ({deleted_count} رکورد) با موفقیت پاک شدند.")

    except Exception as e:
        messages.error(request, f"❌ خطا در پاک کردن داده‌های انبار: {str(e)}")

    return redirect('invoice_list')