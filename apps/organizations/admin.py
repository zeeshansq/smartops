from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Organization, OrganizationMember


class OrganizationMemberInline(TabularInline):
    """
    Inline editor for memberships inside the OrganizationAdmin.
    Exposes the is_active toggle so admins can suspend individual members
    without deleting the membership record.
    """
    model = OrganizationMember
    extra = 0                                    # Don't show empty rows by default
    fields = ('user', 'role', 'is_active', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    """
    Unfold admin for the Organization (tenant) model.
    """
    list_display = ('name', 'slug', 'is_active', 'created_at', 'member_count')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationMemberInline]

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'slug', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj.members.filter(is_active=True).count()


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(ModelAdmin):
    """
    Unfold admin for individual organization memberships.
    """
    list_display = ('user_email', 'organization_name', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__email', 'organization__name')
    readonly_fields = ('id', 'joined_at')

    fieldsets = (
        (None, {
            'fields': ('id', 'organization', 'user', 'role'),
        }),
        ('Access Control', {
            'fields': ('is_active',),
            'description': (
                'Deactivating a membership suspends workspace access without '
                'deleting the record — preserving audit history.'
            ),
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='User Email', ordering='user__email')
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description='Organization', ordering='organization__name')
    def organization_name(self, obj):
        return obj.organization.name
