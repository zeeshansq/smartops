from django.contrib.auth import get_user_model
from rest_framework import serializers

from authentication.api.serializers import UserSerializer
from organizations.models import Organization, OrganizationMember

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Organization (workspace) model.

    - `id` and `slug` are read-only; slug is auto-generated from name on create.
    - `is_active` is read-only in API responses to prevent clients from
      self-suspending their workspace accidentally. Suspension is an admin action.
    """

    class Meta:
        model = Organization
        fields = ('id', 'name', 'slug', 'is_active', 'created_at')
        read_only_fields = ('id', 'slug', 'is_active', 'created_at')


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for an organization membership record.
    Nests a read-only UserSerializer for the member's identity.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = OrganizationMember
        fields = ('id', 'user', 'role', 'is_active', 'joined_at')
        read_only_fields = ('id', 'user', 'is_active', 'joined_at')


class AddMemberSerializer(serializers.Serializer):
    """
    Write-only serializer used when adding a member to a workspace.

    Accepts `email` and `role` rather than a user PK to avoid exposing
    internal IDs in the API contract.
    """

    email = serializers.EmailField(
        help_text='Email address of the user to add to this workspace.',
    )
    role = serializers.ChoiceField(
        choices=OrganizationMember.ROLE_CHOICES,
        default=OrganizationMember.ROLE_MEMBER,
        help_text='Role to assign to the new member.',
    )

    def validate_email(self, value: str) -> str:
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'No user with this email address exists.'
            )
        self._resolved_user = user
        return value

    def validate(self, attrs: dict) -> dict:
        """Cross-field validation: prevent adding a user who is already a member."""
        organization = self.context.get('organization')
        if organization and hasattr(self, '_resolved_user'):
            if OrganizationMember.objects.filter(
                organization=organization,
                user=self._resolved_user,
            ).exists():
                raise serializers.ValidationError(
                    {'email': 'This user is already a member of this workspace.'}
                )
        return attrs
