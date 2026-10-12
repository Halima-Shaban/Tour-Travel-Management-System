from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from core.mixins import StyledFormMixin

from .models import Profile


class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class SignUpForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if username and User.objects.filter(username__iexact=username, is_active=True).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        email = self.cleaned_data.get("email", "").strip().lower()
        username = self.cleaned_data.get("username", "").strip()

        # Remove any previous unverified accounts with the same email or username
        User.objects.filter(email__iexact=email, is_active=False).delete()
        User.objects.filter(username__iexact=username, is_active=False).delete()

        user = super().save(commit=False)
        user.email = email
        user.is_active = False  # Requires OTP email verification to activate
        if not user.first_name:
            user.first_name = user.username
        if commit:
            user.save()
        return user


class VerifyOTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter 6-digit code",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "class": "otp-code-input",
                "autofocus": "autofocus",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Please enter a valid 6-digit verification code.")
        return code


class ForgotPasswordForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email address",
                "autocomplete": "email",
                "autofocus": "autofocus",
            }
        )
    )


class ResetPasswordForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email address",
                "autocomplete": "email",
            }
        )
    )
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "placeholder": "6-digit code",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
            }
        ),
    )
    new_password = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "New password",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm new password",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Please enter a valid 6-digit verification code.")
        return code

    def clean(self):
        from django.contrib.auth.password_validation import validate_password

        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        email = cleaned_data.get("email")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                user = User.objects.filter(email__iexact=email).first() if email else None
                try:
                    validate_password(new_password, user=user)
                except forms.ValidationError as error:
                    self.add_error("new_password", error)
        return cleaned_data


class UserForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["phone", "avatar", "bio"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class GuideProfileForm(ProfileForm):
    class Meta(ProfileForm.Meta):
        fields = ["phone", "avatar", "bio", "languages", "years_experience", "is_available"]
