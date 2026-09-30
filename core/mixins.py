"""Small reusable helpers shared by every app."""
from django import forms


class StyledFormMixin:
    """Adds Bootstrap classes to every widget so templates can render ``{{ field }}`` directly."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                css = ""
            else:
                css = "form-control"
            if isinstance(widget, forms.TextInput) and getattr(widget, "input_type", "") == "color":
                css = "form-control form-control-color"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css}".strip()
            if field.required and not isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("required", True)
