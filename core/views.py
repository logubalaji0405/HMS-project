import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET, require_POST

from .models import Profile, Appointment, ChatMessage, ChatRoom

logger = logging.getLogger(__name__)


def home(request):
    user_role = None
    if request.user.is_authenticated:
        profile = Profile.objects.filter(user=request.user).first()
        if profile:
            user_role = profile.role
    return render(request, 'home.html', {'user_role': user_role})


def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', 'patient').strip()
        department = request.POST.get('department', '').strip()

        if not first_name or not username or not email or not password1 or not password2:
            messages.error(request, "Please fill all required fields.")
            return redirect('register')

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register')

        if role == 'doctor' and not department:
            messages.error(request, "Department is required for doctor registration.")
            return redirect('register')

        approved = False if role == 'doctor' else True

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            email=email,
            password=password1
        )

        Profile.objects.create(
            user=user,
            role=role,
            phone=phone,
            department=department if role == 'doctor' else '',
            is_approved=approved
        )

        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    if request.user.is_authenticated:
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role == 'patient':
                return redirect('patient_dashboard')
            elif profile.role == 'doctor':
                return redirect('doctor_dashboard')
            elif profile.role == 'admin':
                return redirect('admin_dashboard')
        except Profile.DoesNotExist:
            return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'admin' if user.is_superuser else 'patient',
                    'is_approved': True
                }
            )

            if profile.role == 'doctor' and not profile.is_approved:
                messages.error(request, "Doctor account waiting for admin approval.")
                return redirect('login')

            login(request, user)
            return redirect('home')

        messages.error(request, "Invalid username or password.")
        return redirect('login')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')


@login_required
def patient_dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'patient':
        return redirect('home')

    total_doctors = Profile.objects.filter(role='doctor', is_approved=True).count()
    my_bookings = Appointment.objects.filter(patient=request.user).count()
    upcoming = Appointment.objects.filter(patient=request.user).order_by('appointment_date', 'appointment_time')[:5]
    history = Appointment.objects.filter(patient=request.user).order_by('-created_at')

    return render(request, 'patient_dashboard.html', {
        'total_doctors': total_doctors,
        'my_bookings': my_bookings,
        'upcoming': upcoming,
        'history': history,
    })


@login_required
def doctor_dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'doctor':
        return redirect('home')

    total_bookings = Appointment.objects.filter(doctor=request.user).count()
    pending_bookings = Appointment.objects.filter(doctor=request.user, status='pending').count()
    confirmed_bookings = Appointment.objects.filter(doctor=request.user, status='confirmed').count()
    appointments = Appointment.objects.filter(doctor=request.user).order_by('-created_at')

    return render(request, 'doctor_dashboard.html', {
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'appointments': appointments,
    })


@login_required
def admin_dashboard(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            'role': 'admin' if request.user.is_superuser else 'patient',
            'is_approved': True
        }
    )

    if profile.role != 'admin':
        return redirect('home')

    pending_doctors = Profile.objects.filter(role='doctor', is_approved=False)
    total_patients = Profile.objects.filter(role='patient').count()
    total_doctors = Profile.objects.filter(role='doctor', is_approved=True).count()
    total_appointments = Appointment.objects.count()
    daily_stats = Appointment.objects.values('appointment_date').annotate(total=Count('id')).order_by('-appointment_date')[:7]

    return render(request, 'admin_dashboard.html', {
        'pending_doctors': pending_doctors,
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'daily_stats': daily_stats,
    })


@login_required
def doctor_list(request):
    doctors = User.objects.filter(profile__role='doctor', profile__is_approved=True)
    return render(request, 'chat/doctor_list.html', {'doctors': doctors})


@login_required
def start_chat(request, doctor_id):
    doctor = get_object_or_404(User, id=doctor_id, profile__role='doctor', profile__is_approved=True)

    if request.user.profile.role != 'patient':
        return HttpResponseForbidden("Only patients can start chat with doctor.")

    room, _ = ChatRoom.objects.get_or_create(
        patient=request.user,
        doctor=doctor
    )
    return redirect('chat_room', room_id=room.id)


@login_required
def my_chats(request):
    if request.user.profile.role == 'patient':
        rooms = ChatRoom.objects.filter(patient=request.user).select_related('doctor', 'patient')
    elif request.user.profile.role == 'doctor':
        rooms = ChatRoom.objects.filter(doctor=request.user).select_related('doctor', 'patient')
    else:
        rooms = ChatRoom.objects.none()

    return render(request, 'chat/my_chats.html', {'rooms': rooms})


@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom.objects.select_related('patient', 'doctor'), id=room_id)

    if request.user != room.patient and request.user != room.doctor:
        return HttpResponseForbidden("You are not allowed to access this chat.")

    other_user = room.doctor if request.user == room.patient else room.patient

    return render(request, 'chat/chat_room.html', {
        'room': room,
        'other_user': other_user,
    })


@login_required
@require_GET
def get_messages(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user != room.patient and request.user != room.doctor:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    messages_qs = ChatMessage.objects.filter(room=room).select_related('sender').order_by('timestamp')
    messages_qs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    logger.warning(f"LOAD -> room={room.id}, count={messages_qs.count()}, user={request.user.username}")

    data = []
    for msg in messages_qs:
        data.append({
            'id': msg.id,
            'message': msg.message,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'is_me': msg.sender_id == request.user.id,
            'timestamp': msg.timestamp.strftime('%d %b %Y, %I:%M %p'),
        })

    return JsonResponse({'messages': data})


@login_required
@require_POST
def send_message(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user != room.patient and request.user != room.doctor:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    message_text = request.POST.get('message', '').strip()
    if not message_text:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    msg = ChatMessage.objects.create(
        room=room,
        sender=request.user,
        message=message_text
    )

    logger.warning(f"SEND -> room={room.id}, user={request.user.username}, text={message_text}")

    return JsonResponse({
        'success': True,
        'id': msg.id,
        'message': msg.message,
        'sender': msg.sender.username,
        'sender_id': msg.sender.id,
        'is_me': True,
        'timestamp': msg.timestamp.strftime('%d %b %Y, %I:%M %p'),
    })