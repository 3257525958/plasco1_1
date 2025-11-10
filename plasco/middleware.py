# در فایل plasco/middleware.py این کد را اضافه کنید:

import hashlib
from django.utils.deprecation import MiddlewareMixin


class StrictSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # اگر کاربر لاگین کرده است
        if request.user.is_authenticated:
            # ایجاد fingerprint از کاربر و مرورگر
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            fingerprint_source = f"{request.user.id}-{user_agent}-{accept_language}"
            expected_fingerprint = hashlib.md5(fingerprint_source.encode()).hexdigest()

            # بررسی fingerprint در session
            session_fingerprint = request.session.get('user_fingerprint')

            if session_fingerprint != expected_fingerprint:
                # اگر fingerprint مطابقت ندارد، کاربر را logout کن
                from django.contrib.auth import logout
                logout(request)
                request.session.flush()

                # ایجاد session جدید
                request.session.create()
                request.session['user_fingerprint'] = expected_fingerprint

    def process_response(self, request, response):
        # بعد از login، fingerprint را ذخیره کن
        if request.user.is_authenticated and not request.session.get('user_fingerprint'):
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            fingerprint_source = f"{request.user.id}-{user_agent}-{accept_language}"
            expected_fingerprint = hashlib.md5(fingerprint_source.encode()).hexdigest()

            request.session['user_fingerprint'] = expected_fingerprint
            request.session.modified = True

        return response