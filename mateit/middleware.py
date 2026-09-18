from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers


class SplitSessionMiddleware(SessionMiddleware):
    """
    /admin 아래에서는 'admin_sessionid' 쿠키를,
    그 외 경로에서는 기본 SESSION_COOKIE_NAME('sessionid')를 사용.
    """
    admin_prefix = "/admin"
    admin_cookie_name = getattr(settings, "ADMIN_SESSION_COOKIE_NAME", "admin_sessionid")

    def _cookie_name(self, request):
        return self.admin_cookie_name if request.path.startswith(self.admin_prefix) \
               else settings.SESSION_COOKIE_NAME

    def process_request(self, request):
        cookie_name = self._cookie_name(request)
        request.session = self.SessionStore(request.COOKIES.get(cookie_name))

    def process_response(self, request, response):
        session = getattr(request, "session", None)
        if session is None:
            return response

        cookie_name = self._cookie_name(request)

        path     = settings.SESSION_COOKIE_PATH
        domain   = settings.SESSION_COOKIE_DOMAIN
        secure   = settings.SESSION_COOKIE_SECURE
        httponly = settings.SESSION_COOKIE_HTTPONLY
        samesite = settings.SESSION_COOKIE_SAMESITE

        # 빈 세션이면 쿠키 제거
        if session.is_empty():
            if cookie_name in request.COOKIES:
                response.delete_cookie(cookie_name, path=path, domain=domain, samesite=samesite)
            return response

        if session.accessed:
            patch_vary_headers(response, ("Cookie",))

        if session.modified or settings.SESSION_SAVE_EVERY_REQUEST:
            # 세션 저장(키 보장)
            session.save()

            cookie_kwargs = dict(
                path=path,
                domain=domain,
                secure=secure,
                httponly=httponly,
                samesite=samesite,
            )

            # 브라우저 종료 시 만료가 아니면 max_age만 설정 (expires는 전달하지 않음!)
            if not session.get_expire_at_browser_close():
                cookie_kwargs["max_age"] = session.get_expiry_age()

            response.set_cookie(cookie_name, session.session_key, **cookie_kwargs)

        return response
