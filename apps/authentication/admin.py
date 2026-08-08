from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import User


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class UserCreationForm(forms.ModelForm):
    """
    Secure user creation form for the admin.
    Presents two password fields that must match; stores the hashed result.
    """
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as above, for verification."),
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_email_verified')

    def clean_password2(self) -> str:
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("The two password fields didn't match."))
        return password2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """
    Secure user change form for the admin.
    Replaces the raw password field with a read-only hash display widget,
    preventing accidental hash exposure or direct hash editing.
    """
    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored. You cannot see this user's password, "
            "but you can change it using <a href='../password/'>this form</a>."
        ),
    )

    class Meta:
        model = User
        fields = (
            'email', 'password', 'first_name', 'last_name',
            'is_active', 'is_email_verified', 'is_staff', 'is_superuser',
            'last_login_ip',
        )


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@admin.register(User)
class UserAdmin(ModelAdmin):
    """
    Unfold-styled admin for the custom User model.
    Enforces secure password handling via custom forms.
    """
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        'email', 'first_name', 'last_name',
        'is_active', 'is_email_verified', 'is_staff', 'date_joined',
    )
    list_filter = ('is_staff', 'is_active', 'is_email_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('id', 'date_joined', 'last_login', 'last_login_ip')

    # Fields shown when editing an existing user
    fieldsets = (
        (None, {
            'fields': ('id', 'email', 'password'),
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name'),
        }),
        (_('Account Status'), {
            'fields': ('is_active', 'is_email_verified'),
            'description': _(
                'Deactivating a user prevents login without deleting their data. '
                'Email verification is required for sensitive workflows.'
            ),
        }),
        (_('Permissions'), {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Audit Trail'), {
            'fields': ('date_joined', 'last_login', 'last_login_ip'),
            'classes': ('collapse',),
        }),
    )

    # Fields shown when creating a new user
    add_fieldsets = (
        (None, {
            'fields': ('email', 'password1', 'password2'),
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name'),
        }),
        (_('Account Status'), {
            'fields': ('is_active', 'is_email_verified', 'is_staff'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Use the creation form when adding a new user, change form otherwise."""
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)
