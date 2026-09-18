# admin.py
from django.contrib import admin
from .models import UserProfile, CustomUser, LikedProfile, Message, RoommateRequest   # ← 추가!
from social_django.models import UserSocialAuth
from django.shortcuts import redirect

import social_django.admin

# 그대로 유지
admin.site.register(UserProfile)
admin.site.register(CustomUser)
admin.site.register(LikedProfile)

# RoommateRequest (조회 전용)
@admin.register(RoommateRequest)
class RoommateRequestAdmin(admin.ModelAdmin):
    list_display = ("sender_display", "receiver_display", "status",
                    "created_at", "decided_at")
    list_filter  = ("status",)
    search_fields = (
        "sender__student_id", "sender__userprofile__nickname",
        "receiver__student_id", "receiver__userprofile__nickname",
    )
    ordering = ("-created_at",)
    readonly_fields = ("sender", "receiver", "status", "created_at", "decided_at")

    # 조회 전용(추가/수정/삭제 막기)
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    # 보기 좋은 표시용 컬럼
    def sender_display(self, obj):
        nick = getattr(getattr(obj.sender, "userprofile", None), "nickname", None)
        return nick or obj.sender.student_id
    sender_display.short_description = "보낸 사람"

    def receiver_display(self, obj):
        nick = getattr(getattr(obj.receiver, "userprofile", None), "nickname", None)
        return nick or obj.receiver.student_id
    receiver_display.short_description = "받는 사람"

# Message
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "text_short", "timestamp", "is_read")
    list_display_links = ("id", "text_short")
    list_filter = (
        ("sender", admin.RelatedOnlyFieldListFilter),
        ("receiver", admin.RelatedOnlyFieldListFilter),
        "is_read",
        "timestamp",
    )
    search_fields = (
        "text",
        "sender__student_id", "receiver__student_id",
        "sender__userprofile__nickname", "receiver__userprofile__nickname",
    )
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"
    list_select_related = ("sender", "receiver")
    list_per_page = 50
    actions = ["mark_read", "mark_unread"]

    def conversation(self, obj):
        s = getattr(getattr(obj.sender, "userprofile", None), "nickname", None) or getattr(obj.sender, "student_id", "")
        r = getattr(getattr(obj.receiver, "userprofile", None), "nickname", None) or getattr(obj.receiver, "student_id", "")
        return f"{s} → {r}"
    conversation.short_description = "대화"

    def text_short(self, obj):
        t = obj.text or ""
        return (t[:30] + "…") if len(t) > 30 else t
    text_short.short_description = "메시지"

    def mark_read(self, request, queryset):
        n = queryset.update(is_read=True)
        self.message_user(request, f"{n}개 읽음 처리")
    mark_read.short_description = "선택 항목 읽음 처리"

    def mark_unread(self, request, queryset):
        n = queryset.update(is_read=False)
        self.message_user(request, f"{n}개 안읽음 처리")
    mark_unread.short_description = "선택 항목 안읽음 처리"

# 기본 등록 해제 (이미 해제돼 있어도 예외 처리)
try:
    admin.site.unregister(UserSocialAuth)
except admin.sites.NotRegistered:
    pass

@admin.register(UserSocialAuth)
class UserSocialAuthAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "uid", "created", "modified")
    list_display_links = ("user",)
    search_fields = ("user__username", "user__email", "uid")
    list_filter = ("provider",)
    ordering = ("-created",)
