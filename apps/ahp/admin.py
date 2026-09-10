from django.contrib import admin

from apps.ahp.models import RandomIndex


@admin.register(RandomIndex)
class RandomIndexAdmin(admin.ModelAdmin):
    list_display = ("matrix_size", "value", "is_active", "source", "updated_at")
    list_editable = ("value", "is_active")
    search_fields = ("matrix_size", "source")
    ordering = ("matrix_size",)
