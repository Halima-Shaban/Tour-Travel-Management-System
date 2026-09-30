from django.contrib import admin

from .models import Category, Comment, Post

admin.site.register(Category)
admin.site.register(Comment)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "is_published", "created_at"]
    list_filter = ["is_published", "category"]
    search_fields = ["title", "body"]
