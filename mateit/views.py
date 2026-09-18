from django.shortcuts import get_object_or_404
from django.contrib import messages
from .forms import UserProfileForm
from utils.label_dict import STYLE_LABELS
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Q
from .models import UserProfile, CustomUser, LikedProfile
from django.http import Http404
from .models import Message
import random
import json
import logging
logger = logging.getLogger(__name__)
from django.contrib.auth import login as auth_login
from django.views.decorators.csrf import csrf_exempt
import unicodedata
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from datetime import timedelta
from django.utils import timezone
import re
from django.urls import reverse
from urllib.parse import urlencode
from django.contrib.auth import logout as auth_logout
from social_django.models import UserSocialAuth
from .models import RoommateRequest
from django.contrib.auth.decorators import login_required




# ✅ 메인 페이지 (권장 버전)
def dormitory_view(request):
    user_gender = ""
    user_dorm_type = ""
    allowed_buildings = []

    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            user_gender = profile.gender
            user_dorm_type = profile.dorm_type
            allowed_buildings = allowed_buildings_for(profile)
        except UserProfile.DoesNotExist:
            pass  # 프로필 없으면 기본값 유지

    return render(request, 'main.html', {
        # 'user_student_id': getattr(request.user, 'student_id', None),  # ← 더 이상 필요 없음
        'user_gender': user_gender,
        'user_dorm_type': user_dorm_type,
        'allowed_buildings': allowed_buildings,
    })

# ✅ 로그인
def dormitory_login(request):
    if request.method == 'POST':
        student_id = request.POST.get('studentId', '').strip()
        password = request.POST.get('password', '')

        try:
            user = CustomUser.objects.get(student_id=student_id)
            if user.check_password(password):
                # ✅ Django 인증 세션 활성화
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                # (호환을 위해 유지) 필요하면 세션 키도 남겨둠
                request.session['user_student_id'] = student_id
                return redirect('home')
            else:
                return render(request, 'login.html', {
                    'studentId': student_id,
                    'pw_error': '비밀번호가 일치하지 않습니다.'
                })
        except CustomUser.DoesNotExist:
            return render(request, 'login.html', {
                'id_error': '존재하지 않는 사용자입니다.'
            })

    return render(request, 'login.html')

# ✅ 회원가입
def dormitory_signup(request):
    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        student_id = request.POST.get('studentId', '').strip()
        password   = request.POST.get('password', '')
        password2  = request.POST.get('password2', '')

        # 0) 이름 유효성 검사 (한글+영문만 허용)
        if not re.match(r'^[가-힣a-zA-Z]+$', name):
            return render(request, 'signup.html', {
                'name_error': '이름에는 한글과 영문만 입력 가능합니다.',
                'name': name,
                'studentId': student_id,
            })

        # 1) 비번 불일치
        if password != password2:
            return render(request, 'signup.html', {
                'pw_error': '비밀번호가 일치하지 않습니다.',   # ← 키 이름 통일
                'name': name,
                'studentId': student_id,
            })

        # 2) 중복 학번
        if CustomUser.objects.filter(student_id=student_id).exists():
            return render(request, 'signup.html', {
                'id_error': '이미 존재하는 학번입니다.',      # ← 키 이름 통일
                'name': name,
                'studentId': student_id,
            })

        CustomUser.objects.create_user(student_id=student_id, name=name, password=password)
        return redirect('login')

    return render(request, 'signup.html')

# ✅ 로그아웃
def dormitory_logout(request):
    auth_logout(request)                 # Django 인증 로그아웃
    request.session.flush()              # 기존 세션 키도 정리 (user_student_id 등)
    return redirect('home')

# ✅ 내 정보 입력하기
def profile_input_view(request):
    user_student_id = request.session.get('user_student_id')
    if not user_student_id:
        return redirect('login')

    user = get_object_or_404(CustomUser, student_id=user_student_id)
    semesters = ['1-1', '1-2', '2-1', '2-2', '3-1', '3-2', '4-1', '4-2']
    birth_years = list(range(1990, 2008))

    try:
        profile = user.userprofile
        is_edit = True
    except UserProfile.DoesNotExist:
        profile = None
        is_edit = False

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            prev_gender = profile.gender if is_edit else None
            prev_dorm = profile.dorm_type if is_edit else None

            # 저장 준비
            new_profile = form.save(commit=False)
            new_profile.user = user

            # 🔹 자동 키워드 생성
            tags = []
            for field, value in form.cleaned_data.items():
                if field in STYLE_LABELS and value in STYLE_LABELS[field]:
                    tags.append(STYLE_LABELS[field][value])
            new_profile.keyword_tags = ' '.join(tags)

            # 실제 저장
            new_profile.save()

            # 성별/기숙사 변경 시 찜 초기화
            if is_edit and (prev_gender != new_profile.gender or prev_dorm != new_profile.dorm_type):
                LikedProfile.objects.filter(from_user=user).delete()
                LikedProfile.objects.filter(to_user=user).delete()
                Message.objects.filter(
                    Q(sender=user) | Q(receiver=user)
                ).delete()

                messages.info(request, "성별/기숙사 변경으로 찜 목록과 채팅 기록이 초기화되었습니다.")

            # 저장/수정 메시지
            messages.success(request, "프로필이 수정되었습니다." if is_edit else "프로필이 저장되었습니다.")
            return redirect('profile_input')
        else:
            messages.error(request, "입력 정보를 다시 확인해주세요.")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'profile_input.html', {
        'form': form,
        'semesters': semesters,
        'birth_years': birth_years,
        'is_edit': is_edit
    })

#✅ 동 접근 규칙: 성별+기숙사 → 허용 동 코드
def allowed_buildings_for(profile):
    if not profile:
        return []
    rule = (profile.gender, profile.dorm_type)  # ('남성','신기숙사') 등
    table = {
        ('남성', '신기숙사'): ['A'],
        ('여성', '신기숙사'): ['BC'],
        ('남성', '구기숙사'): ['D'],
        ('여성', '구기숙사'): ['E'],
    }
    return table.get(rule, [])

# ✅ 룸메이트 찾기
# 여기에 MyPage에서 입력받은 profile_emoji 필드가 있다고 가정합니다
FILTER_KEYS = [
    'daily_rhythm','wake_habit','weekend_life','sleep_habit',
    'personality_type','opinion_style','privacy_need','scent_sensitivity',
    'earphone_use','preferred_temp','cleaning_style','study_place',
    'shower_time','shared_item_opinion','outing_frequency',
    'smoking','military',
]

DORM_TYPE_MAP = {
    'A': '신기숙사',
    'BC': '신기숙사',
    'D': '구기숙사',
    'E': '구기숙사',
}

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import UserProfile, CustomUser, LikedProfile

# ⚠️ FILTER_KEYS는 기존처럼 유지
FILTER_KEYS = [
    "daily_rhythm",
    "wake_habit",
    "weekend_life",
    "sleep_habit",
    "personality_type",
    "opinion_style",
    "privacy_need",
    "scent_sensitivity",
    "earphone_use",
    "preferred_temp",
    "cleaning_style",
    "study_place",
    "shower_time",
    "shared_item_opinion",
    "outing_frequency",
    "smoking",
    "military",  # dorm in "AD"일 때만 사용됨
]

def find_roommate(request, dorm):

    # 로그인 확인
    student_id = request.session.get('user_student_id')
    if not student_id:
        return redirect('login')

    me = CustomUser.objects.filter(student_id=student_id).first()
    if not me:
        return redirect('login')

    try:
        my_profile = UserProfile.objects.get(user=me)
    except UserProfile.DoesNotExist:
        messages.error(request, "먼저 프로필을 입력해 주세요.")
        return redirect('profile_input')

    # 허용 동 체크
    allowed = allowed_buildings_for(my_profile)
    if dorm not in allowed:
        messages.error(request, "해당 기숙사는 본인 입장 대상이 아닙니다.")
        return redirect('home')

    # dorm -> DB 그룹(신/구기숙사) 매핑
    dorm_group = DORM_TYPE_MAP.get(dorm)
    if not dorm_group:
        messages.error(request, "알 수 없는 동 코드입니다.")
        return redirect('home')

    # 기본조건 (성별 + 기숙사 그룹)
    base_q = Q(gender=my_profile.gender, dorm_type=dorm_group) & Q(confirmed_with__isnull=True)

    # GET 필터 AND 묶기
    and_q = Q()
    for key in FILTER_KEYS:
        val = request.GET.get(key)
        if val:  # 값이 있을 때만 누적
            and_q &= Q(**{key: val})

    # 최종 조건 = 기본조건 + 추가 필터
    final_q = base_q & and_q

    profiles = (
        UserProfile.objects
        .filter(final_q)
        .exclude(user=me)
    )

    # 내가 찜했는지 표시
    liked_ids = set(
        LikedProfile.objects.filter(from_user=me).values_list('to_user_id', flat=True)
    )
    for p in profiles:
        p.is_liked = (p.user_id in liked_ids)

    return render(request, 'find_roommate.html', {
        'profiles': profiles,
        'dorm': dorm,
    })



# ✅ 하트 토글
def like_user(request, user_id):
    if request.method == 'POST':
        from_user = CustomUser.objects.get(student_id=request.session['user_student_id'])
        to_profile = UserProfile.objects.get(id=user_id)

        try:
            # 🔹 요청 body에서 action 값 추출
            data = json.loads(request.body)
            action = data.get('action')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'})

        if action == 'like':
            LikedProfile.objects.get_or_create(from_user=from_user, to_user=to_profile.user)
            return JsonResponse({'success': True, 'action': 'liked'})

        elif action == 'unlike':
            LikedProfile.objects.filter(from_user=from_user, to_user=to_profile.user).delete()
            return JsonResponse({'success': True, 'action': 'unliked'})

        else:
            return JsonResponse({'success': False, 'message': 'Unknown action'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ✅ 룸메이트 찾기 팝업창
def get_profile(request, user_id):
    try:
        profile = UserProfile.objects.select_related('user').get(id=user_id)

        return JsonResponse({
            'nickname': profile.nickname,
            'birth_year': profile.birth_year,
            'intro_sentence': profile.intro_sentence,
            'profile_emoji': profile.profile_emoji or "👤",
            'keyword_tags': profile.keyword_tags or "",
            'dorm_type': profile.dorm_type,
            'gender': profile.gender,
            'semester': profile.semester,
        })
    except UserProfile.DoesNotExist:
        raise Http404("해당 사용자를 찾을 수 없습니다.")

# ✅ 마이페이지
def mypage(request):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return redirect('login')

    try:
        user = CustomUser.objects.get(student_id=student_id)
        profile = UserProfile.objects.get(user=user)
    except (CustomUser.DoesNotExist, UserProfile.DoesNotExist):
        return redirect('profile_input')

    # 키워드(기존)
    keywords = [
        profile.daily_rhythm, profile.wake_habit, profile.weekend_life,
        profile.sleep_habit, profile.personality_type, profile.opinion_style,
        profile.privacy_need, profile.scent_sensitivity, profile.earphone_use,
        profile.preferred_temp, profile.cleaning_style, profile.study_place,
        profile.shower_time, profile.shared_item_opinion,
        profile.outing_frequency, profile.smoking,
    ]
    if profile.gender == '남성' and profile.military:
        keywords.append(profile.military)
    keyword_tag_list = profile.keyword_tags.split() if profile.keyword_tags else []

    # ✅ 추가: 확정 상태 및 상대 닉네임
    confirmed_with_id = profile.confirmed_with_id
    confirmed_with_nickname = None
    if confirmed_with_id:
        try:
            confirmed_with_nickname = UserProfile.objects.get(user_id=confirmed_with_id).nickname
        except UserProfile.DoesNotExist:
            confirmed_with_nickname = ""

    # 취소 횟수(최대 5회 규칙 기준)
    cancel_count = getattr(profile, 'cancel_count', 0)
    remaining_cancels = max(0, 5 - cancel_count)

    return render(request, 'mypage.html', {
        'nickname': profile.nickname,
        'semester': profile.semester,
        'birth_year': profile.birth_year,
        'gender': profile.gender,
        'dorm_type': profile.dorm_type,
        'intro_sentence': profile.intro_sentence,
        'profile_emoji': profile.profile_emoji,
        'keyword_list': keyword_tag_list,

        # 🔻 템플릿에서 사용할 값들
        'confirmed_with_id': confirmed_with_id,
        'confirmed_with_nickname': confirmed_with_nickname,
        'cancel_count': cancel_count,
        'remaining_cancels': remaining_cancels,
    })

# ✅ 프로필 이미지 선택
def profile_image_select(request):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return redirect('login')

    try:
        user = CustomUser.objects.get(student_id=student_id)
        profile = UserProfile.objects.get(user=user)
    except (CustomUser.DoesNotExist, UserProfile.DoesNotExist):
        return redirect('profile_input')

    if request.method == 'POST':
        chosen = request.POST.get('profile_image')
        if chosen:
            profile.profile_emoji = chosen
            profile.save()
            messages.success(request, "프로필 사진이 변경되었습니다.")
            return redirect('mypage')
        else:
            messages.error(request, "하나를 선택해 주세요.")

    return render(request, 'profile_image_select.html', {})

# ✅ 찜한 사용자
def has_final_consonant(korean_char):
    base = ord(korean_char) - 0xAC00
    return base % 28 != 0

# ✅ 찜한 사용자 목록 보기
def liked_list(request):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return redirect('login')

    try:
        user = CustomUser.objects.get(student_id=student_id)
        my_profile = UserProfile.objects.get(user=user)
    except (CustomUser.DoesNotExist, UserProfile.DoesNotExist):
        return redirect('profile_input')

    # 내 현재 성별/기숙사에 맞는 사람만 노출
    liked_qs = (
        LikedProfile.objects
        .filter(
            from_user=user,
            to_user__userprofile__gender=my_profile.gender,
            to_user__userprofile__dorm_type=my_profile.dorm_type,
        )
        .select_related('to_user', 'to_user__userprofile')
    )

    # 아예 DB에서 정리하고 싶다면 다음 줄 주석 해제:
    LikedProfile.objects.filter(from_user=user).exclude(
         to_user__userprofile__gender=my_profile.gender,
         to_user__userprofile__dorm_type=my_profile.dorm_type,
    ).delete()

    result_profiles = []
    for lp in liked_qs:
        up = getattr(lp.to_user, 'userprofile', None)
        if not up:
            continue
        nickname = up.nickname or ""
        last_char = nickname[-1] if nickname else ""
        josa = '과' if last_char and ((ord(last_char) - 44032) % 28 != 0) else '와'

        result_profiles.append({
            'profile': up,
            'josa': josa,
        })

    return render(request, 'liked_list.html', {
        'profiles': result_profiles
    })

# ✅ 찜 -> 채팅방 보기
def chat_room_view(request, user_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return redirect('login')

    from_user      = get_object_or_404(CustomUser, student_id=student_id)
    target_user    = get_object_or_404(CustomUser, id=user_id)
    target_profile = get_object_or_404(UserProfile, user=target_user)
    my_profile     = get_object_or_404(UserProfile, user=from_user)   # ← 추가

    # 읽음 처리
    Message.objects.filter(sender=target_user, receiver=from_user, is_read=False).update(is_read=True)

    # 오른쪽 말풍선(오래된→최신)
    chat_messages = Message.objects.filter(
        Q(sender=from_user, receiver=target_user) |
        Q(sender=target_user, receiver=from_user)
    ).order_by('timestamp')

    # 왼쪽 목록
    interacted_users = CustomUser.objects.filter(
        Q(sent_messages__receiver=from_user) |
        Q(received_messages__sender=from_user)
    ).distinct()

    chat_user_data = []
    very_old = timezone.now() - timedelta(days=365*100)

    for u in interacted_users:
        try:
            profile = UserProfile.objects.get(user=u)
        except UserProfile.DoesNotExist:
            continue

        latest_message = Message.objects.filter(
            Q(sender=from_user, receiver=u) | Q(sender=u, receiver=from_user)
        ).order_by('-timestamp').first()

        unread_count = Message.objects.filter(
            sender=u, receiver=from_user, is_read=False
        ).count()

        last_ts = latest_message.timestamp if latest_message else very_old

        chat_user_data.append({
            'id': u.id,
            'profile_id': profile.id,
            'nickname': profile.nickname,
            'latest_text': latest_message.text if latest_message else '',
            'unread_count': unread_count,
            'last_ts': last_ts,
        })

    chat_user_data.sort(key=lambda x: x['last_ts'], reverse=True)

    pending_incoming = RoommateRequest.objects.filter(
        sender=target_user, receiver=from_user, status=RoommateRequest.PENDING
    ).first()
    pending_outgoing = RoommateRequest.objects.filter(
        sender=from_user, receiver=target_user, status=RoommateRequest.PENDING
    ).first()

    # 내가 '누구에게든' 보낸 대기중 요청이 있는지 (전역)
    has_any_pending_outgoing = RoommateRequest.objects.filter(
        sender=from_user, status=RoommateRequest.PENDING
    ).exists()

    is_liked_target = LikedProfile.objects.filter(
        from_user=from_user, to_user=target_user
    ).exists()

    # ✅ 확정 상태 플래그
    me_confirmed = bool(my_profile.confirmed_with_id)
    you_confirmed = bool(target_profile.confirmed_with_id)

    # ✅ 버튼 활성화 조건은 '나만' 본다 (상대가 확정이어도 활성화)
    can_request = not me_confirmed

    return render(request, 'chat_room.html', {
        'target_user': target_user,
        'target_profile': target_profile,
        'messages': chat_messages,
        'from_user': from_user,
        'chat_users': chat_user_data,
        'pending_incoming': pending_incoming,
        'pending_outgoing': pending_outgoing,
        'is_liked_target': is_liked_target,
        'can_request': can_request,
        'me_confirmed': me_confirmed,
        'you_confirmed': you_confirmed,
        'my_nickname': my_profile.nickname,
        'has_any_pending_outgoing': has_any_pending_outgoing,
    })

@csrf_exempt
def send_message_view(request, user_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        # Ajax 요청이면 JSON, 그 외에는 로그인 페이지로
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)
        return redirect('login')

    if request.method == 'POST':
        from_user = get_object_or_404(CustomUser, student_id=student_id)
        to_user = get_object_or_404(CustomUser, id=user_id)
        content = (request.POST.get('message') or '').strip()

        if content:
            msg = Message.objects.create(sender=from_user, receiver=to_user, text=content)

            # ✅ Ajax 전송이면 페이지 리로드 없이 JSON 반환
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'id': msg.id,
                    'text': msg.text,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                })

    # ✅ 일반 폼 전송 fallback (리로드 허용)
    return redirect('chat_room', user_id=user_id)

# ✅ 홈 -> 채팅방 보기
def chat_home_view(request):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return redirect('login')

    from_user = get_object_or_404(CustomUser, student_id=student_id)

    # 🔻 여기에서 404 대신 리다이렉트
    try:
        my_profile = UserProfile.objects.get(user=from_user)
    except UserProfile.DoesNotExist:
        return redirect('profile_input')

    # 내가 '누구에게든' 보낸 대기중 요청이 있는지 (전역)
    has_any_pending_outgoing = RoommateRequest.objects.filter(
        sender=from_user, status=RoommateRequest.PENDING
    ).exists()

    interacted_users = CustomUser.objects.filter(
        Q(sent_messages__receiver=from_user) |
        Q(received_messages__sender=from_user)
    ).distinct()

    chat_user_data = []
    very_old = timezone.now() - timedelta(days=365*100)

    for u in interacted_users:
        try:
            profile = UserProfile.objects.get(user=u)
        except UserProfile.DoesNotExist:
            continue

        latest_message = Message.objects.filter(
            Q(sender=from_user, receiver=u) | Q(sender=u, receiver=from_user)
        ).order_by('-timestamp').first()

        unread_count = Message.objects.filter(
            sender=u, receiver=from_user, is_read=False
        ).count()

        last_ts = latest_message.timestamp if latest_message else very_old

        chat_user_data.append({
            'id': u.id,
            'profile_id': profile.id,
            'nickname': profile.nickname,
            'latest_text': latest_message.text if latest_message else '',
            'unread_count': unread_count,
            'last_ts': last_ts,
        })

    chat_user_data.sort(key=lambda x: x['last_ts'], reverse=True)

    return render(request, 'chat_room.html', {
        'chat_users': chat_user_data,
        'from_user': from_user,
        'target_user': None,
        'target_profile': None,
        'messages': [],
        'my_nickname': my_profile.nickname or '',
        'has_any_pending_outgoing': has_any_pending_outgoing,
    })

# ✅ 채팅 삭제하기
@require_POST
def delete_message_view(request, message_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)

    try:
        message = Message.objects.get(id=message_id)

        # 보낸 사람만 삭제 가능
        if message.sender.student_id != student_id:
            return JsonResponse({'success': False, 'message': '삭제 권한이 없습니다.'}, status=403)

        # ✅ 시스템 메시지 여부 체크
        protected_phrases = [
            "룸메이트 확정을 요청했습니다.",
            "룸메이트 확정 요청을 보냈습니다",
            "응답을 기다리는 중",
            "룸메이트 확정 요청을 수락했습니다",
            "룸메이트 확정 요청을 거절했습니다",
            "룸메이트 확정을 취소했습니다",
            "룸메이트 확정이 완료되었습니다",
        ]
        if any(phrase in (message.text or "") for phrase in protected_phrases):
            return JsonResponse({'success': False, 'message': '이 메시지는 삭제할 수 없습니다.'}, status=400)

        # 일반 메시지라면 삭제 허용
        message.delete()
        return JsonResponse({'success': True})

    except Message.DoesNotExist:
        return JsonResponse({'success': False, 'message': '메시지를 찾을 수 없습니다.'}, status=404)


# ✅ 실시간 채팅 가져오기
@require_GET
def fetch_messages(request, user_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'messages': []}, status=403)

    from_user = get_object_or_404(CustomUser, student_id=student_id)
    to_user   = get_object_or_404(CustomUser, id=user_id)

    last_id = int(request.GET.get('after', 0))

    qs = (Message.objects
          .filter(Q(sender=from_user, receiver=to_user) |
                  Q(sender=to_user,   receiver=from_user))
          .filter(id__gt=last_id)
          .order_by('id'))

    payload = []
    for m in qs:
        t = (m.text or "")

        # 내가 거절했을 때: 내 화면에서 숨김
        if m.sender_id == from_user.id and "확정 요청을 거절했습니다" in t:
            continue

        # 상대 화면에서 보이면 안 되는 취소 메시지 숨김
        if m.sender_id != from_user.id and "룸메이트 확정을 취소했습니다" in t:
            continue

        # "응답을 기다리는 중"은 '보낸 사람(B) 본인 화면'에서만 숨김
        if m.sender_id == from_user.id and "응답을 기다리는 중" in t:
            continue

        if "확정 요청을 취소했습니다" in t:
            continue

        payload.append({
            'id': m.id,
            'text': m.text,
            'mine': (m.sender_id == from_user.id),
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        })

    # (선택) 읽음처리
    Message.objects.filter(sender=to_user, receiver=from_user, is_read=False).update(is_read=True)

    return JsonResponse({'messages': payload})


# ✅ 구글 최초 로그인 시 '학번 1회 입력' 페이지
def ask_student_id(request):
    token = (
        request.GET.get('partial_token')
        or request.POST.get('partial_token')
        or request.session.get('partial_token')
    )
    prefill = request.GET.get('p') or ''
    error_msg = request.session.pop('ask_error', None)

    if request.method == 'POST':
        sid = (request.POST.get('student_id') or '').strip()

        # 1) 형식 체크
        if not sid.isdigit() or not (7 <= len(sid) <= 10):
            return render(request, 'ask_student_id.html', {
                'error': '학번은 숫자 7~10자리여야 합니다.',
                'prefill': sid,
                'partial_token': token or '',
            })

        # 2) 중복 학번이면 같은 페이지 유지(redirect X)
        if CustomUser.objects.filter(student_id=sid).exists():
            return render(request, 'ask_student_id.html', {
                'error': '이미 다른 계정으로 등록된 학번입니다.',
                'prefill': sid,                 # 사용자가 입력한 값 유지
                'partial_token': token or '',   # hidden input 유지
            })

        # 3) 통과 → 파이프라인 재개
        request.session['pending_student_id'] = sid
        return redirect(
            reverse('social:complete', args=['google-oauth2']) + f'?partial_token={token}'
        )

    # GET: 첫 진입
    return render(request, 'ask_student_id.html', {
        'prefill': prefill,
        'partial_token': token or '',
        'error': error_msg,
    })

# ✅ 탈퇴하기
def _current_user(request):
    """Django 인증 또는 세션 학번으로 현재 사용자 찾기"""
    if request.user.is_authenticated:
        return request.user
    sid = request.session.get('user_student_id')
    if not sid:
        return None
    try:
        return CustomUser.objects.get(student_id=sid)
    except CustomUser.DoesNotExist:
        return None

def delete_account_view(request):
    """
    계정 탈퇴:
    - 확인 문구 'DELETE' 입력 후 POST
    - 메시지/찜/프로필/소셜연동 제거 → 사용자 삭제 → 로그아웃
    """
    user = _current_user(request)
    if not user:
        # 로그인 안 했으면 로그인 페이지로
        return redirect('login')

    if request.method == 'POST':
        confirm = (request.POST.get('confirm') or '').strip().upper()
        if confirm != 'DELETE':
            return render(request, 'delete_account.html', {
                'error': "확인 문구로 대문자 DELETE를 입력해 주세요."
            })

        # 1) 관련 객체 정리(안전하게 선삭제; on_delete=CASCADE여도 문제없음)
        LikedProfile.objects.filter(Q(from_user=user) | Q(to_user=user)).delete()
        Message.objects.filter(Q(sender=user) | Q(receiver=user)).delete()
        UserProfile.objects.filter(user=user).delete()
        UserSocialAuth.objects.filter(user=user).delete()

        # 2) 사용자 삭제
        user.delete()

        # 3) 로그아웃 & 세션 정리
        auth_logout(request)
        request.session.flush()

        messages.success(request, "탈퇴가 완료되었습니다.")
        return redirect('home')

    # GET: 확인 페이지
    return render(request, 'delete_account.html')

# ✅ 확정하기
@require_POST
def roommate_request_view(request, user_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)

    me  = get_object_or_404(CustomUser, student_id=student_id)
    you = get_object_or_404(CustomUser, id=user_id)

    # 자기 자신 요청 방지
    if me.id == you.id:
        return JsonResponse({'success': False, 'message': '자기 자신에게는 요청할 수 없습니다.'}, status=400)

    me_p  = get_object_or_404(UserProfile, user=me)
    you_p = get_object_or_404(UserProfile, user=you)

    # 이미 확정된 경우 차단
    if me_p.confirmed_with_id or you_p.confirmed_with_id:
        return JsonResponse({'success': False, 'message': '이미 확정된 사용자가 있습니다.'}, status=400)

    # 대기 중인 요청 중복 방지
    exists = RoommateRequest.objects.filter(
        Q(sender=me, receiver=you) | Q(sender=you, receiver=me),
        status=RoommateRequest.PENDING
    ).exists()
    if exists:
        return JsonResponse({'success': False, 'message': '대기 중인 요청이 이미 있어요.'}, status=400)

    rr = RoommateRequest.objects.create(sender=me, receiver=you)

    # 받은 사람(B)에게만 보이는 안내 (수락/거절 버튼 달리는 문구)
    Message.objects.create(
        sender=me, receiver=you,
        text=f"{me_p.nickname} 님이 룸메이트 확정을 요청했습니다."
    )

    # ❌ 보낸 사람(A)에게 '응답을 기다리는 중…' 메시지는 만들지 않음 (프론트에서만 임시로 보여줌)

    return JsonResponse({'success': True, 'request_id': rr.id})


@require_POST
@transaction.atomic
def roommate_accept_view(request, user_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)

    me = get_object_or_404(CustomUser, student_id=student_id)   # 수락자(요청의 receiver)
    you = get_object_or_404(CustomUser, id=user_id)             # 요청 보낸 사람

    me_p  = get_object_or_404(UserProfile, user=me)
    you_p = get_object_or_404(UserProfile, user=you)

    # 나에게 들어온 보류중 요청 1건만 찾기
    rr = RoommateRequest.objects.filter(sender=you, receiver=me, status=RoommateRequest.PENDING).first()
    if not rr:
        return JsonResponse({'success': False, 'message': '진행 중인 요청이 없습니다.'}, status=400)

    # 이미 확정된 경우 방어
    if me_p.confirmed_with_id or you_p.confirmed_with_id:
        return JsonResponse({'success': False, 'message': '이미 확정된 사용자가 있습니다.'}, status=400)

    # 상태 바꾸기
    rr.status = RoommateRequest.ACCEPTED
    rr.decided_at = timezone.now()
    rr.save(update_fields=['status', 'decided_at'])

    # 상호 확정
    me_p.confirmed_with  = you
    you_p.confirmed_with = me
    me_p.save(update_fields=['confirmed_with'])
    you_p.save(update_fields=['confirmed_with'])

    # ✅ 요청자 화면의 "응답을 기다리는 중…" 대기 문구를 서버에서도 정리
    Message.objects.filter(
        Q(sender=you, receiver=me) | Q(sender=me, receiver=you),
        text__contains="응답을 기다리는 중"
    ).delete()

    # 시스템 메시지 (각자 다르게 보이도록)
    Message.objects.create(
        sender=me, receiver=you,
        text=f"{me_p.nickname} 님이 룸메이트 확정 요청을 수락했습니다. 룸메이트 확정 완료!"
    )
    Message.objects.create(
        sender=you, receiver=me,
        text=f"{you_p.nickname} 님과 룸메이트 확정이 완료되었습니다."
    )

    return JsonResponse({'success': True})

@require_POST
@transaction.atomic
def roommate_reject_view(request, user_id):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)

    me = get_object_or_404(CustomUser, student_id=student_id)   # 거절자(요청의 receiver)
    you = get_object_or_404(CustomUser, id=user_id)             # 요청 보낸 사람

    me_p  = get_object_or_404(UserProfile, user=me)
    you_p = get_object_or_404(UserProfile, user=you)

    rr = RoommateRequest.objects.filter(sender=you, receiver=me, status=RoommateRequest.PENDING).first()
    if not rr:
        return JsonResponse({'success': False, 'message': '진행 중인 요청이 없습니다.'}, status=400)

    rr.status = RoommateRequest.DECLINED
    rr.decided_at = timezone.now()
    rr.save(update_fields=['status', 'decided_at'])

    # ✅ 요청자 화면의 "응답을 기다리는 중…" 삭제 (새로고침에도 반영)
    Message.objects.filter(
        Q(sender=you, receiver=me) | Q(sender=me, receiver=you),
        text__contains="응답을 기다리는 중"
    ).delete()

    # ✅ 시스템 메시지 "단 1건" (거절자 → 요청자)
    #    → 이후 서버 필터로 거절자 화면에선 숨김
    Message.objects.create(
        sender=me, receiver=you,
        text=f"{me_p.nickname} 님이 룸메이트 확정 요청을 거절했습니다."
    )

    # ❌ 더 이상 요청자→거절자 메시지는 만들지 않음
    return JsonResponse({'success': True})

# ✅ 확정 취소하기 (views.py)
@require_POST
@transaction.atomic
def roommate_cancel_view(request):
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)

    me = get_object_or_404(CustomUser, student_id=student_id)  # 취소자
    me_p = get_object_or_404(UserProfile, user=me)

    if not me_p.confirmed_with_id:
        return JsonResponse({'success': False, 'message': '확정된 룸메이트가 없습니다.'}, status=400)

    if me_p.cancel_count >= 5:
        return JsonResponse({'success': False, 'message': '확정 취소 가능 횟수를 모두 사용했습니다.'}, status=400)

    you = me_p.confirmed_with
    you_p = get_object_or_404(UserProfile, user=you)

    # 해제 + 내 취소횟수 1 소모
    me_p.confirmed_with = None
    you_p.confirmed_with = None
    me_p.cancel_count += 1
    me_p.save(update_fields=['confirmed_with', 'cancel_count'])
    you_p.save(update_fields=['confirmed_with'])

    # 시스템 메시지(상대 화면엔 숨김 처리됨)
    Message.objects.create(
        sender=me, receiver=you,
        text=f"{me_p.nickname} 님이 룸메이트 확정을 취소했습니다."
    )

    remaining = max(0, 5 - me_p.cancel_count)

    return JsonResponse({
        'success': True,
        'message': '룸메이트 확정을 취소했습니다.',
        'partner_nickname': getattr(you_p, 'nickname', ''),
        'remaining_cancels': remaining,
    })

@require_POST
def roommate_request_cancel_view(request, user_id):
    """내가 보낸 '보류중' 확정요청을 취소한다 (상대가 아직 수락/거절 전)."""
    student_id = request.session.get('user_student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=403)

    me  = get_object_or_404(CustomUser, student_id=student_id)
    you = get_object_or_404(CustomUser, id=user_id)

    # 내가 '보낸' PENDING 요청 1건만 찾기
    rr = RoommateRequest.objects.filter(sender=me, receiver=you, status=RoommateRequest.PENDING).first()
    if not rr:
        return JsonResponse({'success': False, 'message': '취소할 보류 중 요청이 없습니다.'}, status=400)

    # 관련 안내 메시지들 삭제:
    # - 상대에게 보낸:  "<내닉> 님이 룸메이트 확정을 요청했습니다."
    # - 내 화면에 뜬:   "<상대닉> 님에게 확정 요청을 보냈습니다. 응답을 기다리는 중…"
    Message.objects.filter(
        Q(sender=me, receiver=you, text__endswith="룸메이트 확정을 요청했습니다.") |
        Q(sender=you, receiver=me, text__contains="응답을 기다리는 중")
    ).delete()

    # 요청 자체 제거(혹은 rr.status = RoommateRequest.DECLINED 로 바꿔도 됨)
    rr.delete()

    return JsonResponse({'success': True})


# ✅ 랜덤 찾기
# 유틸: 프로필을 dict로 직렬화
def profile_to_dict(profile, similarity=None, matched_labels=None):
    return {
        # ❗️핵심: id는 '프로필 PK'로 내려보냅니다.
        "id": profile.id,                 # ← 기존: profile.user.id (잘못)
        "profile_id": profile.id,         # (명시적으로도 넣어둠)
        "user_id": profile.user.id,       # (필요시 사용)

        "nickname": profile.nickname,
        "birth_year": profile.birth_year,
        "intro_sentence": profile.intro_sentence,
        "profile_emoji": profile.profile_emoji,
        "is_liked": getattr(profile, "is_liked", False),
        "similarity": round(similarity, 2) if similarity is not None else None,
        "matched_labels": matched_labels or [],
    }


# 유틸: 빈값 정규화
def normalize_value(field, val):
    mapping = {
        "sleep_habit": {"": "quiet"},
        "scent_sensitivity": {"": "not_sensitive"},
        "preferred_temp": {"": "cool"},
        "cleaning_style": {"": "not_clean"},
    }
    return mapping.get(field, {}).get(val, val)

# 유사도 계산기
def compute_similarity(base, target):
    keys = [
        "daily_rhythm","wake_habit","weekend_life","sleep_habit","personality_type",
        "opinion_style","privacy_need","scent_sensitivity","earphone_use","preferred_temp",
        "cleaning_style","study_place","shower_time","shared_item_opinion",
        "outing_frequency","smoking","military",
    ]
    match = 0
    total = 0
    matched_labels = []

    for k in keys:
        base_val = normalize_value(k, getattr(base, k, None))
        target_val = normalize_value(k, getattr(target, k, None))
        if not base_val or not target_val:
            continue
        total += 1
        if base_val == target_val:
            match += 1
            matched_labels.append(f"#{k}:{base_val}")

    if total == 0:
        return 0.0, []
    return match / total, matched_labels

@login_required
def recommendations_api(request):
    user = request.user
    try:
        my_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "프로필을 먼저 저장하세요."}, status=400)

    # 추천 파라미터
    threshold = float(request.GET.get("threshold", 0.5))
    seed      = int(request.GET.get("seed", random.randint(0, 999999)))
    limit     = int(request.GET.get("limit", 8))

    # 기본 조건(성별/기숙사 동일 + 확정X)
    base_q = Q(
        gender=my_profile.gender,
        dorm_type=my_profile.dorm_type,
        confirmed_with__isnull=True,
    )

    # 라디오 필터 적용
    and_q = Q()
    for key in FILTER_KEYS:
        val = request.GET.get(key)
        if val:
            and_q &= Q(**{key: val})

    # 후보군
    qs = (
        UserProfile.objects
        .filter(base_q & and_q)
        .exclude(user=user)
        .select_related('user')
    )

    # ✅ 내가 좋아요한 유저 id 집합
    liked_ids = set(
        LikedProfile.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    )

    # 유사도 계산 + 임계값
    candidates = []
    for p in qs:
        p.is_liked = (p.user_id in liked_ids)  # ✅ 요 줄이 핵심: 하트 상태 주입
        sim, matched = compute_similarity(my_profile, p)
        if sim >= threshold:
            candidates.append((p, sim, matched))

    if not candidates:
        return JsonResponse([], safe=False)

    # 시드 섞기 + 점수순
    rnd = random.Random(seed)
    rnd.shuffle(candidates)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # 직렬화(여기서 p.is_liked 사용됨)
    result = [profile_to_dict(p, sim, matched) for p, sim, matched in candidates[:limit]]
    return JsonResponse(result, safe=False)
