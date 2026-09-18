from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# =====================================
# 기본 경로 & 환경변수 로드
# =====================================
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()  # .env 지원(로컬)

def _split_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]

# =====================================
# 보안/디버그 (환경변수 우선)
# =====================================
SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only"))
# 서버 기본값은 안전하게 False, 로컬은 .env로 True 주입해서 사용
DEBUG = (os.getenv("DEBUG", os.getenv("DJANGO_DEBUG", "False")).lower() == "true")

# Render가 제공하는 외부 호스트명(예: mate-it.onrender.com)
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")

# ALLOWED_HOSTS: ENV 우선, 없으면 Render/로컬 기본 허용
ALLOWED_HOSTS = _split_csv_env("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".onrender.com"]
    if RENDER_HOST:
        ALLOWED_HOSTS.append(RENDER_HOST)

# CSRF_TRUSTED_ORIGINS: ENV 우선, 없으면 Render/기본 구성
CSRF_TRUSTED_ORIGINS = _split_csv_env("CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]
    if RENDER_HOST:
        CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

# 프록시(Load Balancer) 뒤 HTTPS 인식
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# =====================================
# 앱 설정
# =====================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "mateit.apps.MateitConfig",
    "social_django",
]

# =====================================
# 미들웨어
#  - WhiteNoise는 SecurityMiddleware 바로 다음
#  - 커스텀 SplitSessionMiddleware 유지
# =====================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # "django.contrib.sessions.middleware.SessionMiddleware",  # 기본 세션 미사용이면 주석 그대로
    "mateit.middleware.SplitSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

# 관리자 세션 분리(기존 유지)
ADMIN_SESSION_COOKIE_NAME = "admin_sessionid"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =====================================
# 데이터베이스
#  - DATABASE_URL 있으면 그걸 사용(배포)
#  - 없으면 로컬 sqlite3
# =====================================
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DB_SSL_REQUIRE = os.getenv("DB_SSL_REQUIRE", "False").lower() == "true"
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL, conn_max_age=600, ssl_require=DB_SSL_REQUIRE
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# =====================================
# 인증/비밀번호
# =====================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =====================================
# 국제화
# =====================================
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = False  # 기존 유지

# =====================================
# 정적 파일 (WhiteNoise + collectstatic)
# =====================================
STATIC_URL = "/static/"

# 개발용 소스 디렉터리(있을 때만 참고해도 무방)
STATICFILES_DIRS = [BASE_DIR / "static"]

# collectstatic 대상
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: 압축/해시 파일
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =====================================
# 사용자 모델
# =====================================
AUTH_USER_MODEL = "mateit.CustomUser"

# =====================================
# 기본 PK 타입
# =====================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =====================================
# 소셜 로그인
# =====================================
AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.kakao.KakaoOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("GOOGLE_CLIENT_ID", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["openid", "email", "profile"]
SOCIAL_AUTH_ASSOCIATE_BY_EMAIL = True
# 프록시 뒤에서 콜백이 https로 인식되게
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",

    "mateit.pipeline.enforce_email_verified",

    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",

    "mateit.pipeline.find_or_ask_student_id",
    "mateit.pipeline.create_user_with_sid",

    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",

    "mateit.pipeline.set_session_student_id",
)

# =====================================
# (선택) 프로덕션 보안 권장 — ENV로 제어
# =====================================
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"
