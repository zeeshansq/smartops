from rest_framework import serializers
from ai_services.models import AIRequestLog


class AIGenerateSerializer(serializers.Serializer):
    """
    Input validation serializer for initiating an AI generation job.
    """

    prompt = serializers.CharField(
        required=True,
        min_length=3,
        help_text="Text prompt to pass to the AI LLM service.",
    )

    def validate_prompt(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Prompt cannot consist solely of whitespace.")
        return value


class AIRequestLogSerializer(serializers.ModelSerializer):
    """
    Read-only serializer exposing AI request task status and output.
    """

    class Meta:
        model = AIRequestLog
        fields = (
            'id',
            'task_id',
            'prompt',
            'response',
            'status',
            'error_message',
            'tokens_used',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields
