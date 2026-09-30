from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from accounts.models import Profile
from core.mixins import StyledFormMixin


class GuideCreateForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    languages = forms.CharField(max_length=200, required=False, help_text="Comma separated")
    years_experience = forms.IntegerField(min_value=0, initial=0)
    bio = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile = user.profile
        profile.role = Profile.Role.GUIDE
        for name in ["phone", "languages", "years_experience", "bio"]:
            setattr(profile, name, self.cleaned_data[name])
        profile.save()
        return user


class UserRoleForm(StyledFormMixin, forms.ModelForm):
    is_active = forms.BooleanField(required=False, label="Account active")

    class Meta:
        model = Profile
        fields = ["role", "phone", "languages", "years_experience", "is_available", "bio"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].initial = self.instance.user.is_active
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"

    def save(self, commit=True):
        profile = super().save(commit)
        user = profile.user
        user.is_active = self.cleaned_data["is_active"]
        user.is_staff = profile.role == Profile.Role.ADMIN or user.is_superuser
        user.save(update_fields=["is_active", "is_staff"])
        return profile
