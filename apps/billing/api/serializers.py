from rest_framework import serializers
from billing.models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing API keys.

    Security:
    - `hashed_key` is NEVER included in any response field.
    - Only `prefix` is shown for key identification purposes.
    - `raw_key` is intentionally absent — it exists only in `APIKeyCreateResponseSerializer`.
    """

    class Meta:
        model = APIKey
        fields = ('id', 'name', 'prefix', 'is_active', 'created_at', 'last_used_at')
        read_only_fields = fields


class APIKeyCreateSerializer(serializers.Serializer):
    """
    Write-only serializer for API key creation.

    Accepts only `name` from the client. All key material is generated
    server-side by `APIKeyManager.create_key()`.
    """

    name = serializers.CharField(
        max_length=100,
        help_text="Human-readable label for this key, e.g. 'Production AI Integration'.",
    )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Key name cannot be blank.')
        return value


class APIKeyCreateResponseSerializer(serializers.ModelSerializer):
    """
    One-time response serializer returned immediately after key creation.

    Includes `raw_key` — this is the ONLY time the full key value is presented.
    Any subsequent GET requests will use `APIKeySerializer` which excludes it.
    """

    raw_key = serializers.CharField(
        read_only=True,
        help_text=(
            'The full API key value. Store this securely — it will never be shown again.'
        ),
    )

    class Meta:
        model = APIKey
        fields = ('id', 'name', 'prefix', 'is_active', 'created_at', 'raw_key')
        read_only_fields = fields
