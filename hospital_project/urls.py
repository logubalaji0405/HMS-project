from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),  # Django default admin panel

    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('book/', views.book_appointment, name='book_appointment'),
    path('booking-history/', views.booking_history, name='booking_history'),

    path('confirm-booking/<int:appointment_id>/', views.confirm_booking, name='confirm_booking'),
    path('reject-booking/<int:appointment_id>/', views.reject_booking, name='reject_booking'),
    path('approve-doctor/<int:profile_id>/', views.approve_doctor, name='approve_doctor'),

    path('chat/<int:receiver_id>/', views.chat_view, name='chat'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
]