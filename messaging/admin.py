from django.contrib import admin

from .models import Message, Thread


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ["booking", "updated_at"]
    inlines = [MessageInline]
