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





# views.py - اضافه کردن ویو save_cash_payment
from django.utils import timezone
from .models import Invoicefrosh, InvoiceItemfrosh, CashPayment, InventoryCount
from account_app.models import ProductPricing
@login_required
@csrf_exempt
def save_cash_payment(request):
    """ذخیره اطلاعات پرداخت نقدی و ثبت فاکتور"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📋 اطلاعات دریافتی نقدی:", data)

            # دریافت داده‌ها
            cash_amount = int(data.get('cash_amount', 0))
            remaining_amount = int(data.get('remaining_amount', 0))
            remaining_pos_device_id = data.get('remaining_pos_device_id')

            print(f"💰 مبلغ نقدی: {cash_amount}")
            print(f"💰 مبلغ باقیمانده: {remaining_amount}")
            print(f"💰 دستگاه پوز: {remaining_pos_device_id}")

            # اعتبارسنجی
            if cash_amount <= 0:
                return JsonResponse({'status': 'error', 'message': 'مبلغ نقدی باید بیشتر از صفر باشد'})

            if not remaining_pos_device_id and remaining_amount > 0:
                return JsonResponse({'status': 'error', 'message': 'برای پرداخت باقیمانده باید دستگاه پوز انتخاب شود'})

            # بررسی وجود شعبه و آیتم‌ها
            branch_id = request.session.get('branch_id')
            items = request.session.get('invoice_items', [])

            print(f"🏢 شعبه: {branch_id}")
            print(f"📦 تعداد آیتم‌ها: {len(items)}")

            if not branch_id:
                return JsonResponse({'status': 'error', 'message': 'شعبه انتخاب نشده'})
            if not items:
                return JsonResponse({'status': 'error', 'message': 'فاکتور خالی است'})

            # محاسبه مبلغ کل
            total_without_discount = sum(item['total'] for item in items)
            items_discount = sum(item.get('discount', 0) for item in items)
            invoice_discount = request.session.get('discount', 0)
            total_discount = items_discount + invoice_discount
            total_amount = max(0, total_without_discount - total_discount)

            # اعتبارسنجی مبلغ نقدی
            if cash_amount > total_amount:
                return JsonResponse({'status': 'error', 'message': 'مبلغ نقدی نمی‌تواند از مبلغ فاکتور بیشتر باشد'})

            print(f"💰 مبلغ فاکتور: {total_amount} تومان")
            print(f"💰 مبلغ نقدی: {cash_amount} تومان")
            print(f"💰 مبلغ باقیمانده: {remaining_amount} تومان")

            # محاسبه مجموع قیمت معیار
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

            # ایجاد فاکتور - این بخش باید کاملاً صحیح باشد
            invoice = Invoicefrosh.objects.create(
                branch_id=branch_id,
                created_by=request.user,
                payment_method='cash',
                total_amount=total_amount,
                total_without_discount=total_without_discount,
                discount=total_discount,
                is_finalized=True,
                is_paid=True,  # فاکتور نقدی بلافاصله پرداخت شده محسوب می‌شود
                payment_date=timezone.now(),
                customer_name=request.session.get('customer_name', ''),
                customer_phone=request.session.get('customer_phone', ''),
                paid_amount=cash_amount,
                total_standard_price=total_standard_price
            )

            print(f"✅ فاکتور ایجاد شد: {invoice.id}")

            # ثبت آیتم‌های فاکتور
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
                product.save()

            # bulk create برای آیتم‌ها
            InvoiceItemfrosh.objects.bulk_create(invoice_items)
            print(f"✅ {len(invoice_items)} آیتم فاکتور ثبت شد")

            # ثبت اطلاعات پرداخت نقدی
            cash_payment = CashPayment.objects.create(
                invoice=invoice,
                cash_amount=cash_amount,
                remaining_amount=remaining_amount,
                remaining_payment_method='pos',  # همیشه پوز برای باقیمانده
                pos_device_id=remaining_pos_device_id if remaining_pos_device_id else None
            )

            print(f"✅ اطلاعات پرداخت نقدی ثبت شد: {cash_payment.id}")

            # پاکسازی session
            session_keys = ['invoice_items', 'customer_name', 'customer_phone',
                            'payment_method', 'discount', 'pos_device_id']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

            print(f"✅ فاکتور نقدی با موفقیت ثبت شد. شماره فاکتور: {invoice.id}")
            print(f"💰 قیمت معیار: {total_standard_price}, سود: {invoice.total_profit}")

            return JsonResponse({
                'status': 'success',
                'message': 'فاکتور نقدی با موفقیت ثبت شد',
                'invoice_id': invoice.id,
                'cash_id': cash_payment.id,
                'total_amount': total_amount,
                'cash_amount': cash_amount,
                'remaining_amount': remaining_amount,
                'total_standard_price': total_standard_price,
                'total_profit': invoice.total_profit
            })

        except Exception as e:
            print(f"❌ خطا در ذخیره اطلاعات نقدی: {str(e)}")
            import traceback
            print(f"❌ جزئیات خطا: {traceback.format_exc()}")
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})


# ------------------------------------------بستن فاکتورهای روزانه----------------------------------------
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from jdatetime import datetime as jdatetime
from datetime import datetime, timedelta
from cantact_app.models import Branch  # import مدل شعبه
from .models import Invoicefrosh, InvoiceItemfrosh, CheckPayment, CreditPayment, CashPayment, POSTransaction
import json


@login_required
def daily_invoices(request):
    """
    نمایش فاکتورهای روزانه با فیلتر شعبه
    """
    # دریافت تاریخ امروز
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    # دریافت پارامترهای فیلتر
    branch_id = request.GET.get('branch')
    date_filter = request.GET.get('date')
    payment_method_filter = request.GET.get('payment_method')

    # ایجاد query اولیه
    invoices = Invoicefrosh.objects.all()

    # اعمال فیلتر تاریخ
    if date_filter:
        try:
            # تبدیل تاریخ جلالی به میلادی
            jalali_date = jdatetime.strptime(date_filter, '%Y/%m/%d')
            gregorian_date = jalali_date.togregorian()
            date_start = timezone.make_aware(datetime.combine(gregorian_date, datetime.min.time()))
            date_end = timezone.make_aware(datetime.combine(gregorian_date, datetime.max.time()))
            invoices = invoices.filter(created_at__range=(date_start, date_end))
            selected_date = date_filter
        except Exception as e:
            messages.warning(request, f'تاریخ وارد شده معتبر نیست. خطا: {str(e)}')
            invoices = invoices.filter(created_at__range=(today_start, today_end))
            selected_date = jdatetime.fromgregorian(date=today).strftime('%Y/%m/%d')
    else:
        # فیلتر بر اساس تاریخ امروز
        invoices = invoices.filter(created_at__range=(today_start, today_end))
        selected_date = jdatetime.fromgregorian(date=today).strftime('%Y/%m/%d')

    # اعمال فیلتر شعبه
    if branch_id and branch_id != '':
        invoices = invoices.filter(branch_id=branch_id)

    # اعمال فیلتر روش پرداخت
    if payment_method_filter and payment_method_filter != 'all':
        invoices = invoices.filter(payment_method=payment_method_filter)

    # مرتب‌سازی و join جداول مرتبط
    invoices = invoices.select_related('branch', 'created_by', 'pos_device').order_by('-created_at')

    # محاسبه آمار کلی
    stats = {
        'total_count': invoices.count(),
        'total_amount': invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'total_discount': invoices.aggregate(Sum('discount'))['discount__sum'] or 0,
        'total_profit': invoices.aggregate(Sum('total_profit'))['total_profit__sum'] or 0,
        'paid_count': invoices.filter(is_paid=True).count(),
        'unpaid_count': invoices.filter(is_paid=False).count(),
    }

    # محاسبه آمار بر اساس روش پرداخت
    payment_stats = {
        'cash': {
            'count': invoices.filter(payment_method='cash').count(),
            'total': invoices.filter(payment_method='cash').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'paid': invoices.filter(payment_method='cash', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='cash', is_paid=False).count(),
        },
        'pos': {
            'count': invoices.filter(payment_method='pos').count(),
            'total': invoices.filter(payment_method='pos').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'paid': invoices.filter(payment_method='pos', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='pos', is_paid=False).count(),
        },
        'check': {
            'count': invoices.filter(payment_method='check').count(),
            'total': invoices.filter(payment_method='check').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'paid': invoices.filter(payment_method='check', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='check', is_paid=False).count(),
        },
        'credit': {
            'count': invoices.filter(payment_method='credit').count(),
            'total': invoices.filter(payment_method='credit').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'paid': invoices.filter(payment_method='credit', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='credit', is_paid=False).count(),
        }
    }

    # محاسبه مجموع کل هر ستون
    total_summary = {
        'total_all_methods': sum(payment_stats[method]['total'] for method in payment_stats),
        'count_all_methods': sum(payment_stats[method]['count'] for method in payment_stats),
    }

    # دریافت لیست شعبه‌ها برای dropdown
    branches = Branch.objects.all()

    context = {
        'invoices': invoices,
        'stats': stats,
        'payment_stats': payment_stats,
        'total_summary': total_summary,
        'branches': branches,
        'selected_branch': branch_id,
        'selected_date': selected_date,
        'selected_payment_method': payment_method_filter or 'all',
        'payment_methods': Invoicefrosh.PAYMENT_METHODS,
        'today': jdatetime.fromgregorian(date=today).strftime('%Y/%m/%d'),
    }

    return render(request, 'invoice_app/daily_invoices.html', context)


@login_required
def invoice_detail(request, invoice_id):
    """
    نمایش جزئیات یک فاکتور
    """
    invoice = get_object_or_404(
        Invoicefrosh.objects.select_related(
            'branch', 'created_by', 'pos_device'
        ).prefetch_related('items'),
        id=invoice_id
    )

    # دریافت اطلاعات پرداخت بر اساس روش پرداخت
    payment_info = None
    if invoice.payment_method == 'check' and hasattr(invoice, 'check_payment'):
        payment_info = invoice.check_payment
    elif invoice.payment_method == 'credit' and hasattr(invoice, 'credit_payment'):
        payment_info = invoice.credit_payment
    elif invoice.payment_method == 'cash' and hasattr(invoice, 'cash_payment'):
        payment_info = invoice.cash_payment
    elif invoice.payment_method == 'pos' and hasattr(invoice, 'pos_transaction'):
        payment_info = invoice.pos_transaction

    context = {
        'invoice': invoice,
        'payment_info': payment_info,
        'items': invoice.items.all(),
        'jalali_date': invoice.get_jalali_date(),
        'jalali_time': invoice.get_jalali_time(),
    }

    return render(request, 'invoice_app/invoice_detail.html', context)


@login_required
def edit_invoice(request, invoice_id):
    """
    ویرایش فاکتور
    """
    invoice = get_object_or_404(Invoicefrosh, id=invoice_id)

    # بررسی دسترسی کاربر برای ویرایش
    if not (request.user.is_superuser or invoice.created_by == request.user):
        messages.error(request, 'شما مجوز ویرایش این فاکتور را ندارید.')
        return redirect('daily_invoices')

    if request.method == 'POST':
        try:
            data = request.POST

            # به‌روزرسانی اطلاعات اصلی فاکتور
            invoice.customer_name = data.get('customer_name', invoice.customer_name)
            invoice.customer_phone = data.get('customer_phone', invoice.customer_phone)
            invoice.discount = int(data.get('discount', invoice.discount))

            # محاسبه مجدد مبلغ کل با احتساب تخفیف
            if 'total_amount' in data:
                total = int(data.get('total_amount'))
                invoice.total_amount = total - invoice.discount
                invoice.total_without_discount = total

            # به‌روزرسانی وضعیت پرداخت
            if 'is_paid' in data:
                invoice.is_paid = data.get('is_paid') == 'on'
                if invoice.is_paid and not invoice.payment_date:
                    invoice.payment_date = timezone.now()

            invoice.save()

            # به‌روزرسانی آیتم‌های فاکتور
            items_data = json.loads(request.POST.get('items', '[]'))
            for item_data in items_data:
                if 'id' in item_data:
                    item = InvoiceItemfrosh.objects.get(id=item_data['id'], invoice=invoice)
                    item.quantity = int(item_data.get('quantity', item.quantity))
                    item.price = int(item_data.get('price', item.price))
                    item.total_price = item.quantity * item.price
                    item.save()

            messages.success(request, 'فاکتور با موفقیت ویرایش شد.')
            return redirect('invoice_detail', invoice_id=invoice.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش فاکتور: {str(e)}')

    # دریافت لیست آیتم‌ها برای نمایش در فرم
    items = invoice.items.all()

    context = {
        'invoice': invoice,
        'items': items,
        'payment_methods': Invoicefrosh.PAYMENT_METHODS,
        'jalali_date': invoice.get_jalali_date(),
        'jalali_time': invoice.get_jalali_time(),
    }

    return render(request, 'invoice_app/edit_invoice.html', context)


@login_required
def delete_invoice(request, invoice_id):
    """
    حذف فاکتور
    """
    invoice = get_object_or_404(Invoicefrosh, id=invoice_id)

    # بررسی دسترسی کاربر برای حذف
    if not (request.user.is_superuser or invoice.created_by == request.user):
        messages.error(request, 'شما مجوز حذف این فاکتور را ندارید.')
        return redirect('invoice_app:daily_invoices')

    if request.method == 'POST':
        try:
            # ذخیره اطلاعات برای نمایش پیام
            invoice_serial = invoice.serial_number
            invoice.delete()
            messages.success(request, f'فاکتور شماره {invoice_serial} با موفقیت حذف شد.')
            return redirect('invoice_app:daily_invoices')
        except Exception as e:
            messages.error(request, f'خطا در حذف فاکتور: {str(e)}')
            return redirect('invoice_app:invoice_detail', invoice_id=invoice.id)

    context = {
        'invoice': invoice,
        'jalali_date': invoice.get_jalali_date(),
    }

    return render(request, 'invoice_app/delete_invoice.html', context)
@login_required
def update_invoice_status(request, invoice_id):
    """
    به‌روزرسانی وضعیت فاکتور (پرداخت/نهایی‌سازی) از طریق AJAX
    """
    if request.method == 'POST' and request.is_ajax():
        try:
            invoice = get_object_or_404(Invoicefrosh, id=invoice_id)
            data = json.loads(request.body)

            if 'is_paid' in data:
                invoice.is_paid = data['is_paid']
                if invoice.is_paid and not invoice.payment_date:
                    invoice.payment_date = timezone.now()

            if 'is_finalized' in data:
                invoice.is_finalized = data['is_finalized']

            invoice.save()

            return JsonResponse({
                'success': True,
                'message': 'وضعیت فاکتور با موفقیت به‌روزرسانی شد.',
                'is_paid': invoice.is_paid,
                'is_finalized': invoice.is_finalized,
                'payment_date': invoice.payment_date.strftime('%Y-%m-%d %H:%M') if invoice.payment_date else None
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'خطا در به‌روزرسانی: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'درخواست نامعتبر'})


@login_required
def filter_invoices(request):
    """
    فیلتر فاکتورها بر اساس تاریخ و شعبه و روش پرداخت
    """
    if request.method == 'GET':
        date_str = request.GET.get('date')
        branch_id = request.GET.get('branch')
        payment_method = request.GET.get('payment_method')

        try:
            invoices = Invoicefrosh.objects.all()

            if date_str:
                # تبدیل تاریخ جلالی به میلادی
                jalali_date = jdatetime.strptime(date_str, '%Y/%m/%d')
                gregorian_date = jalali_date.togregorian()
                date_start = timezone.make_aware(datetime.combine(gregorian_date, datetime.min.time()))
                date_end = timezone.make_aware(datetime.combine(gregorian_date, datetime.max.time()))
                invoices = invoices.filter(created_at__range=(date_start, date_end))

            if branch_id and branch_id != '':
                invoices = invoices.filter(branch_id=branch_id)

            if payment_method and payment_method != 'all':
                invoices = invoices.filter(payment_method=payment_method)

            invoices = invoices.select_related('branch', 'created_by').order_by('-created_at')

            stats = {
                'total_count': invoices.count(),
                'total_amount': invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                'total_discount': invoices.aggregate(Sum('discount'))['discount__sum'] or 0,
                'paid_count': invoices.filter(is_paid=True).count(),
                'unpaid_count': invoices.filter(is_paid=False).count(),
                'total_profit': invoices.aggregate(Sum('total_profit'))['total_profit__sum'] or 0,
            }

            # آمار روش‌های پرداخت
            payment_stats = {
                'cash': {
                    'count': invoices.filter(payment_method='cash').count(),
                    'total': invoices.filter(payment_method='cash').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                    'paid': invoices.filter(payment_method='cash', is_paid=True).count(),
                    'unpaid': invoices.filter(payment_method='cash', is_paid=False).count(),
                },
                'pos': {
                    'count': invoices.filter(payment_method='pos').count(),
                    'total': invoices.filter(payment_method='pos').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                    'paid': invoices.filter(payment_method='pos', is_paid=True).count(),
                    'unpaid': invoices.filter(payment_method='pos', is_paid=False).count(),
                },
                'check': {
                    'count': invoices.filter(payment_method='check').count(),
                    'total': invoices.filter(payment_method='check').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                    'paid': invoices.filter(payment_method='check', is_paid=True).count(),
                    'unpaid': invoices.filter(payment_method='check', is_paid=False).count(),
                },
                'credit': {
                    'count': invoices.filter(payment_method='credit').count(),
                    'total': invoices.filter(payment_method='credit').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                    'paid': invoices.filter(payment_method='credit', is_paid=True).count(),
                    'unpaid': invoices.filter(payment_method='credit', is_paid=False).count(),
                }
            }

            # مجموع کل همه روش‌های پرداخت
            total_summary = {
                'total_all_methods': sum(payment_stats[method]['total'] for method in payment_stats),
                'count_all_methods': sum(payment_stats[method]['count'] for method in payment_stats),
            }

            return JsonResponse({
                'success': True,
                'invoices': list(invoices.values(
                    'id', 'serial_number', 'branch__name', 'total_amount',
                    'discount', 'is_paid', 'is_finalized', 'customer_name',
                    'customer_phone', 'payment_method', 'created_at', 'total_profit'
                )),
                'stats': stats,
                'payment_stats': payment_stats,
                'total_summary': total_summary,
                'date': date_str
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'خطا در فیلتر: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'درخواست نامعتبر'})


# @login_required
# def create_invoice(request):
#     """
#     ایجاد فاکتور جدید
#     """
#     # این ویو باید با منطق ایجاد فاکتور پر شود
#     # فعلاً فقط redirect می‌کنیم
#     messages.info(request, 'صفحه ایجاد فاکتور جدید به زودی اضافه خواهد شد.')
#     return redirect('daily_invoices')

# --------------------------------------مرجوعی--------------------


from django.db.models import Sum
from datetime import datetime as datetime_module
import math


# ==================== ویوهای مرجوع کالا ====================
# 🔴 اصلاحات در بالای views.py - بخش importها
import requests
import json
import http.client
import socket
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.utils import timezone
from decimal import Decimal
import jdatetime
from datetime import datetime as dt  # 🔴 تغییر نام برای جلوگیری از conflict
from datetime import timedelta
import csv

from account_app.models import InventoryCount, Branch, ProductPricing
from .models import Invoicefrosh, InvoiceItemfrosh, POSDevice, CheckPayment, CreditPayment, CashPayment, POSTransaction
from .forms import BranchSelectionForm, POSDeviceForm, CheckPaymentForm, CreditPaymentForm

from django.db.models import Sum, Count
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime as datetime_module  # 🔴 تغییر نام برای جلوگیری از conflict
from datetime import timedelta
import json

@login_required
def return_goods_main(request):
    """صفحه اصلی مرجوع کالا"""
    branches = Branch.objects.all()
    today = datetime_module.now().date()
    today_jalali = jdatetime.fromgregorian(date=today).strftime('%Y/%m/%d')

    return render(request, 'invoice_app/return_goods.html', {
        'branches': branches,
        'today_jalali': today_jalali,
    })


@login_required
@csrf_exempt
def get_invoices_by_date(request):
    """دریافت فاکتورهای یک تاریخ خاص - نسخه ساده"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date', '').strip()
            branch_id = data.get('branch_id', 'all')

            print(f"🔍 دریافت فاکتورها برای تاریخ: {date_str}")

            if not date_str:
                return JsonResponse({
                    'status': 'error',
                    'message': 'تاریخ الزامی است'
                })

            # فیلترهای پایه
            invoices = Invoicefrosh.objects.select_related('branch')

            # فیلتر بر اساس تاریخ
            try:
                date_parts = date_str.split('/')
                if len(date_parts) == 3:
                    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])

                    # تبدیل تاریخ شمسی به میلادی
                    jalali_date = jdatetime.date(year, month, day)
                    gregorian_date = jalali_date.togregorian()

                    # ایجاد رنج تاریخ
                    start_date = dt.combine(gregorian_date, dt.min.time())
                    end_date = dt.combine(gregorian_date, dt.max.time())

                    # تبدیل به timezone aware
                    start_date_tz = timezone.make_aware(start_date)
                    end_date_tz = timezone.make_aware(end_date)

                    print(f"📅 فیلتر تاریخ: {date_str} -> {gregorian_date}")

                    invoices = invoices.filter(
                        created_at__gte=start_date_tz,
                        created_at__lte=end_date_tz
                    )
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'فرمت تاریخ نامعتبر. باید YYYY/MM/DD باشد'
                    })
            except Exception as e:
                print(f"❌ خطا در تبدیل تاریخ: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'خطا در پردازش تاریخ: {str(e)}'
                })

            # فیلتر بر اساس شعبه
            if branch_id and branch_id != 'all':
                invoices = invoices.filter(branch_id=branch_id)

            # مرتب‌سازی
            invoices = invoices.order_by('-created_at')

            print(f"✅ تعداد فاکتورهای یافت شده: {invoices.count()}")

            # آماده‌سازی داده‌ها
            invoices_data = []
            for invoice in invoices:
                item_count = invoice.items.count()

                invoices_data.append({
                    'id': invoice.id,
                    'serial_number': invoice.serial_number or f'FAK-{invoice.id}',
                    'branch_name': invoice.branch.name if invoice.branch else 'نامشخص',
                    'branch_id': invoice.branch.id if invoice.branch else 0,
                    'customer_name': invoice.customer_name or 'مشتری ناشناس',
                    'customer_phone': invoice.customer_phone or '-',
                    'total_amount': invoice.total_amount,
                    'total_profit': invoice.total_profit,
                    'payment_method': invoice.get_payment_method_display(),
                    'payment_method_code': invoice.payment_method,
                    'created_at': invoice.get_jalali_date() + ' ' + invoice.get_jalali_time(),
                    'item_count': item_count,
                    'is_paid': invoice.is_paid,
                    'is_finalized': invoice.is_finalized,
                })

            return JsonResponse({
                'status': 'success',
                'invoices': invoices_data,
                'count': len(invoices_data),
                'date': date_str,
            })

        except Exception as e:
            print(f"❌ خطا در دریافت فاکتورها: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': f'خطا: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})
@login_required
@csrf_exempt
def get_invoice_items(request, invoice_id):
    """دریافت آیتم‌های یک فاکتور"""
    try:
        invoice = get_object_or_404(Invoicefrosh, id=invoice_id)

        items = invoice.items.select_related('product').all()

        items_data = []
        for item in items:
            # موجودی فعلی محصول
            current_stock = item.product.quantity if item.product else 0

            items_data.append({
                'id': item.id,
                'product_id': item.product.id,
                'product_name': item.product.product_name,
                'barcode': item.product.barcode_data or '',
                'quantity': item.quantity,
                'price': item.price,
                'total_price': item.total_price,
                'standard_price': item.standard_price,
                'discount': item.discount,
                'current_stock': current_stock,
                'max_return': item.quantity,  # حداکثر تعداد قابل مرجوع
            })

        invoice_data = {
            'id': invoice.id,
            'serial_number': invoice.serial_number,
            'branch_name': invoice.branch.name,
            'customer_name': invoice.customer_name or 'مشتری ناشناس',
            'total_amount': invoice.total_amount,
            'total_without_discount': invoice.total_without_discount,
            'discount': invoice.discount,
            'payment_method': invoice.get_payment_method_display(),
            'created_at': invoice.get_jalali_date() + ' ' + invoice.get_jalali_time(),
            'is_paid': invoice.is_paid,
        }

        return JsonResponse({
            'status': 'success',
            'invoice': invoice_data,
            'items': items_data,
            'total_items': len(items_data),
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})


@login_required
@csrf_exempt
def process_return(request):
    """پردازش مرجوع کالا"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            invoice_id = data.get('invoice_id')
            return_items = data.get('return_items', [])
            return_reason = data.get('return_reason', '')

            print(f"🔄 شروع پردازش مرجوع برای فاکتور {invoice_id}")
            print(f"📦 آیتم‌های مرجوع: {return_items}")
            print(f"📝 دلیل مرجوع: {return_reason}")

            if not invoice_id:
                return JsonResponse({'status': 'error', 'message': 'فاکتور مشخص نشده'})

            if not return_items:
                return JsonResponse({'status': 'error', 'message': 'هیچ آیتمی برای مرجوع انتخاب نشده'})

            # دریافت فاکتور
            invoice = get_object_or_404(Invoicefrosh, id=invoice_id)
            print(f"📄 فاکتور یافت شد: {invoice.serial_number}")

            # بررسی موجودیت آیتم‌ها
            valid_return_items = []
            for item in return_items:
                item_id = item.get('item_id')
                return_quantity = int(item.get('return_quantity', 0))

                if return_quantity <= 0:
                    continue

                try:
                    invoice_item = InvoiceItemfrosh.objects.get(id=item_id, invoice=invoice)

                    # بررسی تعداد مرجوع
                    if return_quantity > invoice_item.quantity:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'تعداد مرجوع برای کالای {invoice_item.product.product_name} بیشتر از تعداد خریداری شده است'
                        })

                    valid_return_items.append({
                        'item': invoice_item,
                        'return_quantity': return_quantity,
                        'product': invoice_item.product,
                    })

                    print(f"✅ آیتم معتبر: {invoice_item.product.product_name} - {return_quantity} عدد")

                except InvoiceItemfrosh.DoesNotExist:
                    print(f"⚠️ آیتم با ID {item_id} در فاکتور یافت نشد")
                    continue

            if not valid_return_items:
                return JsonResponse({'status': 'error', 'message': 'هیچ آیتم معتبری برای مرجوع پیدا نشد'})

            # شروع تراکنش
            from django.db import transaction

            with transaction.atomic():
                # لیست آیتم‌های به‌روز شده و حذف شده
                updated_items = []
                deleted_items = []

                # مجموع مبالغ مرجوع
                total_return_amount = 0
                total_return_profit = 0

                # پردازش هر آیتم مرجوع
                for return_data in valid_return_items:
                    item = return_data['item']
                    return_quantity = return_data['return_quantity']
                    product = return_data['product']

                    # محاسبه مبلغ مرجوع برای این آیتم
                    item_price = item.price * return_quantity
                    item_discount = (item.discount * return_quantity) / item.quantity
                    item_total = item_price - item_discount
                    total_return_amount += int(item_total)

                    # محاسبه سود مرجوع
                    item_profit = max(0, (item.price - item.standard_price) * return_quantity)
                    total_return_profit += item_profit

                    # افزایش موجودی انبار
                    product.quantity += return_quantity
                    product.save()

                    print(f"📦 مرجوع کالا: {product.product_name}")
                    print(f"   تعداد مرجوع: {return_quantity}")
                    print(f"   موجودی جدید: {product.quantity}")
                    print(f"   مبلغ مرجوع: {item_total}")

                    # به روزرسانی یا حذف آیتم فاکتور
                    if return_quantity == item.quantity:
                        # اگر همه کالا مرجوع شد، آیتم را حذف کن
                        deleted_items.append({
                            'item_id': item.id,
                            'quantity': return_quantity,
                            'product_name': product.product_name
                        })
                        item.delete()
                        print(f"   ❌ آیتم حذف شد")
                    else:
                        # کاهش تعداد آیتم
                        new_quantity = item.quantity - return_quantity

                        # محاسبه تخفیف جدید (نسبتی)
                        new_discount = int((item.discount * new_quantity) / item.quantity)

                        # به‌روزرسانی آیتم
                        item.quantity = new_quantity
                        item.discount = new_discount
                        item.total_price = (item.price * new_quantity) - new_discount
                        item.save()

                        updated_items.append({
                            'item_id': item.id,
                            'old_quantity': item.quantity + return_quantity,
                            'new_quantity': new_quantity,
                            'product_name': product.product_name
                        })
                        print(f"   ✅ آیتم به‌روزرسانی شد: {new_quantity} عدد")

                # اگر تمام آیتم‌ها حذف شدند، فاکتور را حذف کن
                remaining_items = invoice.items.count()
                print(f"📊 تعداد آیتم‌های باقیمانده: {remaining_items}")

                if remaining_items == 0:
                    print(f"🗑️ فاکتور حذف می‌شود (بدون آیتم باقی‌مانده)")

                    # حذف اطلاعات پرداخت مرتبط
                    payment_method = invoice.payment_method

                    if payment_method == 'check' and hasattr(invoice, 'check_payment'):
                        invoice.check_payment.delete()
                    elif payment_method == 'credit' and hasattr(invoice, 'credit_payment'):
                        invoice.credit_payment.delete()
                    elif payment_method == 'cash' and hasattr(invoice, 'cash_payment'):
                        invoice.cash_payment.delete()

                    invoice.delete()

                    return JsonResponse({
                        'status': 'success',
                        'message': 'تمام کالاهای فاکتور مرجوع شدند و فاکتور حذف گردید',
                        'invoice_deleted': True,
                        'return_summary': {
                            'total_return_amount': total_return_amount,
                            'total_return_profit': total_return_profit,
                            'updated_items': len(updated_items),
                            'deleted_items': len(deleted_items),
                        }
                    })
                else:
                    # محاسبه مجدد مبالغ فاکتور
                    items = invoice.items.all()

                    total_without_discount = sum(item.price * item.quantity for item in items)
                    items_discount = sum(item.discount for item in items)
                    invoice_discount = invoice.discount - sum(
                        item.discount for item in items if item.id in [u['item_id'] for u in updated_items])
                    total_discount = items_discount + max(0, invoice_discount)
                    total_amount = max(0, total_without_discount - total_discount)

                    # محاسبه مجدد مجموع قیمت معیار
                    total_standard_price = sum(item.standard_price * item.quantity for item in items)

                    # به‌روزرسانی فاکتور
                    invoice.total_without_discount = total_without_discount
                    invoice.total_amount = total_amount
                    invoice.discount = total_discount
                    invoice.total_standard_price = total_standard_price
                    invoice.save()  # سود به طور خودکار محاسبه می‌شود

                    print(f"💰 فاکتور به‌روزرسانی شد:")
                    print(f"   مبلغ جدید: {total_amount}")
                    print(f"   تخفیف: {total_discount}")
                    print(f"   سود جدید: {invoice.total_profit}")

                    # ایجاد لاگ مرجوع (اگر مدل ReturnLog وجود دارد)
                    try:
                        ReturnLog.objects.create(
                            invoice=invoice,
                            returned_by=request.user,
                            return_amount=total_return_amount,
                            return_profit=total_return_profit,
                            reason=return_reason,
                            return_data=json.dumps({
                                'updated_items': updated_items,
                                'deleted_items': deleted_items,
                            }, ensure_ascii=False)
                        )
                        print(f"📝 لاگ مرجوع ثبت شد")
                    except Exception as e:
                        print(f"⚠️ خطا در ثبت لاگ: {e}")

                    return JsonResponse({
                        'status': 'success',
                        'message': 'مرجوع کالا با موفقیت انجام شد',
                        'invoice_deleted': False,
                        'new_invoice_data': {
                            'id': invoice.id,
                            'total_amount': invoice.total_amount,
                            'total_profit': invoice.total_profit,
                            'item_count': remaining_items,
                        },
                        'return_summary': {
                            'total_return_amount': total_return_amount,
                            'total_return_profit': total_return_profit,
                            'updated_items': len(updated_items),
                            'deleted_items': len(deleted_items),
                        }
                    })

        except Exception as e:
            print(f"❌ خطا در پردازش مرجوع: {str(e)}")
            import traceback
            print(f"❌ جزئیات خطا: {traceback.format_exc()}")
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})

@login_required
@csrf_exempt
def get_return_logs(request):
    """دریافت لاگ‌های مرجوع"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            branch_id = data.get('branch_id')

            # فیلتر لاگ‌ها
            return_logs = ReturnLog.objects.select_related('invoice', 'returned_by', 'invoice__branch')

            if date_str:
                try:
                    date_parts = date_str.split('/')
                    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                    jalali_date = jdatetime.date(year, month, day)
                    gregorian_date = jalali_date.togregorian()

                    start_date = timezone.make_aware(
                        datetime_module.combine(gregorian_date, datetime_module.min.time()))
                    end_date = timezone.make_aware(datetime_module.combine(gregorian_date, datetime_module.max.time()))

                    return_logs = return_logs.filter(created_at__range=(start_date, end_date))
                except:
                    pass

            if branch_id and branch_id != 'all':
                return_logs = return_logs.filter(invoice__branch_id=branch_id)

            return_logs = return_logs.order_by('-created_at')[:100]  # فقط 100 مورد آخر

            logs_data = []
            for log in return_logs:
                logs_data.append({
                    'id': log.id,
                    'invoice_id': log.invoice.id if log.invoice else None,
                    'invoice_serial': log.invoice.serial_number if log.invoice else 'حذف شده',
                    'branch_name': log.invoice.branch.name if log.invoice and log.invoice.branch else 'نامشخص',
                    'returned_by': log.returned_by.get_full_name() or log.returned_by.username,
                    'return_amount': log.return_amount,
                    'return_profit': log.return_profit,
                    'reason': log.reason or 'بدون دلیل',
                    'created_at': jdatetime.fromgregorian(datetime=log.created_at).strftime('%Y/%m/%d %H:%M'),
                })

            return JsonResponse({
                'status': 'success',
                'logs': logs_data,
                'count': len(logs_data),
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})



@login_required
def daily_invoices(request):
    """صفحه اصلی فاکتورهای روزانه - نسخه ساده و بدون مشکل تاریخ"""
    # تاریخ امروز به شمسی
    today_jalali = jdatetime.datetime.now().strftime('%Y/%m/%d')

    # دریافت پارامترهای فیلتر
    branch_id = request.GET.get('branch', '')
    date_filter = request.GET.get('date', today_jalali)
    payment_method_filter = request.GET.get('payment_method', 'all')

    print(f"🔍 درخواست فاکتورهای روزانه:")
    print(f"   تاریخ: {date_filter}")
    print(f"   شعبه: {branch_id}")
    print(f"   روش پرداخت: {payment_method_filter}")

    # فیلترهای پایه
    invoices = Invoicefrosh.objects.select_related('branch', 'created_by')

    # فیلتر بر اساس تاریخ (با منطق ساده)
    if date_filter:
        try:
            # تبدیل تاریخ شمسی به میلادی - روش ساده
            date_parts = date_filter.split('/')
            if len(date_parts) == 3:
                year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])

                # ایجاد تاریخ شمسی
                jalali_date = jdatetime.date(year, month, day)

                # تبدیل به میلادی
                gregorian_date = jalali_date.togregorian()

                # ایجاد رنج تاریخ
                start_of_day = dt.combine(gregorian_date, dt.min.time())
                end_of_day = dt.combine(gregorian_date, dt.max.time())

                # تبدیل به timezone aware
                start_of_day_tz = timezone.make_aware(start_of_day)
                end_of_day_tz = timezone.make_aware(end_of_day)

                print(f"📅 تبدیل تاریخ: {date_filter} -> {gregorian_date}")
                print(f"   از: {start_of_day_tz} تا: {end_of_day_tz}")

                # فیلتر بر اساس رنج تاریخ
                invoices = invoices.filter(
                    created_at__gte=start_of_day_tz,
                    created_at__lte=end_of_day_tz
                )
            else:
                # اگر فرمت تاریخ اشتباه بود، از امروز استفاده کن
                print(f"⚠️ فرمت تاریخ اشتباه: {date_filter}")
        except Exception as e:
            print(f"❌ خطا در تبدیل تاریخ: {e}")

    # فیلتر بر اساس شعبه
    if branch_id and branch_id != '' and branch_id != 'all':
        invoices = invoices.filter(branch_id=branch_id)

    # فیلتر بر اساس روش پرداخت
    if payment_method_filter and payment_method_filter != 'all':
        invoices = invoices.filter(payment_method=payment_method_filter)

    # مرتب‌سازی
    invoices = invoices.order_by('-created_at')

    print(f"✅ تعداد فاکتورهای یافت شده: {invoices.count()}")

    # محاسبه آمار
    stats = {
        'total_count': invoices.count(),
        'total_amount': sum(invoice.total_amount for invoice in invoices),
        'total_discount': sum(invoice.discount for invoice in invoices),
        'total_profit': sum(invoice.total_profit for invoice in invoices),
        'paid_count': invoices.filter(is_paid=True).count(),
        'unpaid_count': invoices.filter(is_paid=False).count(),
    }

    # آمار روش‌های پرداخت
    payment_stats = {
        'cash': {
            'count': invoices.filter(payment_method='cash').count(),
            'total': sum(invoice.total_amount for invoice in invoices.filter(payment_method='cash')),
            'paid': invoices.filter(payment_method='cash', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='cash', is_paid=False).count(),
        },
        'pos': {
            'count': invoices.filter(payment_method='pos').count(),
            'total': sum(invoice.total_amount for invoice in invoices.filter(payment_method='pos')),
            'paid': invoices.filter(payment_method='pos', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='pos', is_paid=False).count(),
        },
        'check': {
            'count': invoices.filter(payment_method='check').count(),
            'total': sum(invoice.total_amount for invoice in invoices.filter(payment_method='check')),
            'paid': invoices.filter(payment_method='check', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='check', is_paid=False).count(),
        },
        'credit': {
            'count': invoices.filter(payment_method='credit').count(),
            'total': sum(invoice.total_amount for invoice in invoices.filter(payment_method='credit')),
            'paid': invoices.filter(payment_method='credit', is_paid=True).count(),
            'unpaid': invoices.filter(payment_method='credit', is_paid=False).count(),
        }
    }

    # مجموع کل
    total_summary = {
        'total_all_methods': sum(payment_stats[method]['total'] for method in payment_stats),
        'count_all_methods': sum(payment_stats[method]['count'] for method in payment_stats),
    }

    # دریافت شعبه‌ها
    from cantact_app.models import Branch as CantactBranch  # 🔴 این احتمالاً مدل درست است
    branches = CantactBranch.objects.all()

    context = {
        'invoices': invoices,
        'stats': stats,
        'payment_stats': payment_stats,
        'total_summary': total_summary,
        'branches': branches,
        'selected_branch': branch_id,
        'selected_date': date_filter,
        'selected_payment_method': payment_method_filter,
        'payment_methods': Invoicefrosh.PAYMENT_METHODS,
        'today': today_jalali,
    }

    return render(request, 'invoice_app/daily_invoices.html', context)


@login_required
def return_goods_main(request):
    """صفحه اصلی مرجوع کالا"""
    # تاریخ امروز به شمسی
    today_jalali = jdatetime.datetime.now().strftime('%Y/%m/%d')

    # دریافت شعبه‌ها
    from cantact_app.models import Branch
    branches = Branch.objects.all()

    return render(request, 'invoice_app/return_goods.html', {
        'branches': branches,
        'today_jalali': today_jalali,
    })