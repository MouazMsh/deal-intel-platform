"""Application exception hierarchy.

Guardrail exceptions (``MockProviderInProductionError``,
``NoonProviderBlockedError``, ``PublishGuardrailError``) are intentionally
their own subclasses rather than generic ``RuntimeError`` / ``ValueError`` —
this lets tests assert on the *specific* guardrail that fired, and lets a
future alerting layer treat guardrail trips as a distinct, high-priority
signal rather than an ordinary bug.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-raised errors."""


class ProviderError(AppError):
    """Base class for provider-layer errors."""


class ProviderNotConfiguredError(ProviderError):
    """A real provider was requested without the credentials it needs."""


class MockProviderInProductionError(ProviderError):
    """Guardrail: a mock provider was about to be used with ENVIRONMENT=production."""


class NoonProviderBlockedError(ProviderError):
    """Guardrail: NoonProvider was instantiated. No compliant data source exists yet."""


class PublishGuardrailError(AppError):
    """Guardrail: a Telegram publish attempt failed a safety check."""
