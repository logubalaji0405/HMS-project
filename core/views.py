from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import Profile, Appointment, ChatMessage


def home(request):
    user_role = None
    if request.user.is_authenticated:
        profile = Profile.objects.filter(user=request.user).first()
        if profile:
            user_role = profile.role
    return render(request, 'home.html')


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

        approved = True
        if role == 'doctor':
            approved = False

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
            profile, created = Profile.objects.get_or_create(
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

            if profile.role == 'patient':
                return redirect('home')
            elif profile.role == 'doctor':
                return redirect('home')
            elif profile.role == 'admin':
                return redirect('home')
            else:
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

    context = {
        'total_doctors': total_doctors,
        'my_bookings': my_bookings,
        'upcoming': upcoming,
        'history': history,
    }
    return render(request, 'patient_dashboard.html', context)


@login_required
def doctor_dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'doctor':
        return redirect('home')

    total_bookings = Appointment.objects.filter(doctor=request.user).count()
    pending_bookings = Appointment.objects.filter(doctor=request.user, status='pending').count()
    confirmed_bookings = Appointment.objects.filter(doctor=request.user, status='confirmed').count()
    appointments = Appointment.objects.filter(doctor=request.user).order_by('-created_at')

    context = {
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'appointments': appointments,
    }
    return render(request, 'doctor_dashboard.html', context)


@login_required
def admin_dashboard(request):
    profile, created = Profile.objects.get_or_create(
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

    context = {
        'pending_doctors': pending_doctors,
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'daily_stats': daily_stats,
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def book_appointment(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'patient':
        return redirect('home')

    doctors = Profile.objects.filter(role='doctor', is_approved=True)

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        problem = request.POST.get('problem')

        doctor_user = get_object_or_404(User, id=doctor_id)

        Appointment.objects.create(
            patient=request.user,
            doctor=doctor_user,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            problem=problem,
            status='pending'
        )

        messages.success(request, "Appointment booked successfully.")
        return redirect('booking_history')

    return render(request, 'booking.html', {'doctors': doctors})


@login_required
def booking_history(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'patient':
        return redirect('home')

    appointments = Appointment.objects.filter(patient=request.user).order_by('-created_at')
    return render(request, 'booking_history.html', {'appointments': appointments})


@login_required
def confirm_booking(request, appointment_id):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'doctor':
        return redirect('home')

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = 'confirmed'
    appointment.save()
    messages.success(request, "Appointment confirmed.")
    return redirect('doctor_dashboard')


@login_required
def reject_booking(request, appointment_id):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'doctor':
        return redirect('home')

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = 'rejected'
    appointment.save()
    messages.success(request, "Appointment rejected.")
    return redirect('doctor_dashboard')


@login_required
def approve_doctor(request, profile_id):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.role != 'admin':
        return redirect('home')

    doctor_profile = get_object_or_404(Profile, id=profile_id, role='doctor')
    doctor_profile.is_approved = True
    doctor_profile.save()
    messages.success(request, "Doctor approved successfully.")
    return redirect('admin_dashboard')


@login_required
def chat_view(request, receiver_id):
    receiver = get_object_or_404(User, id=receiver_id)

    messages_list = ChatMessage.objects.filter(
        sender__in=[request.user, receiver],
        receiver__in=[request.user, receiver]
    ).order_by('sent_at')

    if request.method == 'POST':
        msg = request.POST.get('message', '').strip()
        if msg:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                message=msg
            )
            return redirect('chat', receiver_id=receiver.id)

    return render(request, 'chat.html', {
        'receiver': receiver,
        'messages_list': messages_list
    })

@login_required
def profile(request):
    return render(request, 'profile.html')

    
@login_required
def edit_profile(request):
    profile = request.user.profile

    if request.method == 'POST':
        profile.phone = request.POST.get('phone')
        profile.age = request.POST.get('age')
        profile.address = request.POST.get('address')

        if request.FILES.get('profile_image'):
            profile.profile_image = request.FILES.get('profile_image')

        profile.save()
        return redirect('profile')

    return render(request, 'edit_profile.html')