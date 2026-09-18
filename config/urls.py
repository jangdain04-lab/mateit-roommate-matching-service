from django.contrib import admin
from django.urls import path, include
from mateit import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dormitory_view, name='home'),
    path('login/', views.dormitory_login, name='login'),
    path('signup/', views.dormitory_signup, name='signup'),
    path('logout/', views.dormitory_logout, name='logout'),
    path('profile_input/', views.profile_input_view, name='profile_input'),
    path('liked/', views.liked_list, name='liked_list'),
    path('mypage/', views.mypage, name='mypage'),
    path('profile/image/', views.profile_image_select, name='profile_image_select'),
    path('find_roommate/<str:dorm>/', views.find_roommate, name='find_roommate'),
    path('like/<int:user_id>/', views.like_user, name='like_user'),
    path('get_profile/<int:user_id>/', views.get_profile, name='get_profile'),

    path("api/recommendations/", views.recommendations_api, name="recommendations_api"),
    path('chat/', views.chat_home_view, name='chat_home'),
    path('chat/<int:user_id>/', views.chat_room_view, name='chat_room'),
    path('chat/<int:user_id>/send/', views.send_message_view, name='send_message'),
    path('delete_message/<int:message_id>/', views.delete_message_view, name='delete_message'),
    path('chat/<int:user_id>/poll/', views.fetch_messages, name='chat_poll'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('oauth/ask-student-id/', views.ask_student_id, name='ask_student_id'),

    path('account/delete/', views.delete_account_view, name='delete_account'),

    path('roommate/request/<int:user_id>/', views.roommate_request_view, name='roommate_request'),
    path('roommate/accept/<int:user_id>/', views.roommate_accept_view, name='roommate_accept'),
    path('roommate/reject/<int:user_id>/', views.roommate_reject_view, name='roommate_reject'),
    path('roommate/cancel/', views.roommate_cancel_view, name='roommate_cancel'),
    path('roommate/request-cancel/<int:user_id>/', views.roommate_request_cancel_view, name='roommate_request_cancel'),

]
