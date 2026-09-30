from django import forms

from core.mixins import StyledFormMixin

from .models import Comment, Post


class CommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["name", "email", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}
        labels = {"body": "Comment"}


class PostForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "category", "excerpt", "body", "image", "image_url", "is_published"]
        widgets = {"body": forms.Textarea(attrs={"rows": 12})}
        help_texts = {"body": "Separate paragraphs with a blank line."}
