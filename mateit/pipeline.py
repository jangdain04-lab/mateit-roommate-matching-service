from django.contrib.auth import get_user_model
from django.urls import reverse
from urllib.parse import urlencode
from social_core.exceptions import AuthForbidden
from social_core.pipeline.partial import partial

User = get_user_model()

def enforce_email_verified(backend=None, response=None, *args, **kwargs):
    if backend and backend.name == 'google-oauth2':
        if not bool((response or {}).get('email_verified', False)):
            raise AuthForbidden(backend)

def _localpart(email: str) -> str:
    try:
        return (email or '').split('@')[0]
    except Exception:
        return ''

# ✅ 반드시 partial!
@partial
def find_or_ask_student_id(strategy=None, backend=None, details=None, user=None, *args, **kwargs):
    if not backend or backend.name != 'google-oauth2':
        return
    # 이미 연결된 소셜이면 통과(재로그인 경로)
    if kwargs.get('social'):
        return
    # 관리자/스태프로 연동 시도 차단
    if user and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)):
        raise AuthForbidden(backend)

    # 이전 프리필 세션 정리(선택)
    for k in ('prefill_name', 'prefill_email', 'prefill_student_id'):
        try:
            strategy.session_pop(k)
        except Exception:
            pass

    details  = details or {}
    response = kwargs.get('response') or {}

    email = (details.get('email') or response.get('email') or '').lower()
    fullname = (
        details.get('fullname')
        or details.get('first_name')
        or response.get('name')
        or response.get('given_name')
        or ''
    )

    # ✅ 같은 이메일의 기존 유저가 있고 학번이 이미 있으면 곧바로 로그인
    if email:
        try:
            existing = User.objects.get(email=email)
        except User.DoesNotExist:
            existing = None
        if existing and getattr(existing, 'student_id', None):
            return {'user': existing}

    # 이미 학번을 받아 둔 경우(입력 완료 직후)면 다음 단계로 진행
    if strategy.session_get('pending_student_id'):
        return

    # 이메일 로컬파트가 숫자면 학번 프리필로 사용
    lp = _localpart(email)
    prefill_sid = lp if lp.isdigit() else ''

    # ✅ partial token 확보 + 세션에도 보관(후속 단계에서 안전하게 사용)
    cp = kwargs.get('current_partial')
    token = getattr(cp, 'token', None)
    if token:
        strategy.session_set('partial_token', token)

    # ask_student_id로 이동
    # (계정표시를 안 쓰면 'n','e'는 빼도 됨. 여기서는 깔끔하게 p만 보냄)
    params = {'partial_token': token or '', 'p': prefill_sid}
    url = reverse('ask_student_id') + '?' + urlencode(params)
    return strategy.redirect(url)

def create_user_with_sid(strategy=None, backend=None, details=None, user=None, *args, **kwargs):
    if not backend or backend.name != 'google-oauth2':
        return
    if user:
        return

    sid = strategy.session_get('pending_student_id')
    if not sid:
        return

    details  = details or {}
    response = kwargs.get('response') or {}
    email = (details.get('email') or response.get('email') or '').lower()
    fullname = (
        details.get('fullname') or details.get('first_name')
        or response.get('name') or response.get('given_name') or ''
    )

    # === 0) 학번 중복 사전 검사 (IntegrityError 방지) ===
    try:
        sid_owner = User.objects.get(student_id=sid)
    except User.DoesNotExist:
        sid_owner = None

    if sid_owner and (not email or sid_owner.email.lower() != email):
        # 다른 계정이 이미 사용 중인 학번 → 입력 화면으로 되돌리기
        strategy.session_set('ask_error', '이미 다른 계정으로 등록된 학번입니다.')

        # partial_token을 최대한 안전하게 확보 (없어도 동작하도록)
        token = None
        cp = kwargs.get('current_partial')
        if cp:
            token = getattr(cp, 'token', None)
        if not token:
            token = (strategy.request_data() or {}).get('partial_token') or strategy.session_get('partial_token')

        params = {'p': sid}
        if token:
            params['partial_token'] = token

        url = reverse('ask_student_id') + '?' + urlencode(params)
        return strategy.redirect(url)

    # === 1) 같은 이메일의 유저 보강/생성 ===
    instance = None
    if email:
        try:
            instance = User.objects.get(email=email)
        except User.DoesNotExist:
            instance = None

    if instance is None:
        # (실무 안전장치) email이 비어오면 생성하지 말고 돌려보내기
        if not email:
            strategy.session_set('ask_error', '이메일 정보를 가져오지 못했습니다. 다시 시도해 주세요.')
            token = strategy.session_get('partial_token')
            url = reverse('ask_student_id') + ('?partial_token=' + token if token else '')
            return strategy.redirect(url)

        instance = User(email=email, name=fullname)
        setattr(instance, 'student_id', sid)
        instance.set_unusable_password()  # 소셜 전용 로그인
        instance.save()
    else:
        if not getattr(instance, 'student_id', None):
            setattr(instance, 'student_id', sid)
            instance.save()

    # === 2) 사용한 세션키 정리 ===
    for k in ('pending_student_id', 'prefill_name', 'prefill_email', 'prefill_student_id'):
        try:
            strategy.session_pop(k)
        except Exception:
            pass

    return {'user': instance}

def set_session_student_id(strategy=None, backend=None, user=None, *args, **kwargs):
    """로그인 완료 시 세션에 학번 저장(UX 통일)"""
    if user and getattr(user, 'student_id', None):
        strategy.request.session['user_student_id'] = str(user.student_id)
    return {}
