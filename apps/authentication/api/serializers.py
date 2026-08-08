from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the User model.

    Exposes only non-sensitive, public-facing fields.
    Intentionally excludes: password, last_login_ip, is_staff, is_superuser,
    groups, user_permissions.
    """

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'is_email_verified',
            'date_joined',
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """
    Write-only serializer used exclusively for user registration.

    Security:
    - `password` is write-only (never returned in any response).
    - `validate_password()` is called to enforce the global AUTH_PASSWORD_VALIDATORS
      (minimum 12 chars, common password check, numeric-only check).
    - User creation is delegated to `User.objects.create_user()` which calls
      `full_clean()` and hashes the password — never stored in plain text.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Must be at least 12 characters and not a commonly used password.',
    )

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate_password(self, value: str) -> str:
        """
        Run Django's full password validator suite against the candidate password.
        Raises `ValidationError` with human-readable messages on failure.
        """
        validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Partial-update serializer for the authenticated user's own profile.

    Allows updating first_name and last_name only.
    Email changes are intentionally excluded to prevent account takeover
    without a dedicated verified-email-change flow.
    """

    class Meta:
        model = User
        fields = ('first_name', 'last_name')
