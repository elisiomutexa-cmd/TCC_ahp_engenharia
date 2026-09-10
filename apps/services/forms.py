from django import forms

from apps.accounts.forms import StyledFormMixin
from apps.services.models import EngineeringService


class EngineeringServiceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EngineeringService
        fields = (
            "name",
            "service_type",
            "description",
            "location",
            "priority",
            "requested_at",
            "deadline",
            "status",
        )
        widgets = {
            "requested_at": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
