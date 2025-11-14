# # cantact_app/middleware.py
# from django.contrib.sessions.models import Session
# from django.contrib.auth import logout
# from django.utils import timezone
# from django.http import HttpResponseRedirect
# from django.contrib import messages
# import hashlib
#
# try:
#     import user_agents
#
#     USER_AGENTS_AVAILABLE = True
# except ImportError:
#     USER_AGENTS_AVAILABLE = False
#
#
# class SingleSessionMiddleware:
#     """
#     میدلوار برای مدیریت سشن‌ها - هر کاربر فقط از یک دستگاه می‌تواند لاگین باشد
#     """
#
#     def __init__(self, get_response):
#         self.get_response = get_response
#         self.session_timeout = 3600 * 24  # 24 ساعت
#
#     def __call__(self, request):
#         """
#         پردازش اصلی هر درخواست
#         """
#         try:
#             # پردازش قبل از view
#             response = self.process_request(request)
#
#             # اگر response برگردانده شده باشد، یعنی خطایی رخ داده
#             if response:
#                 return response
#
#             # اجرای view اصلی
#             response = self.get_response(request)
#
#             return response
#
#         except Exception as e:
#             print(f"⚠️ خطای بحرانی در میدلوار: {e}")
#             return self.get_response(request)
#
#     def process_request(self, request):
#         """
#         پردازش هر درخواست قبل از رسیدن به view
#         """
#         try:
#             # فقط برای کاربران لاگین شده پردازش انجام بده
#             if not request.user.is_authenticated:
#                 return None
#
#             current_session_key = request.session.session_key
#             if not current_session_key:
#                 print("❌ سشن کیی موجود نیست")
#                 return self.safe_force_logout(request)
#
#             # بررسی معتبر بودن سشن فعلی
#             if not self.is_session_valid(request, current_session_key):
#                 print("❌ سشن معتبر نیست")
#                 return self.safe_force_logout(request)
#
#             # قطع تمام سشن‌های دیگر این کاربر (بدون تأثیر روی سشن فعلی)
#             self.terminate_other_sessions(request.user, current_session_key)
#
#             # به‌روزرسانی آخرین فعالیت
#             self.update_last_activity(request.user, current_session_key)
#
#         except Exception as e:
#             print(f"⚠️ خطا در پردازش درخواست: {e}")
#
#         return None
#
#     def safe_force_logout(self, request):
#         """
#         خروج امن کاربر بدون ایجاد SessionInterrupted
#         """
#         try:
#             if request.user.is_authenticated:
#                 username = request.user.username
#                 print(f"🔐 خروج امن: {username}")
#
#                 # ابتدا کاربر را logout کن
#                 logout(request)
#
#                 # سپس سشن را در پس‌زمینه غیرفعال کن
#                 self.background_terminate_session(request.session.session_key, request.user)
#
#                 # یک سشن جدید ایجاد کن
#                 request.session.cycle_key()
#
#                 messages.warning(
#                     request,
#                     "🔐 سشن شما منقضی شده است. لطفاً مجدداً وارد شوید."
#                 )
#
#                 return HttpResponseRedirect('/cantact/login/')
#
#         except Exception as e:
#             print(f"⚠️ خطا در خروج امن: {e}")
#             # در صورت خطا، فقط ریدایرکت کن
#             return HttpResponseRedirect('/cantact/login/')
#
#         return None
#
#     def background_terminate_session(self, session_key, user):
#         """
#         غیرفعال کردن سشن در پس‌زمینه
#         """
#         try:
#             from .models import UserSessionLog
#
#             if session_key:
#                 # غیرفعال کردن سشن در لاگ
#                 UserSessionLog.objects.filter(
#                     session_key=session_key,
#                     user=user
#                 ).update(is_active=False, forced_logout=True)
#
#                 # حذف سشن از دیتابیس (در پس‌زمینه)
#                 try:
#                     Session.objects.filter(session_key=session_key).delete()
#                 except:
#                     pass
#
#         except Exception as e:
#             print(f"⚠️ خطا در غیرفعال کردن سشن در پس‌زمینه: {e}")
#
#     def terminate_other_sessions(self, user, current_session_key):
#         """
#         قطع تمام سشن‌های دیگر کاربر به جز سشن فعلی
#         """
#         try:
#             from .models import UserSessionLog
#
#             # پیدا کردن تمام سشن‌های فعال کاربر به جز سشن فعلی
#             other_sessions = UserSessionLog.objects.filter(
#                 user=user,
#                 is_active=True
#             ).exclude(session_key=current_session_key)
#
#             terminated_count = 0
#             for session_log in other_sessions:
#                 # از تابع terminate مدل استفاده کن
#                 session_log.terminate()
#                 terminated_count += 1
#
#             if terminated_count > 0:
#                 print(f"🔒 {terminated_count} سشن دیگر کاربر {user.username} قطع شد")
#
#         except Exception as e:
#             print(f"⚠️ خطا در قطع سشن‌های دیگر: {e}")
#
#     def is_session_valid(self, request, session_key):
#         """
#         بررسی معتبر بودن سشن
#         """
#         try:
#             from .models import UserSessionLog
#
#             if not request.user.is_authenticated or not session_key:
#                 return False
#
#             # بررسی وجود سشن در لاگ
#             try:
#                 session_log = UserSessionLog.objects.get(
#                     session_key=session_key,
#                     user=request.user,
#                     is_active=True
#                 )
#             except UserSessionLog.DoesNotExist:
#                 print(f"❌ سشن در لاگ یافت نشد: {session_key}")
#                 return False
#
#             # بررسی timeout
#             timeout_time = timezone.now() - timezone.timedelta(seconds=self.session_timeout)
#             if session_log.last_activity < timeout_time:
#                 print(f"⏰ سشن منقضی شده: {request.user.username}")
#                 return False
#
#             return True
#
#         except Exception as e:
#             print(f"⚠️ خطا در بررسی سشن: {e}")
#             return True  # در صورت خطا، اجازه بده ادامه دهد
#
#     def update_last_activity(self, user, session_key):
#         """
#         به‌روزرسانی زمان آخرین فعالیت
#         """
#         try:
#             from .models import UserSessionLog
#
#             session_log = UserSessionLog.objects.get(
#                 session_key=session_key,
#                 user=user
#             )
#             session_log.last_activity = timezone.now()
#             session_log.save()
#
#         except UserSessionLog.DoesNotExist:
#             print(f"⚠️ سشن برای به‌روزرسانی یافت نشد: {session_key}")
#         except Exception as e:
#             print(f"⚠️ خطا در به‌روزرسانی فعالیت: {e}")
#
#     def handle_successful_login(self, request):
#         """
#         مدیریت لاگین موفق - ایجاد سشن لاگ جدید
#         """
#         try:
#             from .models import UserSessionLog
#
#             user = request.user
#             session_key = request.session.session_key
#
#             if not session_key:
#                 print("❌ سشن کیی در لاگین موجود نیست")
#                 return
#
#             # قطع تمام سشن‌های قبلی این کاربر
#             self.terminate_all_user_sessions(user)
#
#             # ایجاد fingerprint امنیتی
#             security_fingerprint = self.create_security_fingerprint(request)
#             request.session['security_fingerprint'] = security_fingerprint
#
#             # تشخیص اطلاعات دستگاه
#             device_info = self.detect_device_info(request)
#
#             # ایجاد سشن لاگ جدید
#             UserSessionLog.objects.create(
#                 user=user,
#                 session_key=session_key,
#                 ip_address=self.get_client_ip(request),
#                 user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
#                 device_type=device_info['type'],
#                 device_info=device_info,
#                 location=self.get_estimated_location(request),
#                 is_active=True
#             )
#
#             print(f"✅ لاگین موفق و سشن ایجاد شد: {user.username}")
#
#         except Exception as e:
#             print(f"⚠️ خطا در مدیریت لاگین موفق: {e}")
#
#     def terminate_all_user_sessions(self, user):
#         """
#         قطع تمام سشن‌های یک کاربر
#         """
#         try:
#             from .models import UserSessionLog
#
#             # پیدا کردن تمام سشن‌های فعال کاربر
#             active_sessions = UserSessionLog.objects.filter(
#                 user=user,
#                 is_active=True
#             )
#
#             terminated_count = 0
#             for session_log in active_sessions:
#                 session_log.terminate()
#                 terminated_count += 1
#
#             if terminated_count > 0:
#                 print(f"🔒 {terminated_count} سشن قبلی کاربر {user.username} قطع شد")
#
#         except Exception as e:
#             print(f"⚠️ خطا در قطع تمام سشن‌ها: {e}")
#
#     def create_security_fingerprint(self, request):
#         """
#         ایجاد fingerprint امنیتی بر اساس مشخصات دستگاه
#         """
#         try:
#             user_agent = request.META.get('HTTP_USER_AGENT', '')
#             accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
#             accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
#             ip = self.get_client_ip(request)
#
#             fingerprint_string = f"{request.user.id}-{user_agent}-{accept_language}-{accept_encoding}-{ip}"
#             return hashlib.sha256(fingerprint_string.encode()).hexdigest()
#         except:
#             return "default_fingerprint"
#
#     def detect_device_info(self, request):
#         """
#         تشخیص اطلاعات دستگاه
#         """
#         user_agent_string = request.META.get('HTTP_USER_AGENT', '')
#
#         if USER_AGENTS_AVAILABLE:
#             try:
#                 ua = user_agents.parse(user_agent_string)
#                 device_type = self.get_device_type(ua)
#                 browser = f"{ua.browser.family} {ua.browser.version_string}"
#                 os = f"{ua.os.family} {ua.os.version_string}"
#                 device = ua.device.family
#             except:
#                 device_type, browser, os, device = self.fallback_device_detection(user_agent_string)
#         else:
#             device_type, browser, os, device = self.fallback_device_detection(user_agent_string)
#
#         return {
#             'type': device_type,
#             'browser': browser,
#             'os': os,
#             'device': device,
#         }
#
#     def fallback_device_detection(self, user_agent_string):
#         """
#         تشخیص ساده دستگاه در صورت عدم دسترسی به user_agents
#         """
#         user_agent_lower = user_agent_string.lower()
#
#         if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
#             device_type = 'mobile'
#         elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
#             device_type = 'tablet'
#         else:
#             device_type = 'desktop'
#
#         # تشخیص مرورگر ساده
#         if 'chrome' in user_agent_lower:
#             browser = 'Chrome'
#         elif 'firefox' in user_agent_lower:
#             browser = 'Firefox'
#         elif 'safari' in user_agent_lower:
#             browser = 'Safari'
#         else:
#             browser = 'Unknown'
#
#         # تشخیص سیستم عامل ساده
#         if 'windows' in user_agent_lower:
#             os = 'Windows'
#         elif 'mac' in user_agent_lower:
#             os = 'Mac OS'
#         elif 'linux' in user_agent_lower:
#             os = 'Linux'
#         elif 'android' in user_agent_lower:
#             os = 'Android'
#         elif 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
#             os = 'iOS'
#         else:
#             os = 'Unknown'
#
#         return device_type, browser, os, 'Unknown'
#
#     def get_device_type(self, ua):
#         """
#         تعیین نوع دستگاه
#         """
#         if ua.is_mobile:
#             return 'mobile'
#         elif ua.is_tablet:
#             return 'tablet'
#         elif ua.is_pc:
#             return 'desktop'
#         else:
#             return 'web'
#
#     def get_client_ip(self, request):
#         """
#         دریافت IP واقعی کاربر
#         """
#         try:
#             x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#             if x_forwarded_for:
#                 ip = x_forwarded_for.split(',')[0].strip()
#             else:
#                 ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
#             return ip
#         except:
#             return '0.0.0.0'
#
#     def get_estimated_location(self, request):
#         """
#         تخمین موقعیت جغرافیایی (ساده)
#         """
#         try:
#             ip = self.get_client_ip(request)
#             if ip.startswith('192.168.') or ip.startswith('10.') or ip == '127.0.0.1':
#                 return 'شبکه داخلی'
#             return 'نامشخص'
#         except:
#             return 'نامشخص'