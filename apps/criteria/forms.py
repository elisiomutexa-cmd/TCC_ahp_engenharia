from django import forms

from apps.accounts.forms import StyledFormMixin
from apps.criteria.models import Criterion


class CriterionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Criterion
        fields = (
            "code",
            "name",
            "description",
            "kind",
            "parent",
            "catalog_weight",
            "is_active",
            "sort_order",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Criterion.objects.filter(parent__isnull=True)
        self.fields["parent"].required = False
        self._style()
