from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from core.mixins import StyledFormMixin

from .models import Booking, Destination, Review, Tour


class BookingForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["full_name", "email", "phone", "travel_date", "travelers", "special_requests"]
        widgets = {
            "travel_date": forms.DateInput(attrs={"type": "date"}),
            "special_requests": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, tour=None, **kwargs):
        self.tour = tour
        super().__init__(*args, **kwargs)
        self.fields["travel_date"].widget.attrs["min"] = (timezone.localdate() + timezone.timedelta(days=1)).isoformat()
        if tour:
            self.fields["travelers"].widget.attrs["max"] = tour.max_group_size

    def clean_travel_date(self):
        date = self.cleaned_data["travel_date"]
        if date <= timezone.localdate():
            raise forms.ValidationError("Please choose a future date.")
        return date

    def clean(self):
        data = super().clean()
        date, travelers = data.get("travel_date"), data.get("travelers")
        if self.tour and date and travelers:
            left = self.tour.seats_left(date)
            if travelers > left:
                raise forms.ValidationError(
                    f"Only {left} seat(s) left on {date:%d %b %Y}. Please pick another date or fewer travelers."
                )
        return data


class ReviewForm(StyledFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(coerce=int, choices=[(i, f"{i} star{'s' if i > 1 else ''}") for i in range(5, 0, -1)])

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}


class TourFilterForm(forms.Form):
    SORTS = [
        ("", "Recommended"),
        ("price", "Price: low to high"),
        ("-price", "Price: high to low"),
        ("duration", "Shortest first"),
        ("-rating", "Top rated"),
        ("-created", "Newest"),
    ]
    q = forms.CharField(required=False)
    destination = forms.ModelChoiceField(Destination.objects.all(), required=False, to_field_name="slug", empty_label="All destinations")
    category = forms.ChoiceField(choices=[("", "All categories")] + Tour.Category.choices, required=False)
    duration = forms.ChoiceField(
        choices=[("", "Any length"), ("1-3", "1-3 days"), ("4-7", "4-7 days"), ("8-99", "8+ days")], required=False
    )
    max_price = forms.IntegerField(required=False, min_value=0)
    sort = forms.ChoiceField(choices=SORTS, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css
        self.fields["q"].widget.attrs["placeholder"] = "Where do you want to go?"
        self.fields["max_price"].widget.attrs["placeholder"] = "Max price"


class TourForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tour
        exclude = ["slug", "created_at", "updated_at"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "highlights": forms.Textarea(attrs={"rows": 4}),
            "itinerary": forms.Textarea(attrs={"rows": 5}),
            "included": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guide"].queryset = User.objects.filter(profile__role="guide").order_by("first_name")
        self.fields["guide"].label_from_instance = lambda u: u.get_full_name() or u.username

    def clean(self):
        data = super().clean()
        if data.get("sale_price") and data.get("price") and data["sale_price"] >= data["price"]:
            self.add_error("sale_price", "Sale price must be lower than the regular price.")
        return data


class DestinationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Destination
        exclude = ["slug"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class BookingAdminForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["full_name", "email", "phone", "travel_date", "travelers", "status", "payment_status", "special_requests"]
        widgets = {
            "travel_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "special_requests": forms.Textarea(attrs={"rows": 2}),
        }


class GuideBookingForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["status", "guide_notes"]
        widgets = {"guide_notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Guides can confirm, complete or leave pending - cancellations go through the office.
        self.fields["status"].choices = [c for c in Booking.Status.choices if c[0] != Booking.Status.CANCELLED]
