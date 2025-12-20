# cash_management/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
import json
from datetime import datetime
import jdatetime
from jdatetime import date as jdate
from jdatetime import datetime as jdatetime_datetime

from .models import DiscrepancyLog, Investment, CashExpense, CashInventory
from invoice_app.models import Invoicefrosh, CreditPayment, Branch
from cantact_app.models import accuntmodel


# صفحه اصلی موجودی صندوق
@login_required
def cash_inventory_view(request):
    today_jalali = jdatetime.date.today().strftime('%Y/%m/%d')

    # دریافت تمام شعب و سرمایه‌گذاران
    branches = Branch.objects.all()
    investors = accuntmodel.objects.all()

    context = {
        'today_jalali': today_jalali,
        'branches': branches,
        'investors': investors,
    }
    return render(request, 'cash_management/cash_inventory.html', context)


# صفحه ثبت هزینه‌ها
@login_required
def expense_registration_view(request):
    branches = Branch.objects.all()

    if request.method == 'POST':
        # منطق ثبت هزینه (بعداً کامل می‌کنم)
        pass

    context = {
        'branches': branches,
        'expense_types': Expense.EXPENSE_TYPES,
        'payment_methods': Invoicefrosh.PAYMENT_METHODS,
    }
    return render(request, 'cash_management/expense_registration.html', context)


# صفحه پرداخت هزینه‌ها
@login_required
def expense_payment_view(request):
    expenses = Expense.objects.filter(payment_status='pending').order_by('expense_date')

    context = {
        'expenses': expenses,
    }
    return render(request, 'cash_management/expense_payment.html', context)


# صفحه بررسی مغایرت‌ها
@login_required
def discrepancy_review_view(request):
    discrepancies = DiscrepancyLog.objects.filter(status='pending').order_by('-discrepancy_date')

    context = {
        'discrepancies': discrepancies,
    }
    return render(request, 'cash_management/discrepancy_review.html', context)


# دریافت داده‌های موجودی نقدی (Ajax)
@login_required
@require_POST
@csrf_exempt
def get_cash_inventory_data(request):
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        inventory_type = data.get('type', 'cash')  # cash یا account

        # تبدیل تاریخ شمسی به میلادی
        jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian().date()

        # داده‌های خروجی
        result = {
            'status': 'success',
            'date': date_str,
            'type': inventory_type,
            'branches': [],
            'investors': [],
            'total_calculated': 0,
            'total_actual': 0,
        }

        # محاسبه برای شعب
        branches = Branch.objects.all()
        for branch in branches:
            # محاسبه مبلغ فروش نقدی برای این شعبه در تاریخ مشخص
            cash_invoices = Invoicefrosh.objects.filter(
                branch=branch,
                payment_date__date=gregorian_date,
                payment_method='cash',
                is_paid=True
            )

            # محاسبه مبلغ نسیه‌هایی که باقیمانده‌اش نقدی پرداخت شده
            credit_payments = CreditPayment.objects.filter(
                invoice__branch=branch,
                due_date=gregorian_date,
                remaining_payment_method='cash'
            )

            total_calculated = sum(invoice.paid_amount for invoice in cash_invoices) + \
                               sum(payment.remaining_amount for payment in credit_payments)

            # بررسی وضعیت تایید
            all_invoices_confirmed = all(invoice.is_finalized for invoice in cash_invoices) if cash_invoices else True
            all_credits_confirmed = True  # فرض می‌کنیم همه تایید شده‌اند

            is_confirmed = all_invoices_confirmed and all_credits_confirmed

            # دریافت موجودی ذخیره شده (اگر وجود دارد)
            try:
                inventory = CashInventory.objects.get(
                    inventory_date=gregorian_date,
                    inventory_type=inventory_type,
                    branch=branch
                )
                actual_amount = inventory.actual_amount
                is_confirmed = inventory.is_confirmed
            except CashInventory.DoesNotExist:
                actual_amount = total_calculated

            result['branches'].append({
                'id': branch.id,
                'name': branch.name,
                'calculated_amount': total_calculated,
                'actual_amount': actual_amount,
                'is_confirmed': is_confirmed,
                'has_discrepancy': total_calculated != actual_amount and actual_amount != 0
            })

            result['total_calculated'] += total_calculated
            result['total_actual'] += actual_amount

        # محاسبه برای سرمایه‌گذاران
        investors = accuntmodel.objects.all()
        for investor in investors:
            # محاسبه سرمایه‌گذاری‌های نقدی
            investments = Investment.objects.filter(
                investor=investor,
                investment_date=gregorian_date,
                payment_method='cash',
                is_confirmed=True
            )

            total_investment = sum(investment.amount for investment in investments)

            # دریافت موجودی ذخیره شده
            try:
                inventory = CashInventory.objects.get(
                    inventory_date=gregorian_date,
                    inventory_type=inventory_type,
                    investor=investor
                )
                actual_amount = inventory.actual_amount
                is_confirmed = inventory.is_confirmed
            except CashInventory.DoesNotExist:
                actual_amount = total_investment
                is_confirmed = False

            result['investors'].append({
                'id': investor.id,
                'name': f"{investor.firstname} {investor.lastname}",
                'national_id': investor.melicode,
                'calculated_amount': total_investment,
                'actual_amount': actual_amount,
                'is_confirmed': is_confirmed,
                'has_discrepancy': total_investment != actual_amount and actual_amount != 0
            })

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ثبت تایید موجودی (Ajax)
@login_required
@require_POST
@csrf_exempt
def confirm_inventory(request):
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        inventory_type = data.get('type')
        items = data.get('items', [])  # لیست شعب/سرمایه‌گذاران با مبالغ جدید

        # تبدیل تاریخ
        jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian().date()

        for item in items:
            item_id = item.get('id')
            item_type = item.get('type')  # 'branch' یا 'investor'
            actual_amount = item.get('actual_amount', 0)
            calculated_amount = item.get('calculated_amount', 0)

            if item_type == 'branch':
                branch = get_object_or_404(Branch, id=item_id)

                # ذخیره یا بروزرسانی موجودی
                inventory, created = CashInventory.objects.update_or_create(
                    inventory_date=gregorian_date,
                    inventory_type=inventory_type,
                    branch=branch,
                    defaults={
                        'calculated_amount': calculated_amount,
                        'actual_amount': actual_amount,
                        'is_confirmed': True,
                        'confirmed_by': request.user,
                        'confirmed_at': timezone.now()
                    }
                )

                # اگر مغایرت وجود داشت، در لاگ ثبت شود
                if actual_amount != calculated_amount:
                    DiscrepancyLog.objects.create(
                        discrepancy_date=gregorian_date,
                        user=request.user,
                        branch=branch,
                        old_amount=calculated_amount,
                        new_amount=actual_amount,
                        description=f"مغایرت در موجودی {inventory_type} شعبه {branch.name}"
                    )

                # تایید فاکتورهای مربوطه
                if actual_amount == calculated_amount and inventory_type == 'cash':
                    invoices = Invoicefrosh.objects.filter(
                        branch=branch,
                        payment_date__date=gregorian_date,
                        payment_method='cash',
                        is_paid=True
                    )
                    # علامت زدن فاکتورها به عنوان تایید شده (اگر فیلد is_verified داریم)
                    # در اینجا فرض می‌کنیم فیلد is_finalized معادل تایید است
                    invoices.update(is_finalized=True)

            elif item_type == 'investor':
                investor = get_object_or_404(accuntmodel, id=item_id)

                inventory, created = CashInventory.objects.update_or_create(
                    inventory_date=gregorian_date,
                    inventory_type=inventory_type,
                    investor=investor,
                    defaults={
                        'calculated_amount': calculated_amount,
                        'actual_amount': actual_amount,
                        'is_confirmed': True,
                        'confirmed_by': request.user,
                        'confirmed_at': timezone.now()
                    }
                )

                if actual_amount != calculated_amount:
                    DiscrepancyLog.objects.create(
                        discrepancy_date=gregorian_date,
                        user=request.user,
                        investor=investor,
                        old_amount=calculated_amount,
                        new_amount=actual_amount,
                        description=f"مغایرت در موجودی {inventory_type} سرمایه‌گذار {investor.firstname} {investor.lastname}"
                    )

        return JsonResponse({
            'status': 'success',
            'message': 'موجودی با موفقیت تایید شد.'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ثبت سرمایه‌گذاری جدید (Ajax)
@login_required
@require_POST
@csrf_exempt
def register_investment(request):
    try:
        data = json.loads(request.body)

        # دریافت داده‌ها
        national_id = data.get('national_id')
        amount = int(data.get('amount', 0))
        date_str = data.get('date')
        payment_method = data.get('payment_method', 'cash')
        credit_account_id = data.get('credit_account_id')
        notes = data.get('notes', '')

        # تبدیل تاریخ
        jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian().date()

        # پیدا کردن سرمایه‌گذار با کد ملی
        try:
            investor = accuntmodel.objects.get(melicode=national_id)
        except accuntmodel.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'سرمایه‌گذار با این کد ملی یافت نشد.'
            })

        # اگر روش پرداخت حساب باشد، حساب را پیدا کن
        credit_account = None
        if payment_method == 'credit' and credit_account_id:
            try:
                credit_account = CreditPayment.objects.get(id=credit_account_id)
            except CreditPayment.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'حساب اعتباری یافت نشد.'
                })

        # ایجاد رکورد سرمایه‌گذاری
        investment = Investment.objects.create(
            investor=investor,
            amount=amount,
            investment_date=gregorian_date,
            payment_method=payment_method,
            credit_account=credit_account,
            notes=notes,
            created_by=request.user,
            is_confirmed=True,  # به طور پیش‌فرض تایید می‌شود
            confirmed_by=request.user,
            confirmed_at=timezone.now()
        )

        return JsonResponse({
            'status': 'success',
            'message': 'سرمایه‌گذاری با موفقیت ثبت شد.',
            'investment_id': investment.id
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# بررسی و رفع مغایرت (Ajax)
@login_required
@require_POST
@csrf_exempt
def resolve_discrepancy(request, discrepancy_id):
    try:
        data = json.loads(request.body)
        resolution_notes = data.get('resolution_notes', '')
        action = data.get('action')  # 'confirm' یا 'adjust'

        discrepancy = get_object_or_404(DiscrepancyLog, id=discrepancy_id)

        if action == 'confirm':
            # تایید مبلغ جدید و رفع مغایرت
            discrepancy.status = 'resolved'
            discrepancy.reviewed_by = request.user
            discrepancy.review_date = timezone.now()
            discrepancy.resolution_notes = resolution_notes

            # بروزرسانی موجودی با مبلغ جدید
            if discrepancy.branch:
                CashInventory.objects.filter(
                    inventory_date=discrepancy.discrepancy_date,
                    branch=discrepancy.branch
                ).update(
                    actual_amount=discrepancy.new_amount,
                    is_confirmed=True,
                    confirmed_by=request.user,
                    confirmed_at=timezone.now()
                )
            elif discrepancy.investor:
                CashInventory.objects.filter(
                    inventory_date=discrepancy.discrepancy_date,
                    investor=discrepancy.investor
                ).update(
                    actual_amount=discrepancy.new_amount,
                    is_confirmed=True,
                    confirmed_by=request.user,
                    confirmed_at=timezone.now()
                )

        elif action == 'adjust':
            # برگشت به مبلغ قبلی
            discrepancy.status = 'reviewed'
            discrepancy.reviewed_by = request.user
            discrepancy.review_date = timezone.now()
            discrepancy.review_notes = resolution_notes

            # بروزرسانی موجودی با مبلغ قبلی
            if discrepancy.branch:
                CashInventory.objects.filter(
                    inventory_date=discrepancy.discrepancy_date,
                    branch=discrepancy.branch
                ).update(
                    actual_amount=discrepancy.old_amount
                )
            elif discrepancy.investor:
                CashInventory.objects.filter(
                    inventory_date=discrepancy.discrepancy_date,
                    investor=discrepancy.investor
                ).update(
                    actual_amount=discrepancy.old_amount
                )

        discrepancy.save()

        return JsonResponse({
            'status': 'success',
            'message': 'مغایرت با موفقیت پردازش شد.'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# جستجوی سرمایه‌گذار با کد ملی (Ajax)
@login_required
@require_GET
def search_investor(request):
    national_id = request.GET.get('national_id', '')

    if not national_id:
        return JsonResponse({'status': 'error', 'message': 'کد ملی را وارد کنید.'})

    try:
        investor = accuntmodel.objects.get(melicode=national_id)

        return JsonResponse({
            'status': 'success',
            'investor': {
                'id': investor.id,
                'firstname': investor.firstname,
                'lastname': investor.lastname,
                'national_id': investor.melicode,
                'phone': investor.phonnumber,
            }
        })
    except accuntmodel.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'سرمایه‌گذار یافت نشد.'})


# دریافت لیست حساب‌های اعتباری (Ajax)
@login_required
@require_GET
def get_credit_accounts(request):
    accounts = CreditPayment.objects.filter(
        remaining_amount__gt=0
    ).select_related('invoice', 'invoice__branch')

    account_list = []
    for account in accounts:
        account_list.append({
            'id': account.id,
            'customer_name': account.customer_name,
            'customer_family': account.customer_family,
            'national_id': account.national_id,
            'remaining_amount': account.remaining_amount,
            'due_date': account.due_date.strftime('%Y/%m/%d'),
            'branch': account.invoice.branch.name if account.invoice.branch else ''
        })

    return JsonResponse({
        'status': 'success',
        'accounts': account_list
    })


# cash_management/views.py

@login_required
@require_POST
@csrf_exempt
def get_account_inventory_data(request):
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        account_type = data.get('account_type', 'all')  # all, check, credit, pos

        # تبدیل تاریخ شمسی به میلادی
        jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian().date()

        result = {
            'status': 'success',
            'date': date_str,
            'account_type': account_type,
            'accounts': [],
            'total_invoices': 0,
            'total_amount': 0,
            'confirmed_count': 0,
            'pending_count': 0
        }

        # فاکتورهای با روش پرداخت غیر نقدی
        invoices = Invoicefrosh.objects.filter(
            payment_date__date=gregorian_date,
            is_paid=True,
            payment_method__in=['check', 'credit', 'pos']
        )

        # فیلتر بر اساس نوع حساب
        if account_type != 'all':
            invoices = invoices.filter(payment_method=account_type)

        for invoice in invoices:
            # محاسبه مبلغ باقیمانده برای فاکتورهای اعتباری
            if invoice.payment_method == 'credit':
                credit_payments = CreditPayment.objects.filter(invoice=invoice)
                remaining_amount = sum(payment.remaining_amount for payment in credit_payments)
            else:
                remaining_amount = invoice.paid_amount

            # وضعیت تایید
            is_confirmed = invoice.is_finalized

            account_info = {
                'id': invoice.id,
                'invoice_number': invoice.id,
                'invoice_id': invoice.id,
                'branch_name': invoice.branch.name if invoice.branch else '',
                'customer_name': f"{invoice.customer_name} {invoice.customer_family}" if invoice.customer_name else '',
                'account_type': invoice.payment_method,
                'amount': remaining_amount,
                'due_date': invoice.payment_date.strftime('%Y/%m/%d'),
                'status': 'confirmed' if is_confirmed else 'pending',
                'is_confirmed': is_confirmed
            }

            result['accounts'].append(account_info)
            result['total_invoices'] += 1
            result['total_amount'] += remaining_amount

            if is_confirmed:
                result['confirmed_count'] += 1
            else:
                result['pending_count'] += 1

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def get_expenses_for_payment(request):
    try:
        data = json.loads(request.body)
        from_date_str = data.get('from_date')
        to_date_str = data.get('to_date')
        status = data.get('status', 'pending')

        # تبدیل تاریخ شمسی به میلادی
        jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d')
        gregorian_from = jalali_from.togregorian().date()

        jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
        gregorian_to = jalali_to.togregorian().date()

        # فیلتر هزینه‌ها
        expenses = CashExpense.objects.filter(
            expense_date__range=[gregorian_from, gregorian_to]
        )

        if status != 'all':
            expenses = expenses.filter(payment_status=status)

        expenses_list = []
        total_pending = 0
        total_paid = 0

        for expense in expenses:
            expense_data = {
                'id': expense.id,
                'title': expense.title,
                'expense_type': expense.expense_type,
                'amount': expense.amount,
                'expense_date': expense.get_jalali_date(),
                'branch_name': expense.branch.name if expense.branch else '-',
                'payment_method': expense.payment_method,
                'payment_status': expense.payment_status,
                'description': expense.description[:50] + '...' if expense.description and len(
                    expense.description) > 50 else expense.description or ''
            }

            expenses_list.append(expense_data)

            if expense.payment_status == 'pending':
                total_pending += expense.amount
            elif expense.payment_status == 'paid':
                total_paid += expense.amount

        return JsonResponse({
            'status': 'success',
            'expenses': expenses_list,
            'count': len(expenses_list),
            'pending_amount': total_pending,
            'paid_amount': total_paid,
            'pending_count': expenses.filter(payment_status='pending').count()
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def process_payments(request):
    try:
        data = json.loads(request.body)
        expense_ids = data.get('expense_ids', [])
        payment_date_str = data.get('payment_date')
        notes = data.get('notes', '')

        # تبدیل تاریخ پرداخت
        jalali_date = jdatetime.datetime.strptime(payment_date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian().date()

        # به‌روزرسانی وضعیت هزینه‌ها
        updated_count = CashExpense.objects.filter(
            id__in=expense_ids,
            payment_status='pending'
        ).update(
            payment_status='paid',
            paid_at=timezone.now()
        )

        return JsonResponse({
            'status': 'success',
            'message': f'{updated_count} هزینه با موفقیت پرداخت شد.',
            'updated_count': updated_count
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def register_expense(request):
    try:
        # دریافت داده‌ها از فرم
        title = request.POST.get('title')
        expense_type = request.POST.get('expense_type')
        amount = int(request.POST.get('amount', 0))
        date_str = request.POST.get('expense_date')
        branch_id = request.POST.get('branch')
        payment_method = request.POST.get('payment_method')
        description = request.POST.get('description', '')

        # تبدیل تاریخ
        jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian().date()

        # پیدا کردن شعبه
        branch = None
        if branch_id:
            branch = Branch.objects.get(id=branch_id)

        # ایجاد هزینه جدید
        expense = CashExpense.objects.create(
            title=title,
            expense_type=expense_type,
            amount=amount,
            expense_date=gregorian_date,
            branch=branch,
            payment_method=payment_method,
            description=description,
            created_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'message': 'هزینه با موفقیت ثبت شد.',
            'expense_id': expense.id
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_GET
def get_today_expenses(request):
    try:
        today = timezone.now().date()

        # تبدیل امروز به شمسی برای نمایش
        today_jalali = jdatetime.date.fromgregorian(date=today)

        # هزینه‌های امروز
        expenses = CashExpense.objects.filter(
            created_at__date=today
        ).select_related('branch')

        expenses_list = []
        total = 0

        for expense in expenses:
            expense_data = {
                'id': expense.id,
                'title': expense.title,
                'expense_type': expense.expense_type,
                'amount': expense.amount,
                'expense_date': expense.get_jalali_date(),
                'branch_name': expense.branch.name if expense.branch else '-',
                'payment_status': expense.payment_status,
                'description': expense.description
            }

            expenses_list.append(expense_data)
            total += expense.amount

        return JsonResponse({
            'status': 'success',
            'expenses': expenses_list,
            'count': len(expenses_list),
            'total': total,
            'today': today_jalali.strftime('%Y/%m/%d')
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def delete_expense(request, expense_id):
    try:
        expense = get_object_or_404(CashExpense, id=expense_id)

        # فقط هزینه‌هایی که پرداخت نشده‌اند قابل حذف هستند
        if expense.payment_status == 'paid':
            return JsonResponse({
                'status': 'error',
                'message': 'هزینه پرداخت شده قابل حذف نیست.'
            })

        expense.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'هزینه با موفقیت حذف شد.'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def get_discrepancies(request):
    try:
        data = json.loads(request.body)
        from_date_str = data.get('from_date')
        to_date_str = data.get('to_date')
        status = data.get('status', 'all')
        type_filter = data.get('type', 'all')

        # تبدیل تاریخ
        jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d')
        gregorian_from = jalali_from.togregorian().date()

        jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
        gregorian_to = jalali_to.togregorian().date()

        # فیلتر مغایرت‌ها
        discrepancies = DiscrepancyLog.objects.filter(
            discrepancy_date__range=[gregorian_from, gregorian_to]
        )

        if status != 'all':
            discrepancies = discrepancies.filter(status=status)

        if type_filter != 'all':
            if type_filter == 'branch':
                discrepancies = discrepancies.filter(branch__isnull=False)
            elif type_filter == 'investor':
                discrepancies = discrepancies.filter(investor__isnull=False)

        discrepancies_list = []
        total_difference = 0
        pending_count = 0
        resolved_count = 0

        for disc in discrepancies:
            discrepancy_data = {
                'id': disc.id,
                'discrepancy_date': disc.discrepancy_date.strftime('%Y/%m/%d'),
                'type': 'branch' if disc.branch else 'investor',
                'name': disc.branch.name if disc.branch else f"{disc.investor.firstname} {disc.investor.lastname}",
                'old_amount': disc.old_amount,
                'new_amount': disc.new_amount,
                'difference': disc.difference,
                'description': disc.description,
                'status': disc.status,
                'user_name': disc.user.get_full_name() if disc.user else '',
                'created_at': disc.created_at.strftime('%Y/%m/%d %H:%M')
            }

            discrepancies_list.append(discrepancy_data)
            total_difference += disc.difference

            if disc.status == 'pending':
                pending_count += 1
            elif disc.status == 'resolved':
                resolved_count += 1

        return JsonResponse({
            'status': 'success',
            'discrepancies': discrepancies_list,
            'total': len(discrepancies_list),
            'pending': pending_count,
            'resolved': resolved_count,
            'total_difference': total_difference
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_GET
def get_discrepancy_detail(request, discrepancy_id):
    try:
        discrepancy = get_object_or_404(DiscrepancyLog, id=discrepancy_id)

        return JsonResponse({
            'status': 'success',
            'discrepancy': {
                'id': discrepancy.id,
                'discrepancy_date': discrepancy.discrepancy_date.strftime('%Y/%m/%d'),
                'type': 'branch' if discrepancy.branch else 'investor',
                'name': discrepancy.branch.name if discrepancy.branch else f"{discrepancy.investor.firstname} {discrepancy.investor.lastname}",
                'old_amount': discrepancy.old_amount,
                'new_amount': discrepancy.new_amount,
                'difference': discrepancy.difference,
                'description': discrepancy.description,
                'status': discrepancy.status,
                'user_name': discrepancy.user.get_full_name() if discrepancy.user else '',
                'created_at': discrepancy.created_at.strftime('%Y/%m/%d %H:%M')
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# -----------------------------سرمایه گزاری------------------------------------------------------
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .forms import InvestmentForm
from .models import Investment
from cantact_app.models import accuntmodel
from invoice_app.models import Paymentnumber


def number_to_words(num):
    """تبدیل عدد به حروف فارسی - نسخه ساده"""
    if num == 0:
        return 'صفر'

    # واحدها
    ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه']
    tens = ['', 'ده', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
    hundreds = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
    teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']

    def convert_three_digits(n):
        """تبدیل سه رقم به حروف"""
        result = ''

        # صدگان
        if n >= 100:
            result += hundreds[n // 100] + ' و '
            n %= 100

        # دهگان و یکان
        if n >= 20:
            result += tens[n // 10]
            if n % 10 > 0:
                result += ' و ' + ones[n % 10]
        elif n >= 10:
            result += teens[n - 10]
        elif n > 0:
            result += ones[n]

        return result.rstrip(' و ')

    # جداکننده هزارگان
    result = ''

    # میلیارد
    if num >= 1000000000:
        result += convert_three_digits(num // 1000000000) + ' میلیارد و '
        num %= 1000000000

    # میلیون
    if num >= 1000000:
        result += convert_three_digits(num // 1000000) + ' میلیون و '
        num %= 1000000

    # هزار
    if num >= 1000:
        thousand_part = num // 1000
        if thousand_part == 1:
            result += 'هزار و '
        else:
            result += convert_three_digits(thousand_part) + ' هزار و '
        num %= 1000

    # واحد
    if num > 0:
        result += convert_three_digits(num)

    # حذف " و " اضافی در انتها
    result = result.rstrip(' و ')

    return result + ' تومان'


@csrf_exempt
def check_melicode(request):
    """بررسی وجود کد ملی در دیتابیس"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            melicode = data.get('melicode', '')

            if len(melicode) != 10 or not melicode.isdigit():
                return JsonResponse({
                    'exists': False,
                    'message': 'کد ملی باید 10 رقم باشد'
                })

            try:
                investor = accuntmodel.objects.get(melicode=melicode)
                return JsonResponse({
                    'exists': True,
                    'firstname': investor.firstname or '',
                    'lastname': investor.lastname or '',
                    'fullname': f"{investor.firstname or ''} {investor.lastname or ''}".strip()
                })
            except accuntmodel.DoesNotExist:
                return JsonResponse({
                    'exists': False,
                    'message': 'کد ملی در سیستم وجود ندارد. لطفا ابتدا ثبت نام کنید.'
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'داده نامعتبر'}, status=400)

    return JsonResponse({'error': 'متد نامعتبر'}, status=400)


@csrf_exempt
def convert_amount_to_words(request):
    """تبدیل مبلغ به حروف"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount_str = data.get('amount', '0')

            try:
                amount_int = int(amount_str)
                if amount_int <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'مبلغ باید بزرگتر از صفر باشد'
                    })

                words = number_to_words(amount_int)
                return JsonResponse({
                    'success': True,
                    'amount_letters': words
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'مبلغ نامعتبر است'
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'داده نامعتبر'}, status=400)

    return JsonResponse({'error': 'متد نامعتبر'}, status=400)


from datetime import datetime
import jdatetime


def investment_registration(request):
    """صفحه ثبت سرمایه‌گذاری"""
    payment_accounts = Paymentnumber.objects.filter(is_active=True)

    if request.method == 'POST':
        melicode = request.POST.get('melicode', '').strip()
        investment_date = request.POST.get('investment_date')  # تاریخ شمسی
        gregorian_date = request.POST.get('gregorian_date')  # تاریخ میلادی از فیلد مخفی
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        payment_account_id = request.POST.get('payment_account')

        # بررسی کد ملی
        if not melicode or len(melicode) != 10 or not melicode.isdigit():
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'کد ملی باید 10 رقم باشد',
                'payment_accounts': payment_accounts
            })

        try:
            investor = accuntmodel.objects.get(melicode=melicode)
        except accuntmodel.DoesNotExist:
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'کد ملی در سیستم وجود ندارد. لطفا ابتدا ثبت نام کنید.',
                'payment_accounts': payment_accounts
            })

        # بررسی مبلغ
        try:
            amount_int = int(amount)
            if amount_int <= 0:
                return render(request, 'cash_management/investment_registration.html', {
                    'error': 'مبلغ باید بزرگتر از صفر باشد',
                    'payment_accounts': payment_accounts
                })
        except (ValueError, TypeError):
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'مبلغ نامعتبر است',
                'payment_accounts': payment_accounts
            })

        # بررسی روش پرداخت
        if payment_method == 'bank_transfer' and not payment_account_id:
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'برای روش واریز به حساب، لطفاً حساب بانکی را انتخاب کنید.',
                'payment_accounts': payment_accounts
            })

        # **تبدیل تاریخ به میلادی**
        investment_date_obj = None

        # اولویت اول: استفاده از تاریخ میلادی ارسال شده از فیلد مخفی
        if gregorian_date:
            try:
                investment_date_obj = datetime.strptime(gregorian_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        # اگر تاریخ میلادی معتبر نبود، تاریخ شمسی را تبدیل کنیم
        if not investment_date_obj and investment_date:
            try:
                # حذف فاصله و نرمال‌سازی تاریخ
                investment_date_clean = investment_date.strip()

                # جدا کردن بخش‌های تاریخ
                # فرض بر این است که فرمت: ۱۴۰۴/۰۹/۰۱
                parts = investment_date_clean.split('/')
                if len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])

                    # تبدیل تاریخ شمسی به میلادی
                    jalali_date = jdatetime.date(year, month, day)
                    gregorian_date_obj = jalali_date.togregorian()
                    investment_date_obj = gregorian_date_obj
                else:
                    return render(request, 'cash_management/investment_registration.html', {
                        'error': 'فرمت تاریخ نامعتبر است. باید به فرمت ۱۴۰۴/۰۹/۰۱ باشد.',
                        'payment_accounts': payment_accounts
                    })
            except (ValueError, IndexError, AttributeError) as e:
                return render(request, 'cash_management/investment_registration.html', {
                    'error': f'تاریخ وارد شده معتبر نیست: {str(e)}',
                    'payment_accounts': payment_accounts
                })

        if not investment_date_obj:
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'تاریخ وارد نشده یا نامعتبر است',
                'payment_accounts': payment_accounts
            })

        # ایجاد رکورد سرمایه‌گذاری
        try:
            investment = Investment(
                investor=investor,
                investment_date=investment_date_obj,  # تاریخ میلادی
                amount=amount_int,
                amount_letters=number_to_words(amount_int),
                payment_method=payment_method
            )

            if payment_method == 'bank_transfer' and payment_account_id:
                payment_account = Paymentnumber.objects.get(id=payment_account_id, is_active=True)
                investment.payment_account = payment_account

            investment.save()

            # ثبت موفق
            return render(request, 'cash_management/investment_registration.html', {
                'success_message': f'سرمایه‌گذاری با موفقیت ثبت شد. تاریخ: {investment_date}',
                'payment_accounts': payment_accounts
            })

        except Exception as e:
            return render(request, 'cash_management/investment_registration.html', {
                'error': f'خطا در ثبت اطلاعات: {str(e)}',
                'payment_accounts': payment_accounts
            })

    # درخواست GET
    return render(request, 'cash_management/investment_registration.html', {
        'payment_accounts': payment_accounts
    })


# --------------------------------------------------------گزارش سرمایه گداری-------------------------------------------------
#
# import jdatetime
# from datetime import datetime, timedelta
# from django.db.models import Sum, Count, Q, Max, Min
# from django.db.models.functions import TruncMonth, TruncYear
#
#
# def investment_report_view(request):
#     """گزارش سرمایه‌گذاری‌ها"""
#
#     # تاریخ امروز شمسی
#     today_jalali = jdatetime.date.today()
#
#     # پارامترهای فیلتر
#     payment_method = request.GET.get('payment_method', 'all')
#     filter_type = request.GET.get('filter_type', 'monthly')
#
#     # مقادیر پیش‌فرض - سال و ماه شمسی
#     try:
#         year = int(request.GET.get('year', today_jalali.year))
#     except:
#         year = today_jalali.year
#
#     try:
#         month = int(request.GET.get('month', today_jalali.month))
#     except:
#         month = today_jalali.month
#
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')
#
#     # ایجاد کوئری پایه
#     investments = Investment.objects.all().select_related(
#         'investor', 'payment_account'
#     ).order_by('-investment_date')
#
#     # فیلتر بر اساس روش پرداخت
#     if payment_method != 'all':
#         investments = investments.filter(payment_method=payment_method)
#
#     # فیلتر بر اساس نوع گزارش
#     if filter_type == 'monthly':
#         try:
#             # تبدیل سال و ماه شمسی به میلادی
#             jalali_start = jdatetime.date(year, month, 1)
#
#             # محاسبه آخر ماه شمسی
#             if month == 12:
#                 next_month = jdatetime.date(year + 1, 1, 1)
#             else:
#                 next_month = jdatetime.date(year, month + 1, 1)
#
#             jalali_end = next_month - timedelta(days=1)
#
#             gregorian_start = jalali_start.togregorian()
#             gregorian_end = jalali_end.togregorian()
#
#             investments = investments.filter(
#                 investment_date__gte=gregorian_start,
#                 investment_date__lte=gregorian_end
#             )
#         except Exception as e:
#             # در صورت خطا، فیلتر نزنیم
#             print(f"خطا در فیلتر ماهانه: {e}")
#
#     elif filter_type == 'yearly':
#         try:
#             jalali_start = jdatetime.date(year, 1, 1)
#             jalali_end = jdatetime.date(year, 12, 29)
#
#             investments = investments.filter(
#                 investment_date__gte=jalali_start.togregorian(),
#                 investment_date__lte=jalali_end.togregorian()
#             )
#         except Exception as e:
#             print(f"خطا در فیلتر سالانه: {e}")
#
#     elif filter_type == 'custom' and start_date and end_date:
#         try:
#             # تبدیل تاریخ‌های شمسی به میلادی
#             start_parts = start_date.split('/')
#             end_parts = end_date.split('/')
#
#             if len(start_parts) == 3 and len(end_parts) == 3:
#                 jalali_start = jdatetime.date(
#                     int(start_parts[0]), int(start_parts[1]), int(start_parts[2])
#                 )
#                 jalali_end = jdatetime.date(
#                     int(end_parts[0]), int(end_parts[1]), int(end_parts[2])
#                 )
#
#                 investments = investments.filter(
#                     investment_date__gte=jalali_start.togregorian(),
#                     investment_date__lte=jalali_end.togregorian()
#                 )
#         except Exception as e:
#             print(f"خطا در فیلتر بازه دلخواه: {e}")
#
#     # محاسبات آماری
#     total_amount = investments.aggregate(total=Sum('amount'))['total'] or 0
#     investment_count = investments.count()
#     average_amount = total_amount / investment_count if investment_count > 0 else 0
#
#     # گروه‌بندی بر اساس روش پرداخت
#     by_payment_method = investments.values('payment_method').annotate(
#         total=Sum('amount'),
#         count=Count('id')
#     ).order_by('-total')
#
#     # گروه‌بندی بر اساس سرمایه‌گذار
#     by_investor = investments.values(
#         'investor__id',
#         'investor__firstname',
#         'investor__lastname',
#         'investor__melicode'
#     ).annotate(
#         total=Sum('amount'),
#         count=Count('id')
#     ).order_by('-total')[:10]
#
#     # لیست سال‌های موجود (شمسی)
#     years_jalali = []
#
#     # روش ۱: استخراج از تاریخ‌های موجود
#     distinct_dates = Investment.objects.dates('investment_date', 'month')
#     for date in distinct_dates:
#         try:
#             jalali_date = jdatetime.date.fromgregorian(date=date)
#             if jalali_date.year not in years_jalali:
#                 years_jalali.append(jalali_date.year)
#         except:
#             continue
#
#     # اگر سالی وجود نداشت، سال جاری را اضافه کن
#     if not years_jalali:
#         years_jalali.append(today_jalali.year)
#
#     # مرتب‌سازی نزولی
#     years_jalali.sort(reverse=True)
#
#     # اگر سال جاری در لیست نیست، اضافه کن
#     if today_jalali.year not in years_jalali:
#         years_jalali.insert(0, today_jalali.year)
#
#     # نام‌های فارسی ماه‌ها
#     persian_months = [
#         (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
#         (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
#         (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
#         (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
#     ]
#
#     # پیش‌پردازش سرمایه‌گذاری‌ها برای template
#     investments_list = []
#     for inv in investments:
#         # تبدیل تاریخ به شمسی برای نمایش
#         try:
#             inv.jalali_date = jdatetime.date.fromgregorian(date=inv.investment_date)
#             inv.jalali_date_str = inv.jalali_date.strftime('%Y/%m/%d')
#         except:
#             inv.jalali_date_str = str(inv.investment_date)
#         investments_list.append(inv)
#
#     # آماده‌سازی context
#     context = {
#         'investments': investments_list,
#         'total_amount': total_amount,
#         'investment_count': investment_count,
#         'average_amount': average_amount,
#         'by_payment_method': by_payment_method,
#         'by_investor': by_investor,
#         'years': years_jalali,  # سال‌های شمسی
#         'persian_months': persian_months,
#         'payment_method': payment_method,
#         'filter_type': filter_type,
#         'selected_year': year,
#         'selected_month': month,
#         'start_date': start_date,
#         'end_date': end_date,
#         'today_jalali': today_jalali.strftime('%Y/%m/%d'),
#         'payment_methods': Investment.PAYMENT_METHOD_CHOICES,
#     }
#
#     return render(request, 'cash_management/investment_report.html', context)

import jdatetime
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, Min, Max
from django.shortcuts import render
from .models import Investment
from invoice_app.models import Paymentnumber


def investment_report_view(request):
    """گزارش سرمایه‌گذاری‌ها"""

    # تاریخ امروز شمسی
    today_jalali = jdatetime.date.today()

    # پارامترهای فیلتر
    payment_method = request.GET.get('payment_method', 'all')
    filter_type = request.GET.get('filter_type', 'monthly')
    account_id = request.GET.get('account_id', 'all')

    # مقادیر پیش‌فرض - سال و ماه شمسی
    try:
        year = int(request.GET.get('year', today_jalali.year))
    except:
        year = today_jalali.year

    try:
        month = int(request.GET.get('month', today_jalali.month))
    except:
        month = today_jalali.month

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # ایجاد کوئری پایه
    investments = Investment.objects.all().select_related(
        'investor', 'payment_account'
    ).order_by('-investment_date')

    # فیلتر بر اساس روش پرداخت
    if payment_method != 'all':
        investments = investments.filter(payment_method=payment_method)

    # فیلتر بر اساس حساب بانکی
    if account_id != 'all' and account_id:
        try:
            account_id_int = int(account_id)
            investments = investments.filter(payment_account_id=account_id_int)
        except (ValueError, TypeError):
            # اگر account_id معتبر نیست، نادیده بگیر
            pass

    # فیلتر بر اساس نوع گزارش
    if filter_type == 'monthly':
        try:
            # تبدیل سال و ماه شمسی به میلادی
            jalali_start = jdatetime.date(year, month, 1)

            # محاسبه آخر ماه شمسی
            if month == 12:
                next_month = jdatetime.date(year + 1, 1, 1)
            else:
                next_month = jdatetime.date(year, month + 1, 1)

            jalali_end = next_month - timedelta(days=1)

            gregorian_start = jalali_start.togregorian()
            gregorian_end = jalali_end.togregorian()

            investments = investments.filter(
                investment_date__gte=gregorian_start,
                investment_date__lte=gregorian_end
            )
        except Exception as e:
            # در صورت خطا، فیلتر نزنیم
            print(f"خطا در فیلتر ماهانه: {e}")

    elif filter_type == 'yearly':
        try:
            jalali_start = jdatetime.date(year, 1, 1)
            jalali_end = jdatetime.date(year, 12, 29)

            investments = investments.filter(
                investment_date__gte=jalali_start.togregorian(),
                investment_date__lte=jalali_end.togregorian()
            )
        except Exception as e:
            print(f"خطا در فیلتر سالانه: {e}")

    elif filter_type == 'custom' and start_date and end_date:
        try:
            # تبدیل تاریخ‌های شمسی به میلادی
            start_parts = start_date.split('/')
            end_parts = end_date.split('/')

            if len(start_parts) == 3 and len(end_parts) == 3:
                jalali_start = jdatetime.date(
                    int(start_parts[0]), int(start_parts[1]), int(start_parts[2])
                )
                jalali_end = jdatetime.date(
                    int(end_parts[0]), int(end_parts[1]), int(end_parts[2])
                )

                investments = investments.filter(
                    investment_date__gte=jalali_start.togregorian(),
                    investment_date__lte=jalali_end.togregorian()
                )
        except Exception as e:
            print(f"خطا در فیلتر بازه دلخواه: {e}")

    # محاسبات آماری
    total_amount = investments.aggregate(total=Sum('amount'))['total'] or 0
    investment_count = investments.count()
    average_amount = total_amount / investment_count if investment_count > 0 else 0

    # گروه‌بندی بر اساس روش پرداخت
    by_payment_method = investments.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # گروه‌بندی بر اساس سرمایه‌گذار
    by_investor = investments.values(
        'investor__id',
        'investor__firstname',
        'investor__lastname',
        'investor__melicode'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]

    # گروه‌بندی بر اساس حساب بانکی
    by_payment_account = investments.values(
        'payment_account__id',
        'payment_account__name',
        'payment_account__bank_name',
        'payment_account__account_number'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # لیست حساب‌های بانکی فعال
    payment_accounts = Paymentnumber.objects.filter(is_active=True).order_by('name')

    # لیست سال‌های موجود (شمسی)
    years_jalali = []

    # روش 1: استفاده از Min و Max (بهینه)
    try:
        earliest_date = Investment.objects.aggregate(earliest=Min('investment_date'))['earliest']
        latest_date = Investment.objects.aggregate(latest=Max('investment_date'))['latest']

        if earliest_date and latest_date:
            try:
                jalali_earliest = jdatetime.date.fromgregorian(date=earliest_date)
                jalali_latest = jdatetime.date.fromgregorian(date=latest_date)

                for y in range(jalali_earliest.year, jalali_latest.year + 1):
                    years_jalali.append(y)
            except:
                years_jalali.append(today_jalali.year)
    except:
        # اگر خطا خورد، از روش جایگزین استفاده کن
        years_jalali = []
        distinct_dates = Investment.objects.dates('investment_date', 'year')
        for date in distinct_dates:
            try:
                jalali_date = jdatetime.date.fromgregorian(date=date)
                if jalali_date.year not in years_jalali:
                    years_jalali.append(jalali_date.year)
            except:
                continue

    # اگر لیست سال‌ها خالی است، سال جاری را اضافه کن
    if not years_jalali:
        years_jalali.append(today_jalali.year)

    # مرتب‌سازی نزولی
    years_jalali.sort(reverse=True)

    # اگر سال جاری در لیست نیست، اضافه کن
    if today_jalali.year not in years_jalali:
        years_jalali.insert(0, today_jalali.year)

    # نام‌های فارسی ماه‌ها
    persian_months = [
        (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
        (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
        (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
        (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
    ]

    # پیش‌پردازش سرمایه‌گذاری‌ها برای template
    investments_list = []
    for inv in investments:
        # تبدیل تاریخ به شمسی برای نمایش
        try:
            inv.jalali_date = jdatetime.date.fromgregorian(date=inv.investment_date)
            inv.jalali_date_str = inv.jalali_date.strftime('%Y/%m/%d')
        except:
            inv.jalali_date_str = str(inv.investment_date)
        investments_list.append(inv)

    # آماده‌سازی context
    context = {
        'investments': investments_list,
        'total_amount': total_amount,
        'investment_count': investment_count,
        'average_amount': average_amount,
        'by_payment_method': by_payment_method,
        'by_investor': by_investor,
        'by_payment_account': by_payment_account,
        'payment_accounts': payment_accounts,
        'years': years_jalali,
        'persian_months': persian_months,
        'payment_method': payment_method,
        'account_id': account_id,
        'filter_type': filter_type,
        'selected_year': year,
        'selected_month': month,
        'start_date': start_date,
        'end_date': end_date,
        'today_jalali': today_jalali.strftime('%Y/%m/%d'),
        'payment_methods': Investment.PAYMENT_METHOD_CHOICES,
    }

    return render(request, 'cash_management/investment_report.html', context)