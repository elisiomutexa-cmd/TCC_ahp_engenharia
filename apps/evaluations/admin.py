from django.contrib import admin

from apps.evaluations.models import ProposalAttachment


@admin.register(ProposalAttachment)
class ProposalAttachmentAdmin(admin.ModelAdmin):
    list_display = ("evaluation_supplier", "description", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "evaluation_supplier__snapshot_name",
        "description",
        "file",
    )
