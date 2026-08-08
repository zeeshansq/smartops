from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AIRequestLog


@admin.register(AIRequestLog)
class AIRequestLogAdmin(ModelAdmin):
    """
    Unfold admin for AI Request Logs.
    Read-only view for audit history and tracking background task status.
    """

    list_display = ('task_id', 'organization', 'user', 'status', 'tokens_used', 'created_at')
    list_filter = ('status', 'organization', 'created_at')
    search_fields = ('task_id', 'prompt', 'organization__name', 'user__email')
    readonly_fields = (
        'id',
        'organization',
        'user',
        'task_id',
        'prompt',
        'response',
        'status',
        'error_message',
        'tokens_used',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('id', 'task_id', 'organization', 'user', 'status'),
        }),
        ('Payload & Metrics', {
            'fields': ('prompt', 'response', 'tokens_used'),
        }),
        ('Errors & Audit', {
            'fields': ('error_message', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request) -> bool:
        """AI Request Logs are system-generated and cannot be added manually."""
        return False
