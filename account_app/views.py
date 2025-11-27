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
                        print(100000000000000000000000000000000222222222222)
                        inventory_count = InventoryCount.objects.get(
                            product_name=product_name,
                            branch=branch
                        )
                        print(11)
                        inventory_count.quantity += quantity
                        print(111)
                        inventory_count.save()
                        print(1111)
                        print(f"Updated inventory for {product_name} in {branch.name}: +{quantity}")
                    except InventoryCount.DoesNotExist:
                        print(888888)
                        print(quantity)
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


# ----------------------------------چاپ لیبل--------------------------------------------------------
# account_app/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from .models import InventoryCount, ProductPricing
import json
import jdatetime


def convert_persian_arabic_to_english(text):
    """تبدیل اعداد فارسی و عربی به انگلیسی"""
    persian_numbers = '۱۲۳۴۵۶۷۸۹۰'
    arabic_numbers = '١٢٣٤٥٦٧٨٩٠'
    english_numbers = '1234567890'

    for p, a, e in zip(persian_numbers, arabic_numbers, english_numbers):
        text = text.replace(p, e).replace(a, e)

    return text


@login_required
def label_generator(request):
    """صفحه اصلی تولید لیبل"""
    return render(request, 'account_app/label_generator.html')


# account_app/views.py
@login_required
@require_GET
def search_products_for_label(request):
    """جستجوی محصولات برای لیبل - نسخه اصلاح شده"""
    query = request.GET.get('q', '').strip()

    print(f"🔍 جستجوی محصولات: '{query}'")

    if len(query) < 2:
        return JsonResponse({'results': []})

    try:
        # تبدیل اعداد فارسی و عربی به انگلیسی
        query_english = convert_persian_arabic_to_english(query)
        print(f"🔢 کوئری تبدیل شده: '{query_english}'")

        # جستجو در نام کالا و بارکد - نسخه ایمن‌تر
        from django.db.models import Q

        # ابتدا محصولات منحصربه‌فرد را پیدا کنیم
        product_names = InventoryCount.objects.filter(
            Q(product_name__icontains=query_english) |
            Q(barcode_data__icontains=query_english)
        ).values_list('product_name', flat=True).distinct()

        print(f"✅ تعداد محصولات منحصربه‌فرد: {len(product_names)}")

        results = []
        for product_name in product_names[:50]:  # محدودیت برای عملکرد
            try:
                # اولین نمونه از هر محصول را بگیریم
                product = InventoryCount.objects.filter(
                    product_name=product_name
                ).select_related('branch').first()

                if not product:
                    continue

                # دریافت قیمت
                try:
                    pricing = ProductPricing.objects.filter(
                        product_name=product_name
                    ).first()
                    price = pricing.standard_price if pricing else 0
                except Exception as pricing_error:
                    print(f"⚠️ خطا در دریافت قیمت برای {product_name}: {pricing_error}")
                    price = 0

                product_data = {
                    'product_name': product_name,
                    'barcode': product.barcode_data or 'ندارد',
                    'price': str(price) if price else '0',
                    'branch': product.branch.name if product and product.branch else 'نامشخص'
                }
                results.append(product_data)

            except Exception as product_error:
                print(f"❌ خطا در پردازش محصول {product_name}: {product_error}")
                continue

        print(f"📊 نتایج نهایی: {len(results)} آیتم")
        return JsonResponse({'results': results})

    except Exception as e:
        print(f"❌ خطای کلی در جستجو: {e}")
        import traceback
        print(f"📋 جزئیات خطا: {traceback.format_exc()}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
@require_POST
def add_product_to_label_cart(request):
    """افزودن محصول به سبد لیبل"""
    try:
        data = json.loads(request.body)
        product_name = data.get('product_name')

        # دریافت اطلاعات محصول
        product = InventoryCount.objects.filter(product_name=product_name).first()
        if not product:
            return JsonResponse({'success': False, 'error': 'کالا یافت نشد'})

        try:
            pricing = ProductPricing.objects.get(product_name=product_name)
            price = str(pricing.standard_price) if pricing.standard_price else '0'
        except ProductPricing.DoesNotExist:
            price = '0'

        product_data = {
            'product_name': product_name,
            'barcode': product.barcode_data,
            'price': price,
            'quantity': 1,  # تعداد پیش‌فرض
            'show_name': True,
            'show_price': True
        }

        # ذخیره در سشن
        if 'label_cart' not in request.session:
            request.session['label_cart'] = []

        # بررسی وجود تکراری
        cart = request.session['label_cart']
        existing_index = next((i for i, item in enumerate(cart) if item['product_name'] == product_name), -1)

        if existing_index >= 0:
            cart[existing_index]['quantity'] += 1
        else:
            cart.append(product_data)

        request.session['label_cart'] = cart
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'cart_count': len(cart),
            'product_name': product_name
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
    """دریافت سبد خرید لیبل"""
    cart = request.session.get('label_cart', [])
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
                item['quantity'] = max(1, quantity)  # حداقل 1
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
    """صفحه تنظیمات لیبل"""
    cart = request.session.get('label_cart', [])

    if request.method == 'POST':
        # پردازش تنظیمات
        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                product_name = key.replace('quantity_', '')
                for item in cart:
                    if item['product_name'] == product_name:
                        try:
                            item['quantity'] = int(value)
                        except (ValueError, TypeError):
                            item['quantity'] = 1

            elif key.startswith('show_name_'):
                product_name = key.replace('show_name_', '')
                for item in cart:
                    if item['product_name'] == product_name:
                        item['show_name'] = (value == 'on')

            elif key.startswith('show_price_'):
                product_name = key.replace('show_price_', '')
                for item in cart:
                    if item['product_name'] == product_name:
                        item['show_price'] = (value == 'on')

        request.session['label_cart'] = cart
        request.session.modified = True

        return redirect('label_print')

    return render(request, 'account_app/label_settings.html', {'cart': cart})


@login_required
def label_print(request):
    """صفحه چاپ لیبل - نسخه کامل"""
    cart = request.session.get('label_cart', [])

    # ایجاد لیست کامل از تمام لیبل‌هایی که باید چاپ شوند
    all_labels = []
    for item in cart:
        for i in range(item['quantity']):
            all_labels.append(item)

    # اگر سبد خالی است، یک آیتم نمونه ایجاد کنیم
    if not all_labels:
        all_labels = [{
            'product_name': 'محصول نمونه',
            'barcode': '123456789012',
            'price': '10000',
            'show_name': True,
            'show_price': True
        }]

    total_labels = len(all_labels)

    return render(request, 'account_app/label_print.html', {
        'all_labels': all_labels,
        'total_labels': total_labels
    })

# ویوهای کمکی برای template tags
def get_label_range(value):
    """تولید range برای template (برای استفاده در template tags)"""
    return range(int(value))