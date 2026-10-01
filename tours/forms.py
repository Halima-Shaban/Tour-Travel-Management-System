from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from core.mixins import StyledFormMixin

from .models import Booking, Destination, GuideUnavailability, Participant, Review, Tour


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
        if self.tour and date and self.tour.guide_id:
            end = date + timezone.timedelta(days=self.tour.duration_days - 1)
            if GuideUnavailability.overlapping(self.tour.guide, date, end).exists():
                raise forms.ValidationError("Our guide isn't available on these dates. Please choose another date.")
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


class GuideNotesForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["guide_notes"]
        widgets = {"guide_notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Pickup time, meeting point, reminders..."})}
        labels = {"guide_notes": "Private notes (visible to the office)"}
        help_texts = {"guide_notes": ""}


class DeclineForm(forms.Form):
    reason = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Reason (optional) - e.g. already booked that week"}),
    )


class ParticipantForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Participant
        fields = ["full_name", "age", "nationality", "notes"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "age": forms.NumberInput(attrs={"placeholder": "Age", "min": 0, "max": 120}),
            "nationality": forms.TextInput(attrs={"placeholder": "Nationality"}),
            "notes": forms.TextInput(attrs={"placeholder": "Diet, allergies, mobility..."}),
        }


ParticipantFormSet = forms.inlineformset_factory(
    Booking, Participant, form=ParticipantForm, extra=0, can_delete=True, validate_max=True
)


class UnavailabilityForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = GuideUnavailability
        fields = ["start_date", "end_date", "reason"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        data = super().clean()
        start, end = data.get("start_date"), data.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date must be on or after the start date.")
        if start and start < timezone.localdate():
            self.add_error("start_date", "Choose today or a future date.")
        return data


class AssignGuideForm(forms.Form):
    guide = forms.ModelChoiceField(User.objects.none(), required=True, widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guide"].queryset = User.objects.filter(profile__role="guide", is_active=True).order_by("first_name")
        self.fields["guide"].label_from_instance = lambda u: (u.get_full_name() or u.username) + ("" if u.profile.is_available else " (unavailable)")
