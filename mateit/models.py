from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

# ✅ 사용자 관리자
# mateit/models.py

class CustomUserManager(BaseUserManager):
    def create_user(self, student_id, email=None, password=None, name=None, **extra_fields):
        if not student_id:
            raise ValueError("학번은 필수입니다.")

        # 소셜에서 올 수 있는 잉여 키 정리
        # (모델에 없으면 pop 해서 제거)
        extra_fields.pop('email', None)        # 모델에 email 없으면 제거
        extra_fields.pop('username', None)
        extra_fields.pop('first_name', None)
        extra_fields.pop('last_name', None)
        extra_fields.pop('fullname', None)
        extra_fields.pop('nickname', None)

        email = self.normalize_email(email) if email else None

        # name이 비어 있으면 details에서 보조 추출 시도 (없으면 빈 문자열)
        if not name:
            name = ""  # 필요하면 위에서 pop한 값 중 하나를 우선순위로 채워도 됨

        user = self.model(student_id=student_id, name=name, email=email,  **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, password, name=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(student_id, password=password, name=name, **extra_fields)


# ✅ 사용자 모델
class CustomUser(AbstractBaseUser, PermissionsMixin):
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=30)

    # ✅ 이메일 필드 추가 (이메일 머지/매칭용)
    email = models.EmailField(unique=True, null=True, blank=True)

    # ★ 추가
    student_id_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.student_id

# ✅ 프로필 모델 (공개 정보)
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30)
    semester = models.CharField(max_length=10)
    birth_year = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)
    dorm_type = models.CharField(max_length=10)
    intro_sentence = models.CharField(max_length=10)

    daily_rhythm = models.CharField(max_length=20)
    wake_habit = models.CharField(max_length=20)
    weekend_life = models.CharField(max_length=20)
    sleep_habit = models.CharField(max_length=20)
    personality_type = models.CharField(max_length=20)
    opinion_style = models.CharField(max_length=20)
    privacy_need = models.CharField(max_length=20)
    scent_sensitivity = models.CharField(max_length=20)
    earphone_use = models.CharField(max_length=20)
    preferred_temp = models.CharField(max_length=20)
    cleaning_style = models.CharField(max_length=20)
    study_place = models.CharField(max_length=20)
    shower_time = models.CharField(max_length=20)
    shared_item_opinion = models.CharField(max_length=20)
    outing_frequency = models.CharField(max_length=20)
    smoking = models.CharField(max_length=20)
    military = models.CharField(max_length=20, blank=True)

    profile_emoji = models.CharField(max_length=4, blank=True, default='')
    keyword_tags = models.TextField(blank=True)

    confirmed_with = models.ForeignKey(
        CustomUser,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='confirmed_partner_of'
    )

    cancel_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.nickname} ({self.user.student_id})"

# ✅ 찜 모델 (💖)
class LikedProfile(models.Model):
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='likes_given')
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='likes_received')
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.name} → {self.to_user.name}"

# ✅ 채팅 메시지 모델
class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.name} → {self.receiver.name}: {self.text[:20]}"

class StudentIdVerification(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    student_id = models.CharField(max_length=10)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    @classmethod
    def create_code(cls, user, student_id):
        import random
        code = f"{random.randint(0, 999999):06d}"
        now = timezone.now()
        return cls.objects.create(
            user=user,
            student_id=student_id,
            code=code,
            expires_at=now + timedelta(minutes=10)
        )

    def is_valid(self, code):
        return (not self.is_used) and (self.code == code) and (timezone.now() <= self.expires_at)

class RoommateRequest(models.Model):
    PENDING  = "P"
    ACCEPTED = "A"
    DECLINED = "D"
    STATUS_CHOICES = [
        (PENDING,  "Pending"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
    ]

    sender   = models.ForeignKey(
        CustomUser, related_name="sent_roommate_requests",
        on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        CustomUser, related_name="received_roommate_requests",
        on_delete=models.CASCADE
    )

    status     = models.CharField(max_length=1, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # 같은 두 사람 사이에 동시에 "PENDING" 요청은 하나만 존재
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver", "status"],
                condition=Q(status="P"),
                name="uniq_pending_roommate_request_pair",
            )
        ]
        indexes = [
            models.Index(fields=["sender", "receiver", "status"]),
        ]

    def __str__(self):
        return f"{self.sender.name} → {self.receiver.name} [{self.get_status_display()}]"