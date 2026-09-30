from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm
from .models import Category, Post


def _sidebar():
    return {
        "categories": Category.objects.annotate(n=Count("posts", filter=Q(posts__is_published=True))).filter(n__gt=0),
        "recent_posts": Post.objects.published()[:4],
    }


def post_list(request):
    posts = Post.objects.published().select_related("author", "category")
    category = None
    if slug := request.GET.get("category"):
        category = get_object_or_404(Category, slug=slug)
        posts = posts.filter(category=category)
    if q := request.GET.get("q"):
        posts = posts.filter(Q(title__icontains=q) | Q(body__icontains=q))
    page = Paginator(posts, 6).get_page(request.GET.get("page"))
    return render(request, "blog/list.html", {"page": page, "category": category, **_sidebar()})


def post_detail(request, slug):
    post = get_object_or_404(Post.objects.published().select_related("author", "category"), slug=slug)
    form = CommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.save()
        messages.success(request, "Your comment has been posted.")
        return redirect(post.get_absolute_url() + "#comments")
    comments = post.comments.filter(is_approved=True)
    return render(request, "blog/detail.html", {"post": post, "form": form, "comments": comments, **_sidebar()})
