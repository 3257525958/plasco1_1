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


from django.db import transaction
import time
from django.db.models import Q


# @require_POST
# @transaction.atomic
# def distribute_inventory(request):
#     print("🎬 شروع فرآیند توزیع موجودی - روش کامل به هر شعبه")
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
#         print(f"📦 تعداد محصولات برای توزیع: {len(products_to_distribute)}")
#
#         # بخش ProductPricing
#         for product in products_to_distribute:
#             product_name = product['name']
#             print(f"💵 پردازش قیمت‌گذاری برای: {product_name}")
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
#                 print(f"✅ قیمت‌گذاری {'ایجاد شد' if created else 'به‌روزرسانی شد'}: {product_name}")
#
#             except Exception as e:
#                 print(f"❌ خطا در قیمت‌گذاری برای {product_name}: {str(e)}")
#                 continue
#
#         print("🚀 شروع توزیع کالاها به شعب...")
#
#         # توزیع کالاها
#         total_distributed = 0
#         distribution_details = []
#         label_settings_updated = []
#
#         for product in products_to_distribute:
#             total_remaining = product['total_remaining']
#             product_distributed = 0
#
#             print(f"📤 توزیع محصول: {product['name']} - تعداد: {total_remaining} عدد")
#
#             # توزیع به هر شعبه
#             for branch in branches:
#                 qty_for_branch = total_remaining
#
#                 print(f"   🏪 برای شعبه {branch.name}: {qty_for_branch} عدد")
#
#                 try:
#                     # چک کردن آیا قبلاً این محصول در این شعبه وجود دارد
#                     existing_record = InventoryCount.objects.filter(
#                         product_name=product['name'],
#                         branch=branch,
#                         is_new=product['is_new']
#                     ).first()
#
#                     if existing_record:
#                         # اگر وجود دارد، تعداد را اضافه می‌کنیم
#                         existing_record.quantity += qty_for_branch
#                         existing_record.selling_price = max(
#                             existing_record.selling_price or Decimal('0'),
#                             product['max_selling_price']
#                         )
#                         existing_record.profit_percentage = Decimal('70.00')
#                         existing_record.counter = request.user
#                         existing_record.save()
#                         created = False
#                     else:
#                         # اگر وجود ندارد، رکورد جدید ایجاد می‌کنیم
#                         InventoryCount.objects.create(
#                             product_name=product['name'],
#                             branch=branch,
#                             is_new=product['is_new'],
#                             quantity=qty_for_branch,
#                             counter=request.user,
#                             selling_price=product['max_selling_price'],
#                             profit_percentage=Decimal('70.00')
#                         )
#                         created = True
#
#                     product_distributed += qty_for_branch
#                     total_distributed += qty_for_branch
#
#                     print(f"   ✅ شعبه {branch.name}: {qty_for_branch} عدد اضافه شد")
#
#                 except Exception as e:
#                     print(f"   ❌ خطا در توزیع به شعبه {branch.name}: {str(e)}")
#                     continue
#
#             distribution_details.append(
#                 f"{product['name']} ({product['type']}): هر شعبه {total_remaining} عدد - مجموع: {product_distributed} عدد"
#             )
#             print(f"✅ توزیع محصول {product['name']} تکمیل شد")
#
#         # 🔴 بخش جدید: ایجاد/به‌روزرسانی تنظیمات چاپ لیبل برای هر محصول و هر شعبه
#         print("🏷️  شروع به‌روزرسانی تنظیمات چاپ لیبل...")
#
#         for product in products_to_distribute:
#             product_name = product['name']
#
#             for branch in branches:
#                 try:
#                     # ایجاد یا به‌روزرسانی تنظیمات چاپ لیبل
#                     label_setting, created = ProductLabelSetting.objects.update_or_create(
#                         product_name=product_name,
#                         branch=branch,
#                         defaults={
#                             'barcode': f'PRD-{product_name}-{branch.id}',
#                             # می‌توانید منطق مناسب‌تر برای بارکد داشته باشید
#                             'allow_print': True
#                         }
#                     )
#
#                     if created:
#                         print(f"   ✅ تنظیمات لیبل ایجاد شد: {product_name} - {branch.name}")
#                         label_settings_updated.append(f"{product_name} در شعبه {branch.name}: ایجاد تنظیمات جدید")
#                     else:
#                         # اگر از قبل وجود داشت، فقط allow_print را True می‌کنیم
#                         if not label_setting.allow_print:
#                             label_setting.allow_print = True
#                             label_setting.save()
#                             print(f"   🔄 تنظیمات لیبل به‌روزرسانی شد: {product_name} - {branch.name}")
#                             label_settings_updated.append(f"{product_name} در شعبه {branch.name}: فعال‌سازی چاپ")
#                         else:
#                             print(f"   ℹ️  تنظیمات لیبل از قبل فعال بود: {product_name} - {branch.name}")
#
#                 except Exception as e:
#                     print(f"   ❌ خطا در تنظیمات لیبل برای {product_name} - {branch.name}: {str(e)}")
#                     continue
#
#         # صفر کردن remaining_quantity
#         zeroed_count = all_items.update(remaining_quantity=0)
#         print(f"🔄 صفر شدن {zeroed_count} آیتم")
#
#         # محاسبه آماری جدید
#         total_for_each_branch = sum(product['total_remaining'] for product in products_to_distribute)
#         total_for_all_branches = total_for_each_branch * branch_count
#
#         # آماده‌سازی پیام موفقیت
#         detail_message = "\n".join(distribution_details)
#
#         # اطلاعات تنظیمات لیبل
#         label_info = ""
#         if label_settings_updated:
#             label_info = f"\n🏷️  تنظیمات چاپ لیبل:\n• " + "\n• ".join(label_settings_updated)
#         else:
#             label_info = "\n🏷️  تنظیمات چاپ لیبل: هیچ تنظیماتی به‌روزرسانی نشد"
#
#         messages.success(
#             request,
#             f'✅ توزیع کامل به همه شعب با موفقیت انجام شد!\n\n'
#             f'📊 خلاصه عملکرد:\n'
#             f'• تعداد کل کالاهای توزیع شده: {total_distributed:,} عدد\n'
#             f'• تعداد کالاهای منحصر به فرد: {len(products_to_distribute)} مورد\n'
#             f'• تعداد شعب: {branch_count} شعبه\n'
#             f'• آیتم‌های به روز شده: {zeroed_count} مورد\n'
#             f'• تنظیمات لیبل به‌روزرسانی شده: {len(label_settings_updated)} مورد\n'
#             f'• تعداد برای هر شعبه: {total_for_each_branch:,} عدد\n'
#             f'• مجموع همه شعب: {total_for_all_branches:,} عدد\n'
#             f'{label_info}\n\n'
#             f'📦 جزئیات توزیع:\n{detail_message}'
#         )
#
#         print(f"🎉 فرآیند توزیع با موفقیت پایان یافت. مجموع توزیع: {total_distributed:,} عدد")
#
#     except Exception as e:
#         print(f"❌ خطای کلی در distribute_inventory: {str(e)}")
#         messages.error(request, f'❌ خطا در توزیع کالاها: {str(e)}')
#
#     return redirect('invoice_list')
@require_POST
@transaction.atomic
def distribute_inventory(request):
    print("🎬 شروع فرآیند توزیع موجودی - روش کامل به هر شعبه")

    selected_invoice_ids = request.POST.getlist('selected_invoices')

    if not selected_invoice_ids:
        messages.warning(request, 'هیچ فاکتوری انتخاب نشده است.')
        return redirect('invoice_list')

    try:
        # دریافت تمام شعب
        branches = list(Branch.objects.all())
        if not branches:
            messages.error(request, 'هیچ شعبه‌ای تعریف نشده است.')
            return redirect('invoice_list')

        branch_count = len(branches)
        print(f"🏪 تعداد شعب: {branch_count}")

        # فقط آیتم‌هایی که remaining_quantity دارند
        all_items = InvoiceItem.objects.filter(
            invoice_id__in=selected_invoice_ids,
            remaining_quantity__gt=0
        ).select_related('invoice')

        if not all_items:
            messages.warning(request, 'هیچ کالایی با تعداد باقیمانده برای توزیع یافت نشد.')
            return redirect('invoice_list')

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
            messages.warning(request, 'هیچ کالایی با تعداد باقیمانده معتبر برای توزیع یافت نشد.')
            return redirect('invoice_list')

        print(f"📦 تعداد محصولات برای توزیع: {len(products_to_distribute)}")

        # بخش ۱: ProductPricing با منطق StoreInvoiceItems
        print("💵 شروع پردازش قیمت‌گذاری...")
        for product in products_to_distribute:
            product_name = product['name']
            print(f"  🔍 پردازش قیمت‌گذاری برای: {product_name}")

            try:
                # یافتن بالاترین قیمت واحد برای این محصول از InvoiceItem
                highest_price_item = InvoiceItem.objects.filter(
                    product_name=product_name,
                    invoice_id__in=selected_invoice_ids
                ).order_by('-unit_price').first()

                if highest_price_item:
                    new_price = highest_price_item.unit_price
                    invoice = highest_price_item.invoice

                    print(f"    💰 قیمت جدید: {new_price}")

                    # یافتن یا ایجاد ProductPricing
                    product_pricing, created = ProductPricing.objects.get_or_create(
                        product_name=product_name,
                        defaults={
                            'highest_purchase_price': new_price,
                            'invoice_date': invoice.jalali_date,
                            'invoice_number': invoice.serial_number,
                            'standard_price': new_price,
                            'adjustment_percentage': Decimal('0')
                        }
                    )

                    if created:
                        print(f"    ✅ ProductPricing جدید ایجاد شد برای: {product_name}")
                    else:
                        # دریافت مقادیر قدیم
                        old_highest_price = product_pricing.highest_purchase_price or Decimal('0')
                        print(f"    📊 قیمت قدیم: {old_highest_price}")

                        # منطق تصمیم‌گیری
                        if new_price <= old_highest_price:
                            print(f"    📉 حالت 1: قیمت جدید ≤ قیمت قدیم")
                            product_pricing.standard_price = old_highest_price
                            product_pricing.adjustment_percentage = Decimal('0')
                        else:
                            print(f"    📈 حالت 2: قیمت جدید > قیمت قدیم")
                            product_pricing.highest_purchase_price = new_price
                            product_pricing.standard_price = new_price
                            product_pricing.adjustment_percentage = Decimal('0')

                        # به‌روزرسانی اطلاعات فاکتور
                        product_pricing.invoice_date = invoice.jalali_date
                        product_pricing.invoice_number = invoice.serial_number
                        product_pricing.save()
                        print(f"    ✅ قیمت‌گذاری به‌روزرسانی شد برای: {product_name}")

                else:
                    print(f"    ⚠️  هیچ فاکتوری برای محصول {product_name} یافت نشد")
                    # ایجاد ProductPricing با مقادیر پیشفرض
                    ProductPricing.objects.get_or_create(
                        product_name=product_name,
                        defaults={
                            'highest_purchase_price': Decimal('0'),
                            'standard_price': Decimal('0'),
                            'adjustment_percentage': Decimal('0')
                        }
                    )

            except Exception as e:
                print(f"    ❌ خطا در قیمت‌گذاری برای {product_name}: {str(e)}")
                continue

        # بخش ۲: توزیع کالاها به انبار (InventoryCount)
        print("🚀 شروع توزیع کالاها به شعب...")
        total_distributed = 0
        distribution_details = []

        for product in products_to_distribute:
            total_remaining = product['total_remaining']
            product_distributed = 0

            print(f"📤 توزیع محصول: {product['name']} - تعداد: {total_remaining} عدد")

            for branch in branches:
                qty_for_branch = total_remaining  # هر شعبه کل تعداد را دریافت می‌کند

                print(f"   🏪 برای شعبه {branch.name}: {qty_for_branch} عدد")

                try:
                    # چک کردن آیا قبلاً این محصول در این شعبه وجود دارد
                    existing_record = InventoryCount.objects.filter(
                        product_name=product['name'],
                        branch=branch,
                        is_new=product['is_new']
                    ).first()

                    if existing_record:
                        # اگر وجود دارد، تعداد را اضافه می‌کنیم
                        existing_record.quantity += qty_for_branch
                        existing_record.selling_price = max(
                            existing_record.selling_price or Decimal('0'),
                            product['max_selling_price']
                        )
                        existing_record.profit_percentage = Decimal('70.00')
                        existing_record.counter = request.user
                        existing_record.save()
                        print(f"   🔄 موجودی شعبه {branch.name} به‌روزرسانی شد")
                    else:
                        # اگر وجود ندارد، رکورد جدید ایجاد می‌کنیم
                        InventoryCount.objects.create(
                            product_name=product['name'],
                            branch=branch,
                            is_new=product['is_new'],
                            quantity=qty_for_branch,
                            counter=request.user,
                            selling_price=product['max_selling_price'],
                            profit_percentage=Decimal('70.00')
                        )
                        print(f"   ✅ رکورد جدید در شعبه {branch.name} ایجاد شد")

                    product_distributed += qty_for_branch
                    total_distributed += qty_for_branch

                    print(f"   ✅ شعبه {branch.name}: {qty_for_branch} عدد اضافه شد")

                except Exception as e:
                    print(f"   ❌ خطا در توزیع به شعبه {branch.name}: {str(e)}")
                    continue

            distribution_details.append(
                f"{product['name']} ({product['type']}): هر شعبه {total_remaining} عدد - مجموع: {product_distributed} عدد"
            )
            print(f"✅ توزیع محصول {product['name']} تکمیل شد")

        # بخش ۳: تنظیمات چاپ لیبل (ProductLabelSetting)
        print("🏷️  شروع به‌روزرسانی تنظیمات چاپ لیبل...")
        label_settings_updated = []

        for product in products_to_distribute:
            product_name = product['name']

            for branch in branches:
                try:
                    # ایجاد بارکد
                    import hashlib
                    barcode_data = f"{product_name}-{branch.id}"
                    barcode_hash = hashlib.md5(barcode_data.encode()).hexdigest()[:10].upper()
                    barcode = f"PRD-{barcode_hash}"

                    # ایجاد یا به‌روزرسانی تنظیمات چاپ لیبل
                    label_setting, created = ProductLabelSetting.objects.update_or_create(
                        product_name=product_name,
                        branch=branch,
                        defaults={
                            'barcode': barcode,
                            'allow_print': True
                        }
                    )

                    if created:
                        print(f"   ✅ تنظیمات لیبل ایجاد شد: {product_name} - {branch.name}")
                        label_settings_updated.append(f"{product_name} در شعبه {branch.name}")
                    else:
                        # اگر از قبل وجود داشت، فقط allow_print را True می‌کنیم
                        if not label_setting.allow_print:
                            label_setting.allow_print = True
                            label_setting.save()
                            print(f"   🔄 تنظیمات لیبل به‌روزرسانی شد: {product_name} - {branch.name}")
                            label_settings_updated.append(f"{product_name} در شعبه {branch.name} (فعال‌سازی)")
                        else:
                            print(f"   ℹ️  تنظیمات لیبل از قبل فعال بود: {product_name} - {branch.name}")

                except Exception as e:
                    print(f"   ❌ خطا در تنظیمات لیبل برای {product_name} - {branch.name}: {str(e)}")
                    continue

        # بخش ۴: صفر کردن remaining_quantity
        zeroed_count = all_items.update(remaining_quantity=0)
        print(f"🔄 {zeroed_count} آیتم صفر شد")

        # محاسبه آماری جدید
        total_for_each_branch = sum(product['total_remaining'] for product in products_to_distribute)
        total_for_all_branches = total_for_each_branch * branch_count

        # آماده‌سازی پیام موفقیت
        detail_message = "\n".join(distribution_details)

        # اطلاعات تنظیمات لیبل
        label_info = ""
        if label_settings_updated:
            unique_labels = set(label_settings_updated)
            label_info = f"\n🏷️  تنظیمات چاپ لیبل:\n• " + "\n• ".join(unique_labels)
        else:
            label_info = "\n🏷️  تنظیمات چاپ لیبل: هیچ تنظیماتی به‌روزرسانی نشد"

        messages.success(
            request,
            f'✅ توزیع کامل به همه شعب با موفقیت انجام شد!\n\n'
            f'📊 خلاصه عملکرد:\n'
            f'• تعداد کل کالاهای توزیع شده: {total_distributed:,} عدد\n'
            f'• تعداد کالاهای منحصر به فرد: {len(products_to_distribute)} مورد\n'
            f'• تعداد شعب: {branch_count} شعبه\n'
            f'• آیتم‌های به روز شده: {zeroed_count} مورد\n'
            f'• تنظیمات لیبل به‌روزرسانی شده: {len(set(label_settings_updated))} مورد\n'
            f'• تعداد برای هر شعبه: {total_for_each_branch:,} عدد\n'
            f'• مجموع همه شعب: {total_for_all_branches:,} عدد\n'
            f'{label_info}\n\n'
            f'📦 جزئیات توزیع:\n{detail_message}'
        )

        print(f"🎉 فرآیند توزیع با موفقیت پایان یافت. مجموع توزیع: {total_distributed:,} عدد")

    except Exception as e:
        print(f"❌ خطای کلی در distribute_inventory: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'❌ خطا در توزیع کالاها: {str(e)}')

    return redirect('invoice_list')
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
from account_app.models import ProductLabelSetting , LabelPrintItem



@require_POST
def clear_inventory(request):
    """
    پاک کردن تمام رکوردهای InventoryCount, ProductLabelSetting و LabelPrintItem
    """
    try:
        # حذف با ترتیب مناسب
        LabelPrintItem.objects.all().delete()
        ProductLabelSetting.objects.all().delete()
        deleted_count = InventoryCount.objects.all().delete()[0]

        messages.success(request, f"✅ تمام داده‌های انبار و تنظیمات چاپ با موفقیت پاک شدند.")
    except Exception as e:
        messages.error(request, f"❌ خطا در پاک کردن داده‌ها: {str(e)}")

    return redirect('invoice_list')