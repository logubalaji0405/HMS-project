from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('patient-dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('doctors/', views.doctor_list, name='doctor_list'),
    path('start-chat/<int:doctor_id>/', views.start_chat, name='start_chat'),
    path('my-chats/', views.my_chats, name='my_chats'),
    path('chat-room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat-room/<int:room_id>/messages/', views.get_messages, name='get_messages'),
    path('chat-room/<int:room_id>/send/', views.send_message, name='send_message'),
]