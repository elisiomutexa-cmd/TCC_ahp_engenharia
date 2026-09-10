from django import forms

from apps.evaluations.models import ProposalAttachment


class ProposalAttachmentForm(forms.ModelForm):
    class Meta:
        model = ProposalAttachment
        fields = ("evaluation_supplier", "file", "description")
        widgets = {
            "evaluation_supplier": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Proposta técnica e financeira"}),
        }
