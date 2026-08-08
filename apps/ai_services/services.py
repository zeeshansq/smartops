import os
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM Service failures."""
    pass


class LLMServiceTimeoutError(LLMServiceError):
    """Raised when an LLM request times out."""
    pass


class LLMServiceAuthenticationError(LLMServiceError):
    """Raised when LLM API credentials are invalid or rejected."""
    pass


class LLMService:
    """
    Service wrapper for interacting with Large Language Model APIs (e.g., OpenAI or Anthropic Claude).

    Design & Security Principles:
    - Encapsulates third-party API interactions.
    - Reads API keys securely from environment variables.
    - Gracefully falls back to an offline mock generator when API keys are absent,
      enabling deterministic local dev, testing, and CI/CD without paid credentials.
    - Sanitizes error messages to ensure sensitive API keys and headers are never leaked.
    """

    def __init__(self, model_name: str = 'gpt-4o-mini', timeout: int = 30):
        self.model_name = model_name
        self.timeout = timeout
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')

    def generate(self, prompt: str) -> Dict[str, Any]:
        """
        Generate a structured AI completion response for the given prompt.

        Args:
            prompt: The text input prompt.

        Returns:
            Dict containing:
                - content: The completion text output or structured data.
                - model: The model identifier used.
                - tokens_used: Estimated/actual token consumption.
                - metadata: Additional output attributes.

        Raises:
            LLMServiceError: On service, network, or provider failure.
        """
        if not prompt or not prompt.strip():
            raise LLMServiceError("Prompt cannot be empty.")

        # If live API credentials are configured, execute live request handler
        if self.openai_api_key or self.anthropic_api_key:
            return self._call_live_provider(prompt)

        # Fallback to mock generator for offline dev/testing
        return self._generate_mock_response(prompt)

    def _call_live_provider(self, prompt: str) -> Dict[str, Any]:
        """
        Executes live API request with error handling and timeout protection.
        """
        try:
            # Check if openai package is installed and key is present
            if self.openai_api_key:
                try:
                    import openai
                    client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                    response = client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    choice = response.choices[0]
                    usage = getattr(response, 'usage', None)
                    total_tokens = usage.total_tokens if usage else 150

                    return {
                        "content": choice.message.content,
                        "model": self.model_name,
                        "tokens_used": total_tokens,
                        "metadata": {
                            "finish_reason": choice.finish_reason,
                            "provider": "openai",
                        },
                    }
                except ImportError:
                    logger.warning("openai package not installed; falling back to mock provider.")
                    return self._generate_mock_response(prompt)
                except Exception as exc:
                    logger.error("OpenAI API call failed: %s", str(exc))
                    err_msg = str(exc)
                    # Mask any accidentally echoed keys in error message
                    if self.openai_api_key in err_msg:
                        err_msg = err_msg.replace(self.openai_api_key, '[REDACTED_API_KEY]')
                    raise LLMServiceError(f"OpenAI service error: {err_msg}") from exc

            # Anthropic fallback
            if self.anthropic_api_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=self.anthropic_api_key, timeout=self.timeout)
                    response = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    content = response.content[0].text if response.content else ""
                    input_tokens = response.usage.input_tokens if hasattr(response, 'usage') else 50
                    output_tokens = response.usage.output_tokens if hasattr(response, 'usage') else 100

                    return {
                        "content": content,
                        "model": "claude-3-haiku-20240307",
                        "tokens_used": input_tokens + output_tokens,
                        "metadata": {
                            "provider": "anthropic",
                        },
                    }
                except ImportError:
                    logger.warning("anthropic package not installed; falling back to mock provider.")
                    return self._generate_mock_response(prompt)
                except Exception as exc:
                    logger.error("Anthropic API call failed: %s", str(exc))
                    err_msg = str(exc)
                    if self.anthropic_api_key in err_msg:
                        err_msg = err_msg.replace(self.anthropic_api_key, '[REDACTED_API_KEY]')
                    raise LLMServiceError(f"Anthropic service error: {err_msg}") from exc

        except Exception as exc:
            if not isinstance(exc, LLMServiceError):
                raise LLMServiceError(f"Provider request failed: {str(exc)}") from exc
            raise

        return self._generate_mock_response(prompt)

    def _generate_mock_response(self, prompt: str) -> Dict[str, Any]:
        """
        Simulates structured LLM execution for offline development and testing.
        """
        # Calculate deterministic mock token count based on prompt length
        prompt_words = len(prompt.split())
        estimated_tokens = prompt_words * 2 + 120

        content = (
            f"[SmartOps AI Engine Mock Response]\n\n"
            f"Successfully processed prompt: \"{prompt[:100]}{'...' if len(prompt) > 100 else ''}\"\n\n"
            f"Summary: Automated analytical analysis generated cleanly for your workflow."
        )

        return {
            "content": content,
            "model": f"{self.model_name}-mock",
            "tokens_used": estimated_tokens,
            "metadata": {
                "provider": "mock_provider",
                "mock_execution": True,
            },
        }
