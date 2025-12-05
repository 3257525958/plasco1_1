from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.db import transaction
from decimal import Decimal
import math
import time
import json
from dashbord_app.models import Invoice, InvoiceItem
from cantact_app.models import Branch
from account_app.models import InventoryCount, ProductPricing
from django.db.models import Max, Sum
from django.http import JsonResponse
import threading
import uuid
from datetime import datetime

# دیکشنری برای ذخیره وضعیت کارها
distribution_tasks = {}


def invoice_list(request):
    """
    نمایش لیست فاکتورها
    """
    invoices = Invoice.objects.all().prefetch_related('items')

    # محاسبه مجموع remaining_quantity برای هر فاکتور
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
        # پیدا کردن آیتم‌های فاکتورهای انتخاب شده
        selected_items = InvoiceItem.objects.filter(invoice_id__in=selected_invoice_ids)
        updated_count = 0

        # آپدیت تعداد باقیمانده
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
def distribute_inventory(request):
    """
    شروع فرآیند توزیع موجودی - ایجاد تسک جدید
    """
    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        messages.warning(request, 'هیچ فاکتوری انتخاب نشده است.')
        return redirect('invoice_list')

    # ایجاد یک ID منحصر به فرد برای تسک
    task_id = str(uuid.uuid4())

    # ذخیره اطلاعات اولیه تسک
    distribution_tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'current_stage': 'آماده‌سازی',
        'details': [],
        'start_time': datetime.now(),
        'end_time': None,
        'total_items': 0,
        'distributed_items': 0,
        'branches_count': 0,
        'products_count': 0,
        'error': None
    }

    # شروع تسک در یک thread جداگانه
    thread = threading.Thread(
        target=run_distribution_task,
        args=(task_id, selected_invoice_ids, request.user)
    )
    thread.daemon = True
    thread.start()

    # بازگشت به صفحه با task_id
    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'message': 'فرآیند توزیع با موفقیت شروع شد.'
    })


def run_distribution_task(task_id, selected_invoice_ids, user):
    """
    اجرای فرآیند توزیع در background
    """
    try:
        task = distribution_tasks[task_id]
        task['status'] = 'running'

        # مرحله 1: آماده‌سازی
        task['current_stage'] = 'در حال آماده‌سازی...'
        task['progress'] = 5
        time.sleep(0.5)  # کمی تاخیر برای نمایش بهتر

        # دریافت تمام شعب
        branches = list(Branch.objects.all())
        if not branches:
            task['error'] = 'هیچ شعبه‌ای تعریف نشده است.'
            task['status'] = 'failed'
            return

        branch_count = len(branches)
        task['branches_count'] = branch_count
        task['details'].append(f'تعداد شعب: {branch_count}')

        # مرحله 2: خواندن اطلاعات فاکتورها
        task['current_stage'] = 'در حال خواندن اطلاعات فاکتورها...'
        task['progress'] = 10

        # فقط آیتم‌هایی که remaining_quantity دارند
        all_items = InvoiceItem.objects.filter(
            invoice_id__in=selected_invoice_ids,
            remaining_quantity__gt=0
        ).select_related('invoice')

        if not all_items:
            task['error'] = 'هیچ کالایی با تعداد باقیمانده برای توزیع یافت نشد.'
            task['status'] = 'completed'
            return

        task['total_items'] = all_items.count()

        # مرحله 3: گروه‌بندی کالاها
        task['current_stage'] = 'در حال گروه‌بندی کالاها...'
        task['progress'] = 20

        product_summary = {}
        for item in all_items:
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

        products_to_distribute = []
        for key, data in product_summary.items():
            if data['total_remaining'] > 0:
                products_to_distribute.append(data)

        if not products_to_distribute:
            task['error'] = 'هیچ کالایی با تعداد باقیمانده معتبر برای توزیع یافت نشد.'
            task['status'] = 'completed'
            return

        task['products_count'] = len(products_to_distribute)
        task['details'].append(f'تعداد کالاهای منحصر به فرد: {len(products_to_distribute)}')

        # مرحله 4: بروزرسانی ProductPricing
        task['current_stage'] = 'در حال بروزرسانی اطلاعات قیمت‌گذاری...'
        task['progress'] = 30

        for idx, product in enumerate(products_to_distribute):
            product_name = product['name']
            try:
                highest_purchase = InvoiceItem.objects.filter(
                    product_name=product_name,
                    invoice_id__in=selected_invoice_ids
                ).aggregate(max_price=Max('unit_price'))['max_price'] or Decimal('0')

                standard_price = product['max_selling_price']

                pricing_obj, created = ProductPricing.objects.update_or_create(
                    product_name=product_name,
                    defaults={
                        'highest_purchase_price': highest_purchase,
                        'standard_price': standard_price
                    }
                )

                task['details'].append(f'✅ قیمت‌گذاری: {product_name} - قیمت معیار: {standard_price:,} تومان')

            except Exception as e:
                task['details'].append(f'⚠️ خطا در قیمت‌گذاری {product_name}: {str(e)}')

            # به‌روزرسانی پیشرفت
            progress = 30 + int((idx + 1) / len(products_to_distribute) * 20)
            task['progress'] = min(progress, 50)

        # مرحله 5: توزیع کالاها در انبارها
        task['current_stage'] = 'در حال توزیع کالاها بین شعب...'
        task['progress'] = 50

        total_distributed = 0
        for idx, product in enumerate(products_to_distribute):
            total_remaining = product['total_remaining']
            product_distributed = 0

            # توزیع بر اساس منطق شما
            if total_remaining < 3:
                # اگر کمتر از ۳ باشد، به هر شعبه یک کالا بده
                for branch in branches:
                    qty_for_branch = 1

                    try:
                        inventory_obj, created = InventoryCount.objects.get_or_create(
                            product_name=product['name'],
                            branch=branch,
                            is_new=product['is_new'],
                            defaults={
                                'quantity': qty_for_branch,
                                'counter': user,
                                'selling_price': product['max_selling_price'],
                                'profit_percentage': Decimal('70.00')
                            }
                        )

                        if not created:
                            inventory_obj.quantity += qty_for_branch
                            inventory_obj.selling_price = max(
                                inventory_obj.selling_price or 0,
                                product['max_selling_price']
                            )
                            inventory_obj.profit_percentage = Decimal('70.00')
                            inventory_obj.save()

                        product_distributed += qty_for_branch
                        total_distributed += qty_for_branch

                    except Exception as e:
                        task['details'].append(f'⚠️ خطا در توزیع {product["name"]} به شعبه {branch.name}: {str(e)}')
            else:
                # منطق عادی توزیع
                base_per_branch = total_remaining // branch_count
                remainder = total_remaining % branch_count

                for i, branch in enumerate(branches):
                    qty_for_branch = base_per_branch
                    if i < remainder:
                        qty_for_branch += 1

                    if qty_for_branch > 0:
                        try:
                            inventory_obj, created = InventoryCount.objects.get_or_create(
                                product_name=product['name'],
                                branch=branch,
                                is_new=product['is_new'],
                                defaults={
                                    'quantity': qty_for_branch,
                                    'counter': user,
                                    'selling_price': product['max_selling_price'],
                                    'profit_percentage': Decimal('70.00')
                                }
                            )

                            if not created:
                                inventory_obj.quantity += qty_for_branch
                                inventory_obj.selling_price = max(
                                    inventory_obj.selling_price or 0,
                                    product['max_selling_price']
                                )
                                inventory_obj.profit_percentage = Decimal('70.00')
                                inventory_obj.save()

                            product_distributed += qty_for_branch
                            total_distributed += qty_for_branch

                        except Exception as e:
                            task['details'].append(f'⚠️ خطا در توزیع {product["name"]} به شعبه {branch.name}: {str(e)}')

            task['distributed_items'] = total_distributed
            task['details'].append(f'📦 {product["name"]}: {product_distributed} عدد توزیع شد')

            # به‌روزرسانی پیشرفت
            progress = 50 + int((idx + 1) / len(products_to_distribute) * 30)
            task['progress'] = min(progress, 80)

        # مرحله 6: صفر کردن تعداد باقیمانده
        task['current_stage'] = 'در حال صفر کردن تعداد باقیمانده...'
        task['progress'] = 80

        zeroed_count = all_items.update(remaining_quantity=0)
        task['details'].append(f'✅ تعداد باقیمانده {zeroed_count} آیتم صفر شد')

        # مرحله 7: اتمام
        task['current_stage'] = 'توزیع با موفقیت انجام شد!'
        task['progress'] = 100
        task['status'] = 'completed'
        task['end_time'] = datetime.now()

        # محاسبه زمان انجام کار
        duration = (task['end_time'] - task['start_time']).total_seconds()
        task['details'].append(f'⏱️ زمان انجام کار: {duration:.2f} ثانیه')

    except Exception as e:
        task = distribution_tasks.get(task_id)
        if task:
            task['error'] = str(e)
            task['status'] = 'failed'
            task['current_stage'] = f'خطا: {str(e)}'


@require_GET
def get_distribution_status(request, task_id):
    """
    دریافت وضعیت فعلی توزیع
    """
    task = distribution_tasks.get(task_id)

    if not task:
        return JsonResponse({
            'status': 'not_found',
            'message': 'تسک یافت نشد'
        })

    return JsonResponse({
        'status': task['status'],
        'progress': task['progress'],
        'current_stage': task['current_stage'],
        'details': task['details'][-10:],  # فقط 10 مورد آخر
        'total_items': task['total_items'],
        'distributed_items': task['distributed_items'],
        'branches_count': task['branches_count'],
        'products_count': task['products_count'],
        'error': task['error']
    })


@require_http_methods(["GET", "POST"])
def delete_all_product_pricing(request):
    """
    ویو برای حذف تمام رکوردهای ProductPricing با تأیید کاربر
    """
    print("🔍 1 - ویو فراخوانی شد")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'confirm':
            # شمارش رکوردها قبل از حذف
            record_count = ProductPricing.objects.count()

            if record_count == 0:
                messages.warning(request, '❌ هیچ رکوردی برای حذف وجود ندارد.')
                return redirect('delete_all_product_pricing')

            try:
                # حذف تمام رکوردها
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

    # GET request - نمایش صفحه تأیید
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
        # بررسی وجود رکورد برای نمایش پیام مناسب
        record_count = InventoryCount.objects.count()

        if record_count == 0:
            messages.warning(request, "در حال حاضر هیچ داده‌ای در انبار وجود ندارد.")
        else:
            # پاک کردن تمام رکوردها
            deleted_count = InventoryCount.objects.all().delete()[0]
            messages.success(request, f"✅ تمام داده‌های انبار ({deleted_count} رکورد) با موفقیت پاک شدند.")

    except Exception as e:
        messages.error(request, f"❌ خطا در پاک کردن داده‌های انبار: {str(e)}")

    return redirect('invoice_list')