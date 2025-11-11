# cantact_app/middleware.py
from django.contrib.sessions.models import Session
from django.contrib.auth import logout
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
import hashlib
import json

try:
    import user_agents

    USER_AGENTS_AVAILABLE = True
except ImportError:
    USER_AGENTS_AVAILABLE = False


class AdvancedSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # تنظیمات قابل تنظیم
        self.max_sessions_per_user = 1  # حداکثر تعداد سشن فعال
        self.allow_multiple_admin_sessions = False  # آیا ادمین‌ها چند سشن داشته باشند؟
        self.session_timeout = 3600  # 1 ساعت

    def __call__(self, request):
        # پردازش درخواست
        response = self.process_request(request)

        if not response:
            response = self.get_response(request)

        # پردازش پاسخ
        return self.process_response(request, response)

    def process_request(self, request):
        """پردازش هر درخواست قبل از رسیدن به view"""

        # اگر کاربر لاگین شده است
        if request.user.is_authenticated:
            current_session_key = request.session.session_key

            # بررسی آیا سشن معتبر است
            if not self.is_session_valid(request):
                return self.force_logout(request)

            # بروزرسانی آخرین فعالیت
            self.update_last_activity(request)

            # بررسی و مدیریت سشن‌های متعدد
            self.manage_user_sessions(request)

    def process_response(self, request, response):
        """پردازش هر پاسخ قبل از ارسال به کاربر"""

        # بعد از لاگین موفق
        if (request.user.is_authenticated and
                self.is_login_successful(request, response)):
            self.handle_successful_login(request)

        return response

    def is_login_successful(self, request, response):
        """بررسی آیا لاگین موفق بوده است"""
        login_urls = ['/login/', '/cantact/login/', '/admin/login/']
        is_login_url = any(request.path.startswith(url) for url in login_urls)
        is_successful = response.status_code in [200, 302]

        return is_login_url and is_successful and request.user.is_authenticated

    def handle_successful_login(self, request):
        """مدیریت لاگین موفق"""
        try:
            from .models import UserSessionLog

            user = request.user
            session_key = request.session.session_key

            # ایجاد fingerprint برای امنیت بیشتر
            security_fingerprint = self.create_security_fingerprint(request)
            request.session['security_fingerprint'] = security_fingerprint

            # تشخیص نوع دستگاه
            device_info = self.detect_device_info(request)

            # ذخیره اطلاعات سشن
            UserSessionLog.objects.create(
                user=user,
                session_key=session_key,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],  # محدود کردن طول
                device_type=device_info['type'],
                device_info=device_info,
                location=self.get_estimated_location(request),
                is_active=True
            )

            # مدیریت سشن‌های قدیمی
            self.cleanup_old_sessions(user, session_key)

            print(f"✅ لاگین موفق: {user.username} از {device_info['type']}")

        except Exception as e:
            print(f"⚠️ خطا در ذخیره سشن: {e}")

    def create_security_fingerprint(self, request):
        """ایجاد fingerprint امنیتی"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        ip = self.get_client_ip(request)

        fingerprint_string = f"{request.user.id}-{user_agent}-{accept_language}-{ip}"
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()

    def detect_device_info(self, request):
        """تشخیص اطلاعات دستگاه"""
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')

        if USER_AGENTS_AVAILABLE:
            ua = user_agents.parse(user_agent_string)
            device_type = self.get_device_type(ua)
            browser = f"{ua.browser.family} {ua.browser.version_string}"
            os = f"{ua.os.family} {ua.os.version_string}"
            device = ua.device.family
        else:
            # اگر user_agents نصب نیست، تشخیص ساده
            user_agent_lower = user_agent_string.lower()
            if 'mobile' in user_agent_lower:
                device_type = 'mobile'
            elif 'tablet' in user_agent_lower:
                device_type = 'tablet'
            else:
                device_type = 'desktop'
            browser = 'Unknown'
            os = 'Unknown'
            device = 'Unknown'

        return {
            'type': device_type,
            'browser': browser,
            'os': os,
            'device': device,
        }

    def get_device_type(self, ua):
        """تعیین نوع دستگاه"""
        if ua.is_mobile:
            return 'mobile'
        elif ua.is_tablet:
            return 'tablet'
        elif ua.is_pc:
            return 'desktop'
        else:
            return 'web'

    def get_client_ip(self, request):
        """دریافت IP واقعی کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_estimated_location(self, request):
        """تخمین موقعیت جغرافیایی (ساده)"""
        ip = self.get_client_ip(request)

        # برای IPهای داخلی
        if ip.startswith('192.168.') or ip.startswith('10.') or ip == '127.0.0.1':
            return 'شبکه داخلی'

        return 'نامشخص'

    def cleanup_old_sessions(self, user, current_session_key):
        """پاکسازی سشن‌های قدیمی"""
        try:
            from .models import UserSessionLog

            active_sessions = UserSessionLog.objects.filter(
                user=user,
                is_active=True
            ).exclude(session_key=current_session_key)

            # اگر کاربر ادمین است و اجازه سشن‌های متعدد دارد
            if user.is_staff and self.allow_multiple_admin_sessions:
                # فقط سشن‌های قدیمی‌تر از timeout را پاک کن
                timeout_time = timezone.now() - timezone.timedelta(seconds=self.session_timeout)
                old_sessions = active_sessions.filter(last_activity__lt=timeout_time)
            else:
                # برای کاربران عادی، تمام سشن‌های دیگر را پاک کن
                old_sessions = active_sessions

            for session_log in old_sessions:
                session_log.terminate()
                print(f"🗑️ سشن قدیمی پاک شد: {user.username} - {session_log.session_key}")

        except Exception as e:
            print(f"⚠️ خطا در پاکسازی سشن‌های قدیمی: {e}")

    def is_session_valid(self, request):
        """بررسی معتبر بودن سشن"""
        if not request.user.is_authenticated:
            return True

        try:
            from .models import UserSessionLog

            # بررسی fingerprint امنیتی
            current_fingerprint = self.create_security_fingerprint(request)
            stored_fingerprint = request.session.get('security_fingerprint')

            if stored_fingerprint and current_fingerprint != stored_fingerprint:
                print(f"🚨 خطای امنیتی: fingerprint مطابقت ندارد - {request.user.username}")
                return False

            # بررسی وجود سشن در لاگ
            session_log = UserSessionLog.objects.get(
                session_key=request.session.session_key,
                user=request.user,
                is_active=True
            )

            # بررسی timeout
            timeout_time = timezone.now() - timezone.timedelta(seconds=self.session_timeout)
            if session_log.last_activity < timeout_time:
                print(f"⏰ سشن منقضی شده: {request.user.username}")
                return False

        except UserSessionLog.DoesNotExist:
            print(f"🔍 سشن در لاگ پیدا نشد: {request.user.username}")
            return False
        except Exception as e:
            print(f"⚠️ خطا در بررسی سشن: {e}")
            return True  # در صورت خطا، اجازه ادامه بده

        return True

    def update_last_activity(self, request):
        """بروزرسانی زمان آخرین فعالیت"""
        if request.user.is_authenticated:
            try:
                from .models import UserSessionLog

                session_log = UserSessionLog.objects.get(
                    session_key=request.session.session_key,
                    user=request.user
                )
                session_log.last_activity = timezone.now()
                session_log.save()
            except Exception as e:
                print(f"⚠️ خطا در بروزرسانی فعالیت: {e}")

    def manage_user_sessions(self, request):
        """مدیریت سشن‌های کاربر"""
        try:
            from .models import UserSessionLog

            user = request.user
            current_session_key = request.session.session_key

            # تعداد سشن‌های فعال
            active_count = UserSessionLog.objects.filter(user=user, is_active=True).count()

            # اگر بیشتر از حد مجاز سشن فعال دارد
            if active_count > self.max_sessions_per_user:
                # پیدا کردن سشن‌های قدیمی‌تر
                old_sessions = UserSessionLog.objects.filter(
                    user=user,
                    is_active=True
                ).exclude(session_key=current_session_key).order_by('last_activity')

                # پاک کردن سشن‌های اضافی
                sessions_to_remove = old_sessions[:active_count - self.max_sessions_per_user]
                for session_log in sessions_to_remove:
                    session_log.terminate()
                    print(f"🔒 حذف سشن اضافی: {user.username}")

        except Exception as e:
            print(f"⚠️ خطا در مدیریت سشن‌ها: {e}")

    def force_logout(self, request):
        """اجباری کردن خروج"""
        try:
            from .models import UserSessionLog

            if request.user.is_authenticated:
                print(f"🔐 خروج اجباری: {request.user.username}")

                # غیرفعال کردن سشن در لاگ
                try:
                    session_log = UserSessionLog.objects.get(
                        session_key=request.session.session_key,
                        user=request.user
                    )
                    session_log.is_active = False
                    session_log.forced_logout = True
                    session_log.save()
                except UserSessionLog.DoesNotExist:
                    pass

                # logout کاربر
                logout(request)
                request.session.flush()

                # اضافه کردن پیام
                storage = messages.get_messages(request)
                storage.used = True  # پاک کردن پیام‌های قبلی

                messages.warning(
                    request,
                    "دسترسی شما به دلیل فعالیت از دستگاه دیگر یا مشکل امنیتی قطع شد. لطفاً مجدداً وارد شوید."
                )

                return HttpResponseRedirect(reverse('login'))

        except Exception as e:
            print(f"⚠️ خطا در خروج اجباری: {e}")

        return None