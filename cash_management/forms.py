from django import forms
from .models import Investment, DailyCashAdjustment
from cantact_app.models import accuntmodel
from invoice_app.models import Paymentnumber


class InvestmentForm(forms.ModelForm):
    melicode = forms.CharField(
        max_length=10,
        label='کد ملی',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'کد ملی را وارد کنید',
            'id': 'melicode_input'
        })
    )

    investment_date = forms.DateField(
        label='تاریخ سرمایه‌گذاری',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'investment_date'
        })
    )

    amount = forms.IntegerField(
        label='مبلغ سرمایه‌گذاری (تومان)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'مبلغ را وارد کنید',
            'id': 'amount_input'
        })
    )

    payment_method = forms.ChoiceField(
        label='روش پرداخت',
        choices=Investment.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
            'id': 'payment_method'
        })
    )

    payment_account = forms.ModelChoiceField(
        queryset=Paymentnumber.objects.filter(is_active=True),
        label='انتخاب حساب',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'payment_account'
        })
    )

    class Meta:
        model = Investment
        fields = ['investment_date', 'amount', 'payment_method', 'payment_account']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_account'].queryset = Paymentnumber.objects.filter(is_active=True)


class AdjustmentForm(forms.ModelForm):
    class Meta:
        model = DailyCashAdjustment
        fields = ['adjustment_type', 'description', 'amount', 'is_positive']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }