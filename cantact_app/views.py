from django.shortcuts import render , redirect
import tkinter
from tkinter import messagebox
import datetime
from jalali_date import date2jalali,datetime2jalali
from datetime import timedelta
from cantact_app.models import accuntmodel,savecodphon,dataacont,phonnambermodel
from cantact_app.forms import accuntform
from kavenegar import *
import random
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login, logout
from PIL import Image
import os
import shutil
from django.conf import settings

# ابتدا ماژول‌های استاندارد
import os
from pathlib import Path

# سپس ماژول‌های جانبی
# import torch
from django.core.files import File



# import matplotlib
# matplotlib.use('Agg')

def strb(tdef):
    x = str(datetime2jalali(tdef).strftime('%a %d %b %y'))
    rmonth = x[7:10]
    ag_month = rmonth
    if ag_month == 'Far':
        ag_month = 'فروردین'
    if ag_month == 'Ord':
        ag_month = 'اردیبهشت'
    if ag_month == 'Kho':
        ag_month = 'خرداد'
    if ag_month == 'Tir':
        ag_month = 'تیر'
    if ag_month == 'Mor':
        ag_month = 'مرداد'
    if ag_month == 'Sha':
        ag_month = 'شهریور'
    if ag_month == 'Meh':
        ag_month = 'مهر'
    if ag_month == 'Aba':
        ag_month = 'آبان'
    if ag_month == 'Aza':
        ag_month = 'آذر'
    if ag_month == 'Dey':
        ag_month = 'دی'
    if ag_month == 'Bah':
        ag_month = 'بهمن'
    if ag_month == 'Esf':
        ag_month = 'اسفند'
    rmonth = ag_month
    return (rmonth)
def strd(tdef):
    x = str(datetime2jalali(tdef).strftime('%a %d %b %y'))
    rday = x[4:6]
    if rday == '01':
        rday = '1'
    if rday == '02':
        rday = '2'
    if rday == '03':
        rday = '3'
    if rday == '04':
        rday = '4'
    if rday == '05':
        rday = '5'
    if rday == '06':
        rday = '6'
    if rday == '07':
        rday = '7'
    if rday == '08':
        rday = '8'
    if rday == '09':
        rday = '9'
    return (rday)
def cuntmounth(x):
    w = ""
    if x == 1 :
        w = "فروردین"
    if x == 2 :
        w = "اردیبهشت"
    if x == 3 :
        w = "خرداد"
    if x == 4 :
        w = "تیر"
    if x == 5 :
        w = "مرداد"
    if x == 6 :
        w = "شهریور"
    if x == 7 :
        w = "مهر"
    if x == 8 :
        w = "آبان"
    if x == 9 :
        w = "آذر"
    if x == 10 :
        w = "دی"
    if x == 11 :
        w = "بهمن"
    if x == 12 :
        w = "اسفند"
    return (w)


def stra(tdef):
    x = str(datetime2jalali(tdef).strftime('%a %d %b %y'))
    rweek = x[0:3]
    if rweek == 'Sat':
        rweek = 'شنبه'
    if rweek == 'Sun':
        rweek = 'یکشنبه'
    if rweek == 'Mon':
        rweek = 'دوشنبه'
    if rweek == 'Tue':
        rweek = 'سه‌شنبه'
    if rweek == 'Wed':
        rweek = 'چهارشنبه'
    if rweek == 'Thu':
        rweek = 'پنج‌شنبه'
    if rweek == 'Fri':
        rweek = 'جمعه'
    return (rweek)
def stry(tdef):
    x = str(datetime2jalali(tdef).strftime('%a %d %b %y'))
    ryear = x[11:]
    return (ryear)
def stradb(tdef):
    r = stra(tdef)+' '+strd(tdef)+' '+strb(tdef)
    return (r)
def stradby(tdef):
    r = stra(tdef)+' '+strd(tdef)+' '+strb(tdef)+' '+stry(tdef)
    return (r)
def stryabd(tdef):
    r = stry(tdef)+' '+stra(tdef)+' '+strb(tdef)+' '+strd(tdef)
    return (r)
def stryadb(tdef):
    r = stry(tdef)+' '+stra(tdef)+' '+strd(tdef)+' '+strb(tdef)
    return (r)
def strn():
    tx = datetime.datetime.now()
    r = stry(tx)+' '+stra(tx)+' '+strd(tx)+' '+strb(tx)
    return (r)
def strbd(tdef):
    r = strb(tdef)+' '+strd(tdef)
    return (r)

t = [datetime.datetime.now()]
t[0] = datetime.datetime.now()
# year = [int(str('14' + stry(datetime.datetime.now())))]
# year[0] = []
# year[0] =int(str('14' + stry(datetime.datetime.now())))
calandarshow = ['0']
calandarshow[0] ='0'
calandarmiladidate = [datetime.datetime.now()]
calandarmiladidate[0] = datetime.datetime.now()
calandarshamsidate = [stradby(t[0])]
calandarshamsidate [0] = stradby(t[0])
firstname_r = ['']
lastname_r = ['']
melicod_r = ['']
phonnumber_r = ['']
berthmiladi_r = [datetime.datetime.now()]
berthmiladi_r[0] = datetime.datetime.now()
melicod_etebar = ['true']
mounth_number = ['']
year = [1402]
yearjarray = ['']
yearjarray[0] = ''
mounthjarry = ['']
mounthjarry[0] = ''
dayjarray = ['']
dayjarray[0] = ''
def convert_farsi_to_english(number_str):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    translation_table = str.maketrans(persian_digits, english_digits)
    return number_str.translate(translation_table)


def dateset(datejalalifarsi):
    year = ''
    mounth = ''
    day = ''
    if datejalalifarsi != None:
        year = convert_farsi_to_english(str(datejalalifarsi).split("/")[0])
        m = convert_farsi_to_english(str(datejalalifarsi).split("/")[1])
        if m == "01":
            mounth = "فروردین"
        if m == "02":
            mounth = "اردیبهشت"
        if m == "03":
            mounth = "خرداد"
        if m == "04":
            mounth = "تیر"
        if m == "05":
            mounth = "مرداد"
        if m == "06":
            mounth = "شهریور"
        if m == "07":
            mounth = "مهر"
        if m == "08":
            mounth = "آبان"
        if m == "09":
            mounth = "آذر"
        if m == "10":
            mounth = "دی"
        if m == "11":
            mounth = "بهمن"
        if m == "12":
            mounth = "اسفند"
        day = convert_farsi_to_english(str(datejalalifarsi).split("/")[2])
        if day == '01':
            day = '1'
        if day == '02':
            day = '2'
        if day == '03':
            day = '3'
        if day == '04':
            day = '4'
        if day == '05':
            day = '5'
        if day == '06':
            day = '6'
        if day == '07':
            day = '7'
        if day == '08':
            day = '8'
        if day == '09':
            day = '9'
    return (year,mounth,day)

def format_phone_number(input_str):
    persian_numbers = {
        '0': '۰',
        '1': '۱',
        '2': '۲',
        '3': '۳',
        '4': '۴',
        '5': '۵',
        '6': '۶',
        '7': '۷',
        '8': '۸',
        '9': '۹'
    }
    result = []
    for char in input_str:
        if char in persian_numbers:
            result.append(persian_numbers[char])
    while len(result) < 11:
         result.insert(0,"0")
    telhide = result[0]+result[1]+result[2]+result[3]+result[4]+result[5]+'XXX'+result[9]+result[10]
    return telhide


def compress_and_move_images():
    # تنظیمات مسیرها
    source_dir = os.path.join(settings.MEDIA_ROOT, 'profilepicstest')
    destination_dir = os.path.join(settings.MEDIA_ROOT, 'profilepics')

    # تنظیمات فشردهسازی
    COMPRESSION_SETTINGS = {
        'JPEG_QUALITY': 85,  # بین 1-100 (بالاتر=کیفیت بهتر)
        'WEBP_QUALITY': 80,  # بین 0-100
        'PNG_COMPRESSION': 6,  # بین 0-9 (بالاتر=فشردهتر)
        'MAX_WIDTH': 1920,  # حداکثر عرض تصویر
        'MAX_HEIGHT': 1080  # حداکثر ارتفاع تصویر
    }

    # لیست پسوندهای مجاز
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

    # ایجاد پوشه مقصد
    os.makedirs(destination_dir, exist_ok=True)

    if not os.path.exists(source_dir):
        print(f"Error: Source directory not found: {source_dir}")
        return

    processed_files = 0
    errors = 0

    for filename in os.listdir(source_dir):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in image_extensions:
            continue

        source_path = os.path.join(source_dir, filename)
        base_name = os.path.splitext(filename)[0]

        try:
            # تعیین نام فایل مقصد
            if file_ext == '.bmp':
                dest_ext = '.jpg'
            else:
                dest_ext = file_ext

            destination_path = os.path.join(destination_dir, f"{base_name}{dest_ext}")

            # پردازش بر اساس نوع فایل
            if file_ext == '.gif':
                # انتقال فایلهای GIF بدون تغییر
                shutil.move(source_path, destination_path)
            else:
                with Image.open(source_path) as img:
                    # تغییر سایز اگر لازم باشد
                    img.thumbnail(
                        (COMPRESSION_SETTINGS['MAX_WIDTH'],
                         COMPRESSION_SETTINGS['MAX_HEIGHT']),
                        Image.LANCZOS
                    )

                    # تبدیل به RGB برای فرمتهای غیر شفاف
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')

                    # ذخیره با تنظیمات فشردهسازی
                    if dest_ext in ('.jpg', '.jpeg'):
                        img.save(
                            destination_path,
                            quality=COMPRESSION_SETTINGS['JPEG_QUALITY'],
                            optimize=True,
                            progressive=True
                        )
                    elif dest_ext == '.png':
                        img.save(
                            destination_path,
                            optimize=True,
                            compress_level=COMPRESSION_SETTINGS['PNG_COMPRESSION']
                        )
                    elif dest_ext == '.webp':
                        img.save(
                            destination_path,
                            quality=COMPRESSION_SETTINGS['WEBP_QUALITY'],
                            method=6
                        )
                    else:
                        img.save(destination_path)

                # حذف فایل مبدا پس از پردازش موفق
                os.remove(source_path)

            processed_files += 1
            print(f"Successfully processed: {filename}")

        except Exception as e:
            errors += 1
            print(f"Error processing {filename}: {str(e)}")

    print(f"\nOperation summary:")
    print(f"Total processed: {processed_files}")
    print(f"Successful: {processed_files - errors}")
    print(f"Errors: {errors}")


def modify_url(image_field_file):
    # استخراج نام فایل از شیء ImageFieldFile
    filename = image_field_file.name.split('/')[-1]
    # ساخت آدرس جدید
    new_url = f"profilepics/{filename}"
    return new_url


def addcantactdef(request):
    logout(request)
    profile_pic = request.FILES.get('profile_picture')
    mounth_number[0] = request.POST.get('mbtn')
    if mounth_number[0] == None :
        mounth_number[0] == ''
    bbtn = request.POST.get("bbtn")
    button_upmounth = request.POST.get("button_upmounth")
    button_downmounth = request.POST.get("button_downmounth")
    button_calandar = request.POST.get("button_calandar")
    button_back = request.POST.get("button_back")
    button_send = request.POST.get('button_send')
    buttoncode_repeat = request.POST.get('buttoncode_repeat')
    buttoncode_send = request.POST.get('buttoncode_send')
    inputcode_regester = request.POST.get('inputcode_regester')
    formuser = accuntform(request.POST, request.FILES)
    facebotton = request.POST.get("facebutton")


    birthdate = request.POST.get('birthdate')
    year, mounth, day =dateset(birthdate)

    yearj = year
    if (yearj != '') and ( yearj != None) :
        yearjarray[0] = yearj
    else: yearj = yearjarray[0]

    mounthj = mounth
    if (mounthj != '') and ( mounthj != None) :
        mounthjarry[0] = mounthj
    else: mounthj = mounthjarry[0]

    dayj = day
    if (dayj != '') and ( dayj != None) :
        dayjarray[0] = dayj
    else: dayj = dayjarray[0]

# ---------- در این قسمت داده هایی که به صفحه addcontact داده میشود در آرایه هایدمربوطه ذخیره میشه تا با زدن دکمه ها اونا نپرن ----
    input_year = request.POST.get("input_year")
    if (input_year != '') and ( input_year != None) :
        year[0] = input_year

    # ------اگر ماه رو اشتباه وارد کرده باشه و بخواد ماه رو عوض کنه روی ماه میزنه و سال صفر میشه د دوباره کلید تقویم میخورد و همه جی از اول-----
    mounthbtn = request.POST.get("mounthbtn")
    if mounthbtn == "accept":
        button_calandar = "accept"
        year[0] = []

    firstname = request.POST.get("firstname")
    if (firstname != '') and ( firstname != None) :
        firstname_r[0] = firstname
    if firstname_r[0] == None :
        firstname_r[0] = ''

    lastname = request.POST.get("lastname")
    if (lastname != '') and ( lastname != None) :
        lastname_r[0] = lastname
    if lastname_r[0] == None :
        lastname_r[0] = ''


    melicod_etebar[0] = 'f'
    melicod = convert_farsi_to_latin(request.POST.get("melicod"))

    if (melicod != '') and ( melicod != None) :
        melicod_etebar[0] = 'true'

        users = accuntmodel.objects.all()
        for user in users :
            if user.melicode == melicod :
                melicod_etebar[0] = 'false'
        melicod_r[0] = melicod

    if melicod_r[0] == None :
        melicod_r[0] = ''

    phonnumber = convert_farsi_to_latin(request.POST.get("phonnumber"))
    if (phonnumber != '') and ( phonnumber != None) :
        phonnumber_r[0] = phonnumber
    if phonnumber_r[0] == None :
        phonnumber_r[0] = ''

# --------پس از وارد کردن یک عدد چهار رقمی در باکس سال توسط جاوا دکمه battonface زده میشود در این قسمت میگوید اگر اگر زده شد یعتی سال وارد شده و پس جدول ماهها باز شور---------
    if facebotton == "accept":
        mounth_number[0] = "0"
        return render(request,'calander.html',context={
                                                       "firstname":firstname_r[0],
                                                       "lastname":lastname_r[0],
                                                       "melicod":melicod_r[0],
                                                       "phonnumber":phonnumber_r[0],
                                                        "year" : year[0],
                                                        "mounth": mounth_number[0],
                                                        "calandar_aray":calandarshow,
                                                       })
# # ****************************************************کلید برگشت**********************************************
    if button_back == "accept" :
        melicod_r[0] = ''
        # return redirect('/')
        return redirect('https://drmahdiasadpour.ir')
# ------------------------------------------------بعد از زدن دکمه ارسال در صفحه add_cantact- و یا بعد از زدن دکمه ارسال مجدد----کد ارسال میکنخ با پیامک-------------------------
    if (button_send == 'accept') or (buttoncode_repeat == 'accept'):
        if (melicod_r[0] == '') and (melicod_r[0] == None)  :
            melicod_etebar[0] = 'empty'
        if (melicod_etebar[0] == 'true') or (buttoncode_repeat == 'accept') :
            savecods = savecodphon.objects.all()
            for savecode in savecods:
                a = savecodphon.objects.filter(melicode=savecode.melicode)
                a.delete()
            randomcode = random.randint(1000, 9999)
            # randomcode = 'سلام شما به مهمانی دعوت شده اید منتظرتان هستیم'
            # randomcode=randomcode.split(' ')

            instans = savecodphon.objects.create(firstname=firstname_r[0],
                                       lastname=lastname_r[0],
                                       melicode=str(melicod_r[0]),
                                       phonnumber=str(phonnumber_r[0]),
                                       berthdayyear =str(yearj),
                                       berthdayday=str(dayj),
                                       berthdaymounth=str(mounthj),
                                       code=str(randomcode),
                                       expaiercode="2",
                                       profile_picture=profile_pic
                                       )
            instans.save()
            smstext = firstname_r[0] + ' ' + lastname_r[0] + ' ' + 'عزیز' + '\n' + 'کد چهاررقمی شما برای ثبت نام در سایت ' + ' ' + str(randomcode) + '\n' + 'با تشکر' + 'سفروشگاه لوازم آشپزخانه موسوی' + '\n' + '\n' + '\n' + 'لغو ارسال پیامک 11'
            try:
                api = KavenegarAPI(
                    '527064632B7931304866497A5376334B6B506734634E65422F627346514F59596C767475564D32656E61553D')
                params = {
                    'sender': '9982003178',  # optional
                    'receptor': phonnumber_r[0],  # multiple mobile number, split by comma
                    'message': smstext,
                }
                response = api.sms_send(params)
                telhide = format_phone_number(phonnumber_r[0])
                return render(request, 'code_cantact.html',context={'telhide':telhide})
            except APIException as e:
                m = 'tellerror'
                return render(request, 'add_cantact.html', context={'melicod_etebar': m})
            except HTTPException as e:
                m = 'neterror'
                return render(request, 'add_cantact.html', context={'melicod_etebar': m}, )
        else :
            yearcant = [0]
            yearcant.clear()
            tyear = datetime.datetime.now()
            h = int(stry(tyear)) + 1400
            while 1300 <= h:
                yearcant.append(h)
                h -= 1
            day = [1]
            hh = 1
            while hh <= 30:
                hh += 1
                day.append(hh)

            return render(request, 'new_addcontact.html', context={'melicod_etebar': melicod_etebar[0],
                                                                "yearcant": yearcant,
                                                                "day": day,
                                                                })

    # --------------------------------------------------------------------------------------------------------------------------------
    if (buttoncode_send != None) and (buttoncode_send != '') and (inputcode_regester != None) and (inputcode_regester != ''):
        savecods = savecodphon.objects.all()
        for savecode in savecods :
            if int(savecode.code) == int(inputcode_regester):
                print(inputcode_regester)
                yj = savecode.berthdayyear
                dj = savecode.berthdayday
                mj = savecode.berthdaymounth
                time = datetime.datetime.now()
                q = '14'
                while int(str(q + stry(time))) >= int(yj):
                    time -= timedelta(days=30)
                    if int(stry(time)) == int('99'):
                        q = '13'
                while int(str(q + stry(time))) == int(yj):
                    time += timedelta(days=1)
                while strb(time) != mj:
                    time += timedelta(days=1)
                while int(strd(time)) != int(dj):
                    time += timedelta(days=1)

                if User.objects.filter(username=savecode.melicode).exists():
                    a = accuntmodel.objects.filter(melicode=savecode.melicode)
                    a.delete()
                    b = User.objects.filter(username=savecode.melicode)
                    b.delete()
                # if __name__ == '__main__':
                compress_and_move_images()
                ins = accuntmodel.objects.create(
                                firstname=savecode.firstname,
                                lastname=savecode.lastname,
                                melicode=savecode.melicode,
                                phonnumber=savecode.phonnumber,
                                savesabt=stradby(datetime.datetime.now()),
                                pasword=savecode.phonnumber,
                                dayb= savecode.berthdayday,
                                mountb= savecode.berthdaymounth,
                                yearb=savecode.berthdayyear,
                                profile_picture=modify_url(savecode.profile_picture),
                )
                ins.save()
                User.objects.create_user(username=savecode.melicode,
                                        password=savecode.phonnumber,
                                        first_name=savecode.firstname,
                                        last_name=savecode.lastname,
                                            )
                user_login =authenticate(request,
                                             username=savecode.melicode,
                                             password=savecode.phonnumber,
                                             )

                login (request,user_login)
                e = 'succes'

                a = savecodphon.objects.filter(melicode=savecode.melicode)
                a.delete()

                return render(request,'code_cantact.html',context={'etebar':e},)
            else:
                e = 'false'
                return render(request, 'code_cantact.html', context={'etebar': e}, )
    yearcant = [0]
    yearcant.clear()
    tyear = datetime.datetime.now()
    h = int(stry(tyear))+1400
    while 1300 <= h :
        yearcant.append(str(h))
        h -= 1
    day = [1]
    hh = 1
    while hh <= 30 :
        hh +=1
        day.append(hh)
    return render(request,'new_addcontact.html',context={'melicod_etebar':melicod_etebar[0],
                                                                    "yearcant":yearcant,
                                                                    "day":day,
                                                                    })


login_etebar = ['f']


def convert_farsi_to_latin(input_str):
    if (input_str != None) and (input_str != None) and (input_str != ''):
        """
        اعداد فارسی موجود در رشته ورودی را به معادل لاتین تبدیل می‌کند.

        پارامترها:
            input_str (str): رشته حاوی اعداد فارسی

        بازگشت:
            str: رشته با اعداد لاتین جایگزین شده
        """
        farsi_digits = '۰۱۲۳۴۵۶۷۸۹'
        latin_digits = '0123456789'

        translation_table = str.maketrans(farsi_digits, latin_digits)
        return input_str.translate(translation_table)
    else:
        pass


def logindef(request):
    username = convert_farsi_to_latin(request.POST.get("username"))
    password = convert_farsi_to_latin(request.POST.get("password"))
    button_back = request.POST.get("button_back")
    button_send = request.POST.get("button_send")
    login_etebar[0] = 'f'

    if button_back == 'accept':
        return redirect('/')

    if button_send == 'accept':
        login_etebar[0] = 'false'
        if not username:
            login_etebar[0] = 'empty'
            return render(request, 'new_loggin.html', context={
                "firstname": firstname_r[0],
                "lastname": lastname_r[0],
                "melicod": melicod_r[0],
                "phonnumber": phonnumber_r[0],
                'login_etebar': login_etebar[0],
            })

        users = accuntmodel.objects.all()
        for user in users:
            if username == user.melicode:
                login_etebar[0] = 'false_in_paswoord'
                if password == user.pasword:
                    login_etebar[0] = 'true'

                    # ✅ به جای حذف و ایجاد جدید، بررسی کن کاربر وجود داره یا نه
                    try:
                        # اگر کاربر از قبل وجود داره، از همون استفاده کن
                        existing_user = User.objects.get(username=user.melicode)
                    except User.DoesNotExist:
                        # اگر کاربر وجود نداره، جدید ایجاد کن
                        existing_user = User.objects.create_user(
                            username=user.melicode,
                            password=user.pasword,
                            first_name=user.firstname,
                            last_name=user.lastname,
                        )

                    user_login = authenticate(
                        request,
                        username=user.melicode,
                        password=user.pasword,
                    )

                    if user_login is not None:
                        login(request, user_login)
                        # می‌تونی اینجا redirect کنی به صفحه اصلی
                        # return redirect('/')

    return render(request, 'new_loggin.html', context={
        "firstname": firstname_r[0],
        "lastname": lastname_r[0],
        "melicod": melicod_r[0],
        "phonnumber": phonnumber_r[0],
        'login_etebar': login_etebar[0],
    })
ignor_etebar = ['false']
melicod_ignor = ['']









def ignordef(request):
    ignor_etebar[0] = 'false'
    melicode = convert_farsi_to_latin(request.POST.get('melicode'))
    button_send = request.POST.get('button_send')
    buttoncode_send = request.POST.get('buttoncode_send')
    inputcode_regester = request.POST.get('inputcode_regester')
    changhbutton = request.POST.get("changhbutton")
    newpass = convert_farsi_to_latin(request.POST.get("newpass"))
    buttoncode_repeat = request.POST.get("buttoncode_repeat")
    if (melicode != '') and (melicode != None) :
        melicod_ignor[0] = melicode
    if changhbutton == "accept":
        a = accuntmodel.objects.filter(melicode=melicod_ignor[0])
        a.update(pasword=newpass)
        e = 'succes'
        return render(request,'changepaswoord.html',context={'etebar': e})

    if (buttoncode_send != None) and (buttoncode_send != '') and (inputcode_regester != None) and (inputcode_regester != ''):
        users = accuntmodel.objects.all()
        for user in users:
            if user.melicode == melicod_ignor[0]:
                if inputcode_regester == user.pasword :
                    user_login = authenticate(request,
                                                 username=melicod_ignor[0],
                                                 password=inputcode_regester,
                                             )

                    if user_login is not None :
                        login (request,user_login)
                        return render(request,'changepaswoord.html')
                else:
                    e = 'false'
                    return render(request, 'code_cantact.html', context={'etebar': e}, )

    if (button_send == 'accept') or (buttoncode_repeat == 'accept'):
        if (melicod_ignor[0] == '') or (melicod_ignor[0] == None) :
            ignor_etebar[0] = 'empty'
        if (melicod_ignor[0] != '') and (melicod_ignor[0] != None) :
            ignor_etebar[0] = 'nonempty'
            users = accuntmodel.objects.all()
            for user in users :
                if user.melicode == melicod_ignor[0] :
                    name = user.firstname +" "+user.lastname
                    randomcode = random.randint(1000, 9999)
                    smstext = firstname_r[0] + ' ' + lastname_r[
                        0] + ' ' + 'عزیز' + '\n' + 'کد چهاررقمی شما برای تغیر رمز ورود ' + ' ' + str(
                        randomcode) + '\n' + 'با تشکر' + 'سفروشگاه لوازم آشپزخانه موسوی' + '\n' + '\n' + '\n' + 'لغو ارسال پیامک 11'
                    try:
                        api = KavenegarAPI(
                            '527064632B7931304866497A5376334B6B506734634E65422F627346514F59596C767475564D32656E61553D')
                        params = {
                            'sender': '9982003178',  # optional
                            'receptor': user.phonnumber,  # multiple mobile number, split by comma
                            'message': smstext,
                        }
                        response = api.sms_send(params)

                        a = accuntmodel.objects.filter(melicode=user.melicode)
                        a.update(pasword=randomcode)
                        b = User.objects.filter(username=user.melicode)
                        b.delete()
                        User.objects.create_user(
                            username=melicod_ignor[0],
                            password=str(randomcode),
                            first_name=user.firstname,
                            last_name=user.lastname,
                        )

                        telhide = format_phone_number(str(user.phonnumber))
                        return render(request, 'code_cantact.html', context={'telhide': telhide})
                    except APIException as e:
                        m = 'tellerror'
                        # messages.error(request,'در سیستم ارسال پیامک مشکلی پیش آمده لطفا شماره خود را به درستی وارد کنید و دوباره امتحان کنید در صورتی که مشکل برطرف نشد در اینستاگرام پیام دهید ')
                        return render(request, 'new_addcontact.html',context={'melicod_etebar':m})
                    except HTTPException as e:
                        m = 'neterror'
                        # messages.error(request,'در سیستم ارسال پیامک مشکلی پیش آمده لطفا شماره خود را به درستی وارد کنید و دوباره امتحان کنید در صورتی که مشکل برطرف نشد در اینستاگرام پیام دهید ')
                        # return render(request, 'add_cantact.html')
                        return render(request, 'new_addcontact.html', context={'melicod_etebar': m},)

    return render(request,'ignor_cantact.html',context={'ignor_etebar':ignor_etebar[0],})



def chengpaswoord(request):
    return render(request,'changepaswoord.html')

def addphone(request):
    name = request.POST.get("name")
    lastname = request.POST.get("lastname")
    phonnamber = convert_farsi_to_latin(request.POST.get("phon"))
    phons = phonnambermodel.objects.all()
    button_send= request.POST.get("button_send")
    r = 0
    repeat = "no"
    for p in phons:
        if str(p.phonnumber) == str(phonnamber) :
            r =1
    if (r == 0) and (button_send == "accept"):
        phonnambermodel.objects.create(name=name, lastname=lastname, phonnumber=phonnamber)
    if r == 1 :
        repeat = "yes"
    # i = 0
    # pp = phonnambermodel.objects.all()
    # ppp = phonnambermodel.objects.all()
    # for hh in pp:
    #     for jjj in ppp :
    #         if hh.phonnumber == jjj.phonnumber:
    #             i += 1
    #             if i > 1 :
    #                 jjj.clean_fields()

    return render(request,'add_phon.html',context={"repeat":repeat})


def saveaccantdef(request):
    etebar = ''
    firstname = request.POST.get("firstname")
    lastname = request.POST.get("lastname")
    phonnumber = convert_farsi_to_latin(request.POST.get("phonnumber"))
    button_send =request.POST.get("button_send")
    if (phonnumber != None ) and (phonnumber != '') and (phonnumber != "None") :
        users = accuntmodel.objects.all()
        for user in users:
            if int(user.melicode) == int(phonnumber) or (user.phonnumber == phonnumber):
                etebar = "repeat"

    if (button_send == 'accept') and ( etebar != "repeat" ):
        etebar = 'true'
        accuntmodel.objects.create( firstname = firstname,
                                    lastname = lastname,
                                    melicode = phonnumber,
                                    phonnumber = phonnumber,
                                    savesabt=stradby(datetime.datetime.now()),
                                    pasword = "1",
                                    level = "1",
                                    dayb = "1",
                                    mountb = '1',
                                    yearb = '1',
                                    )
        return redirect('/')
    return render(request,'new_addreserv_cantact.html',context={'etebar': etebar, })


# -----------------------------ویرایش پروفایل----------------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import accuntmodel
from .forms import accuntform
# from  import modify_url, compress_and_move_images, format_phone_number, dateset
import datetime


@login_required
def edit_profile(request):
    userr =request.POST.get('user')
    if (userr != None) and (userr != '') and (userr != 'None'):
        request.session['userr'] = userr
    userr = request.session.get('userr')
    e = 'hello'
    if userr == 'my':
        member_melicod = request.user.username
    else:
        member_melicod = convert_farsi_to_latin(request.POST.get('member'))
    if (member_melicod != None) and (member_melicod != '') and (member_melicod != 'None'):
        request.session['member_id'] = member_melicod
    member = request.session['member_id']
    firstname = request.POST.get("firstname")
    lastname = request.POST.get("lastname")
    melicode = convert_farsi_to_latin(request.POST.get("melicode"))
    phonnumber = convert_farsi_to_latin(request.POST.get("phonnumber"))
    birthdate = request.POST.get("birthdate")
    year = ''
    mounth = ''
    day = ''
    if (birthdate != None) and (birthdate != '') and (birthdate != 'None'):
        year, mounth, day = dateset(birthdate)
    profile_pic = request.FILES.get('profile_picture')

    button_send = request.POST.get('button_send')

    # دریافت اطلاعات کاربر فعلی
    user = request.user
    try:
        profile = accuntmodel.objects.get(melicode=str(member))
    except accuntmodel.DoesNotExist:
        return render(request, 'error.html', {'message': 'پروفایل یافت نشد'})

    if button_send == 'accept':
        if (firstname == None) or (firstname == '') or (firstname == 'None'):
            firstname = profile.firstname
        if (lastname == None) or (lastname == '') or (lastname == 'None'):
            lastname = profile.lastname
        if (melicode == None) or (melicode == '') or (melicode == 'None'):
            melicode = profile.melicode
        if (day == None) or (day == '') or (day == 'None'):
            day = profile.dayb
        if (mounth == None) or (mounth == '') or (mounth == 'None'):
            mounth = profile.mountb
        if (year == None) or (year == '') or (year == 'None'):
            year = profile.yearb
        instans = savecodphon.objects.create(firstname=firstname,
                                             lastname=lastname,
                                             melicode=melicode,
                                             phonnumber=phonnumber,
                                             berthdayyear=year,
                                             berthdayday=day,
                                             berthdaymounth=mounth,
                                             code='110',
                                             expaiercode="110",
                                             profile_picture=profile_pic
                                             )
        instans.save()
        savecods = savecodphon.objects.all()
        for savecode in savecods :
            if int(savecode.code) == int('110'):
                yj = savecode.berthdayyear
                dj = savecode.berthdayday
                mj = savecode.berthdaymounth
                time = datetime.datetime.now()
                q = '14'
                while int(str(q + stry(time))) >= int(yj):
                    time -= timedelta(days=30)
                    if int(stry(time)) == int('99'):
                        q = '13'
                while int(str(q + stry(time))) == int(yj):
                    time += timedelta(days=1)
                while strb(time) != mj:
                    time += timedelta(days=1)
                while int(strd(time)) != int(dj):
                    time += timedelta(days=1)

                if User.objects.filter(username=savecode.melicode).exists():
                    b = User.objects.filter(username=savecode.melicode)
                    b.delete()
                # if __name__ == '__main__':
                compress_and_move_images()
                a = accuntmodel.objects.filter(melicode=str(member))
                a.delete()
                ins = accuntmodel.objects.create(
                                firstname=savecode.firstname,
                                lastname=savecode.lastname,
                                melicode=savecode.melicode,
                                phonnumber=savecode.phonnumber,
                                savesabt=stradby(datetime.datetime.now()),
                                pasword=savecode.phonnumber,
                                dayb= savecode.berthdayday,
                                mountb= savecode.berthdaymounth,
                                yearb=savecode.berthdayyear,
                                profile_picture=modify_url(savecode.profile_picture),
                )
                ins.save()
                User.objects.create_user(username=savecode.melicode,
                                        password=savecode.phonnumber,
                                        first_name=savecode.firstname,
                                        last_name=savecode.lastname,
                                            )
                e = 'ok'
                if userr == 'my':
                    print('1')
                    user_login =authenticate(request,
                                                 username=savecode.melicode,
                                                 password=savecode.phonnumber,
                                                 )

                    login (request,user_login)

                    # e = 'succes'
                    a = savecodphon.objects.filter(melicode=savecode.melicode)
                    a.delete()
                    a = savecodphon.objects.filter(melicode=str(member))
                    a.delete()
                    # request.session.flush()
                    return redirect('/')
                    # return render(request,'new_profile_edit.html',context={'etebar_edit':e})
    #             a = savecodphon.objects.filter(melicode=savecode.melicode)
    #             a.delete()
    #             a = savecodphon.objects.filter(melicode=str(member))
    #             a.delete()
    #             request.session.flush()
            return render(request,'new_profile_edit.html',context={'etebar_edit':e})
    else:
        # فرمت تاریخ تولد برای نمایش در فرم
        birthdate_str = ""
        # if profile.yearb and profile.mountb and profile.dayb:
        #     # تبدیل نام ماه به عدد
        #     month_num = PERSIAN_MONTHS.get(profile.mountb, 1)
        #     birthdate_str = f"{profile.yearb}/{month_num:02d}/{int(profile.dayb):02d}"

        initial_data = {
            'firstname': profile.firstname,
            'lastname': profile.lastname,
            'melicod': profile.melicode,
            'phonnumber': profile.phonnumber,
            'birthdate': birthdate_str,
        }
        form = accuntform(initial=initial_data, instance=profile)

    telhide = format_phone_number(profile.phonnumber) if profile.phonnumber else ""

    return render(request, 'new_profile_edit.html', {
        'etebar_edit': e,
        # 'form': form,
        'profile': profile,
        'telhide': telhide
    })




def logout_view(request):
    logout(request)
    return redirect('/')


# --------------------------ثبت شعب--------------------------------------------------------------
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q
from django.contrib import messages

from .models import Branch, accuntmodel
from .forms import BranchForm, BranchAdminForm
from .utils import convert_persian_to_english

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q
from django.contrib import messages
import json

from .models import Branch, accuntmodel
from .forms import BranchForm, BranchAdminForm
from .utils import convert_persian_to_english


@method_decorator(csrf_exempt, name='dispatch')
class BranchCreateView(View):
    def get(self, request):
        form = BranchForm()
        return render(request, 'branch_form.html', {'form': form})

    def post(self, request):
        # پردازش داده‌های فروشندگان
        post_data = request.POST.copy()
        sellers_str = post_data.get('sellers', '')

        if sellers_str:
            # تبدیل رشته به لیست اعداد
            try:
                sellers_list = [int(seller_id) for seller_id in sellers_str.split(',') if seller_id.strip()]
                post_data.setlist('sellers', sellers_list)
            except ValueError:
                messages.error(request, 'فرمت داده فروشندگان نامعتبر است.')
                form = BranchForm(post_data)
                return render(request, 'branch_form.html', {'form': form})

        form = BranchForm(post_data)
        if form.is_valid():
            branch = form.save()
            messages.success(request, 'شعبه با موفقیت ایجاد شد.')
            return redirect('cantact_app:branch_list')
        else:
            messages.error(request, 'خطا در ایجاد شعبه. لطفاً اطلاعات را بررسی کنید.')
            return render(request, 'branch_form.html', {'form': form})


def branch_edit(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        # پردازش داده‌های فروشندگان
        post_data = request.POST.copy()
        sellers_str = post_data.get('sellers', '')

        if sellers_str:
            # تبدیل رشته به لیست اعداد
            try:
                sellers_list = [int(seller_id) for seller_id in sellers_str.split(',') if seller_id.strip()]
                post_data.setlist('sellers', sellers_list)
            except ValueError:
                messages.error(request, 'فرمت داده فروشندگان نامعتبر است.')
                form = BranchForm(post_data, instance=branch)
                return render(request, 'branch_form.html', {'form': form, 'edit_mode': True})

        form = BranchForm(post_data, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'شعبه با موفقیت ویرایش شد.')
            return redirect('cantact_app:branch_list')
    else:
        form = BranchForm(instance=branch)

    return render(request, 'branch_form.html', {'form': form, 'edit_mode': True})
# در فایل cantact_app/views.py


def branch_list(request):
    branches = Branch.objects.all().prefetch_related('sellers')
    return render(request, 'branch_list.html', {'branches': branches})


def branch_detail(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    return render(request, 'branch_detail.html', {'branch': branch})




def branch_delete(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        branch.delete()
        messages.success(request, 'شعبه با موفقیت حذف شد.')
        return redirect('cantact_app:branch_list')

    return render(request, 'branch_confirm_delete.html', {'branch': branch})



def search_sellers(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})

    # تبدیل اعداد فارسی به انگلیسی
    query_english = convert_persian_to_english(query)

    # جستجو در نام، نام خانوادگی و کد ملی
    sellers = accuntmodel.objects.filter(
        Q(firstname__icontains=query) |
        Q(lastname__icontains=query) |
        Q(melicode__icontains=query) |
        Q(firstname__icontains=query_english) |
        Q(lastname__icontains=query_english) |
        Q(melicode__icontains=query_english)
    )[:10]

    results = []
    for seller in sellers:
        results.append({
            'id': seller.id,
            'text': f"{seller.firstname} {seller.lastname} - {seller.melicode}",
            'firstname': seller.firstname,
            'lastname': seller.lastname,
            'melicode': seller.melicode
        })

    return JsonResponse({'results': results})

#
# -----------------------------------------------لاگین ها---------------------------------------
# ------------------------------- مدیریت سشن‌ها ---------------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from cantact_app.models import UserSessionLog



# در views.py - اضافه کردن این توابع

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from cantact_app.models import UserSessionLog, accuntmodel



@login_required(login_url='/cantact/login/')
def terminate_other_sessions_view(request):
    """خاتمه دادن به سایر سشن‌های کاربر جاری"""
    if request.method == 'POST':
        current_session_key = request.session.session_key
        specific_session_key = request.POST.get('session_key')

        if specific_session_key:
            # قطع سشن خاص
            try:
                session_log = UserSessionLog.objects.get(
                    user=request.user,  # فقط سشن‌های کاربر جاری
                    session_key=specific_session_key,
                    is_active=True
                )
                session_log.terminate()
                messages.success(request, "دستگاه مورد نظر قطع ارتباط شد.")
            except UserSessionLog.DoesNotExist:
                messages.error(request, "سشن مورد نظر یافت نشد.")
        else:
            # قطع تمام سشن‌های دیگر کاربر جاری
            other_sessions = UserSessionLog.objects.filter(
                user=request.user,  # فقط کاربر جاری
                is_active=True
            ).exclude(session_key=current_session_key)

            terminated_count = 0
            for session_log in other_sessions:
                session_log.terminate()
                terminated_count += 1

            if terminated_count > 0:
                messages.success(request, f"از {terminated_count} دستگاه دیگر خارج شدید.")
            else:
                messages.info(request, "هیچ دستگاه فعال دیگری وجود ندارد.")

    return redirect('cantact_app:session_management')


@login_required(login_url='/cantact/login/')
def session_management_view(request):
    """صفحه مدیریت سشن‌های کاربر جاری"""
    # فقط سشن‌های فعال کاربر جاری را نمایش بده
    user_sessions = UserSessionLog.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-last_activity')

    current_session_key = request.session.session_key

    # 🔥 **رفع مشکل اصلی: دریافت صحیح اطلاعات کاربر**
    try:
        # روش ۱: دریافت از مدل accuntmodel با استفاده از username کاربر جاری
        user_profile = accuntmodel.objects.get(melicode=request.user.username)
        full_name = f"{user_profile.firstname} {user_profile.lastname}"
        print(f"✅ اطلاعات کاربر از accuntmodel: {full_name}")

    except accuntmodel.DoesNotExist:
        try:
            # روش ۲: دریافت از مدل User
            full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            if not full_name or full_name == " ":
                full_name = request.user.username
            print(f"✅ اطلاعات کاربر از User: {full_name}")

        except Exception as e:
            # روش ۳: استفاده از username در صورت خطا
            full_name = request.user.username
            print(f"⚠️ استفاده از username: {full_name}")

    context = {
        'user_sessions': user_sessions,
        'current_session_key': current_session_key,
        'full_name': full_name,
        'username': request.user.username,
    }

    return render(request, 'cantact_app/session_management.html', context)


# در views.py - قبل از توابع اصلی
def debug_user_info(request):
    """تابع کمکی برای دیباگ اطلاعات کاربر"""
    print("=" * 50)
    print("🔍 دیباگ اطلاعات کاربر:")
    print(f"✅ کاربر جاری: {request.user}")
    print(f"✅ username: {request.user.username}")
    print(f"✅ first_name: {request.user.first_name}")
    print(f"✅ last_name: {request.user.last_name}")
    print(f"✅ is_authenticated: {request.user.is_authenticated}")

    # بررسی وجود کاربر در accuntmodel
    try:
        accunt_user = accuntmodel.objects.get(melicode=request.user.username)
        print(f"✅ کاربر در accuntmodel: {accunt_user.firstname} {accunt_user.lastname}")
    except accuntmodel.DoesNotExist:
        print("❌ کاربر در accuntmodel یافت نشد")

    print("=" * 50)