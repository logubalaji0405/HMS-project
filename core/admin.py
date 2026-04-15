from django.contrib import admin
from .models import Profile, Appointment, ChatMessage

admin.site.register(Profile)
admin.site.register(Appointment)
admin.site.register(ChatMessage)