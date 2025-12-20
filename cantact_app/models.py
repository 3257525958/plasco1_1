
from django.db import models


class accuntmodel(models.Model):
    firstname = models.CharField(max_length=100 ,null=True)
    lastname = models.CharField(max_length=100 ,null=True)
    melicode = models.CharField(max_length=15 , default='0',null=True)
    phonnumber = models.CharField(max_length=11 ,null=True, default='0')
    savesabt = models.CharField(max_length=100,null=True)
    pasword = models.CharField(max_length=100,null=True)
    level = models.CharField(max_length=50,default='دسترسی معمولی' ,null=True)
    dayb = models.CharField(max_length=3 , default='0',null=True)
    mountb = models.CharField(max_length=20 , default='0',null=True)
    yearb = models.CharField(max_length=5, default='0',null=True)
    profile_picture = models.ImageField(upload_to='profilepics/', null=True, blank=True,)


    def __str__(self):
        return f"{self.melicode}"
class savecodphon(models.Model):
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    melicode = models.CharField(max_length=20 , default="0")
    phonnumber = models.CharField(max_length=20 , default="0")
    berthdayyear = models.CharField(max_length=100)
    berthdayday = models.CharField(max_length=100)
    berthdaymounth = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    expaiercode = models.CharField(max_length=20)
    profile_picture = models.ImageField(upload_to='profilepicstest/', null=True, blank=True)
    def __str__(self):
        return f"{self.melicode}"



class dataacont(models.Model):
    firstname = models.CharField(max_length=100,null=True)
    lastname = models.CharField(max_length=100,null=True)
    melicode = models.CharField(max_length=20 , default="0")
    phonnumber = models.CharField(max_length=20 , default="0")
    berthday = models.CharField(max_length=100,null=True)
    miladiarray = models.CharField(max_length=5000 , default="0")
    shamsiarray = models.CharField(max_length=5000 , default="0")
    showclandarray = models.CharField(max_length=5000 , default="0")
    def __str__(self):
        return f"{self.melicode}"


class phonnambermodel(models.Model):
    name = models.CharField(max_length=100,default="0")
    lastname = models.CharField(max_length=100, default="0")
    phonnumber = models.CharField(max_length=20 , default="0")
    saver = models.CharField(max_length=20 , default="0")
    def __str__(self):
        return f"{self.phonnumber}"
# ----------------------------ثبت شعب-----------------------------------------
from django.db import models
from django.core.exceptions import ValidationError
import re


def validate_english_numbers(value):
    if value and not re.match(r'^[0-9]*$', value):
        raise ValidationError('لطفاً فقط از اعداد انگلیسی استفاده کنید.')


class Branch(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام شعبه")
    address = models.TextField(verbose_name="آدرس شعبه")
    sellers = models.ManyToManyField('accuntmodel', blank=True, verbose_name="فروشندگان")
    modem_ip = models.GenericIPAddressField(
        verbose_name="IP مودم",
        blank=True,
        null=True,
        help_text="آدرس IP مودم شعبه"
    )

    class Meta:
        verbose_name = "شعبه"
        verbose_name_plural = "شعب"

    def __str__(self):
        return self.name

class BranchAdmin(models.Model):
    branch = models.OneToOneField(Branch, on_delete=models.CASCADE, verbose_name="شعبه")
    admin_user = models.ForeignKey('accuntmodel', on_delete=models.CASCADE, verbose_name="مدیر شعبه")

    class Meta:
        verbose_name = "مدیر شعبه"
        verbose_name_plural = "مدیران شعب"

    def __str__(self):
        return f"{self.admin_user.firstname} {self.admin_user.lastname} - {self.branch.name}"
