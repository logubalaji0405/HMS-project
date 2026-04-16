from django.contrib import admin
from .models import Profile, Appointment, ChatMessage,ChatRoom
admin.site.register(Profile)
admin.site.register(Appointment)
admin.site.register(ChatMessage)
admin.site.register(ChatRoom)