from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
import math
import time
from dashbord_app.models import Invoice, InvoiceItem
from cantact_app.models import Branch
from account_app.models import InventoryCount, ProductPricing
from django.db.models import Max, Sum
from decimal import Decimal
from django.http import JsonResponse
import json


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


@transaction.atomic
def distribute_single_invoice(invoice_id, user):
    """
    توزیع یک فاکتور به صورت جداگانه
    """
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        branches = list(Branch.objects.all())

        if not branches:
            return False, "هیچ شعبه‌ای تعریف نشده است."

        branch_count = len(branches)

        # آیتم‌هایی که remaining_quantity دارند
        all_items = InvoiceItem.objects.filter(
            invoice_id=invoice_id,
            remaining_quantity__gt=0
        )

        if not all_items:
            return False, "هیچ کالایی با تعداد باقیمانده برای توزیع یافت نشد."

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
            return False, "هیچ کالایی با تعداد باقیمانده معتبر برای توزیع یافت نشد."

        # توزیع کالاها
        total_distributed = 0
        distribution_details = []

        for product in products_to_distribute:
            total_remaining = product['total_remaining']
            base_per_branch = total_remaining // branch_count
            remainder = total_remaining % branch_count

            product_distributed = 0

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
                                'profit_percentage': Decimal('100.00')
                            }
                        )

                        if not created:
                            inventory_obj.quantity += qty_for_branch
                            inventory_obj.selling_price = max(
                                inventory_obj.selling_price or 0,
                                product['max_selling_price']
                            )
                            inventory_obj.profit_percentage = Decimal('100.00')
                            inventory_obj.save()

                        product_distributed += qty_for_branch
                        total_distributed += qty_for_branch

                    except Exception as e:
                        print(f"Error distributing to branch {branch.name}: {str(e)}")
                        continue

            distribution_details.append(
                f"{product['name']}: {product_distributed} عدد"
            )

        # صفر کردن remaining_quantity
        zeroed_count = all_items.update(remaining_quantity=0)

        # ثبت اطلاعات ProductPricing
        for product in products_to_distribute:
            try:
                highest_purchase = InvoiceItem.objects.filter(
                    product_name=product['name'],
                    invoice_id=invoice_id
                ).aggregate(max_price=Max('unit_price'))['max_price'] or Decimal('0')

                ProductPricing.objects.update_or_create(
                    product_name=product['name'],
                    defaults={
                        'highest_purchase_price': highest_purchase,
                        'standard_price': product['max_selling_price']
                    }
                )
            except Exception as e:
                print(f"Error in ProductPricing for {product['name']}: {str(e)}")
                continue

        return True, {
            'invoice_serial': invoice.serial_number,
            'seller': invoice.seller,
            'total_distributed': total_distributed,
            'products_count': len(products_to_distribute),
            'details': distribution_details,
            'zeroed_count': zeroed_count
        }

    except Exception as e:
        return False, f"خطا در توزیع فاکتور: {str(e)}"


@require_POST
def start_distribution(request):
    """
    شروع توزیع ترتیبی - ذخیره اطلاعات در session و نمایش صفحه پیشرفت
    """
    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        messages.warning(request, 'هیچ فاکتوری انتخاب نشده است.')
        return redirect('invoice_list')

    # ذخیره اطلاعات در session
    request.session['pending_invoices'] = selected_invoice_ids
    request.session['current_invoice_index'] = 0
    request.session['distribution_results'] = []
    request.session['total_invoices'] = len(selected_invoice_ids)

    return render(request, 'distribution_progress.html', {
        'total_invoices': len(selected_invoice_ids),
        'selected_invoices': selected_invoice_ids
    })


def distribute_next_invoice(request):
    """
    توزیع فاکتور بعدی - فراخوانی توسط Ajax
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            pending_invoices = request.session.get('pending_invoices', [])
            current_index = request.session.get('current_invoice_index', 0)
            results = request.session.get('distribution_results', [])

            if current_index >= len(pending_invoices):
                return JsonResponse({
                    'completed': True,
                    'results': results
                })

            # توزیع فاکتور جاری
            invoice_id = pending_invoices[current_index]
            success, result = distribute_single_invoice(invoice_id, request.user)

            # به‌روزرسانی session
            current_index += 1
            request.session['current_invoice_index'] = current_index

            results.append({
                'invoice_number': current_index,
                'total_invoices': len(pending_invoices),
                'success': success,
                'data': result if success else None,
                'error': result if not success else None
            })
            request.session['distribution_results'] = results

            return JsonResponse({
                'completed': False,
                'current_invoice': current_index,
                'total_invoices': len(pending_invoices),
                'success': success,
                'data': result if success else None,
                'error': result if not success else None
            })

        except Exception as e:
            return JsonResponse({
                'completed': False,
                'error': f'خطا در توزیع: {str(e)}'
            })

    return JsonResponse({'error': 'درخواست نامعتبر'})


def complete_distribution(request):
    """
    اتمام توزیع و نمایش نتایج
    """
    results = request.session.get('distribution_results', [])
    total_invoices = request.session.get('total_invoices', 0)

    # پاک کردن session
    if 'pending_invoices' in request.session:
        del request.session['pending_invoices']
    if 'current_invoice_index' in request.session:
        del request.session['current_invoice_index']
    if 'distribution_results' in request.session:
        del request.session['distribution_results']

    # ایجاد پیام خلاصه
    success_count = sum(1 for r in results if r.get('success', False))
    failed_count = total_invoices - success_count

    if success_count > 0:
        summary_message = f'✅ توزیع {success_count} از {total_invoices} فاکتور با موفقیت انجام شد!\n\n'

        for result in results:
            if result.get('success'):
                data = result['data']
                summary_message += f'📦 فاکتور {result["invoice_number"]}: {data["invoice_serial"]} - فروشنده: {data["seller"]}\n'
                summary_message += f'   • تعداد کالاهای توزیع شده: {data["total_distributed"]} عدد\n'
                summary_message += f'   • تعداد محصولات منحصر به فرد: {data["products_count"]} مورد\n'
                for detail in data['details']:
                    summary_message += f'   • {detail}\n'
                summary_message += '\n'
            else:
                summary_message += f'❌ فاکتور {result["invoice_number"]}: {result["error"]}\n\n'

        messages.success(request, summary_message)
    else:
        messages.error(request, 'هیچ فاکتوری با موفقیت توزیع نشد.')

    return redirect('invoice_list')


@require_POST
@transaction.atomic
def distribute_inventory(request):
    """
    توزیع فاکتورها به صورت ترتیبی با تاخیر
    """
    print("Start distribute_inventory")

    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        messages.warning(request, 'هیچ فاکتوری انتخاب نشده است.')
        return redirect('invoice_list')

    try:
        results = []
        total_invoices = len(selected_invoice_ids)

        for index, invoice_id in enumerate(selected_invoice_ids, 1):
            # توزیع هر فاکتور
            success, result = distribute_single_invoice(invoice_id, request.user)

            if success:
                results.append({
                    'invoice_number': index,
                    'total_invoices': total_invoices,
                    'success': True,
                    'data': result
                })
            else:
                results.append({
                    'invoice_number': index,
                    'total_invoices': total_invoices,
                    'success': False,
                    'error': result
                })

            # تاخیر 5 ثانیه بین فاکتورها (در سرور)
            if index < total_invoices:
                time.sleep(5)

        # ایجاد پیام خلاصه
        success_count = sum(1 for r in results if r['success'])
        failed_count = total_invoices - success_count

        summary_message = f'✅ توزیع {success_count} از {total_invoices} فاکتور با موفقیت انجام شد!\n\n'

        for result in results:
            if result['success']:
                data = result['data']
                summary_message += f'📦 فاکتور {result["invoice_number"]}: {data["invoice_serial"]} - فروشنده: {data["seller"]}\n'
                summary_message += f'   • تعداد کالاهای توزیع شده: {data["total_distributed"]} عدد\n'
                summary_message += f'   • تعداد محصولات منحصر به فرد: {data["products_count"]} مورد\n'
                for detail in data['details']:
                    summary_message += f'   • {detail}\n'
                summary_message += '\n'
            else:
                summary_message += f'❌ فاکتور {result["invoice_number"]}: {result["error"]}\n\n'

        if success_count > 0:
            messages.success(request, summary_message)
        else:
            messages.error(request, 'هیچ فاکتوری با موفقیت توزیع نشد.')

    except Exception as e:
        print(f"❌ General error in distribute_inventory: {str(e)}")
        messages.error(request, f'❌ خطا در توزیع کالاها: {str(e)}')

    return redirect('invoice_list')


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