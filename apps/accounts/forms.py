from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django import forms

from apps.accounts.models import User


class StyledFormMixin:
    def _style(self):
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = f"{css} form-check-input".strip()
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"{css} form-select".strip()
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = f"{css} form-control".strip()
                field.widget.attrs.setdefault("rows", 3)
            else:
                field.widget.attrs["class"] = f"{css} form-control".strip()


class UserCreateForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "phone",
            "job_title",
            "organization",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def save(self, commit=True):
        user = super().save(commit=commit)
        group_name = (
            "Administradores" if user.role == User.Role.ADMIN else "Gestores"
        )
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        if user.role == User.Role.ADMIN:
            user.is_staff = True
            if commit:
                user.save(update_fields=["is_staff"])
        return user


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "phone",
            "job_title",
            "organization",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "job_title", "organization")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
