from django import forms

from apps.accounts.forms import StyledFormMixin
from apps.suppliers.models import Supplier


class SupplierForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = (
            "name",
            "nuit",
            "email",
            "phone",
            "address",
            "city",
            "province",
            "contact_person",
            "specialties",
            "experience_years",
            "certifications",
            "status",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
