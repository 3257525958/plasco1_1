from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
import math
from dashbord_app.models import Invoice, InvoiceItem
from cantact_app.models import Branch
from account_app.models import InventoryCount, ProductPricing
from django.db.models import Max, Sum
from decimal import Decimal
from django.http import JsonResponse


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


import time
from django.db import transaction
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# در views.py اضافه کنید
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

# دیکشنری برای ذخیره وضعیت پیشرفت
distribution_progress = {}


@csrf_exempt
def start_distribution(request):
    """شروع فرآیند توزیع و ایجاد جلسه"""
    if request.method == 'POST':
        import uuid
        session_id = str(uuid.uuid4())
        distribution_progress[session_id] = {
            'progress': 0,
            'message': 'آماده‌سازی...',
            'details': [],
            'start_time': datetime.now().isoformat(),
            'status': 'processing'
        }

        # اجرای توزیع در background (می‌توانید از Celery استفاده کنید)
        # برای سادگی، توزیع را در همان thread اجرا می‌کنیم
        # در پروژه واقعی از Celery استفاده شود

        return JsonResponse({
            'session_id': session_id,
            'status': 'started'
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def get_distribution_progress(request, session_id):
    """دریافت وضعیت پیشرفت"""
    if session_id in distribution_progress:
        return JsonResponse(distribution_progress[session_id])
    else:
        return JsonResponse({
            'status': 'not_found',
            'message': 'جلسه توزیع یافت نشد'
        }, status=404)
@csrf_exempt
@require_POST
@transaction.atomic
def distribute_inventory(request):
    print("🎬 شروع فرآیند توزیع موجودی")

    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        return JsonResponse({
            'status': 'error',
            'message': 'هیچ فاکتوری انتخاب نشده است.'
        }, status=400)

    try:
        # دریافت تمام شعب
        branches = list(Branch.objects.all())
        if not branches:
            return JsonResponse({
                'status': 'error',
                'message': 'هیچ شعبه‌ای تعریف نشده است.'
            }, status=400)

        branch_count = len(branches)
        print(f"🏪 تعداد شعب: {branch_count}")

        # فقط آیتم‌هایی که remaining_quantity دارند
        all_items = InvoiceItem.objects.filter(
            invoice_id__in=selected_invoice_ids,
            remaining_quantity__gt=0
        ).select_related('invoice')

        if not all_items:
            return JsonResponse({
                'status': 'warning',
                'message': 'هیچ کالایی با تعداد باقیمانده برای توزیع یافت نشد.'
            })

        # گروه‌بندی کالاها
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
            return JsonResponse({
                'status': 'warning',
                'message': 'هیچ کالایی با تعداد باقیمانده معتبر برای توزیع یافت نشد.'
            })

        print(f"📦 تعداد محصولات برای توزیع: {len(products_to_distribute)}")

        # بخش ProductPricing - به صورت bulk برای عملکرد بهتر
        for product in products_to_distribute:
            try:
                highest_purchase = InvoiceItem.objects.filter(
                    product_name=product['name'],
                    invoice_id__in=selected_invoice_ids
                ).aggregate(max_price=Max('unit_price'))['max_price'] or Decimal('0')

                standard_price = product['max_selling_price']

                pricing_obj, created = ProductPricing.objects.update_or_create(
                    product_name=product['name'],
                    defaults={
                        'highest_purchase_price': highest_purchase,
                        'standard_price': standard_price
                    }
                )

                print(f"💰 قیمت‌گذاری {product['name']}: {'ایجاد شد' if created else 'به‌روزرسانی شد'}")

            except Exception as e:
                print(f"⚠️ خطا در قیمت‌گذاری {product['name']}: {str(e)}")
                continue

        # توزیع کالاها - منطق جدید: به هر شعبه کل کالاها (بدون تقسیم)
        total_distributed = 0
        distribution_details = []
        processed_products = 0

        # بهینه‌سازی: استفاده از bulk operations
        inventory_to_create = []
        inventory_to_update = []

        for product in products_to_distribute:
            total_remaining = product['total_remaining']
            processed_products += 1

            # محاسبه درصد پیشرفت
            progress = int((processed_products / len(products_to_distribute)) * 100)

            print(f"🔄 در حال توزیع {product['name']} ({progress}%): {total_remaining} واحد")

            # به هر شعبه به اندازه کل کالاهای باقیمانده این محصول می‌دهیم
            for branch in branches:
                qty_for_branch = total_remaining  # مقدار کامل، نه تقسیم

                try:
                    # بررسی وجود رکورد
                    existing_inventory = InventoryCount.objects.filter(
                        product_name=product['name'],
                        branch=branch,
                        is_new=product['is_new']
                    ).first()

                    if existing_inventory:
                        # به‌روزرسانی
                        existing_inventory.quantity += qty_for_branch
                        existing_inventory.selling_price = max(
                            existing_inventory.selling_price or 0,
                            product['max_selling_price']
                        )
                        existing_inventory.profit_percentage = Decimal('100.00')  # 100٪ سود
                        inventory_to_update.append(existing_inventory)
                    else:
                        # ایجاد جدید
                        inventory_to_create.append(
                            InventoryCount(
                                product_name=product['name'],
                                branch=branch,
                                is_new=product['is_new'],
                                quantity=qty_for_branch,
                                counter=request.user,
                                selling_price=product['max_selling_price'],
                                profit_percentage=Decimal('100.00')  # 100٪ سود
                            )
                        )

                    total_distributed += qty_for_branch

                except Exception as e:
                    print(f"❌ خطا در توزیع به شعبه {branch.name}: {str(e)}")
                    continue

            distribution_details.append(
                f"{product['name']} ({product['type']}): {total_remaining * branch_count} عدد"
            )

        # ذخیره بهینه شده
        if inventory_to_create:
            InventoryCount.objects.bulk_create(inventory_to_create)
            print(f"✅ {len(inventory_to_create)} رکورد جدید ایجاد شد")

        if inventory_to_update:
            InventoryCount.objects.bulk_update(
                inventory_to_update,
                ['quantity', 'selling_price', 'profit_percentage']
            )
            print(f"✅ {len(inventory_to_update)} رکورد به‌روزرسانی شد")

        # صفر کردن remaining_quantity
        zeroed_count = all_items.update(remaining_quantity=0)
        print(f"🔴 {zeroed_count} آیتم صفر شد")

        # برگرداندن نتیجه
        return JsonResponse({
            'status': 'success',
            'message': '✅ توزیع با موفقیت انجام شد!',
            'details': {
                'total_distributed': total_distributed,
                'unique_products': len(products_to_distribute),
                'branches': branch_count,
                'items_updated': zeroed_count,
                'distribution_details': distribution_details
            }
        })

    except Exception as e:
        print(f"❌ خطای کلی در توزیع موجودی: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'❌ خطا در توزیع کالاها: {str(e)}'
        }, status=500)
# @require_POST
# @transaction.atomic
# def distribute_inventory(request):
#     print("🎬 شروع فرآیند توزیع موجودی")
#
#     selected_invoice_ids = request.POST.getlist('selected_invoices')
#
#     if not selected_invoice_ids:
#         messages.warning(request, 'هیچ فاکتوری انتخاب نشده است.')
#         return redirect('invoice_list')
#
#     try:
#         # دریافت تمام شعب
#         branches = list(Branch.objects.all())
#         if not branches:
#             messages.error(request, 'هیچ شعبه‌ای تعریف نشده است.')
#             return redirect('invoice_list')
#
#         branch_count = len(branches)
#         print(f"🏪 تعداد شعب: {branch_count}")
#
#         # فقط آیتم‌هایی که remaining_quantity دارند
#         all_items = InvoiceItem.objects.filter(
#             invoice_id__in=selected_invoice_ids,
#             remaining_quantity__gt=0
#         ).select_related('invoice')
#
#         if not all_items:
#             messages.warning(request, 'هیچ کالایی با تعداد باقیمانده برای توزیع یافت نشد.')
#             return redirect('invoice_list')
#
#         # گروه‌بندی کالاها
#         product_summary = {}
#         for item in all_items:
#             key = f"{item.product_name}|{item.product_type}"
#             if key not in product_summary:
#                 product_summary[key] = {
#                     'name': item.product_name,
#                     'type': item.product_type,
#                     'total_remaining': 0,
#                     'max_selling_price': item.selling_price or item.unit_price,
#                     'is_new': item.product_type == 'new',
#                     'source_items': []
#                 }
#
#             product_summary[key]['total_remaining'] += item.remaining_quantity
#             product_summary[key]['max_selling_price'] = max(
#                 product_summary[key]['max_selling_price'],
#                 item.selling_price or item.unit_price
#             )
#             product_summary[key]['source_items'].append(item.id)
#
#         products_to_distribute = []
#         for key, data in product_summary.items():
#             if data['total_remaining'] > 0:
#                 products_to_distribute.append(data)
#
#         if not products_to_distribute:
#             messages.warning(request, 'هیچ کالایی با تعداد باقیمانده معتبر برای توزیع یافت نشد.')
#             return redirect('invoice_list')
#
#         print(f"Products to distribute: {len(products_to_distribute)}")
#
#         # بخش ProductPricing
#         for product in products_to_distribute:
#             product_name = product['name']
#             print(f"Processing product: {product_name}")
#
#             try:
#                 highest_purchase = InvoiceItem.objects.filter(
#                     product_name=product_name,
#                     invoice_id__in=selected_invoice_ids
#                 ).aggregate(max_price=Max('unit_price'))['max_price'] or Decimal('0')
#
#                 standard_price = product['max_selling_price']
#
#                 pricing_obj, created = ProductPricing.objects.update_or_create(
#                     product_name=product_name,
#                     defaults={
#                         'highest_purchase_price': highest_purchase,
#                         'standard_price': standard_price
#                     }
#                 )
#
#                 print(f"✅ Product pricing {'created' if created else 'updated'}: {product_name}")
#
#             except Exception as e:
#                 print(f"❌ Error in ProductPricing for {product_name}: {str(e)}")
#                 continue
#
#         print("Starting distribution to branches")
#
#         # توزیع کالاها - دقیقاً مطابق دستور
#         total_distributed = 0
#         distribution_details = []
#
#         for product in products_to_distribute:
#             total_remaining = product['total_remaining']
#             product_distributed = 0
#
#             print(f"Distributing {product['name']}: {total_remaining} units")
#
#             # 🔴 دقیقاً مطابق دستور: اگر کمتر از ۳ باشد، به هر شعبه یک کالا بده
#             if total_remaining < 3:
#                 print(f"   ⚠️  تعداد کالا ({total_remaining}) کمتر از ۳ است - دادن ۱ کالا به هر شعبه")
#
#                 # به هر شعبه دقیقاً یک کالا می‌دهیم
#                 for branch in branches:
#                     qty_for_branch = 1  # همیشه ۱ کالا به هر شعبه
#
#                     try:
#                         inventory_obj, created = InventoryCount.objects.get_or_create(
#                             product_name=product['name'],
#                             branch=branch,
#                             is_new=product['is_new'],
#                             defaults={
#                                 'quantity': qty_for_branch,
#                                 'counter': request.user,
#                                 'selling_price': product['max_selling_price'],
#                                 'profit_percentage': Decimal('70.00')
#                             }
#                         )
#
#                         if not created:
#                             inventory_obj.quantity += qty_for_branch
#                             inventory_obj.selling_price = max(
#                                 inventory_obj.selling_price or 0,
#                                 product['max_selling_price']
#                             )
#                             inventory_obj.profit_percentage = Decimal('70.00')
#                             inventory_obj.save()
#
#                         product_distributed += qty_for_branch
#                         total_distributed += qty_for_branch
#
#                         print(f"   ✅ شعبه {branch.name}: 1 کالا")
#
#                     except Exception as e:
#                         print(f"Error distributing to branch {branch.name}: {str(e)}")
#                         continue
#             else:
#                 # منطق عادی برای کالاهای ۳ تا یا بیشتر
#                 base_per_branch = total_remaining // branch_count
#                 remainder = total_remaining % branch_count
#
#                 for i, branch in enumerate(branches):
#                     qty_for_branch = base_per_branch
#                     if i < remainder:
#                         qty_for_branch += 1
#
#                     if qty_for_branch > 0:
#                         try:
#                             inventory_obj, created = InventoryCount.objects.get_or_create(
#                                 product_name=product['name'],
#                                 branch=branch,
#                                 is_new=product['is_new'],
#                                 defaults={
#                                     'quantity': qty_for_branch,
#                                     'counter': request.user,
#                                     'selling_price': product['max_selling_price'],
#                                     'profit_percentage': Decimal('70.00')
#                                 }
#                             )
#
#                             if not created:
#                                 inventory_obj.quantity += qty_for_branch
#                                 inventory_obj.selling_price = max(
#                                     inventory_obj.selling_price or 0,
#                                     product['max_selling_price']
#                                 )
#                                 inventory_obj.profit_percentage = Decimal('70.00')
#                                 inventory_obj.save()
#
#                             product_distributed += qty_for_branch
#                             total_distributed += qty_for_branch
#
#                             print(f"   📦 شعبه {branch.name}: {qty_for_branch} کالا")
#
#                         except Exception as e:
#                             print(f"Error distributing to branch {branch.name}: {str(e)}")
#                             continue
#
#             distribution_details.append(
#                 f"{product['name']} ({product['type']}): {product_distributed} عدد"
#             )
#
#         # صفر کردن remaining_quantity
#         zeroed_count = all_items.update(remaining_quantity=0)
#         print(f"Zeroed {zeroed_count} items")
#
#         # پیام موفقیت
#         detail_message = "\n".join(distribution_details)
#         messages.success(
#             request,
#             f'✅ توزیع با موفقیت انجام شد!\n\n'
#             f'📊 خلاصه عملکرد:\n'
#             f'• تعداد کل کالاهای توزیع شده: {total_distributed} عدد\n'
#             f'• تعداد کالاهای منحصر به فرد: {len(products_to_distribute)} مورد\n'
#             f'• تعداد شعب: {branch_count} شعبه\n'
#             f'• آیتم‌های به روز شده: {zeroed_count} مورد\n\n'
#             f'📦 جزئیات توزیع:\n{detail_message}'
#         )
#
#     except Exception as e:
#         print(f"❌ General error in distribute_inventory: {str(e)}")
#         messages.error(request, f'❌ خطا در توزیع کالاها: {str(e)}')
#
#     return redirect('invoice_list')
# ---------------------------------------------------------------پاک کردن قیمت ها------------------
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods


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


# ------------------------------------------------------پاک کردن کل دیتاهای انبار------------------------------------------
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


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