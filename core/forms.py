from django import forms

from .mixins import StyledFormMixin
from .models import ContactMessage, NewsletterSubscriber, SiteSettings


class ContactForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]


class SiteSettingsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SiteSettings
        exclude = ["updated_at"]
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color"}),
            "secondary_color": forms.TextInput(attrs={"type": "color"}),
            "dark_color": forms.TextInput(attrs={"type": "color"}),
            "border_radius": forms.NumberInput(attrs={"min": 0, "max": 32}),
            "about_text": forms.Textarea(attrs={"rows": 4}),
            "cancellation_policy": forms.Textarea(attrs={"rows": 3}),
            "chatbot_instructions": forms.Textarea(attrs={"rows": 4}),
        }

    # Grouping used by the settings page to render tabs.
    SECTIONS = [
        ("branding", "Branding", "bi-palette", ["site_name", "tagline", "logo", "favicon"]),
        ("theme", "Theme", "bi-brush", ["primary_color", "secondary_color", "dark_color", "font_family", "border_radius"]),
        ("home", "Home page", "bi-house", ["hero_title", "hero_subtitle", "hero_image", "hero_image_url",
                                          "about_title", "about_text", "show_stats", "show_testimonials", "show_blog"]),
        ("contact", "Contact & social", "bi-telephone", ["email", "phone", "address", "whatsapp", "facebook_url",
                                                         "instagram_url", "twitter_url", "youtube_url", "footer_text"]),
        ("booking", "Booking", "bi-bag-check", ["currency_symbol", "booking_enabled", "cancellation_policy"]),
        ("chatbot", "Chatbot", "bi-robot", ["chatbot_enabled", "chatbot_name", "chatbot_welcome", "chatbot_instructions"]),
    ]

    def sections(self):
        for key, title, icon, names in self.SECTIONS:
            yield {"key": key, "title": title, "icon": icon, "fields": [self[name] for name in names]}

    def clean_border_radius(self):
        return min(max(self.cleaned_data["border_radius"], 0), 32)
