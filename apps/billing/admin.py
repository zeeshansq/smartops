from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(ModelAdmin):
    """
    Admin for API keys.

    Security: `hashed_key` is NEVER displayed or editable in the admin.
    The raw key is shown only once at creation time via the API — never here.
    """

    list_display = ('name', 'prefix', 'organization', 'is_active', 'created_at', 'last_used_at')
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'prefix', 'organization__name')
    readonly_fields = ('id', 'prefix', 'hashed_key', 'created_at', 'last_used_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'organization', 'is_active'),
        }),
        ('Key Identification', {
            'fields': ('prefix',),
            'description': (
                'Only the key prefix is shown here. '
                'The full raw key is never stored and was displayed only once at creation.'
            ),
        }),
        ('Audit', {
            'fields': ('created_at', 'last_used_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request) -> bool:
        """
        Disable adding API keys via the admin UI.
        Keys must be created via the API (POST /api/v1/billing/keys/) to ensure
        the raw key is presented to the user exactly once.
        """
        return False
