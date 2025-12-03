from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Sum
import json
from cantact_app.models import Branch
from dashbord_app.models import Invoice, InvoiceItem, Product, Froshande
from .models import *
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Sum
import json
from cantact_app.models import Branch
from dashbord_app.models import Invoice, InvoiceItem, Product, Froshande
from .models import *

def inventory_management(request):
    branches = Branch.objects.all()
    products = Product.objects.all()
    return render(request, 'inventory_management.html', {
        'branches': branches,
        'products': products
    })
#


# ----------------------------------------------------------------------
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q
import json
import logging
from .models import InventoryCount, Branch, Product
from .utils import convert_persian_arabic_to_english

logger = logging.getLogger(__name__)


def get_branches(request):
    try:
        branches = Branch.objects.all().values('id', 'name', 'address')
        return JsonResponse({
            'success': True,
            'branches': list(branches)
        })
    except Exception as e:
        logger.error(f"Error in get_branches: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در دریافت اطلاعات شعب'
        })


def search_products(request):
    try:
        query = request.GET.get('q', '')
        branch_id = request.GET.get('branch_id', '')

        # تبدیل اعداد فارسی/عربی به انگلیسی
        query_english = convert_persian_arabic_to_english(query)

        if len(query_english) < 2:
            return JsonResponse({'results': []})

        # جستجو در محصولات از مدل InventoryCount بدون در نظر گرفتن شعبه
        products_query = InventoryCount.objects.filter(
            Q(product_name__icontains=query_english) |
            Q(product_name__icontains=query)
        )

        # دریافت نام محصولات متمایز (بدون در نظر گرفتن شعبه)
        products = products_query.values_list('product_name', flat=True).distinct()[:10]

        results = []
        for product_name in products:
            results.append({
                'id': product_name,  # استفاده از نام محصول به عنوان ID
                'text': product_name,
                'type': 'product'
            })

        return JsonResponse({'results': results})

    except Exception as e:
        logger.error(f"Error in product search: {str(e)}")
        return JsonResponse({'results': []})
def check_product(request):
    try:
        product_name = request.GET.get('product_name', '')
        branch_id = request.GET.get('branch_id', '')

        if not product_name or not branch_id:
            return JsonResponse({
                'exists': False,
                'last_counts': []
            })

        # بررسی وجود محصول در انبار
        exists = InventoryCount.objects.filter(
            product_name=product_name,
            branch_id=branch_id
        ).exists()

        last_counts = []
        if exists:
            # دریافت تاریخچه شمارش‌های قبلی
            last_counts = InventoryCount.objects.filter(
                product_name=product_name,
                branch_id=branch_id
            ).order_by('-created_at')[:5].values('count_date', 'counter__username', 'quantity')

        return JsonResponse({
            'exists': exists,
            'last_counts': list(last_counts)
        })

    except Exception as e:
        logger.error(f"Error in check_product: {str(e)}")
        return JsonResponse({
            'exists': False,
            'last_counts': []
        })

@method_decorator(csrf_exempt, name='dispatch')
class UpdateInventoryCount(View):
    def post(self, request):
        try:
            # بررسی اینکه کاربر لاگین کرده است یا نه
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'لطفاً ابتدا وارد سیستم شوید'
                })

            data = json.loads(request.body)
            items = data.get('items', [])
            user = request.user

            # لاگ کردن اطلاعات دریافتی برای دیباگ
            logger.info(f"Received items: {items}")

            for item in items:
                # لاگ کردن هر آیتم برای دیباگ
                logger.info(f"Processing item: {item}")

                # ایجاد یا به روزرسانی رکورد شمارش
                inventory_count, created = InventoryCount.objects.update_or_create(
                    product_name=item['productName'],
                    branch_id=item['branchId'],
                    defaults={
                        'is_new': item.get('productType', 'new') == 'new',  # استفاده از get با مقدار پیشفرض
                        'quantity': item['quantity'],
                        'counter': user
                    }
                )
                # به روزرسانی ProductLabelSetting برای این محصول و شعبه
                try:
                    label_setting, created_label = ProductLabelSetting.objects.update_or_create(
                        product_name=item['productName'],
                        branch_id=item['branchId'],
                        defaults={
                            'barcode': inventory_count.barcode_data,
                            'allow_print': True  # تنظیم allow_print به True
                        }
                    )
                    logger.info(
                        f"ProductLabelSetting updated: {label_setting.product_name} - {label_setting.branch.name} - Allow Print: True")
                except Exception as e:
                    logger.error(f"Error updating ProductLabelSetting: {str(e)}")
            return JsonResponse({
                'success': True,
                'message': 'انبار با موفقیت به روزرسانی شد'
            })

        except Exception as e:
            logger.error(f"Error in update_inventory_count: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


# ------------------------------------------------------------------------------------------
# views.py
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import InventoryCount, Branch
from dashbord_app.models import Invoice, InvoiceItem, Froshande
from .utils import convert_persian_arabic_to_english
from django.shortcuts import render


@require_GET
def search_invoices(request):
    query = request.GET.get('q', '')

    if len(query) < 2:
        return JsonResponse({'results': []})

    # جستجو در شماره سریال و نام فروشنده
    invoices = Invoice.objects.filter(
        Q(serial_number__icontains=query) |
        Q(seller__name__icontains=query)  # اگر مدل Froshande فیلد name دارد
    )[:10]  # محدود کردن نتایج به 10 مورد

    results = []
    for invoice in invoices:
        results.append({
            'id': invoice.id,
            'serial_number': invoice.serial_number,
            'seller_name': str(invoice.seller),  # یا invoice.seller.name
            'date': invoice.jalali_date,
            'text': f"{invoice.serial_number} - {invoice.seller}"
        })

    return JsonResponse({'results': results})
# Get invoice details and items
def get_invoice_details(request):
    try:
        invoice_id = request.GET.get('invoice_id', '')

        if not invoice_id:
            return JsonResponse({'success': False, 'error': 'Invoice ID is required'})

        invoice = Invoice.objects.get(id=invoice_id)
        items = invoice.items.all()

        invoice_data = {
            'id': invoice.id,
            'serial_number': invoice.serial_number,
            'seller_name': f"{invoice.seller.name} {invoice.seller.family}",
            'date': invoice.jalali_date
        }

        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'selling_price': str(item.selling_price)
            })

        return JsonResponse({
            'success': True,
            'invoice': invoice_data,
            'items': items_data
        })

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'فاکتور یافت نشد'})
    except Exception as e:
        logger.error(f"Error getting invoice details: {str(e)}")
        return JsonResponse({'success': False, 'error': 'خطا در دریافت اطلاعات فاکتور'})
import sys
import arabic_reshaper
from bidi.algorithm import get_display
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

# تنظیم encoding پیشفرض به UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# تنظیمات reshaper برای فارسی
arabic_reshaper.configuration_for_arabic_letters = {
    'delete_harakat': False,
    'support_ligatures': True,
    'language': 'Farsi',
}

import sys
import arabic_reshaper



def persian_print(text):
    """تابع کمکی برای نمایش متن فارسی در کنسول"""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    print(bidi_text)

# تنظیمات reshaper برای فارسی
arabic_reshaper.configuration_for_arabic_letters = {
    'delete_harakat': False,
    'support_ligatures': True,
    'language': 'Farsi',
}
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
import json
import logging
from decimal import Decimal
from datetime import datetime

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.core.cache import cache
from decimal import Decimal
from datetime import datetime
from .models import InventoryCount, ProductPricing, Branch
from dashbord_app.models import Invoice, InvoiceItem
from account_app.models import FinancialDocument, FinancialDocumentItem


@method_decorator(csrf_exempt, name='dispatch')
class StoreInvoiceItems(View):
    @transaction.atomic
    def post(self, request):
        try:
            # بررسی توکن یکبار مصرف
            data = json.loads(request.body)
            request_id = data.get('request_id')

            if request_id:
                cache_key = f"invoice_request_{request_id}"
                if cache.get(cache_key):
                    return JsonResponse({'success': False, 'error': 'این درخواست قبلاً پردازش شده است'})
                cache.set(cache_key, True, timeout=300)

            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'لطفاً ابتدا وارد سیستم شوید'})

            items = data.get('items', [])
            invoice_id = data.get('invoice_id')

            if not invoice_id:
                return JsonResponse({'success': False, 'error': 'شناسه فاکتور الزامی است'})

            # دریافت اطلاعات فاکتور
            try:
                invoice = Invoice.objects.get(id=invoice_id)
                invoice_items = InvoiceItem.objects.filter(invoice=invoice)
            except Invoice.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'فاکتور یافت نشد'})

            # ایجاد دیکشنری برای جمع‌بندی مقادیر ذخیره‌شده برای هر محصول
            stored_quantities = {}
            for item in items:
                product_name = item.get('product_name')
                quantity = int(item.get('quantity', 0))
                if product_name in stored_quantities:
                    stored_quantities[product_name] += quantity
                else:
                    stored_quantities[product_name] = quantity

            # به روزرسانی مقدار remaining_quantity برای هر آیتم فاکتور
            for invoice_item in invoice_items:
                product_name = invoice_item.product_name
                if product_name in stored_quantities:
                    # کسر مقدار ثبت شده از مقدار باقیمانده
                    new_remaining = invoice_item.remaining_quantity - stored_quantities[product_name]
                    invoice_item.remaining_quantity = max(0, new_remaining)
                    invoice_item.save()

            # ایجاد یک دیکشنری برای ذخیره مقادیر هر محصول در هر شعبه
            product_branch_totals = {}
            print_data = {
                'invoice_number': invoice.serial_number if invoice else 'نامشخص',
                'items': {}
            }

            # مجموعه برای پیگیری محصولاتی که ProductPricing آنها به روز شده است
            processed_products = set()

            for item in items:
                branch_id = item.get('branch_id')
                quantity = int(item.get('quantity'))
                product_name = item.get('product_name')

                if not branch_id or not product_name:
                    continue

                try:
                    branch = Branch.objects.get(id=branch_id)
                except Branch.DoesNotExist:
                    print(f"Branch not found: {branch_id}")
                    return JsonResponse({'success': False, 'error': f'شعبه با شناسه {branch_id} یافت نشد'})

                # ایجاد کلید منحصر به فرد برای هر محصول در هر شعبه
                product_branch_key = f"{product_name}_{branch_id}"

                if product_branch_key not in product_branch_totals:
                    product_branch_totals[product_branch_key] = {
                        'product_name': product_name,
                        'branch': branch,
                        'quantity': quantity
                    }

                    # به روزرسانی موجودی انبار
                    try:
                        inventory_count = InventoryCount.objects.get(
                            product_name=product_name,
                            branch=branch
                        )
                        inventory_count.quantity += quantity
                        inventory_count.save()
                        print(f"Updated inventory for {product_name} in {branch.name}: +{quantity}")
                    except InventoryCount.DoesNotExist:
                        inventory_count = InventoryCount.objects.create(
                            product_name=product_name,
                            branch=branch,
                            quantity=quantity,
                            counter=request.user,
                            is_new=True
                        )

                    # به روزرسانی ProductPricing برای این محصول (فقط یک بار برای هر محصول)
                    if product_name not in processed_products:
                        self.update_product_pricing(product_name)
                        processed_products.add(product_name)

                else:
                    print(3)
                    product_branch_totals[product_branch_key]['quantity'] += quantity
                    inventory_count = InventoryCount.objects.get(
                        product_name=product_name,
                        branch=branch
                    )
                    inventory_count.quantity += quantity
                    inventory_count.save()
            # به روزرسانی ProductLabelSetting برای محصولات
            try:
                for item in items:
                    product_name = item.get('product_name')
                    branch_id = item.get('branch_id')

                    if product_name and branch_id:
                        # پیدا کردن یا ایجاد ProductLabelSetting
                        label_setting, created = ProductLabelSetting.objects.get_or_create(
                            product_name=product_name,
                            branch_id=branch_id,
                            defaults={
                                'barcode': item.get('barcode_data', ''),
                                'allow_print': True  # تنظیم allow_print به True
                            }
                        )

                        # اگر از قبل وجود داشت، allow_print را به True تنظیم کن
                        if not created:
                            label_setting.allow_print = True
                            label_setting.save()

                        print(f"✅ ProductLabelSetting به روز شد: {product_name} - شعبه {branch_id} - Allow Print: True")
            except Exception as e:
                print(f"❌ خطا در به روزرسانی ProductLabelSetting: {str(e)}")
            # تبدیل داده‌های موقت به فرمت مورد نیاز برای چاپ
            for key, data in product_branch_totals.items():
                product_name = data['product_name']
                branch = data['branch']
                quantity = data['quantity']

                if product_name not in print_data['items']:
                    print_data['items'][product_name] = {
                        'total': 0,
                        'branches': {}
                    }

                print_data['items'][product_name]['total'] += quantity

                if branch.name not in print_data['items'][product_name]['branches']:
                    print_data['items'][product_name]['branches'][branch.name] = 0
                print_data['items'][product_name]['branches'][branch.name] += quantity

            # ایجاد یا به روزرسانی سند مالی
            self.create_or_update_financial_document(invoice, invoice_items)

            # چاپ اطلاعات در کنسول
            self.print_invoice_data(print_data)

            # ذخیره اطلاعات برای استفاده در صفحه چاپ
            request.session['print_data'] = print_data

            print("All items processed successfully")
            return JsonResponse({
                'success': True,
                'message': 'اطلاعات انبار با موفقیت ثبت شد و مقادیر فاکتور به روز شدند',
                'print_url': '/account/print-invoice/'
            })

        except Exception as e:
            print(f"Error storing invoice items: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    def update_product_pricing(self, product_name):
        """
        به روزرسانی ProductPricing برای یک محصول خاص
        """
        try:
            # یافتن بالاترین قیمت واحد برای این محصول از InvoiceItem
            highest_price_item = InvoiceItem.objects.filter(
                product_name=product_name).order_by('-unit_price').first()

            if highest_price_item:
                print(f"بالاترین قیمت یافت شد: {highest_price_item.unit_price}")

                # یافتن فاکتور مربوطه
                invoice = highest_price_item.invoice

                # ایجاد یا به روزرسانی ProductPricing
                product_pricing, created = ProductPricing.objects.get_or_create(
                    product_name=product_name,
                    defaults={
                        'highest_purchase_price': highest_price_item.unit_price,
                        'invoice_date': invoice.jalali_date,
                        'invoice_number': invoice.serial_number,
                        'standard_price': highest_price_item.unit_price  # این خط جدید
                    }
                )

                if not created:
                    # اگر از قبل وجود داشت، به روزرسانی کن
                    product_pricing.highest_purchase_price = highest_price_item.unit_price
                    product_pricing.invoice_date = invoice.jalali_date
                    product_pricing.invoice_number = invoice.serial_number
                    product_pricing.standard_price = highest_price_item.unit_price
                    product_pricing.save()

                if created:
                    print(f"ایجاد شد ProductPricing جدید برای: {product_name}")
                else:
                    print(f"به روزرسانی شد ProductPricing برای: {product_name}")

            else:
                print(f"هیچ فاکتوری برای محصول {product_name} یافت نشد")
                # ایجاد ProductPricing با مقادیر پیشفرض اگر فاکتوری یافت نشد
                ProductPricing.objects.get_or_create(
                    product_name=product_name,
                    defaults={
                        'highest_purchase_price': Decimal('0'),
                        'standard_price': Decimal('0')
                    }
                )

        except Exception as e:
            print(f"خطا در به روزرسانی ProductPricing برای {product_name}: {str(e)}")
            import traceback
            traceback.print_exc()
    def update_invoice_remaining_quantities(self, invoice, print_data):
        """به روزرسانی مقادیر باقیمانده فاکتور بر اساس موجودی اضافه شده"""
        for invoice_item in invoice.items.all():
            product_name = invoice_item.product_name
            if product_name in print_data['items']:
                # محاسبه کل مقداری که به انبار اضافه شده
                total_stored = print_data['items'][product_name]['total']

                # به روزرسانی مقدار باقیمانده در فاکتور
                if hasattr(invoice_item, 'remaining_quantity'):
                    invoice_item.remaining_quantity = max(0, invoice_item.quantity - total_stored)
                    invoice_item.save()

    def create_or_update_financial_document(self, invoice, invoice_items):
        """ایجاد یا به روزرسانی سند مالی"""
        try:
            financial_doc, created = FinancialDocument.objects.get_or_create(
                invoice=invoice,
                defaults={
                    'document_date': datetime.now(),
                    'total_amount': Decimal('0'),
                    'paid_amount': Decimal('0'),
                    'status': 'unpaid'
                }
            )

            if not created:
                FinancialDocumentItem.objects.filter(document=financial_doc).delete()

            total_amount = Decimal('0')

            for item in invoice_items:
                price_before_discount = item.selling_price * item.quantity
                discount_amount = (price_before_discount * item.discount) / Decimal('100')
                final_price = price_before_discount - discount_amount

                FinancialDocumentItem.objects.create(
                    document=financial_doc,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                    total_price=final_price
                )

                total_amount += final_price

            financial_doc.total_amount = total_amount

            if financial_doc.paid_amount >= total_amount:
                financial_doc.status = 'settled'
            elif financial_doc.paid_amount > Decimal('0'):
                financial_doc.status = 'partially_paid'
            else:
                financial_doc.status = 'unpaid'

            financial_doc.save()
            print(f"Financial document {'created' if created else 'updated'}: {financial_doc.id}")

        except Exception as e:
            print(f"Error creating financial document: {str(e)}")
            import traceback
            traceback.print_exc()

    def print_invoice_data(self, print_data):
        """چاپ اطلاعات فاکتور در کنسول"""
        print("=" * 50)
        print(f"شماره فاکتور: {print_data['invoice_number']}")
        print("=" * 50)

        for product_name, data in print_data['items'].items():
            print(f"\nکالا: {product_name}")
            print(f"جمع کل: {data['total']}")
            print("توزیع بین شعب:")

            for branch_name, quantity in data['branches'].items():
                print(f"  - {branch_name}: {quantity}")

        print("\n" + "=" * 50)
        print("پایان گزارش")





def print_invoice_view(request):
    """ویو برای نمایش صفحه چاپ فاکتور"""
    print_data = request.session.get('print_data', {})

    if not print_data:
        return HttpResponse("داده‌ای برای چاپ موجود نیست")

    # رندر کردن template با داده‌های فاکتور
    html_content = render_to_string('print_invoice.html', {
        'print_data': print_data
    })

    return HttpResponse(html_content)


import sys
import arabic_reshaper
from bidi.algorithm import get_display
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
import json
import logging
from decimal import Decimal
from datetime import datetime

# تنظیم encoding پیشفرض به UTF-8
if sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')

# تنظیمات reshaper برای فارسی
arabic_reshaper.configuration_for_arabic_letters = {
    'delete_harakat': False,
    'support_ligatures': True,
    'language': 'Farsi',
}


def persian_print(text):
    """تابع کمکی برای نمایش متن فارسی در کنسول"""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        print(bidi_text)
    except Exception as e:
        # اگر خطایی رخ داد، متن را بدون تغییر چاپ کنید
        print(text)


# ---------------------------------------------------------------------------------------

def invoice_status(request, invoice_id):
    """نمایش وضعیت فاکتور و مقادیر باقیمانده"""
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        items = invoice.items.all()

        context = {
            'invoice': invoice,
            'items': items,
        }

        return render(request, 'invoice_status.html', context)

    except Invoice.DoesNotExist:
        return HttpResponse("فاکتور یافت نشد")


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from dashbord_app.models import Invoice, InvoiceItem
import json


@require_GET
def get_invoice_details(request):
    invoice_id = request.GET.get('invoice_id')
    try:
        invoice = Invoice.objects.get(id=invoice_id)

        # دریافت تمام آیتم‌های مربوط به این فاکتور
        items = invoice.items.all()

        # آماده کردن داده‌های آیتم‌ها برای ارسال به frontend
        items_data = []
        for item in items:
            items_data.append({
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'selling_price': str(item.selling_price),
                'discount': str(item.discount),
                'item_number': item.item_number,
                'location': item.location,
                'remaining_quantity': item.remaining_quantity,
            })

        # آماده کردن داده‌های پاسخ
        data = {
            'success': True,
            'invoice': {
                'id': invoice.id,
                'serial_number': invoice.serial_number,
                'seller_name': str(invoice.seller),  # یا invoice.seller.name اگر مدل Froshande فیلد name دارد
                'date': invoice.jalali_date,
            },
            'items': items_data
        }

        return JsonResponse(data)

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'فاکتور پیدا نشد'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ------------------------قیمت نهایی-------------------------------------------------

from django.http import JsonResponse
from django.db.models import Q
from decimal import Decimal
import math
import json
from django.views.decorators.csrf import csrf_exempt


def search_branches_pricing(request):
    """جستجوی شعب برای بخش قیمت‌گذاری"""
    query = request.GET.get('q', '')

    if len(query) < 2:
        return JsonResponse({'results': []})

    branches = Branch.objects.filter(
        Q(name__icontains=query) | Q(address__icontains=query)
    )[:10]

    results = []
    for branch in branches:
        results.append({
            'id': branch.id,
            'name': branch.name,
            'address': branch.address
        })

    return JsonResponse({'results': results})


def get_branch_products(request):
    """دریافت محصولات یک شعبه برای قیمت‌گذاری"""
    branch_id = request.GET.get('branch_id')

    if not branch_id:
        return JsonResponse({'error': 'Branch ID is required'}, status=400)

    try:
        # دریافت محصولات موجود در انبار شعبه
        inventory_items = InventoryCount.objects.filter(branch_id=branch_id)

        products_data = []
        for item in inventory_items:
            # دریافت قیمت معیار از مدل ProductPricing
            try:
                pricing = ProductPricing.objects.get(product_name=item.product_name)
                base_price = pricing.highest_purchase_price
            except ProductPricing.DoesNotExist:
                base_price = 0

            # استفاده از قیمت فروش ذخیره شده در InventoryCount
            selling_price = item.selling_price if item.selling_price is not None else 0

            # محاسبه درصد سود بر اساس قیمت خرید و فروش
            profit_percentage = 0
            if base_price and base_price > 0 and selling_price and selling_price > 0:
                profit_percentage = float(((selling_price - base_price) / base_price) * 100)

            products_data.append({
                'id': item.id,
                'product_name': item.product_name,
                'base_price': float(base_price) if base_price else 0,
                'profit_percentage': profit_percentage,
                'selling_price': float(selling_price) if selling_price else 0
            })

        return JsonResponse({'products': products_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def update_product_pricing(request):
    """به روزرسانی قیمت فروش و محاسبه خودکار درصد سود"""
    if request.method == 'POST':
        try:
            # بررسی اینکه کاربر لاگین کرده است
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'لطفاً ابتدا وارد سیستم شوید'})

            data = json.loads(request.body)
            product_name = data.get('product_name')
            branch_id = data.get('branch_id')
            selling_price = data.get('selling_price')  # دریافت قیمت فروش

            # اعتبارسنجی داده‌های ورودی
            if not all([product_name, branch_id, selling_price is not None]):
                return JsonResponse({'success': False, 'error': 'داده‌های ورودی ناقص است'})

            # تبدیل قیمت فروش به Decimal
            try:
                selling_price = Decimal(str(selling_price))
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'قیمت فروش نامعتبر است'})

            # دریافت قیمت خرید از ProductPricing
            try:
                pricing = ProductPricing.objects.get(product_name=product_name)
                base_price = pricing.highest_purchase_price
            except ProductPricing.DoesNotExist:
                base_price = Decimal('0')

            # محاسبه درصد سود بر اساس قیمت خرید و فروش
            profit_percentage = Decimal('0')
            if base_price and base_price > 0:
                profit_percentage = ((selling_price - base_price) / base_price) * 100

            # به روزرسانی قیمت فروش و درصد سود در InventoryCount
            try:
                inventory_item = InventoryCount.objects.get(
                    product_name=product_name,
                    branch_id=branch_id
                )

                inventory_item.selling_price = selling_price
                inventory_item.profit_percentage = profit_percentage
                inventory_item.save()

                return JsonResponse({
                    'success': True,
                    'message': 'اطلاعات با موفقیت ذخیره شد',
                    'profit_percentage': float(profit_percentage)
                })

            except InventoryCount.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'محصول در این شعبه یافت نشد'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'خطا در ذخیره اطلاعات: {str(e)}'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'داده‌های ارسالی نامعتبر است'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'خطای سرور: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'متد مجاز نیست'}, status=405)


@csrf_exempt
def update_all_product_pricing(request):
    """به روزرسانی کلیه قیمت‌های فروش و محاسبه خودکار درصد سود"""
    if request.method == 'POST':
        try:
            # بررسی اینکه کاربر لاگین کرده است
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'لطفاً ابتدا وارد سیستم شوید'})

            data = json.loads(request.body)
            branch_id = data.get('branch_id')
            prices = data.get('prices', [])

            # اعتبارسنجی داده‌های ورودی
            if not branch_id:
                return JsonResponse({'success': False, 'error': 'شناسه شعبه الزامی است'})

            # پردازش هر قیمت
            for price_data in prices:
                product_name = price_data.get('product_name')
                selling_price = price_data.get('selling_price')

                # رد کردن آیتم‌های ناقص
                if not all([product_name, selling_price is not None]):
                    continue

                # تبدیل قیمت فروش به Decimal
                try:
                    selling_price = Decimal(str(selling_price))
                except (ValueError, TypeError):
                    continue

                # دریافت قیمت خرید از ProductPricing
                try:
                    pricing = ProductPricing.objects.get(product_name=product_name)
                    base_price = pricing.highest_purchase_price
                except ProductPricing.DoesNotExist:
                    base_price = Decimal('0')

                # محاسبه درصد سود بر اساس قیمت خرید و فروش
                profit_percentage = Decimal('0')
                if base_price and base_price > 0:
                    profit_percentage = ((selling_price - base_price) / base_price) * 100

                # به روزرسانی قیمت فروش و درصد سود در InventoryCount
                try:
                    inventory_item = InventoryCount.objects.get(
                        product_name=product_name,
                        branch_id=branch_id
                    )

                    inventory_item.selling_price = selling_price
                    inventory_item.profit_percentage = profit_percentage
                    inventory_item.save()
                except InventoryCount.DoesNotExist:
                    continue
                except Exception as e:
                    # لاگ کردن خطا اما ادامه پردازش سایر آیتم‌ها
                    print(f"خطا در به روزرسانی محصول {product_name}: {str(e)}")
                    continue

            return JsonResponse({'success': True, 'message': 'همه اطلاعات با موفقیت ذخیره شدند'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'داده‌های ارسالی نامعتبر است'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'خطای سرور: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'متد مجاز نیست'}, status=405)


def pricing_management(request):
    """صفحه مدیریت قیمت‌گذاری"""
    return render(request, 'inventory_pricing.html')



# -------------------view----------------------------------

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.core.exceptions import ValidationError
import json

from .models import PaymentMethod
from .forms import PaymentMethodForm


def payment_method_list(request):
    payment_methods = PaymentMethod.objects.all()
    return render(request, 'payment_method_list.html', {
        'payment_methods': payment_methods
    })


def payment_method_create(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save()
            messages.success(request, f'روش پرداخت "{payment_method.name}" با موفقیت ایجاد شد')
            return redirect('account_app:payment_method_list')
    else:
        form = PaymentMethodForm()

    return render(request, 'payment_method_form.html', {
        'form': form,
        'title': 'ایجاد روش پرداخت جدید'
    })


def payment_method_update(request, pk):
    payment_method = get_object_or_404(PaymentMethod, pk=pk)

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=payment_method)
        if form.is_valid():
            payment_method = form.save()
            messages.success(request, f'روش پرداخت "{payment_method.name}" با موفقیت بروزرسانی شد')
            return redirect('account_app:payment_method_list')
    else:
        form = PaymentMethodForm(instance=payment_method)

    return render(request, 'payment_method_form.html', {
        'form': form,
        'title': 'ویرایش روش پرداخت',
        'payment_method': payment_method
    })


def payment_method_delete(request, pk):
    payment_method = get_object_or_404(PaymentMethod, pk=pk)

    if request.method == 'POST':
        method_name = payment_method.name
        payment_method.delete()
        messages.success(request, f'روش پرداخت "{method_name}" با موفقیت حذف شد')
        return redirect('account_app:payment_method_list')

    return render(request, 'payment_method_confirm_delete.html', {
        'payment_method': payment_method
    })


def payment_method_toggle_active(request, pk):
    payment_method = get_object_or_404(PaymentMethod, pk=pk)
    payment_method.is_active = not payment_method.is_active
    payment_method.save()

    action = "فعال" if payment_method.is_active else "غیرفعال"
    messages.success(request, f'روش پرداخت "{payment_method.name}" {action} شد')

    return redirect('account_app:payment_method_list')


def set_default_payment_method(request, pk):
    payment_method = get_object_or_404(PaymentMethod, pk=pk)

    # تمام روش‌ها را از حالت پیش فرض خارج کن
    PaymentMethod.objects.filter(is_default=True).update(is_default=False)

    # این روش را به پیش فرض تبدیل کن
    payment_method.is_default = True
    payment_method.save()

    messages.success(request, f'روش پرداخت "{payment_method.name}" به عنوان پیش فرض تنظیم شد')

    return redirect('account_app:payment_method_list')


def check_auth_status(request):
    return JsonResponse({
        'is_authenticated': False,  # همیشه false چون احراز هویت غیرفعال است
        'username': None,
        'session_key': request.session.session_key,
    })


def session_test(request):
    request.session['test_key'] = 'test_value'
    test_value = request.session.get('test_key', 'not_set')
    return HttpResponse(f"Session test: {test_value}")



# -------------------------------------------------------------------------
def search_branches_count(request):
    """جستجوی شعب برای بخش انبارگردانی"""
    query = request.GET.get('q', '')

    if len(query) < 2:
        return JsonResponse({'results': []})

    branches = Branch.objects.filter(
        Q(name__icontains=query) | Q(address__icontains=query)
    )[:10]

    results = []
    for branch in branches:
        results.append({
            'id': branch.id,
            'name': branch.name,
            'address': branch.address
        })

    return JsonResponse({'results': results})
def search_products_count(request):
    """جستجوی محصولات برای انبارگردانی - فقط محصولات شعبه انتخاب شده"""
    try:
        query = request.GET.get('q', '')
        branch_id = request.GET.get('branch_id', '')

        if len(query) < 2:
            return JsonResponse({'results': []})

        if not branch_id:
            return JsonResponse({'results': []})

        # جستجو فقط در محصولات شعبه انتخاب شده
        products_query = InventoryCount.objects.filter(
            Q(product_name__icontains=query) &
            Q(branch_id=branch_id)
        ).select_related('branch', 'counter')

        results = []
        for product in products_query:
            results.append({
                'id': product.id,
                'product_name': product.product_name,
                'branch_id': product.branch.id,
                'branch_name': product.branch.name,
                'current_quantity': product.quantity,
                'last_counter': product.counter.username if product.counter else 'نامشخص',
                'last_count_date': product.count_date,
                'text': f"{product.product_name} (موجودی: {product.quantity})"
            })

        return JsonResponse({'results': results})

    except Exception as e:
        logger.error(f"Error in product search for count: {str(e)}")
        return JsonResponse({'results': []})
def get_product_details(request):
    """دریافت اطلاعات کامل محصول برای نمایش تاریخچه"""
    try:
        product_name = request.GET.get('product_name', '')
        branch_id = request.GET.get('branch_id', '')

        if not product_name or not branch_id:
            return JsonResponse({
                'exists': False,
                'current_quantity': 0,
                'last_counts': []
            })

        # دریافت اطلاعات فعلی محصول
        current_product = InventoryCount.objects.filter(
            product_name=product_name,
            branch_id=branch_id
        ).first()

        # دریافت تاریخچه شمارش‌ها
        last_counts = InventoryCount.objects.filter(
            product_name=product_name,
            branch_id=branch_id
        ).order_by('-created_at')[:5].values(
            'count_date',
            'counter__username',
            'quantity',
            'created_at'
        )

        current_quantity = current_product.quantity if current_product else 0
        last_counter = current_product.counter.username if current_product and current_product.counter else 'نامشخص'
        last_count_date = current_product.count_date if current_product else 'نامشخص'

        return JsonResponse({
            'exists': current_product is not None,
            'current_quantity': current_quantity,
            'last_counter': last_counter,
            'last_count_date': last_count_date,
            'last_counts': list(last_counts)
        })

    except Exception as e:
        logger.error(f"Error in get_product_details: {str(e)}")
        return JsonResponse({
            'exists': False,
            'current_quantity': 0,
            'last_counts': []
        })


# ---------------------------------ثبت هزینه-------------------------------------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Expense, ExpenseImage
from .forms import ExpenseForm
from cantact_app.models import accuntmodel, Branch
import json


@login_required
def expense_create(request):
    try:
        user_profile = accuntmodel.objects.get(melicode=request.user.username)
    except accuntmodel.DoesNotExist:
        messages.error(request, 'پروفایل کاربری یافت نشد.')
        return redirect('home')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = user_profile
            expense.save()

            # مدیریت آپلود عکس‌ها - کاملاً اختیاری
            images = request.FILES.getlist('images')
            if images:
                for image in images:
                    if image.size > 5 * 1024 * 1024:
                        messages.warning(request, f'عکس {image.name} حجمش بسیار زیاد است و آپلود نشد.')
                        continue

                    try:
                        ExpenseImage.objects.create(expense=expense, image=image)
                    except Exception as e:
                        messages.warning(request, f'خطا در آپلود عکس {image.name}: {str(e)}')

            messages.success(request, 'هزینه با موفقیت ثبت شد.')
            return redirect('expense_list')  # بدون namespace
        else:
            messages.error(request, 'لطفا خطاهای زیر را اصلاح کنید.')
    else:
        form = ExpenseForm()

    branches = Branch.objects.all()

    context = {
        'form': form,
        'user_profile': user_profile,
        'branches': branches,
    }
    return render(request, 'expense_create.html', context)


@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    try:
        user_profile = accuntmodel.objects.get(melicode=request.user.username)
        if expense.user != user_profile:
            messages.error(request, 'شما دسترسی به این هزینه ندارید.')
            return redirect('expense_list')  # بدون namespace
    except accuntmodel.DoesNotExist:
        messages.error(request, 'پروفایل کاربری یافت نشد.')
        return redirect('home')

    context = {
        'expense': expense,
    }
    return render(request, 'expense_detail.html', context)


@login_required
def delete_expense_image(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_id = data.get('image_id')

            image = get_object_or_404(ExpenseImage, id=image_id)

            user_profile = accuntmodel.objects.get(melicode=request.user.username)
            if image.expense.user != user_profile:
                return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'})

            image.delete()
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})


@login_required
def expense_list(request):
    try:
        user_profile = accuntmodel.objects.get(melicode=request.user.username)
    except accuntmodel.DoesNotExist:
        messages.error(request, 'پروفایل کاربری یافت نشد.')
        return redirect('home')

    expenses = Expense.objects.filter(user=user_profile).order_by('-created_at')

    context = {
        'expenses': expenses,
        'user_profile': user_profile,
    }
    return render(request, 'expense_list.html', context)





@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    try:
        user_profile = accuntmodel.objects.get(melicode=request.user.username)
        if expense.user != user_profile:
            messages.error(request, 'شما دسترسی به این هزینه ندارید.')
            return redirect('expense_list')
    except accuntmodel.DoesNotExist:
        messages.error(request, 'پروفایل کاربری یافت نشد.')
        return redirect('home')

    if request.method == 'POST':
        expense_description = expense.description
        expense.delete()
        messages.success(request, f'هزینه "{expense_description}" با موفقیت حذف شد.')
        return redirect('expense_list')

    return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})


# account_app/views.py

# account_app/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q, Sum, Min
from .models import InventoryCount, Branch
import json
from .models import InventoryCount, ProductPricing, Branch

# تابع تبدیل اعداد فارسی و عربی به انگلیسی
def convert_persian_arabic_to_english(text):
    """تبدیل اعداد فارسی و عربی به انگلیسی"""
    persian_numbers = '۱۲۳۴۵۶۷۸۹۰'
    arabic_numbers = '١٢٣٤٥٦٧٨٩٠'
    english_numbers = '1234567890'

    for p, a, e in zip(persian_numbers, arabic_numbers, english_numbers):
        text = text.replace(p, e).replace(a, e)

    return text


# ----------------------- چاپ لیبل -----------------------


@login_required
def label_generator(request):
    """صفحه اصلی تولید لیبل - با ریست کردن سشن هنگام بارگذاری"""
    # پاک کردن سبد خرید لیبل از session هنگام بارگذاری صفحه
    if 'label_cart' in request.session:
        del request.session['label_cart']
        request.session.modified = True

    return render(request, 'account_app/label_generator.html')


@login_required
@require_GET
def get_branches_for_label(request):
    """دریافت لیست شعبه‌ها برای صفحه لیبل"""
    try:
        branches = Branch.objects.all().values('id', 'name')
        return JsonResponse({'branches': list(branches)})
    except Exception as e:
        return JsonResponse({'branches': [], 'error': str(e)})


@login_required
@require_GET
def get_branch_products_for_label(request):
    """دریافت محصولات یک شعبه خاص - فقط کالاهای مجاز برای چاپ"""
    try:
        branch_id = request.GET.get('branch_id')
        if not branch_id:
            return JsonResponse({'products': []})

        # دریافت محصولات این شعبه
        products = InventoryCount.objects.filter(
            branch_id=branch_id
        ).values(
            'product_name', 'barcode_data', 'selling_price'
        ).annotate(
            total_quantity=Sum('quantity')
        ).order_by('product_name')

        product_list = []
        for product in products:
            try:
                # بررسی وضعیت اجازه چاپ
                # اگر مدل وجود ندارد یا allow_print=false باشد، غیرفعال است
                allow_print = False
                try:
                    label_setting = ProductLabelSetting.objects.get(
                        product_name=product['product_name'],
                        branch_id=branch_id
                    )
                    allow_print = label_setting.allow_print
                except ProductLabelSetting.DoesNotExist:
                    # اگر مدل وجود ندارد، غیرفعال در نظر گرفته شود
                    allow_print = False

                # فقط کالاهای مجاز برای چاپ را اضافه کن
                if allow_print:
                    product_list.append({
                        'product_name': product['product_name'],
                        'barcode': product['barcode_data'] or 'ندارد',
                        'price': str(product['selling_price']) if product['selling_price'] else '0',
                        'quantity': product['total_quantity'] or 0,
                        'branch_id': branch_id,
                        'allow_print': allow_print
                    })

            except Exception as e:
                continue

        return JsonResponse({'products': product_list})

    except Exception as e:
        return JsonResponse({'products': [], 'error': str(e)})


@login_required
@require_GET
def search_products_for_label(request):
    """جستجوی محصولات برای لیبل - فقط کالاهای مجاز برای چاپ"""
    query = request.GET.get('q', '').strip()
    branch_id = request.GET.get('branch_id')

    if not branch_id:
        return JsonResponse({'results': []})

    try:
        # فیلتر بر اساس شعبه
        base_query = InventoryCount.objects.filter(branch_id=branch_id)

        # اگر کوئری وجود دارد جستجو می‌کنیم
        if query and len(query) >= 2:
            query_english = convert_persian_arabic_to_english(query)
            products = base_query.filter(
                Q(product_name__icontains=query_english) |
                Q(barcode_data__icontains=query_english)
            ).values(
                'product_name', 'barcode_data', 'selling_price'
            ).annotate(
                total_quantity=Sum('quantity')
            ).order_by('product_name')
        else:
            # همه محصولات این شعبه
            products = base_query.values(
                'product_name', 'barcode_data', 'selling_price'
            ).annotate(
                total_quantity=Sum('quantity')
            ).order_by('product_name')

        results = []
        for product in products:
            try:
                # بررسی وضعیت اجازه چاپ
                # اگر مدل وجود ندارد یا allow_print=false باشد، غیرفعال است
                allow_print = False
                try:
                    label_setting = ProductLabelSetting.objects.get(
                        product_name=product['product_name'],
                        branch_id=branch_id
                    )
                    allow_print = label_setting.allow_print
                except ProductLabelSetting.DoesNotExist:
                    # اگر مدل وجود ندارد، غیرفعال در نظر گرفته شود
                    allow_print = False

                # فقط کالاهای مجاز برای چاپ را اضافه کن
                if allow_print:
                    product_data = {
                        'product_name': product['product_name'],
                        'barcode': product['barcode_data'] or 'ندارد',
                        'price': str(product['selling_price']) if product['selling_price'] else '0',
                        'branch_id': branch_id,
                        'quantity': product['total_quantity'] or 0,
                        'allow_print': allow_print
                    }
                    results.append(product_data)

            except Exception as product_error:
                continue

        return JsonResponse({'results': results})

    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})


@login_required
@require_POST
def add_product_to_label_cart(request):
    """افزودن محصول به سبد لیبل - با چک مجوز چاپ"""
    try:
        data = json.loads(request.body)
        product_name = data.get('product_name')
        branch_id = data.get('branch_id')

        if not branch_id:
            return JsonResponse({'success': False, 'error': 'شعبه انتخاب نشده است'})

        # بررسی اجازه چاپ
        # اگر مدل وجود ندارد یا allow_print=false باشد، غیرفعال است
        allow_print = False
        try:
            label_setting = ProductLabelSetting.objects.get(
                product_name=product_name,
                branch_id=branch_id
            )
            allow_print = label_setting.allow_print
        except ProductLabelSetting.DoesNotExist:
            # اگر مدل وجود ندارد، غیرفعال در نظر گرفته شود
            allow_print = False

        if not allow_print:
            return JsonResponse({'success': False, 'error': 'این کالا برای چاپ غیرفعال شده است'})

        # بقیه کد مثل قبل...
        product_aggregate = InventoryCount.objects.filter(
            product_name=product_name,
            branch_id=branch_id
        ).aggregate(
            total_quantity=Sum('quantity'),
            first_barcode=Min('barcode_data'),
            first_price=Min('selling_price')
        )

        total_quantity = product_aggregate['total_quantity'] or 0

        if total_quantity == 0:
            return JsonResponse({'success': False, 'error': 'این کالا در انبار این شعبه موجود نیست'})

        price = str(product_aggregate['first_price']) if product_aggregate['first_price'] else '0'

        product_data = {
            'product_name': product_name,
            'barcode': product_aggregate['first_barcode'] or 'ندارد',
            'price': price,
            'quantity': total_quantity,
            'show_name': True,
            'show_price': True,
            'branch_id': branch_id
        }

        # ذخیره در سشن
        if 'label_cart' not in request.session:
            request.session['label_cart'] = []

        cart = request.session['label_cart']
        existing_index = next((i for i, item in enumerate(cart)
                               if item['product_name'] == product_name and item['branch_id'] == branch_id), -1)

        if existing_index >= 0:
            cart[existing_index]['quantity'] = total_quantity
        else:
            cart.append(product_data)

        request.session['label_cart'] = cart
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'cart_count': len(cart),
            'product_name': product_name,
            'quantity': total_quantity
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def remove_from_label_cart(request):
    """حذف محصول از سبد لیبل"""
    try:
        data = json.loads(request.body)
        product_name = data.get('product_name')

        cart = request.session.get('label_cart', [])
        cart = [item for item in cart if item['product_name'] != product_name]

        request.session['label_cart'] = cart
        request.session.modified = True

        return JsonResponse({'success': True, 'cart_count': len(cart)})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_GET
def get_label_cart(request):
    """دریافت سبد خرید لیبل - با اطمینان از خالی بودن هنگام بارگذاری اولیه"""
    cart = request.session.get('label_cart', [])

    # اگر سشن خالی است، مطمئن شویم که آرایه خالی برگردانده شود
    if not cart:
        request.session['label_cart'] = []
        request.session.modified = True

    return JsonResponse({'cart': cart})

@login_required
@require_POST
def update_cart_quantity(request):
    """به روزرسانی تعداد محصول در سبد خرید"""
    try:
        data = json.loads(request.body)
        product_name = data.get('product_name')
        quantity = int(data.get('quantity', 1))

        cart = request.session.get('label_cart', [])
        for item in cart:
            if item['product_name'] == product_name:
                item['quantity'] = max(1, quantity)
                break

        request.session['label_cart'] = cart
        request.session.modified = True

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def clear_label_cart(request):
    """پاک کردن کل سبد خرید"""
    request.session['label_cart'] = []
    request.session.modified = True
    return JsonResponse({'success': True})


@login_required
def label_settings(request):
    """صفحه تنظیمات لیبل - نسخه اصلاح شده"""
    cart = request.session.get('label_cart', [])

    if request.method == 'POST':
        print("🔍 POST Data:", dict(request.POST))  # برای دیباگ

        # لیست تمام محصولات در سبد خرید
        product_names = [item['product_name'] for item in cart]

        # به روزرسانی وضعیت نمایش برای هر محصول
        for product_name in product_names:
            for item in cart:
                if item['product_name'] == product_name:
                    # بررسی وضعیت نمایش نام
                    show_name_key = f'show_name_{product_name}'
                    if show_name_key in request.POST:
                        item['show_name'] = True
                        print(f"✅ نمایش نام برای {product_name}: True")
                    else:
                        item['show_name'] = False
                        print(f"❌ نمایش نام برای {product_name}: False")

                    # بررسی وضعیت نمایش قیمت
                    show_price_key = f'show_price_{product_name}'
                    if show_price_key in request.POST:
                        item['show_price'] = True
                        print(f"✅ نمایش قیمت برای {product_name}: True")
                    else:
                        item['show_price'] = False
                        print(f"❌ نمایش قیمت برای {product_name}: False")
                    break

        # ذخیره تغییرات در سشن
        request.session['label_cart'] = cart
        request.session.modified = True

        print("🔍 سبد خرید بعد از به روزرسانی:", cart)  # برای دیباگ
        return redirect('label_print')

    return render(request, 'account_app/label_settings.html', {'cart': cart})


@login_required
def label_print(request):
    """صفحه چاپ لیبل - با ثبت تاریخچه و تغییر وضعیت به false فقط در صورت POST"""
    cart = request.session.get('label_cart', [])

    # ایجاد لیست کامل لیبل‌ها
    all_labels = []
    for item in cart:
        for i in range(item['quantity']):
            all_labels.append(item)

    total_labels = len(all_labels)

    if request.method == 'POST':
        # ثبت تاریخچه چاپ و تغییر وضعیت به false فقط هنگام POST
        if cart:
            try:
                for item in cart:
                    product_name = item['product_name']
                    branch_id = item.get('branch_id')

                    if branch_id:
                        try:
                            # پیدا کردن یا ایجاد تنظیمات کالا
                            label_setting, created = ProductLabelSetting.objects.get_or_create(
                                product_name=product_name,
                                branch_id=branch_id,
                                defaults={
                                    'barcode': item.get('barcode', ''),
                                    'allow_print': True  # پیش‌فرض true
                                }
                            )

                            # ایجاد آیتم تاریخچه
                            LabelPrintItem.objects.create(
                                label_setting=label_setting,
                                print_quantity=item['quantity'],
                                user=request.user
                            )

                            # تغییر وضعیت اجازه چاپ به false
                            label_setting.allow_print = False
                            label_setting.save()

                            print(f"✅ ثبت چاپ و غیرفعال کردن: {product_name}")

                        except Exception as e:
                            print(f"❌ خطا در ثبت برای {product_name}: {e}")

            except Exception as e:
                print(f"❌ خطا در ثبت تاریخچه چاپ: {e}")

        # پس از ثبت، همان صفحه را رندر می‌کنیم تا چاپ انجام شود
        return render(request, 'account_app/label_print.html', {
            'all_labels': all_labels,
            'total_labels': total_labels,
            'auto_print': True  # فلگ برای چاپ خودکار
        })

    # اگر GET باشد، فقط صفحه را نمایش می‌دهیم بدون ثبت تاریخچه
    return render(request, 'account_app/label_print.html', {
        'all_labels': all_labels,
        'total_labels': total_labels,
        'auto_print': False
    })

# ویوهای کمکی برای template tags
def get_label_range(value):
    """تولید range برای template (برای استفاده در template tags)"""
    return range(int(value))


# ------------------------------------------------------برای تعین درصد تعدیل----------------------------------------
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max, Count
import json
from decimal import Decimal
import time
from django.utils import timezone
from django.db import transaction

# Import مدل‌های خودتان
from .models import ProductPricing, InventoryCount, Branch, ProductLabelSetting, Product, LabelPrintItem
from django.contrib.auth.models import User


@require_http_methods(["GET"])
def product_pricing_list(request):
    """صفحه اصلی نمایش لیست قیمت‌گذاری محصولات"""
    return render(request, 'account_app/product_pricing_list.html')


@require_http_methods(["GET"])
def health_check(request):
    """بررسی سلامت سرور"""
    return JsonResponse({
        'status': 'success',
        'message': 'سرور در دسترس است',
        'timestamp': timezone.now().isoformat()
    })


@require_http_methods(["GET"])
def debug_products(request):
    """تست سریع برای عیب‌یابی عملکرد"""
    start_time = time.time()

    try:
        # تست تعداد محصولات
        product_count = ProductPricing.objects.count()

        # تست تعداد شعب
        branch_count = Branch.objects.count()

        # تست تعداد موجودی‌ها
        inventory_count = InventoryCount.objects.count()

        # تست تعداد تنظیمات چاپ لیبل
        label_count = ProductLabelSetting.objects.count()

        end_time = time.time()
        response_time = end_time - start_time

        return JsonResponse({
            'status': 'success',
            'metrics': {
                'product_count': product_count,
                'branch_count': branch_count,
                'inventory_count': inventory_count,
                'label_count': label_count,
                'response_time_seconds': round(response_time, 2)
            },
            'message': f'پاسخ در {response_time:.2f} ثانیه'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_all_products(request):
    """دریافت تمام محصولات - نسخه بهینه‌شده"""
    try:
        # دریافت صفحه از پارامترهای URL
        page = int(request.GET.get('page', 1))
        per_page = 50  # محدود کردن تعداد در هر درخواست

        start = (page - 1) * per_page
        end = start + per_page

        # دریافت تعداد کل محصولات برای آمار
        total_products = ProductPricing.objects.count()

        # دریافت تمام شعب
        branches = Branch.objects.all()
        branch_dict = {branch.id: branch for branch in branches}

        # دریافت محصولات با محدودیت
        products = ProductPricing.objects.all().order_by('product_name')[start:end]

        # اگر محصولی نداریم، خالی برگردان
        if not products.exists():
            return JsonResponse({
                'products': [],
                'branches': [{'id': b.id, 'name': b.name} for b in branches],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'has_next': False,
                    'total_products': total_products
                }
            })

        # پیش‌پردازش داده‌های InventoryCount برای بهینه‌سازی
        product_names = [p.product_name for p in products]

        # دریافت آخرین موجودی برای هر محصول و شعبه
        latest_inventories = InventoryCount.objects.filter(
            product_name__in=product_names
        ).values('product_name', 'branch').annotate(
            latest_created=Max('created_at')
        )

        # دریافت تنظیمات چاپ لیبل برای هر محصول و شعبه
        label_settings = ProductLabelSetting.objects.filter(
            product_name__in=product_names
        ).select_related('branch')

        # ایجاد دیکشنری برای تنظیمات چاپ لیبل
        label_dict = {}
        for label in label_settings:
            key = f"{label.product_name}_{label.branch.id}"
            label_dict[key] = {
                'allow_print': label.allow_print,
                'print_count': LabelPrintItem.objects.filter(label_setting=label).count()
            }

        # ایجاد lookup برای سریع‌تر کردن دسترسی
        inventory_lookup = {}
        for inv in latest_inventories:
            key = f"{inv['product_name']}_{inv['branch']}"
            inventory_lookup[key] = inv['latest_created']

        # دریافت داده‌های کامل برای آخرین موجودی‌ها
        latest_dates = list(inventory_lookup.values())
        if latest_dates:
            actual_inventories = InventoryCount.objects.filter(
                created_at__in=latest_dates
            ).select_related('branch')
        else:
            actual_inventories = InventoryCount.objects.none()

        # ایجاد دیکشنری برای دسترسی سریع
        inventory_dict = {}
        for inv in actual_inventories:
            key = f"{inv.product_name}_{inv.branch.id}"
            inventory_dict[key] = inv

        results = []
        for product in products:
            product_data = {
                'id': product.id,
                'product_name': product.product_name,
                'highest_purchase_price': float(
                    product.highest_purchase_price) if product.highest_purchase_price else 0,
                'invoice_date': product.invoice_date.strftime('%Y-%m-%d') if product.invoice_date else '',
                'invoice_number': product.invoice_number or '',
                'adjustment_percentage': float(product.adjustment_percentage) if product.adjustment_percentage else 0,
                'standard_price': float(product.standard_price) if product.standard_price else 0,
                'created_at': product.created_at.strftime('%Y-%m-%d %H:%M') if product.created_at else '',
                'updated_at': product.updated_at.strftime('%Y-%m-%d %H:%M') if product.updated_at else '',
                'branch_prices': {}
            }

            # پر کردن داده‌های شعب
            for branch in branches:
                lookup_key = f"{product.product_name}_{branch.id}"
                inventory = inventory_dict.get(lookup_key)

                # بررسی وضعیت چاپ لیبل از دیکشنری
                label_info = label_dict.get(lookup_key, {'allow_print': False, 'print_count': 0})

                if inventory:
                    product_data['branch_prices'][branch.id] = {
                        'branch_name': branch.name,
                        'selling_price': inventory.selling_price if inventory.selling_price else 0,
                        'quantity': inventory.quantity,
                        'profit_percentage': float(
                            inventory.profit_percentage) if inventory.profit_percentage else 70.0,
                        'allow_print': label_info['allow_print'],
                        'print_count': label_info['print_count']
                    }
                else:
                    product_data['branch_prices'][branch.id] = {
                        'branch_name': branch.name,
                        'selling_price': 0,
                        'quantity': 0,
                        'profit_percentage': 70.0,
                        'allow_print': label_info['allow_print'],
                        'print_count': label_info['print_count']
                    }

            results.append(product_data)

        return JsonResponse({
            'products': results,
            'branches': [{'id': b.id, 'name': b.name} for b in branches],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'has_next': len(results) == per_page,
                'total_products': total_products
            }
        })

    except Exception as e:
        import traceback
        print(f"❌ خطا در get_all_products: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'خطا در پردازش: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def search_products(request):
    """جستجوی محصولات - نسخه بهینه‌شده"""
    try:
        query = request.GET.get('q', '').strip()

        if len(query) < 2:
            return JsonResponse({'results': [], 'branches': []})

        # محدود کردن نتایج جستجو
        products = ProductPricing.objects.filter(
            product_name__icontains=query
        ).order_by('product_name')[:20]

        branches = Branch.objects.all()
        branch_dict = {branch.id: branch for branch in branches}

        # اگر محصولی پیدا نشد
        if not products.exists():
            return JsonResponse({
                'results': [],
                'branches': [{'id': b.id, 'name': b.name} for b in branches]
            })

        # پیش‌پردازش داده‌های InventoryCount برای بهینه‌سازی
        product_names = [p.product_name for p in products]

        # دریافت آخرین موجودی برای هر محصول و شعبه
        latest_inventories = InventoryCount.objects.filter(
            product_name__in=product_names
        ).values('product_name', 'branch').annotate(
            latest_created=Max('created_at')
        )

        # دریافت تنظیمات چاپ لیبل برای هر محصول و شعبه
        label_settings = ProductLabelSetting.objects.filter(
            product_name__in=product_names
        ).select_related('branch')

        # ایجاد دیکشنری برای تنظیمات چاپ لیبل
        label_dict = {}
        for label in label_settings:
            key = f"{label.product_name}_{label.branch.id}"
            label_dict[key] = {
                'allow_print': label.allow_print,
                'print_count': LabelPrintItem.objects.filter(label_setting=label).count()
            }

        # ایجاد lookup برای سریع‌تر کردن دسترسی
        inventory_lookup = {}
        for inv in latest_inventories:
            key = f"{inv['product_name']}_{inv['branch']}"
            inventory_lookup[key] = inv['latest_created']

        # دریافت داده‌های کامل برای آخرین موجودی‌ها
        latest_dates = list(inventory_lookup.values())
        if latest_dates:
            actual_inventories = InventoryCount.objects.filter(
                created_at__in=latest_dates
            ).select_related('branch')
        else:
            actual_inventories = InventoryCount.objects.none()

        # ایجاد دیکشنری برای دسترسی سریع
        inventory_dict = {}
        for inv in actual_inventories:
            key = f"{inv.product_name}_{inv.branch.id}"
            inventory_dict[key] = inv

        results = []
        for product in products:
            product_data = {
                'id': product.id,
                'product_name': product.product_name,
                'highest_purchase_price': float(
                    product.highest_purchase_price) if product.highest_purchase_price else 0,
                'invoice_date': product.invoice_date.strftime('%Y-%m-%d') if product.invoice_date else '',
                'invoice_number': product.invoice_number or '',
                'adjustment_percentage': float(product.adjustment_percentage) if product.adjustment_percentage else 0,
                'standard_price': float(product.standard_price) if product.standard_price else 0,
                'created_at': product.created_at.strftime('%Y-%m-%d %H:%M') if product.created_at else '',
                'updated_at': product.updated_at.strftime('%Y-%m-%d %H:%M') if product.updated_at else '',
                'branch_prices': {}
            }

            for branch in branches:
                lookup_key = f"{product.product_name}_{branch.id}"
                inventory = inventory_dict.get(lookup_key)

                # بررسی وضعیت چاپ لیبل از دیکشنری
                label_info = label_dict.get(lookup_key, {'allow_print': False, 'print_count': 0})

                if inventory:
                    product_data['branch_prices'][branch.id] = {
                        'branch_name': branch.name,
                        'selling_price': inventory.selling_price if inventory.selling_price else 0,
                        'quantity': inventory.quantity,
                        'profit_percentage': float(
                            inventory.profit_percentage) if inventory.profit_percentage else 70.0,
                        'allow_print': label_info['allow_print'],
                        'print_count': label_info['print_count']
                    }
                else:
                    product_data['branch_prices'][branch.id] = {
                        'branch_name': branch.name,
                        'selling_price': 0,
                        'quantity': 0,
                        'profit_percentage': 70.0,
                        'allow_print': label_info['allow_print'],
                        'print_count': label_info['print_count']
                    }

            results.append(product_data)

        return JsonResponse({
            'results': results,
            'branches': [{'id': b.id, 'name': b.name} for b in branches],
            'pagination': {
                'total_products': len(results)
            }
        })

    except Exception as e:
        import traceback
        print(f"❌ خطا در search_products: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_adjustment_percentage(request):
    """بروزرسانی درصد تعدیل و محاسبه قیمت معیار و فعال کردن چاپ لیبل"""
    try:
        data = json.loads(request.body)
        product_name = data.get('product_name')
        adjustment_percentage = data.get('adjustment_percentage')

        print(f"🔄 به‌روزرسانی درصد تعدیل برای محصول {product_name}: {adjustment_percentage}%")

        # اعتبارسنجی داده‌ها
        if not product_name:
            return JsonResponse({'error': 'نام محصول الزامی است'}, status=400)

        try:
            adjustment_percentage = float(adjustment_percentage)
            if adjustment_percentage < 0 or adjustment_percentage > 100:
                return JsonResponse({'error': 'درصد تعدیل باید بین 0 تا 100 باشد'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'درصد تعدیل باید عدد معتبر باشد'}, status=400)

        # پیدا کردن محصول
        try:
            product = ProductPricing.objects.get(product_name=product_name)
        except ProductPricing.DoesNotExist:
            return JsonResponse({'error': 'محصول یافت نشد'}, status=404)

        # ذخیره درصد تعدیل قبلی برای مقایسه
        old_adjustment_percentage = product.adjustment_percentage

        # بروزرسانی درصد تعدیل با استفاده از atomic transaction
        with transaction.atomic():
            # بروزرسانی درصد تعدیل
            product.adjustment_percentage = Decimal(str(adjustment_percentage))

            # محاسبه قیمت معیار جدید
            if product.highest_purchase_price:
                adjustment_amount = product.highest_purchase_price * (Decimal(str(adjustment_percentage)) / 100)
                product.standard_price = product.highest_purchase_price + adjustment_amount

            # ذخیره محصول
            product.save()

            updated_count = 0

            # اگر درصد تعدیل تغییر کرده باشد
            if old_adjustment_percentage != product.adjustment_percentage:
                print(
                    f"📊 درصد تعدیل برای {product_name} از {old_adjustment_percentage} به {product.adjustment_percentage} تغییر کرد")

                # پیدا کردن تمام تنظیمات چاپ لیبل برای این محصول
                label_settings = ProductLabelSetting.objects.filter(product_name=product_name)

                for label_setting in label_settings:
                    if not label_setting.allow_print:
                        label_setting.allow_print = True
                        label_setting.save()
                        updated_count += 1
                        print(f"✅ تنظیمات چاپ لیبل برای {product_name} در شعبه {label_setting.branch.name} فعال شد")

                # اگر تنظیمات چاپ لیبلی برای این محصول وجود نداشت، برای تمام شعب ایجاد کن
                if updated_count == 0:
                    # پیدا کردن تمام شعب
                    branches = Branch.objects.all()

                    # دریافت بارکد محصول از مدل Product (اگر وجود دارد)
                    try:
                        product_obj = Product.objects.filter(name=product_name).first()
                        barcode = product_obj.barcode if product_obj and hasattr(product_obj, 'barcode') else ''
                    except:
                        barcode = ''

                    for branch in branches:
                        # ایجاد تنظیمات چاپ لیبل جدید
                        label_setting, created = ProductLabelSetting.objects.get_or_create(
                            product_name=product_name,
                            branch=branch,
                            defaults={
                                'barcode': barcode,
                                'allow_print': True
                            }
                        )

                        if created:
                            updated_count += 1
                            print(f"✅ تنظیمات چاپ لیبل جدید برای {product_name} در شعبه {branch.name} ایجاد شد")
                        elif not label_setting.allow_print:
                            label_setting.allow_print = True
                            label_setting.save()
                            updated_count += 1
                            print(f"✅ تنظیمات چاپ لیبل برای {product_name} در شعبه {branch.name} فعال شد")

                print(f"📝 تعداد {updated_count} تنظیمات چاپ لیبل برای محصول {product_name} فعال شدند")

        # محاسبه قیمت معیار جدید
        new_standard_price = product.standard_price

        return JsonResponse({
            'success': True,
            'new_standard_price': float(new_standard_price) if new_standard_price else 0,
            'message': 'درصد تعدیل با موفقیت بروزرسانی شد',
            'print_settings_updated': updated_count,
            'product_name': product_name
        })

    except Exception as e:
        import traceback
        print(f"❌ خطا در بروزرسانی درصد تعدیل: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def bulk_update_adjustment_percentage(request):
    """بروزرسانی درصد تعدیل برای چندین محصول به صورت گروهی"""
    try:
        data = json.loads(request.body)
        product_names = data.get('product_names', [])
        adjustment_percentage = data.get('adjustment_percentage')

        print(f"🔄 بروزرسانی گروهی درصد تعدیل برای {len(product_names)} محصول: {adjustment_percentage}%")

        # اعتبارسنجی داده‌ها
        if not product_names or len(product_names) == 0:
            return JsonResponse({'error': 'لیست محصولات الزامی است'}, status=400)

        try:
            adjustment_percentage = float(adjustment_percentage)
            if adjustment_percentage < 0 or adjustment_percentage > 100:
                return JsonResponse({'error': 'درصد تعدیل باید بین 0 تا 100 باشد'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'درصد تعدیل باید عدد معتبر باشد'}, status=400)

        results = []
        total_updated = 0

        # بروزرسانی هر محصول
        for product_name in product_names:
            try:
                product = ProductPricing.objects.get(product_name=product_name)
                old_adjustment_percentage = product.adjustment_percentage

                # بروزرسانی درصد تعدیل
                product.adjustment_percentage = Decimal(str(adjustment_percentage))

                # محاسبه قیمت معیار جدید
                if product.highest_purchase_price:
                    adjustment_amount = product.highest_purchase_price * (Decimal(str(adjustment_percentage)) / 100)
                    product.standard_price = product.highest_purchase_price + adjustment_amount

                # ذخیره محصول
                product.save()

                # فعال کردن چاپ لیبل
                label_updated_count = 0
                if old_adjustment_percentage != product.adjustment_percentage:
                    label_settings = ProductLabelSetting.objects.filter(product_name=product_name)

                    for label_setting in label_settings:
                        if not label_setting.allow_print:
                            label_setting.allow_print = True
                            label_setting.save()
                            label_updated_count += 1

                results.append({
                    'product_name': product_name,
                    'success': True,
                    'new_standard_price': float(product.standard_price) if product.standard_price else 0,
                    'label_settings_updated': label_updated_count
                })
                total_updated += 1

            except ProductPricing.DoesNotExist:
                results.append({
                    'product_name': product_name,
                    'success': False,
                    'error': 'محصول یافت نشد'
                })
            except Exception as e:
                results.append({
                    'product_name': product_name,
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({
            'success': True,
            'total_updated': total_updated,
            'total_attempted': len(product_names),
            'results': results,
            'message': f'درصد تعدیل {adjustment_percentage}% برای {total_updated} از {len(product_names)} محصول اعمال شد'
        })

    except Exception as e:
        import traceback
        print(f"❌ خطا در بروزرسانی گروهی درصد تعدیل: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)