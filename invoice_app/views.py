# در بالای views.py - بخش importها
import requests  # 🔴 این خط را اضافه کنید
import json
import http.client
import socket
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.utils import timezone
from decimal import Decimal
import jdatetime
from datetime import datetime

from account_app.models import InventoryCount, Branch, ProductPricing
from .models import Invoicefrosh, InvoiceItemfrosh, POSDevice, CheckPayment, CreditPayment
from .forms import BranchSelectionForm, POSDeviceForm, CheckPaymentForm, CreditPaymentForm

# مپینگ شعبه به سرویس واسط - این را قبل از توابع اضافه کنید
BRIDGE_SERVICE_MAPPING = {
    # branch_id: "bridge_service_ip"
    # مثال - اینها را با IPهای واقعی پر کنید:
    1: "192.168.1.172",  # شعبه مرکزی
    2: "192.168.1.101",  # شعبه 1
    3: "192.168.1.102",  # شعبه 2
}


def get_bridge_service_url(branch_id):
    """دریافت آدرس سرویس واسط بر اساس شعبه"""
    bridge_ip = BRIDGE_SERVICE_MAPPING.get(branch_id)
    if not bridge_ip:
        bridge_ip = list(BRIDGE_SERVICE_MAPPING.values())[0] if BRIDGE_SERVICE_MAPPING else '192.168.1.100'
        print(f"⚠️ شعبه {branch_id} در مپینگ نبود، از {bridge_ip} استفاده شد")

    return f"http://{bridge_ip}:5000"


def send_via_bridge_service(branch_id, pos_ip, amount):
    """ارسال از طریق سرویس واسط"""
    try:
        bridge_service_url = get_bridge_service_url(branch_id)
        health_url = f"{bridge_service_url}/health"
        payment_url = f"{bridge_service_url}/pos/payment"

        print(f"🌐 ارسال به سرویس واسط شعبه {branch_id}")
        print(f"📍 آدرس سلامت: {health_url}")
        print(f"📍 آدرس پرداخت: {payment_url}")

        # اول سلامت سرویس را چک کن
        health_response = requests.get(health_url, timeout=10)
        if health_response.status_code != 200:
            return {'status': 'error', 'message': 'سرویس واسط در دسترس نیست'}

        # سپس پرداخت را انجام بده
        payload = {
            'ip': pos_ip,
            'port': 1362,
            'amount': amount
        }

        payment_response = requests.post(payment_url, json=payload, timeout=30)
        result = payment_response.json()

        print(f"✅ پاسخ از سرویس واسط: {result.get('status')}")
        return result

    except requests.exceptions.ConnectionError:
        bridge_ip = BRIDGE_SERVICE_MAPPING.get(branch_id, 'نامشخص')
        error_msg = f"❌ امکان اتصال به سرویس واسط شعبه {branch_id} (IP: {bridge_ip}) وجود ندارد"
        print(error_msg)
        return {'status': 'error', 'message': error_msg}
    except requests.exceptions.Timeout:
        error_msg = f"⏰ timeout در ارتباط با سرویس واسط شعبه {branch_id}"
        print(error_msg)
        return {'status': 'error', 'message': error_msg}
    except Exception as e:
        error_msg = f"❌ خطا در ارتباط با سرویس واسط: {str(e)}"
        print(error_msg)
        return {'status': 'error', 'message': error_msg}


@login_required
@csrf_exempt
def add_item_to_invoice(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            ignore_stock = data.get('ignore_stock', False)

            if quantity <= 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'تعداد باید بیشتر از صفر باشد'
                })

            # بررسی وجود شعبه
            branch_id = request.session.get('branch_id')
            if not branch_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفا ابتدا شعبه را انتخاب کنید'
                })

            product = get_object_or_404(InventoryCount, id=product_id, branch_id=branch_id)

            # بررسی موجودی (مگر اینکه ignore_stock=true باشد)
            if not ignore_stock and product.quantity < quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'موجودی کالای {product.product_name} کافی نیست. موجودی فعلی: {product.quantity}',
                    'available_quantity': product.quantity,
                    'product_name': product.product_name
                })

            items = request.session.get('invoice_items', [])
            item_exists = False

            # بررسی وجود آیتم در فاکتور
            for item in items:
                if item['product_id'] == product_id:
                    new_quantity = item['quantity'] + quantity
                    item['quantity'] = new_quantity
                    item['total'] = product.selling_price * new_quantity
                    item_exists = True
                    break

            # اگر آیتم جدید است
            if not item_exists:
                items.append({
                    'product_id': product_id,
                    'product_name': product.product_name,
                    'barcode': product.barcode_data or '',
                    'price': product.selling_price,
                    'quantity': quantity,
                    'total': product.selling_price * quantity,
                    'discount': 0,
                    'available_quantity': product.quantity
                })

            request.session['invoice_items'] = items
            request.session.modified = True

            # 🔴 محاسبه مبالغ نهایی به روش صحیح
            total_without_discount = sum(item['total'] for item in items)
            items_discount = sum(item.get('discount', 0) for item in items)
            invoice_discount = request.session.get('discount', 0)
            total_discount = items_discount + invoice_discount
            total_amount = max(0, total_without_discount - total_discount)

            return JsonResponse({
                'status': 'success',
                'items': items,
                'total_without_discount': total_without_discount,
                'items_discount': items_discount,
                'invoice_discount': invoice_discount,
                'total_discount': total_discount,
                'total_amount': total_amount,
                'message': 'کالا با موفقیت به فاکتور اضافه شد'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا: {str(e)}'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'درخواست نامعتبر'
    })



@login_required
def create_invoice(request):
    if 'branch_id' not in request.session:
        if request.method == 'POST':
            form = BranchSelectionForm(request.POST)
            if form.is_valid():
                request.session['branch_id'] = form.cleaned_data['branch'].id
                request.session['branch_name'] = form.cleaned_data['branch'].name
                request.session['invoice_items'] = []
                return redirect('invoice_app:create_invoice')
        else:
            form = BranchSelectionForm()
        return render(request, 'invoice_create.html', {'form': form, 'branch_selected': False})

    branch_id = request.session.get('branch_id')
    branch = get_object_or_404(Branch, id=branch_id)
    pos_devices = POSDevice.objects.filter(is_active=True)
    default_pos = pos_devices.filter(is_default=True).first()

    return render(request, 'invoice_create.html', {
        'branch_selected': True,
        'branch': branch,
        'pos_devices': pos_devices,
        'default_pos': default_pos,
        'items': request.session.get('invoice_items', []),
        'customer_name': request.session.get('customer_name', ''),
        'customer_phone': request.session.get('customer_phone', ''),
    })


def convert_persian_arabic_to_english(text):
    """
    تبدیل اعداد فارسی و عربی به انگلیسی
    """
    persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
    arabic_numbers = '٠١٢٣٤٥٦٧٨٩'
    english_numbers = '0123456789'

    translation_table = str.maketrans(persian_numbers + arabic_numbers, english_numbers * 2)
    return text.translate(translation_table)


@login_required
@csrf_exempt
def search_product(request):
    """جستجوی محصولات - نسخه بدون محدودیت با تبدیل اعداد فارسی/عربی"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            branch_id = request.session.get('branch_id')

            if not branch_id:
                return JsonResponse({'error': 'لطفا ابتدا شعبه را انتخاب کنید'}, status=400)

            if len(query) < 2:
                return JsonResponse({'results': []})

            # تبدیل اعداد فارسی و عربی به انگلیسی
            query_english = convert_persian_arabic_to_english(query)
            print(f"🔍 جستجوی اصلی: '{query}' -> تبدیل شده: '{query_english}'")

            # جستجوی بدون محدودیت
            products = InventoryCount.objects.filter(
                branch_id=branch_id
            ).filter(
                models.Q(product_name__icontains=query) |  # جستجو با نام اصلی
                models.Q(product_name__icontains=query_english) |  # جستجو با نام تبدیل شده
                models.Q(barcode_data__icontains=query_english)  # جستجو در بارکد با اعداد انگلیسی
            ).select_related('branch').order_by('product_name')

            # 🔥 حذف کامل محدودیت - تمام نتایج برگردانده می‌شود
            results = []
            for product in products:
                results.append({
                    'id': product.id,
                    'name': product.product_name,
                    'barcode': product.barcode_data or '',
                    'quantity': product.quantity,
                    'price': product.selling_price,
                    'low_stock': product.quantity <= 0,
                    'branch_name': product.branch.name if product.branch else 'نامشخص'
                })

            print(
                f"🔍 جستجوی '{query}' (تبدیل شده: '{query_english}') در شعبه {branch_id}: {len(results)} نتیجه یافت شد")

            return JsonResponse({
                'results': results,
                'total_count': len(results),
                'has_more': False,  # چون همه نتایج برگردانده می‌شود
                'debug': {
                    'original_query': query,
                    'converted_query': query_english,
                    'branch_id': branch_id,
                    'unlimited_results': True
                }
            })

        except Exception as e:
            print(f"❌ خطا در جستجوی محصول: {str(e)}")
            return JsonResponse({'error': f'خطا در جستجو: {str(e)}'}, status=500)

    return JsonResponse({'error': 'درخواست نامعتبر'}, status=400)
@login_required
@csrf_exempt
def remove_item_from_invoice(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')

            items = request.session.get('invoice_items', [])
            items = [item for item in items if item['product_id'] != product_id]

            request.session['invoice_items'] = items
            request.session.modified = True

            total_amount = sum(item['total'] - item.get('discount', 0) for item in items)

            return JsonResponse({
                'status': 'success',
                'items': items,
                'total_amount': total_amount
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error'})

@login_required
@csrf_exempt
def update_item_quantity(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            new_quantity = int(data.get('quantity', 1))

            if new_quantity <= 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'تعداد باید بیشتر از صفر باشد'
                })

            product = get_object_or_404(InventoryCount, id=product_id)

            if product.quantity < new_quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'موجودی کافی نیست. موجودی فعلی: {product.quantity}'
                })

            items = request.session.get('invoice_items', [])
            item_found = False

            for item in items:
                if item['product_id'] == product_id:
                    item['quantity'] = new_quantity
                    item['total'] = product.selling_price * new_quantity
                    item_found = True
                    break

            if not item_found:
                return JsonResponse({
                    'status': 'error',
                    'message': 'کالا در فاکتور یافت نشد'
                })

            request.session['invoice_items'] = items
            request.session.modified = True

            total_amount = sum(item['total'] - item.get('discount', 0) for item in items)

            return JsonResponse({
                'status': 'success',
                'items': items,
                'total_amount': total_amount,
                'message': 'تعداد کالا با موفقیت به روز شد'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})

@login_required
@csrf_exempt
def update_item_discount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            discount = int(data.get('discount', 0))

            if discount < 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'تخفیف نمی‌تواند منفی باشد'
                })

            items = request.session.get('invoice_items', [])
            item_found = False

            for item in items:
                if item['product_id'] == product_id:
                    if discount > item['total']:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'تخفیف نمی‌تواند از قیمت کل بیشتر باشد'
                        })
                    item['discount'] = discount
                    item_found = True
                    break

            if not item_found:
                return JsonResponse({
                    'status': 'error',
                    'message': 'کالا در فاکتور یافت نشد'
                })

            request.session['invoice_items'] = items
            request.session.modified = True

            total_amount = sum(item['total'] - item.get('discount', 0) for item in items)

            return JsonResponse({
                'status': 'success',
                'items': items,
                'total_amount': total_amount,
                'message': 'تخفیف کالا با موفقیت به روز شد'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})

@login_required
@csrf_exempt
def save_customer_info(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request.session['customer_name'] = data.get('customer_name', '').strip()
            request.session['customer_phone'] = data.get('customer_phone', '').strip()
            request.session.modified = True
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})
    return JsonResponse({'status': 'error'})

@login_required
@csrf_exempt
def save_payment_method(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payment_method = data.get('payment_method', 'pos')

            if payment_method not in ['cash', 'pos', 'check', 'credit']:
                return JsonResponse({'status': 'error', 'message': 'روش پرداخت نامعتبر'})

            request.session['payment_method'] = payment_method

            if payment_method == 'pos':
                default_pos = POSDevice.objects.filter(is_default=True, is_active=True).first()
                if default_pos:
                    request.session['pos_device_id'] = default_pos.id
            else:
                if 'pos_device_id' in request.session:
                    del request.session['pos_device_id']
                if 'check_payment_data' in request.session:
                    del request.session['check_payment_data']
                if 'credit_payment_data' in request.session:
                    del request.session['credit_payment_data']

            request.session.modified = True
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})
    return JsonResponse({'status': 'error'})

@login_required
@csrf_exempt
def save_pos_device(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')

            if not device_id:
                return JsonResponse({'status': 'error', 'message': 'دستگاه انتخاب نشده'})

            device = get_object_or_404(POSDevice, id=device_id, is_active=True)
            request.session['pos_device_id'] = device.id
            request.session.modified = True

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})
    return JsonResponse({'status': 'error'})


@login_required
@csrf_exempt
def save_check_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📋 اطلاعات دریافتی چک:", data)

            required_fields = ['owner_name', 'owner_family', 'national_id', 'phone',
                               'check_number', 'amount', 'check_date', 'remaining_amount',
                               'remaining_payment_method']

            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'status': 'error', 'message': f'فیلد {field} الزامی است'})

            # تبدیل تاریخ شمسی به میلادی
            check_date_str = data.get('check_date')
            try:
                if check_date_str and '/' in check_date_str:
                    parts = check_date_str.split('/')
                    if len(parts) == 3:
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                        jalali_date = jdatetime.date(year, month, day)
                        gregorian_date = jalali_date.togregorian()
                        check_date_final = gregorian_date
                    else:
                        check_date_final = check_date_str
                else:
                    check_date_final = check_date_str
            except Exception as e:
                print(f"⚠️ خطا در تبدیل تاریخ: {e}")
                check_date_final = check_date_str

            items = request.session.get('invoice_items', [])
            if not items:
                return JsonResponse({'status': 'error', 'message': 'فاکتور خالی است'})

            total_amount = sum(item['total'] - item.get('discount', 0) for item in items)
            discount = request.session.get('discount', 0)
            total_amount = max(0, total_amount - discount)

            branch_id = request.session.get('branch_id')
            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'شعبه انتخاب نشده'})

            # 🔴 محاسبه مجموع قیمت معیار - اضافه شده
            total_standard_price = 0
            product_ids = [item['product_id'] for item in items]
            products = InventoryCount.objects.filter(id__in=product_ids)
            product_names = [product.product_name for product in products]

            try:
                from account_app.models import ProductPricing
                pricings = ProductPricing.objects.filter(product_name__in=product_names)
                pricing_dict = {p.product_name: p.standard_price for p in pricings}
            except Exception as e:
                print(f"⚠️ خطا در دریافت قیمت‌های معیار: {e}")
                pricing_dict = {}

            product_dict = {p.id: p for p in products}

            for item_data in items:
                product = product_dict.get(item_data['product_id'])
                if not product:
                    continue

                standard_price = pricing_dict.get(product.product_name, 0)
                if standard_price is None:
                    standard_price = 0

                total_standard_price += standard_price * item_data['quantity']

            print(f"💰 مجموع قیمت معیار محاسبه شد: {total_standard_price}")

            # ایجاد فاکتور با قیمت معیار محاسبه شده
            invoice = Invoicefrosh.objects.create(
                branch_id=branch_id,
                created_by=request.user,
                payment_method='check',
                total_amount=total_amount,
                total_without_discount=sum(item['total'] for item in items),
                discount=discount + sum(item.get('discount', 0) for item in items),
                is_finalized=True,
                is_paid=False,
                customer_name=request.session.get('customer_name', ''),
                customer_phone=request.session.get('customer_phone', ''),
                paid_amount=int(data.get('amount', 0)),
                total_standard_price=total_standard_price  # 🔴 حالا مقدار صحیح محاسبه شده
            )

            # ثبت آیتم‌های فاکتور با قیمت معیار
            invoice_items = []
            for item_data in items:
                product = product_dict.get(item_data['product_id'])
                if not product:
                    continue

                item_total_price = (item_data['quantity'] * item_data['price']) - item_data.get('discount', 0)
                standard_price = pricing_dict.get(product.product_name, 0)

                invoice_items.append(InvoiceItemfrosh(
                    invoice=invoice,
                    product=product,
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    total_price=item_total_price,
                    standard_price=standard_price,  # 🔴 قیمت معیار برای هر آیتم
                    discount=item_data.get('discount', 0)
                ))

                # کاهش موجودی
                product.quantity -= item_data['quantity']
                product.save()

            # bulk create برای آیتم‌ها
            InvoiceItemfrosh.objects.bulk_create(invoice_items)

            # ثبت اطلاعات چک
            check_payment = CheckPayment.objects.create(
                invoice=invoice,
                owner_name=data.get('owner_name', '').strip(),
                owner_family=data.get('owner_family', '').strip(),
                national_id=data.get('national_id', '').strip(),
                address=data.get('address', '').strip(),
                phone=data.get('phone', '').strip(),
                check_number=data.get('check_number', '').strip(),
                amount=int(data.get('amount', 0)),
                remaining_amount=int(data.get('remaining_amount', 0)),
                remaining_payment_method=data.get('remaining_payment_method', 'cash'),
                check_date=check_date_final
            )

            if data.get('remaining_payment_method') == 'pos' and data.get('remaining_pos_device_id'):
                check_payment.pos_device_id = data.get('remaining_pos_device_id')
                check_payment.save()

            # پاکسازی session
            session_keys = ['invoice_items', 'customer_name', 'customer_phone',
                            'payment_method', 'discount', 'pos_device_id', 'check_payment_data']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

            print(f"✅ فاکتور چک با موفقیت ثبت شد. شماره فاکتور: {invoice.id}")
            print(f"💰 قیمت معیار: {total_standard_price}, سود: {invoice.total_profit}")

            return JsonResponse({
                'status': 'success',
                'message': 'اطلاعات چک و فاکتور با موفقیت ثبت شد',
                'invoice_id': invoice.id,
                'check_id': check_payment.id,
                'total_standard_price': total_standard_price,
                'total_profit': invoice.total_profit
            })

        except Exception as e:
            print(f"❌ خطا در ذخیره اطلاعات چک: {str(e)}")
            import traceback
            print(f"❌ جزئیات خطا: {traceback.format_exc()}")
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error'})


@login_required
@csrf_exempt
def save_credit_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📋 اطلاعات دریافتی نسیه:", data)

            required_fields = ['customer_name', 'customer_family', 'national_id', 'phone', 'due_date']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'status': 'error', 'message': f'فیلد {field} الزامی است'})

            # تبدیل تاریخ شمسی به میلادی
            due_date_str = data.get('due_date')
            try:
                if due_date_str and '/' in due_date_str:
                    parts = due_date_str.split('/')
                    if len(parts) == 3:
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                        jalali_date = jdatetime.date(year, month, day)
                        gregorian_date = jalali_date.togregorian()
                        due_date_final = gregorian_date
                    else:
                        due_date_final = due_date_str
                else:
                    due_date_final = due_date_str
            except Exception as e:
                print(f"⚠️ خطا در تبدیل تاریخ: {e}")
                due_date_final = due_date_str

            items = request.session.get('invoice_items', [])
            if not items:
                return JsonResponse({'status': 'error', 'message': 'فاکتور خالی است'})

            total_amount = sum(item['total'] - item.get('discount', 0) for item in items)
            discount = request.session.get('discount', 0)
            total_amount = max(0, total_amount - discount)

            branch_id = request.session.get('branch_id')
            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'شعبه انتخاب نشده'})

            # 🔴 محاسبه مجموع قیمت معیار - اضافه شده
            total_standard_price = 0
            product_ids = [item['product_id'] for item in items]
            products = InventoryCount.objects.filter(id__in=product_ids)
            product_names = [product.product_name for product in products]

            try:
                from account_app.models import ProductPricing
                pricings = ProductPricing.objects.filter(product_name__in=product_names)
                pricing_dict = {p.product_name: p.standard_price for p in pricings}
            except Exception as e:
                print(f"⚠️ خطا در دریافت قیمت‌های معیار: {e}")
                pricing_dict = {}

            product_dict = {p.id: p for p in products}

            for item_data in items:
                product = product_dict.get(item_data['product_id'])
                if not product:
                    continue

                standard_price = pricing_dict.get(product.product_name, 0)
                if standard_price is None:
                    standard_price = 0

                total_standard_price += standard_price * item_data['quantity']

            print(f"💰 مجموع قیمت معیار محاسبه شد: {total_standard_price}")

            # ایجاد فاکتور با قیمت معیار محاسبه شده
            invoice = Invoicefrosh.objects.create(
                branch_id=branch_id,
                created_by=request.user,
                payment_method='credit',
                total_amount=total_amount,
                total_without_discount=sum(item['total'] for item in items),
                discount=discount + sum(item.get('discount', 0) for item in items),
                is_finalized=True,
                is_paid=False,
                customer_name=data.get('customer_name', ''),
                customer_phone=data.get('phone', ''),
                paid_amount=int(data.get('credit_amount', 0)),
                total_standard_price=total_standard_price  # 🔴 حالا مقدار صحیح محاسبه شده
            )

            # ثبت آیتم‌های فاکتور با قیمت معیار
            invoice_items = []
            for item_data in items:
                product = product_dict.get(item_data['product_id'])
                if not product:
                    continue

                item_total_price = (item_data['quantity'] * item_data['price']) - item_data.get('discount', 0)
                standard_price = pricing_dict.get(product.product_name, 0)

                invoice_items.append(InvoiceItemfrosh(
                    invoice=invoice,
                    product=product,
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    total_price=item_total_price,
                    standard_price=standard_price,  # 🔴 قیمت معیار برای هر آیتم
                    discount=item_data.get('discount', 0)
                ))

                # کاهش موجودی
                product.quantity -= item_data['quantity']
                product.save()

            # bulk create برای آیتم‌ها
            InvoiceItemfrosh.objects.bulk_create(invoice_items)

            # ثبت اطلاعات نسیه
            credit_payment = CreditPayment.objects.create(
                invoice=invoice,
                customer_name=data.get('customer_name', '').strip(),
                customer_family=data.get('customer_family', '').strip(),
                national_id=data.get('national_id', '').strip(),
                address=data.get('address', '').strip(),
                phone=data.get('phone', '').strip(),
                due_date=due_date_final,
                credit_amount=int(data.get('credit_amount', 0)),
                remaining_amount=int(data.get('remaining_amount', 0)),
                remaining_payment_method=data.get('remaining_payment_method', 'cash')
            )

            if data.get('remaining_payment_method') == 'pos' and data.get('remaining_pos_device_id'):
                credit_payment.pos_device_id = data.get('remaining_pos_device_id')
                credit_payment.save()

            # پاکسازی session
            session_keys = ['invoice_items', 'customer_name', 'customer_phone',
                            'payment_method', 'discount', 'pos_device_id', 'credit_payment_data']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

            print(f"✅ فاکتور نسیه با موفقیت ثبت شد. شماره فاکتور: {invoice.id}")
            print(f"💰 قیمت معیار: {total_standard_price}, سود: {invoice.total_profit}")

            return JsonResponse({
                'status': 'success',
                'message': 'اطلاعات نسیه و فاکتور با موفقیت ثبت شد',
                'invoice_id': invoice.id,
                'credit_id': credit_payment.id,
                'total_standard_price': total_standard_price,
                'total_profit': invoice.total_profit
            })

        except Exception as e:
            print(f"❌ خطا در ذخیره اطلاعات نسیه: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error'})

# @login_required
# @csrf_exempt
# def save_check_payment(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             print("📋 اطلاعات دریافتی چک:", data)  # لاگ برای دیباگ
#
#             required_fields = ['owner_name', 'owner_family', 'national_id', 'phone',
#                                'check_number', 'amount', 'check_date', 'remaining_amount',
#                                'remaining_payment_method']
#
#             for field in required_fields:
#                 if not data.get(field):
#                     return JsonResponse({'status': 'error', 'message': f'فیلد {field} الزامی است'})
#
#             # ذخیره اطلاعات چک در session
#             check_data = {
#                 'owner_name': data.get('owner_name', '').strip(),
#                 'owner_family': data.get('owner_family', '').strip(),
#                 'national_id': data.get('national_id', '').strip(),
#                 'address': data.get('address', '').strip(),
#                 'phone': data.get('phone', '').strip(),
#                 'check_number': data.get('check_number', '').strip(),
#                 'amount': int(data.get('amount', 0)),
#                 'remaining_amount': int(data.get('remaining_amount', 0)),
#                 'remaining_payment_method': data.get('remaining_payment_method', 'cash'),
#                 'remaining_pos_device_id': data.get('remaining_pos_device_id'),
#                 'check_date': data.get('check_date', '')
#             }
#
#             request.session['check_payment_data'] = check_data
#             request.session.modified = True
#
#             print("✅ اطلاعات چک در session ذخیره شد:", check_data)
#
#             return JsonResponse({'status': 'success'})
#         except Exception as e:
#             print(f"❌ خطا در ذخیره اطلاعات چک: {str(e)}")
#             return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})
#     return JsonResponse({'status': 'error'})


@login_required
@csrf_exempt
def save_discount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            discount = int(data.get('discount', 0))

            if discount < 0:
                return JsonResponse({'status': 'error', 'message': 'تخفیف نمی‌تواند منفی باشد'})

            request.session['discount'] = discount
            request.session.modified = True

            items = request.session.get('invoice_items', [])
            total_amount = sum(item['total'] - item.get('discount', 0) for item in items) - discount
            total_amount = max(0, total_amount)

            return JsonResponse({
                'status': 'success',
                'total_amount': total_amount
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})
    return JsonResponse({'status': 'error'})

@login_required
@csrf_exempt
def manage_pos_devices(request):
    """
    Handle all POS device operations (add, delete, set_default)
    """
    if request.method == 'POST':
        try:
            action = request.POST.get('action')

            if action == 'add':
                name = request.POST.get('name', '').strip()
                account_holder = request.POST.get('account_holder', '').strip()
                card_number = request.POST.get('card_number', '').strip()
                account_number = request.POST.get('account_number', '').strip()
                bank_name = request.POST.get('bank_name', '').strip()

                errors = {}
                if not name:
                    errors['name'] = ['نام دستگاه الزامی است']
                if not account_holder:
                    errors['account_holder'] = ['نام صاحب حساب الزامی است']
                if not card_number:
                    errors['card_number'] = ['شماره کارت الزامی است']
                elif len(card_number) != 16 or not card_number.isdigit():
                    errors['card_number'] = ['شماره کارت باید 16 رقم باشد']
                if not account_number:
                    errors['account_number'] = ['شماره حساب الزامی است']
                if not bank_name:
                    errors['bank_name'] = ['نام بانک الزامی است']

                if errors:
                    return JsonResponse({
                        'status': 'error',
                        'errors': errors
                    })

                pos_device = POSDevice.objects.create(
                    name=name,
                    account_holder=account_holder,
                    card_number=card_number,
                    account_number=account_number,
                    bank_name=bank_name
                )

                if POSDevice.objects.filter(is_active=True).count() == 1:
                    pos_device.is_default = True
                    pos_device.save()

                return JsonResponse({
                    'status': 'success',
                    'message': 'دستگاه با موفقیت اضافه شد',
                    'device_id': pos_device.id,
                    'device_name': f"{pos_device.name} - {pos_device.bank_name}"
                })

            elif action == 'delete':
                device_id = request.POST.get('device_id')
                device = get_object_or_404(POSDevice, id=device_id)
                device.delete()
                return JsonResponse({'status': 'success', 'message': 'دستگاه حذف شد'})

            elif action == 'set_default':
                device_id = request.POST.get('device_id')
                POSDevice.objects.filter(is_default=True).update(is_default=False)
                device = get_object_or_404(POSDevice, id=device_id)
                device.is_default = True
                device.save()
                return JsonResponse({'status': 'success', 'message': 'دستگاه پیش فرض تغییر کرد'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})

@login_required
def invoice_success(request, invoice_id):
    """
    نمایش صفحه موفقیت آمیز بودن ثبت فاکتور
    """
    try:
        invoice = get_object_or_404(Invoicefrosh, id=invoice_id)

        # لاگ کردن برای پیگیری
        print(f"📄 نمایش صفحه موفقیت برای فاکتور {invoice_id}")

        # استفاده از redirect به جای render اگر مشکل template باقی ماند
        return render(request, 'invoice_success.html', {
            'invoice': invoice,
            'success_message': 'فاکتور با موفقیت ثبت شد و صفحه برای فاکتور جدید آماده است.'
        })

    except Exception as e:
        print(f"❌ خطا در نمایش صفحه موفقیت: {str(e)}")
        # fallback به یک صفحه ساده
        return render(request, 'simple_success.html', {
            'invoice_id': invoice_id,
            'message': 'فاکتور با موفقیت ثبت شد'
        })

@login_required
def invoice_print(request, invoice_id):
    invoice = get_object_or_404(Invoicefrosh, id=invoice_id)

    payment_details = None
    payment_type = None

    if invoice.payment_method == 'check' and hasattr(invoice, 'check_payment'):
        payment_details = invoice.check_payment
        payment_type = 'check'
    elif invoice.payment_method == 'credit' and hasattr(invoice, 'credit_payment'):
        payment_details = invoice.credit_payment
        payment_type = 'credit'
    elif invoice.payment_method == 'pos' and invoice.pos_device:
        payment_details = invoice.pos_device
        payment_type = 'pos'

    from jdatetime import datetime as jdatetime
    jalali_date = jdatetime.fromgregorian(datetime=invoice.created_at).strftime('%Y/%m/%d')
    jalali_time = jdatetime.fromgregorian(datetime=invoice.created_at).strftime('%H:%M')

    return render(request, 'invoice_print.html', {
        'invoice': invoice,
        'payment_details': payment_details,
        'payment_type': payment_type,
        'jalali_date': jalali_date,
        'jalali_time': jalali_time,
        'print_date': jdatetime.now().strftime('%Y/%m/%d %H:%M')
    })





@login_required
def get_invoice_summary(request):
    """
    دریافت خلاصه فاکتور از session
    """
    if request.method == 'GET':
        try:
            items = request.session.get('invoice_items', [])
            discount = request.session.get('discount', 0)

            # اگر session پاک شده باشد
            if not items and 'invoice_items' not in request.session:
                return JsonResponse({
                    'session_cleared': True,
                    'message': 'session فاکتور خالی است',
                    'success': True
                })

            # 🔴 محاسبه دقیق مبالغ به روش صحیح
            total_without_discount = sum(item['total'] for item in items)
            items_discount = sum(item.get('discount', 0) for item in items)
            total_discount = items_discount + discount
            total_amount = max(0, total_without_discount - total_discount)

            return JsonResponse({
                'session_cleared': False,
                'total_items': len(items),
                'total_without_discount': total_without_discount,
                'items_discount': items_discount,
                'invoice_discount': discount,
                'total_discount': total_discount,
                'total_amount': total_amount,
                'success': True
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'success': False
            })

    return JsonResponse({
        'error': 'درخواست نامعتبر',
        'success': False
    })


@login_required
def cancel_invoice(request):
    """
    ویوی لغو فاکتور و پاکسازی کامل session
    سپس ریدایرکت به صفحه ایجاد فاکتور برای نمایش فرم انتخاب شعبه
    """
    print("🔴 درخواست لغو فاکتور دریافت شد")

    session_keys_to_remove = [
        'invoice_items', 'customer_name', 'customer_phone',
        'payment_method', 'discount', 'pos_device_id',
        'check_payment_data', 'credit_payment_data', 'branch_id', 'branch_name'
    ]

    removed_keys = []
    for key in session_keys_to_remove:
        if key in request.session:
            del request.session[key]
            removed_keys.append(key)

    request.session.modified = True

    print(f"✅ session پاکسازی شد. کلیدهای حذف شده: {removed_keys}")

    # ریدایرکت به صفحه ایجاد فاکتور که فرم انتخاب شعبه را نشان می‌دهد
    return redirect('invoice_app:create_invoice')


@login_required
@csrf_exempt
def confirm_check_payment(request):
    """
    تأیید نهایی پرداخت چک و ثبت فاکتور
    """
    if request.method == 'POST':
        try:
            # بررسی وجود اطلاعات چک در session
            check_data = request.session.get('check_payment_data')
            if not check_data:
                return JsonResponse({
                    'status': 'error',
                    'message': 'اطلاعات چک یافت نشد. لطفا مجدداً اطلاعات چک را وارد کنید.'
                })

            # فراخوانی ویوی نهایی کردن فاکتور
            return finalize_invoice(request)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در تأیید پرداخت چک: {str(e)}'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'درخواست نامعتبر'
    })


# @login_required
# @csrf_exempt
# def save_credit_payment(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             print("📋 اطلاعات دریافتی نسیه:", data)
#
#             # 🔴 اصلاح: استفاده از credit_amount از داده‌های فرم
#             credit_amount = int(data.get('credit_amount', 0))
#
#             # ذخیره اطلاعات کامل در session
#             credit_data = {
#                 'customer_name': data.get('customer_name', '').strip(),
#                 'customer_family': data.get('customer_family', '').strip(),
#                 'national_id': data.get('national_id', '').strip(),
#                 'address': data.get('address', '').strip(),
#                 'phone': data.get('phone', '').strip(),
#                 'due_date': data.get('due_date', ''),
#                 # 🔴 استفاده از credit_amount از فرم، نه total_amount
#                 'credit_amount': credit_amount,
#                 'remaining_amount': data.get('remaining_amount', 0),
#                 'remaining_payment_method': data.get('remaining_payment_method', 'cash'),
#                 'remaining_pos_device_id': data.get('remaining_pos_device_id')
#             }
#
#             request.session['credit_payment_data'] = credit_data
#             request.session.modified = True
#
#             print("✅ اطلاعات نسیه در session ذخیره شد:", credit_data)
#             return JsonResponse({'status': 'success'})
#
#         except Exception as e:
#             print(f"❌ خطا در ذخیره اطلاعات نسیه: {str(e)}")
#             return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})
#     return JsonResponse({'status': 'error'})


# invoice_app/views.py (بخش اصلاح شده)



# ==================== توابع ارتباط با پوز ====================


def normalize_ip(ip):
    """نرمال کردن آدرس IP"""
    parts = ip.split('.')
    normalized_parts = [str(int(part)) for part in parts]
    return '.'.join(normalized_parts)


def build_sale_request(amount):
    """ساخت پیام با فرمت 12 رقمی استاندارد برای دستگاه پوز - amount باید ریال باشد"""
    print(f"🔨 شروع ساخت پیام برای دستگاه پوز")
    print(f"💰 مبلغ ورودی: {amount} ریال")

    # اطمینان از عدد بودن مبلغ
    try:
        amount_int = int(amount)
    except (ValueError, TypeError):
        print(f"❌ مبلغ نامعتبر: {amount}")
        raise ValueError("مبلغ باید عدد باشد")

    # تبدیل به 12 رقم با صفرهای ابتدایی
    amount_12_digit = str(amount_int).zfill(12)
    print(f"💰 مبلغ 12 رقمی: {amount_12_digit}")

    # بررسی طول مبلغ
    if len(str(amount_int)) > 12:
        print(f"❌ مبلغ بیش از حد بزرگ است: {amount_int}")
        raise ValueError("مبلغ نمی‌تواند بیش از 12 رقم باشد")

    # استفاده از فرمت 12 رقمی استاندارد
    message = f"0047RQ034PR006000000AM012{amount_12_digit}CU003364PD0011"

    print(f"📦 پیام نهایی ساخته شد:")
    print(f"   طول: {len(message)}")
    print(f"   محتوا: {message}")
    print(f"   HEX: {message.encode('ascii').hex()}")

    return message



# ==================== ویوهای اصلی فاکتور ====================

@login_required
@csrf_exempt
def finalize_invoice(request):
    """ویوی نهایی کردن فاکتور - فقط برای پوز پیش‌فرض"""
    if request.method == 'POST':
        try:
            # بررسی اینکه آیا دستگاه پوز پیش‌فرض است
            pos_device_id = request.session.get('pos_device_id')
            if pos_device_id:
                pos_device = POSDevice.objects.filter(id=pos_device_id, is_default=True).first()
                if not pos_device:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'این دستگاه پوز پیش‌فرض نیست. لطفا از گزینه ثبت فاکتور استفاده کنید.'
                    })

            # بقیه کدهای موجود...
            # [کدهای موجود بدون تغییر]

        except Exception as e:
            print(f"❌ خطا در ثبت فاکتور: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ثبت فاکتور: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})



@login_required
@csrf_exempt
def finalize_invoice_non_pos(request):
    """ویوی نهایی کردن فاکتور برای پرداخت‌های غیر از پوز - نسخه بهینه‌شده"""
    if request.method == 'POST':
        try:
            # دریافت داده‌های JSON
            import json
            data = json.loads(request.body)

            branch_id = request.session.get('branch_id')
            items = request.session.get('invoice_items', [])
            payment_method = data.get('payment_method', 'cash')
            paid_amount = data.get('paid_amount', 0)

            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'شعبه انتخاب نشده'})

            if not items:
                return JsonResponse({'status': 'error', 'message': 'فاکتور خالی است'})

            # 🔴 محاسبه مبلغ کل به روش صحیح (مانند قبل)
            total_amount = sum(item['total'] - item.get('discount', 0) for item in items)
            discount = request.session.get('discount', 0)
            total_amount = max(0, total_amount - discount)

            # محاسبه مبلغ بدون تخفیف برای نمایش
            total_without_discount = sum(item['total'] for item in items)

            # محاسبه مجموع تخفیف‌ها
            items_discount = sum(item.get('discount', 0) for item in items)
            total_discount = items_discount + discount

            print(f"💰 مبلغ فاکتور: {total_amount} تومان")
            print(f"💰 مبلغ بدون تخفیف: {total_without_discount} تومان")
            print(f"💰 مجموع تخفیف‌ها: {total_discount} تومان")

            # تعیین وضعیت فاکتور
            is_finalized = payment_method == 'cash'
            is_paid = payment_method == 'cash'
            payment_date = timezone.now() if is_paid else None

            # 🔴 محاسبه مجموع قیمت معیار
            total_standard_price = 0

            # جمع‌آوری تمام product_idها برای یک query
            product_ids = [item['product_id'] for item in items]
            products = InventoryCount.objects.filter(id__in=product_ids)

            # جمع‌آوری تمام product_nameها برای pricing
            product_names = [product.product_name for product in products]

            try:
                from account_app.models import ProductPricing
                pricings = ProductPricing.objects.filter(product_name__in=product_names)
                pricing_dict = {p.product_name: p.standard_price for p in pricings}
            except Exception as e:
                print(f"⚠️ خطا در دریافت قیمت‌های معیار: {e}")
                pricing_dict = {}

            product_dict = {p.id: p for p in products}

            # محاسبه مجموع قیمت معیار
            for item_data in items:
                product = product_dict.get(item_data['product_id'])
                if not product:
                    continue

                standard_price = pricing_dict.get(product.product_name, 0)
                if standard_price is None:
                    standard_price = 0

                # محاسبه مجموع قیمت معیار
                total_standard_price += standard_price * item_data['quantity']

            print(f"💰 مجموع قیمت معیار محاسبه شد: {total_standard_price}")

            # 🔴 ثبت فاکتور - فقط مجموع قیمت معیار ذخیره می‌شود، سود در مدل محاسبه می‌شود
            invoice = Invoicefrosh.objects.create(
                branch_id=branch_id,
                created_by=request.user,
                payment_method=payment_method,
                total_amount=total_amount,
                total_without_discount=total_without_discount,
                discount=total_discount,
                is_finalized=is_finalized,
                is_paid=is_paid,
                payment_date=payment_date,
                customer_name=request.session.get('customer_name', ''),
                customer_phone=request.session.get('customer_phone', ''),
                paid_amount=paid_amount if paid_amount > 0 else total_amount,
                total_standard_price=total_standard_price  # 🔴 فقط مجموع قیمت معیار ذخیره می‌شود
                # سود به طور خودکار در مدل محاسبه می‌شود
            )

            # ثبت آیتم‌ها
            invoice_items = []
            for item_data in items:
                product = product_dict.get(item_data['product_id'])
                if not product:
                    continue

                item_total_price = (item_data['quantity'] * item_data['price']) - item_data.get('discount', 0)
                standard_price = pricing_dict.get(product.product_name, 0)

                invoice_items.append(InvoiceItemfrosh(
                    invoice=invoice,
                    product=product,
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    total_price=item_total_price,
                    standard_price=standard_price,
                    discount=item_data.get('discount', 0)
                ))

                # کاهش موجودی
                product.quantity -= item_data['quantity']

            # bulk create و bulk update
            InvoiceItemfrosh.objects.bulk_create(invoice_items)
            InventoryCount.objects.bulk_update(products, ['quantity'])

            # پاکسازی session
            for key in ['invoice_items', 'customer_name', 'customer_phone', 'payment_method', 'discount',
                        'pos_device_id']:
                request.session.pop(key, None)

            return JsonResponse({
                'status': 'success',
                'message': 'فاکتور با موفقیت ثبت شد',
                'invoice_id': invoice.id,
                'total_amount': total_amount,
                'total_standard_price': total_standard_price,
                'total_profit': invoice.total_profit  # 🔴 از مدل خوانده می‌شود
            })

        except Exception as e:
            print(f"❌ خطا در ثبت فاکتور غیر-POS: {str(e)}")
            import traceback
            print(f"❌ جزئیات خطا: {traceback.format_exc()}")

            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ثبت فاکتور: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})

# در views.py - ویوهای مربوط به مدیریت آیتم‌های فاکتور
@login_required
def invoice_add_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        try:
            product = InventoryCount.objects.get(id=product_id)

            # اضافه کردن آیتم به session
            if 'invoice_items' not in request.session:
                request.session['invoice_items'] = []

            # محاسبه قیمت کل آیتم
            item_total = quantity * product.unit_price
            item_discount = data.get('discount', 0)

            item_data = {
                'product_id': product.id,
                'product_name': product.product_name,
                'quantity': quantity,
                'price': product.unit_price,  # این باید با فیلد price در مدل مطابقت کند
                'discount': item_discount,
                'total': item_total - item_discount
            }

            request.session['invoice_items'].append(item_data)
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'message': 'کالا به فاکتور اضافه شد'
            })

        except InventoryCount.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'محصول یافت نشد'
            })
# --------------------------------------------------------------------------
@login_required
@csrf_exempt
def process_pos_payment(request):
    """پردازش پرداخت از طریق پوز - بهبود یافته با مدیریت وضعیت‌ها"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount_toman = data.get('amount')  # مبلغ به تومان
            pos_device_id = data.get('pos_device_id')

            print(f"🔄 شروع پردازش پرداخت POS")
            print(f"📊 داده‌های دریافتی: amount_toman={amount_toman}, device_id={pos_device_id}")

            if not amount_toman:
                return JsonResponse({
                    'status': 'error',
                    'message': 'مبلغ الزامی است'
                })

            if not pos_device_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'دستگاه پوز الزامی است'
                })

            # 🔴 دریافت شعبه از session
            branch_id = request.session.get('branch_id')
            if not branch_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'شعبه انتخاب نشده است'
                })

            try:
                branch = Branch.objects.get(id=branch_id)
                print(f"🏢 شعبه: {branch.name}")

                # 🔴 دریافت IP مودم از شعبه
                branch_modem_ip = branch.modem_ip
                if not branch_modem_ip:
                    print(f"❌ IP مودم برای شعبه {branch.name} تنظیم نشده است")
                    return JsonResponse({
                        'status': 'error',
                        'message': f'IP مودم برای شعبه {branch.name} تنظیم نشده است. لطفا با مدیر سیستم تماس بگیرید.'
                    })

                print(f"📡 IP مودم شعبه: {branch_modem_ip}")

            except Branch.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'شعبه یافت نشد'
                })

            # تبدیل تومان به ریال (ضرب در 10)
            amount_rial = int(amount_toman) * 10
            print(f"💸 تبدیل مبلغ: {amount_toman} تومان → {amount_rial} ریال")

            # دریافت اطلاعات دستگاه پوز
            try:
                pos_device = POSDevice.objects.get(id=pos_device_id, is_active=True)
                print(f"📟 دستگاه پوز یافت شد: {pos_device.name}")
            except POSDevice.DoesNotExist:
                print(f"❌ دستگاه پوز با ID {pos_device_id} یافت نشد")
                return JsonResponse({
                    'status': 'error',
                    'message': 'دستگاه پوز یافت نشد'
                })

            # دریافت پورت از دستگاه پوز
            pos_port = getattr(pos_device, 'port', 1362)

            print(f"📍 اطلاعات اتصال:")
            print(f"   شعبه: {branch.name}")
            print(f"   دستگاه: {pos_device.name}")
            print(f"   IP مودم: {branch_modem_ip}")
            print(f"   پورت: {pos_port}")

            # 🔴 ارسال مبلغ ریال به دستگاه پوز با استفاده از IP مودم شعبه
            print(f"🚀 شروع ارسال به دستگاه پوز...")
            pos_result = send_to_pos_with_status(branch_modem_ip, pos_port, amount_rial)

            # بررسی وضعیت تراکنش
            if pos_result['status'] == 'success':
                transaction_status = pos_result.get('transaction_status', {})

                if transaction_status.get('status_type') == 'success':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'پرداخت با موفقیت انجام شد',
                        'transaction_status': transaction_status,
                        'amount_toman': amount_toman,
                        'amount_rial': amount_rial,
                        'branch_info': {
                            'name': branch.name,
                            'modem_ip': branch_modem_ip
                        },
                        'device_info': {
                            'name': pos_device.name,
                            'port': pos_port
                        },
                        'pos_response': pos_result
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': transaction_status.get('message', 'خطا در پرداخت'),
                        'transaction_status': transaction_status
                    })
            else:
                print(f"❌ خطا در پرداخت POS: {pos_result['message']}")
                return JsonResponse({
                    'status': 'error',
                    'message': pos_result['message'],
                    'transaction_status': {
                        'status_type': 'connection_error',
                        'message': pos_result['message']
                    }
                })

        except json.JSONDecodeError as json_error:
            print(f"❌ خطای JSON: {json_error}")
            return JsonResponse({
                'status': 'error',
                'message': 'داده‌های ارسالی معتبر نیستند'
            })
        except Exception as e:
            print(f"❌ خطای غیرمنتظره در پردازش پرداخت: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در پردازش پرداخت: {str(e)}'
            })

def receive_full_response(sock, timeout=30):  # افزایش به 30 ثانیه
    """دریافت کامل پاسخ از سوکت با مدیریت timeout"""
    print(f"⏳ شروع دریافت پاسخ از دستگاه پوز - timeout: {timeout} ثانیه")

    sock.settimeout(timeout)
    response = b""
    start_time = time.time()

    try:
        while True:
            try:
                # زمان باقیمانده را محاسبه کن
                elapsed_time = time.time() - start_time
                remaining_time = timeout - elapsed_time

                if remaining_time <= 0:
                    print("⏰ زمان دریافت پاسخ به پایان رسید")
                    break

                # از timeout اصلی استفاده کن، نه timeout کوتاه
                sock.settimeout(remaining_time)
                chunk = sock.recv(1024)

                if chunk:
                    response += chunk
                    print(f"📥 دریافت بسته داده: {len(chunk)} بایت")
                    print(f"📋 محتوای بسته: {chunk}")
                    print(f"🔢 HEX بسته: {chunk.hex()}")

                    # اگر پاسخ کامل دریافت شده، خارج شو
                    if len(response) >= 4:
                        try:
                            length_part = response[:4].decode('ascii')
                            expected_length = int(length_part)
                            if len(response) >= expected_length:
                                print(f"✅ پاسخ کامل دریافت شد. طول مورد انتظار: {expected_length}")
                                break
                        except (ValueError, UnicodeDecodeError):
                            # اگر نتوانستیم طول را parse کنیم، ادامه می‌دهیم
                            pass

                else:
                    print("📭 اتصال بسته شد")
                    break

            except socket.timeout:
                print("⏰ timeout در دریافت داده - بررسی می‌کنیم آیا پاسخ کافی دریافت شده")
                # فقط اگر واقعاً timeout اصلی رسیده باشد خارج شو
                elapsed_time = time.time() - start_time
                if elapsed_time >= timeout:
                    print("⏰ timeout اصلی رسید")
                    break
                else:
                    # اگر timeout اصلی نرسیده، ادامه بده
                    print(f"⏱️ هنوز {timeout - elapsed_time:.1f} ثانیه زمان باقی است")
                    continue

    except Exception as e:
        print(f"❌ خطای کلی در دریافت پاسخ: {e}")

    end_time = time.time()
    duration = end_time - start_time
    print(f"⏱️ مدت زمان دریافت پاسخ: {duration:.2f} ثانیه")
    print(f"📦 اندازه پاسخ نهایی: {len(response)} بایت")

    return response


def send_to_pos_with_status(ip, port, amount):
    """ارسال مبلغ به دستگاه پوز با مدیریت کامل وضعیت‌ها"""
    try:
        print(f"💰 ارسال تراکنش برای مبلغ: {amount} ریال به {ip}:{port}")

        if not ip:
            return {
                'status': 'error',
                'message': 'آدرس IP نمی‌تواند خالی باشد',
                'transaction_status': {
                    'status_type': 'connection_error',
                    'message': 'آدرس IP معتبر نیست'
                }
            }

        ip = normalize_ip(ip)
        if not is_valid_ip(ip):
            return {
                'status': 'error',
                'message': 'آدرس IP معتبر نیست',
                'transaction_status': {
                    'status_type': 'connection_error',
                    'message': 'آدرس IP معتبر نیست'
                }
            }

        # ساخت پیام با فرمت 12 رقمی
        message = build_sale_request(amount)

        print(f"📤 ارسال پیام به دستگاه...")
        print(f"📦 پیام ارسالی: {message}")
        print(f"🔢 پیام HEX: {message.encode('ascii').hex()}")

        # ارسال به دستگاه
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # timeout اتصال
        print(f"🔌 در حال اتصال به {ip}:{port}...")

        try:
            sock.connect((ip, port))
        except socket.timeout:
            return {
                'status': 'error',
                'message': 'اتصال به دستگاه پوز timeout خورد',
                'transaction_status': {
                    'status_type': 'connection_error',
                    'message': 'دستگاه پوز در دسترس نیست'
                }
            }

        print("✅ اتصال برقرار شد")

        bytes_sent = sock.send(message.encode('ascii'))
        print(f"✅ {bytes_sent} بایت ارسال شد")

        # زمان برای نمایش مبلغ روی دستگاه
        print("⏳ منتظر نمایش مبلغ روی دستگاه...")
        time.sleep(3)  # 3 ثانیه صبر کن

        # دریافت پاسخ از دستگاه با timeout 30 ثانیه
        print("⏳ در حال دریافت پاسخ از دستگاه پوز...")
        response = receive_full_response(sock, timeout=30)  # 30 ثانیه کامل

        sock.close()
        print("🔒 اتصال بسته شد")

        # تحلیل وضعیت تراکنش
        response_text = response.decode('ascii', errors='ignore') if response else ""
        status_info = get_transaction_status(len(response), response_text)

        print(f"📋 نتیجه تراکنش: {status_info}")

        return {
            'status': 'success',
            'message': f'تراکنش {amount} ریال ارسال شد',
            'transaction_status': status_info,
            'debug': {
                'message_sent': message,
                'response': response_text,
                'response_length': len(response),
                'bytes_sent': bytes_sent,
                'ip_port': f'{ip}:{port}',
                'total_wait_time': '30 ثانیه'
            }
        }

    except socket.timeout as timeout_error:
        print(f"⏰ خطای timeout در اتصال: {timeout_error}")
        return {
            'status': 'error',
            'message': f'اتصال timeout - دستگاه پوز پاسخ نداد: {str(timeout_error)}',
            'transaction_status': {
                'status_type': 'timeout',
                'message': 'زمان پرداخت به پایان رسید. لطفاً مجدداً تلاش کنید.'
            }
        }
    except ConnectionRefusedError as conn_error:
        print(f"🔌 خطای اتصال: {conn_error}")
        return {
            'status': 'error',
            'message': f'اتصال رد شد - پورت باز نیست یا دستگاه خاموش است: {str(conn_error)}',
            'transaction_status': {
                'status_type': 'connection_error',
                'message': 'دستگاه پوز پاسخ نمی‌دهد. از روشن بودن دستگاه اطمینان حاصل کنید.'
            }
        }
    except Exception as e:
        print(f"❌ خطا در ارسال به پوز: {e}")
        return {
            'status': 'error',
            'message': f'خطا در ارسال تراکنش: {str(e)}',
            'transaction_status': {
                'status_type': 'error',
                'message': f'خطا در ارسال تراکنش: {str(e)}'
            }
        }

def get_transaction_status(response_length, response_text):
    """تعیین وضعیت تراکنش بر اساس طول پیام پاسخ"""
    print(f"🔍 تحلیل وضعیت تراکنش - طول پاسخ: {response_length}")

    # اگر پاسخی دریافت نشده باشد
    if response_length == 0:
        return {
            'status_type': 'timeout',
            'message': '⚠️ دستگاه پوز پاسخی ارسال نکرد. ممکن است تراکنش کنسل شده باشد یا ارتباط قطع شده است.'
        }

    # استخراج طول پیام از 4 کاراکتر اول (در صورت موجود بودن)
    length_part = ""
    if response_text and len(response_text) >= 4:
        length_part = response_text[:4]
        print(f"📏 طول پیام از 4 کاراکتر اول: {length_part}")

    # تشخیص وضعیت بر اساس طول پیام
    status_info = {
        'length': response_length,
        'length_part': length_part,
        'message': '',
        'status_type': 'unknown'
    }

    # تشخیص بر اساس طول پیام
    if response_length == 130:  # 0130 به صورت دهدهی
        status_info['message'] = "✅ پرداخت موفق بود - تراکنش با موفقیت انجام شد"
        status_info['status_type'] = 'success'
    elif response_length == 29:  # 0029 به صورت دهدهی
        status_info['message'] = "❌ رمز کارت اشتباه بود - لطفا مجدداً تلاش کنید"
        status_info['status_type'] = 'error'
    elif response_length == 18:  # 0018 به صورت دهدهی
        status_info['message'] = "⚠️ پرداخت کنسل شد - کاربر عملیات را لغو کرد"
        status_info['status_type'] = 'cancelled'
    elif response_length == 24:  # 0018 به صورت دهدهی؟ بررسی کنید
        status_info['message'] = "⚠️ پرداخت کنسل شد - کاربر عملیات را لغو کرد"
        status_info['status_type'] = 'cancelled'
    else:
        # اگر طول شناخته شده نبود، بر اساس length_part چک می‌کنیم
        if length_part == "0130":
            status_info['message'] = "✅ پرداخت موفق بود - تراکنش با موفقیت انجام شد"
            status_info['status_type'] = 'success'
        elif length_part == "0029":
            status_info['message'] = "❌ رمز کارت اشتباه بود - لطفا مجدداً تلاش کنید"
            status_info['status_type'] = 'error'
        elif length_part == "0018":
            status_info['message'] = "⚠️ پرداخت کنسل شد - کاربر عملیات را لغو کرد"
            status_info['status_type'] = 'cancelled'
        else:
            status_info['message'] = f"🔍 وضعیت نامشخص - طول پاسخ: {response_length}, کد: {length_part}"
            status_info['status_type'] = 'unknown'

    print(f"📋 نتیجه تحلیل: {status_info['message']}")
    return status_info

# ------------------------------------------------------------------------------------------
import socket
import time
import re


def send_to_pos_from_server(ip, port, amount):
    """ارسال مستقیم از سرور به دستگاه پوز - نسخه ساده و مطمئن"""
    try:
        print(f"🚀 ارسال از سرور به پوز: {amount} ریال به {ip}:{port}")

        # اعتبارسنجی IP
        if not ip or not is_valid_ip(ip):
            return {
                'status': 'error',
                'message': 'آدرس IP معتبر نیست'
            }

        # ساخت پیام ساده
        amount_str = str(amount).zfill(12)
        message = f"0047RQ034PR006000000AM012{amount_str}CU003364PD0011"

        print(f"📦 پیام ارسالی: {message}")

        # ارسال به دستگاه پوز
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)  # کاهش timeout
        sock.connect((ip, port))

        # ارسال پیام
        sock.send(message.encode('ascii'))
        print("✅ پیام ارسال شد")

        # کمی صبر کن
        time.sleep(2)

        # دریافت پاسخ
        response = b""
        try:
            sock.settimeout(10)
            response = sock.recv(1024)
            print(f"📥 پاسخ دریافت شد: {response}")
        except socket.timeout:
            print("⚠️ پاسخی دریافت نشد")
        finally:
            sock.close()

        return {
            'status': 'success',
            'message': 'مبلغ به پوز ارسال شد',
            'response': response.decode('ascii', errors='ignore') if response else "بدون پاسخ"
        }

    except ConnectionRefusedError:
        return {
            'status': 'error',
            'message': 'دستگاه پوز روشن نیست یا پورت باز نیست'
        }
    except socket.timeout:
        return {
            'status': 'error',
            'message': 'اتصال timeout خورد'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'خطا: {str(e)}'
        }


def is_valid_ip(ip):
    """بررسی ساده IP"""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except:
        return False
# --------------------------------
@login_required
def bridge_mapping_view(request):
    """مدیریت مپینگ شعبه به سرویس واسط"""
    branches = Branch.objects.all()

    current_mapping = []
    for branch in branches:
        current_mapping.append({
            'branch': branch,
            'bridge_ip': BRIDGE_SERVICE_MAPPING.get(branch.id, 'تعیین نشده')
        })

    if request.method == 'POST':
        for branch in branches:
            new_ip = request.POST.get(f'branch_{branch.id}', '').strip()
            if new_ip:
                BRIDGE_SERVICE_MAPPING[branch.id] = new_ip
                print(f"✅ مپینگ به روز شد: شعبه {branch.id} -> {new_ip}")

        return redirect('invoice_app:bridge_mapping')

    return render(request, 'bridge_mapping.html', {
        'current_mapping': current_mapping,
        'branches': branches,
    })


@login_required
@csrf_exempt
def test_bridge_connection(request):
    """تست ارتباط با سرویس واسط"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            branch_id = data.get('branch_id')

            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'شعبه مشخص نشده'})

            bridge_ip = BRIDGE_SERVICE_MAPPING.get(int(branch_id))
            if not bridge_ip:
                return JsonResponse({'status': 'error', 'message': 'سرویس واسط برای این شعبه تنظیم نشده'})

            health_url = f"http://{bridge_ip}:5000/health"
            response = requests.get(health_url, timeout=10)

            if response.status_code == 200:
                return JsonResponse({
                    'status': 'success',
                    'message': f'سرویس واسط شعبه {branch_id} فعال است',
                    'bridge_ip': bridge_ip
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'سرویس واسط پاسخ نمی‌دهد'
                })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در تست ارتباط: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})

@login_required
def quick_pos_test(request):
    """مدیریت مپینگ پوز بریج"""
    branches = Branch.objects.all()

    # ایجاد لیست از مپینگ‌های فعلی
    current_mapping = []
    for branch in branches:
        current_mapping.append({
            'branch': branch,
            'bridge_ip': BRIDGE_SERVICE_MAPPING.get(branch.id, 'تعیین نشده')
        })

    if request.method == 'POST':
        # به روز کردن مپینگ
        for branch in branches:
            new_ip = request.POST.get(f'branch_{branch.id}', '').strip()
            if new_ip:
                BRIDGE_SERVICE_MAPPING[branch.id] = new_ip
                print(f"✅ مپینگ به روز شد: شعبه {branch.id} -> {new_ip}")

        return redirect('invoice_app:quick_pos_test')

    return render(request, 'bridge_mapping.html', {
        'current_mapping': current_mapping,
        'branches': branches,
    })


@login_required
@csrf_exempt
def quick_pos_test_api(request):
    """API برای تست ارتباط با سرویس واسط"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            branch_id = data.get('branch_id')

            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'شعبه مشخص نشده'})

            bridge_ip = BRIDGE_SERVICE_MAPPING.get(int(branch_id))
            if not bridge_ip:
                return JsonResponse({'status': 'error', 'message': 'سرویس واسط برای این شعبه تنظیم نشده'})

            # تست سلامت سرویس با requests
            health_url = f"http://{bridge_ip}:5000/health"

            print(f"🔍 تست سلامت سرویس: {health_url}")

            response = requests.get(health_url, timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                return JsonResponse({
                    'status': 'success',
                    'message': f'سرویس واسط شعبه {branch_id} فعال است',
                    'bridge_ip': bridge_ip,
                    'health_data': health_data
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'سرویس واسط پاسخ نمی‌دهد. کد وضعیت: {response.status_code}'
                })

        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'status': 'error',
                'message': f'امکان اتصال به سرویس واسط در {bridge_ip} وجود ندارد'
            })
        except requests.exceptions.Timeout:
            return JsonResponse({
                'status': 'error',
                'message': f'سرویس واسط timeout خورد'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در تست ارتباط: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})


import uuid
import time
from datetime import datetime, timedelta
from django.db import transaction as db_transaction


# 🔥 ویوهای جدید برای سیستم ارتباط معکوس

@login_required
@csrf_exempt
def create_pos_transaction(request):
    """ایجاد تراکنش پوز جدید و انتظار برای نتیجه"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            branch_id = data.get('branch_id')
            amount_toman = data.get('amount')

            if not branch_id or not amount_toman:
                return JsonResponse({'status': 'error', 'message': 'شعبه و مبلغ الزامی هستند'})

            branch = get_object_or_404(Branch, id=branch_id)

            if not branch.modem_ip:
                return JsonResponse({'status': 'error', 'message': 'IP مودم شعبه تنظیم نشده'})

            # تبدیل به ریال
            amount_rial = int(amount_toman) * 10

            # ایجاد شناسه یکتا برای تراکنش
            transaction_id = f"POS_{int(time.time())}_{uuid.uuid4().hex[:8]}"

            # ایجاد تراکنش در دیتابیس
            pos_transaction = POSTransaction.objects.create(
                branch=branch,
                amount_rial=amount_rial,
                pos_ip=branch.modem_ip,
                status='pending',
                transaction_id=transaction_id
            )

            print(f"🔵 تراکنش ایجاد شد: {transaction_id}")
            print(f"🏢 شعبه: {branch.name}")
            print(f"💸 مبلغ: {amount_rial} ریال")
            print(f"📡 دستگاه پوز: {branch.modem_ip}")

            # انتظار برای نتیجه (تا 2 دقیقه)
            max_wait_time = 120  # ثانیه
            check_interval = 2  # ثانیه

            for i in range(max_wait_time // check_interval):
                time.sleep(check_interval)

                # بررسی به روزرسانی وضعیت
                pos_transaction.refresh_from_db()

                if pos_transaction.status in ['success', 'failed', 'timeout']:
                    if pos_transaction.status == 'success':
                        print(f"✅ تراکنش موفق: {transaction_id}")
                        return JsonResponse({
                            'status': 'success',
                            'message': 'پرداخت با موفقیت انجام شد',
                            'transaction_id': transaction_id
                        })
                    else:
                        error_msg = pos_transaction.result_message or 'خطا در پرداخت'
                        print(f"❌ تراکنش ناموفق: {transaction_id} - {error_msg}")
                        return JsonResponse({
                            'status': 'error',
                            'message': error_msg,
                            'transaction_id': transaction_id
                        })

            # اگر زمان به پایان رسید
            pos_transaction.status = 'timeout'
            pos_transaction.result_message = 'زمان پرداخت به پایان رسید'
            pos_transaction.save()

            return JsonResponse({
                'status': 'error',
                'message': 'زمان پرداخت به پایان رسید. لطفاً مجدداً تلاش کنید.'
            })

        except Exception as e:
            print(f"❌ خطا در ایجاد تراکنش: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد تراکنش: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})


@csrf_exempt
def get_pending_transactions(request):
    """دریافت تراکنش‌های در انتظار برای کامپیوترهای داخلی"""
    if request.method == 'GET':
        try:
            branch_id = request.GET.get('branch_id')
            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'branch_id الزامی است'})

            # پیدا کردن تراکنش‌های در انتظار برای این شعبه
            five_minutes_ago = datetime.now() - timedelta(minutes=5)

            pending_transactions = POSTransaction.objects.filter(
                branch_id=branch_id,
                status='pending',
                created_at__gte=five_minutes_ago
            ).order_by('created_at')[:5]  # فقط 5 تراکنش آخر

            transactions_data = []
            for trans in pending_transactions:
                transactions_data.append({
                    'transaction_id': trans.transaction_id,
                    'amount_rial': trans.amount_rial,
                    'pos_ip': trans.pos_ip,
                    'created_at': trans.created_at.isoformat()
                })

            return JsonResponse({
                'status': 'success',
                'pending_transactions': transactions_data,
                'count': len(transactions_data)
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})


@csrf_exempt
def update_transaction_status(request):
    """به روزرسانی وضعیت تراکنش توسط کامپیوترهای داخلی"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction_id = data.get('transaction_id')
            status = data.get('status')
            message = data.get('message', '')

            if not transaction_id or not status:
                return JsonResponse({'status': 'error', 'message': 'transaction_id و status الزامی هستند'})

            if status not in ['processing', 'success', 'failed']:
                return JsonResponse({'status': 'error', 'message': 'status نامعتبر'})

            # پیدا کردن تراکنش و به روزرسانی
            try:
                pos_transaction = POSTransaction.objects.get(transaction_id=transaction_id)
                pos_transaction.status = status
                pos_transaction.result_message = message
                pos_transaction.save()

                print(f"🟢 وضعیت تراکنش به روز شد: {transaction_id} -> {status}")

                return JsonResponse({'status': 'success', 'message': 'وضعیت به روز شد'})

            except POSTransaction.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'تراکنش یافت نشد'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})


@login_required
def transaction_status(request, transaction_id):
    """بررسی وضعیت یک تراکنش"""
    try:
        pos_transaction = get_object_or_404(POSTransaction, transaction_id=transaction_id)
        return JsonResponse({
            'status': 'success',
            'transaction_status': pos_transaction.status,
            'message': pos_transaction.result_message,
            'created_at': pos_transaction.created_at.isoformat(),
            'updated_at': pos_transaction.updated_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ==================== ویوهای گزارش‌گیری فاکتورها - نسخه اصلاح شده ====================

import csv
from django.http import HttpResponse
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from jdatetime import datetime as jdatetime_datetime


@login_required
def invoice_report(request):
    """صفحه اصلی گزارش‌گیری فاکتورها"""
    branches = Branch.objects.all()

    # تاریخ امروز به شمسی - اصلاح شده
    today_jalali = jdatetime_datetime.now().strftime('%Y/%m/%d')

    context = {
        'branches': branches,
        'today_jalali': today_jalali,
    }

    return render(request, 'invoice_report.html', context)


@login_required
@csrf_exempt
def get_invoice_report_data(request):
    """دریافت داده‌های گزارش فاکتورها به صورت AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            branch_id = data.get('branch_id')
            start_date = data.get('start_date')
            end_date = data.get('end_date')

            print(f"📊 دریافت درخواست گزارش: شعبه {branch_id}, از {start_date} تا {end_date}")

            # فیلترهای پایه
            invoices = Invoicefrosh.objects.select_related('branch', 'created_by').prefetch_related('items')

            # فیلتر بر اساس شعبه
            if branch_id and branch_id != 'all':
                invoices = invoices.filter(branch_id=branch_id)

            # فیلتر بر اساس تاریخ (تبدیل شمسی به میلادی)
            if start_date and end_date:
                try:
                    # تبدیل تاریخ شمسی به میلادی - اصلاح شده
                    start_date_parts = start_date.split('/')
                    end_date_parts = end_date.split('/')

                    start_jalali = jdatetime_datetime(
                        year=int(start_date_parts[0]),
                        month=int(start_date_parts[1]),
                        day=int(start_date_parts[2])
                    )
                    end_jalali = jdatetime_datetime(
                        year=int(end_date_parts[0]),
                        month=int(end_date_parts[1]),
                        day=int(end_date_parts[2])
                    )

                    # تبدیل به میلادی
                    start_gregorian = start_jalali.togregorian()
                    end_gregorian = end_jalali.togregorian()

                    # اضافه کردن زمان به انتهای روز
                    end_gregorian = datetime.combine(end_gregorian, datetime.max.time())

                    # فیلتر بر اساس تاریخ
                    invoices = invoices.filter(
                        created_at__gte=start_gregorian,
                        created_at__lte=end_gregorian
                    )

                    print(f"📅 فیلتر تاریخ: {start_gregorian} تا {end_gregorian}")

                except Exception as e:
                    print(f"❌ خطا در تبدیل تاریخ: {e}")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'فرمت تاریخ نامعتبر است'
                    })

            # مرتب سازی
            invoices = invoices.order_by('-created_at')

            # محاسبه آمار کلی
            total_invoices = invoices.count()
            total_amount = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            total_profit = invoices.aggregate(Sum('total_profit'))['total_profit__sum'] or 0
            avg_sale = invoices.aggregate(Avg('total_amount'))['total_amount__avg'] or 0

            # آمار پرداخت‌ها
            payment_stats = {
                'cash': invoices.filter(payment_method='cash').count(),
                'pos': invoices.filter(payment_method='pos').count(),
                'check': invoices.filter(payment_method='check').count(),
                'credit': invoices.filter(payment_method='credit').count(),
            }

            # آماده سازی داده‌ها برای نمایش
            invoice_data = []
            for invoice in invoices[:1000]:  # محدودیت برای عملکرد بهتر
                invoice_data.append({
                    'id': invoice.id,
                    'serial_number': invoice.serial_number,
                    'date': invoice.get_jalali_date(),
                    'time': invoice.get_jalali_time(),
                    'customer_name': invoice.customer_name or 'فروش حضوری',
                    'customer_phone': invoice.customer_phone or '-',
                    'total_amount': invoice.total_amount,
                    'total_profit': invoice.total_profit,
                    'payment_method': invoice.get_payment_method_display(),
                    'payment_method_code': invoice.payment_method,
                    'is_paid': invoice.is_paid,
                    'is_finalized': invoice.is_finalized,
                    'item_count': invoice.items.count(),
                    'branch_name': invoice.branch.name,
                })

            return JsonResponse({
                'status': 'success',
                'invoices': invoice_data,
                'statistics': {
                    'total_invoices': total_invoices,
                    'total_amount': total_amount,
                    'total_profit': total_profit,
                    'avg_sale': round(avg_sale),
                    'payment_stats': payment_stats
                },
                'filters': {
                    'branch_id': branch_id,
                    'start_date': start_date,
                    'end_date': end_date
                }
            })

        except Exception as e:
            print(f"❌ خطا در دریافت گزارش: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در دریافت گزارش: {str(e)}'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'درخواست نامعتبر'
    })


@login_required
def export_invoice_report_csv(request):
    """خروجی CSV از گزارش فاکتورها"""
    try:
        # دریافت پارامترها
        branch_id = request.GET.get('branch_id')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # فیلترهای مشابه با گزارش
        invoices = Invoicefrosh.objects.select_related('branch', 'created_by').prefetch_related('items')

        if branch_id and branch_id != 'all':
            invoices = invoices.filter(branch_id=branch_id)

        if start_date and end_date:
            try:
                start_date_parts = start_date.split('/')
                end_date_parts = end_date.split('/')

                # اصلاح شده - استفاده از jdatetime_datetime
                start_jalali = jdatetime_datetime(
                    year=int(start_date_parts[0]),
                    month=int(start_date_parts[1]),
                    day=int(start_date_parts[2])
                )
                end_jalali = jdatetime_datetime(
                    year=int(end_date_parts[0]),
                    month=int(end_date_parts[1]),
                    day=int(end_date_parts[2])
                )

                start_gregorian = start_jalali.togregorian()
                end_gregorian = end_jalali.togregorian()

                end_gregorian = datetime.combine(end_gregorian, datetime.max.time())

                invoices = invoices.filter(
                    created_at__gte=start_gregorian,
                    created_at__lte=end_gregorian
                )

            except Exception as e:
                print(f"❌ خطا در تبدیل تاریخ برای CSV: {e}")

        # ایجاد پاسخ CSV
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response[
            'Content-Disposition'] = f'attachment; filename="invoice_report_{jdatetime_datetime.now().strftime("%Y%m%d_%H%M")}.csv"'

        # ایجاد writer CSV
        writer = csv.writer(response)
        writer.writerow([
            'شماره سریال', 'تاریخ', 'ساعت', 'شعبه', 'مشتری',
            'تلفن مشتری', 'مبلغ کل (تومان)', 'سود (تومان)',
            'روش پرداخت', 'وضعیت پرداخت', 'تعداد آیتم‌ها'
        ])

        # نوشتن داده‌ها
        for invoice in invoices:
            writer.writerow([
                invoice.serial_number,
                invoice.get_jalali_date(),
                invoice.get_jalali_time(),
                invoice.branch.name,
                invoice.customer_name or 'فروش حضوری',
                invoice.customer_phone or '-',
                invoice.total_amount,
                invoice.total_profit,
                invoice.get_payment_method_display(),
                'پرداخت شده' if invoice.is_paid else 'در انتظار',
                invoice.items.count()
            ])

        return response

    except Exception as e:
        print(f"❌ خطا در ایجاد خروجی CSV: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در ایجاد خروجی CSV: {str(e)}'
        })


@login_required
def quick_stats(request):
    """آمار سریع برای نمایش در داشبورد"""
    try:
        branch_id = request.GET.get('branch_id', 'all')

        # فیلتر پایه
        invoices = Invoicefrosh.objects.all()

        if branch_id != 'all':
            invoices = invoices.filter(branch_id=branch_id)

        # تاریخ امروز
        today = timezone.now().date()

        # آمار امروز
        today_invoices = invoices.filter(created_at__date=today)
        today_stats = {
            'count': today_invoices.count(),
            'amount': today_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'profit': today_invoices.aggregate(Sum('total_profit'))['total_profit__sum'] or 0
        }

        # آمار ماه جاری
        start_of_month = today.replace(day=1)
        month_invoices = invoices.filter(created_at__date__gte=start_of_month)
        month_stats = {
            'count': month_invoices.count(),
            'amount': month_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'profit': month_invoices.aggregate(Sum('total_profit'))['total_profit__sum'] or 0
        }

        return JsonResponse({
            'status': 'success',
            'today': today_stats,
            'month': month_stats
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })