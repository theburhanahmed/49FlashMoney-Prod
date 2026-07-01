"""
Provider adapter exceptions for 49FlashMoney.

All provider-specific errors are mapped to these base exception types
so callers can handle them uniformly regardless of provider.
"""


class ProviderError(Exception):
    """Base exception for all provider adapter errors."""
    def __init__(self, message: str, provider: str = '', code: str = ''):
        self.provider = provider
        self.code = code
        super().__init__(message)


class ProviderAuthError(ProviderError):
    """Authentication/authorisation failure with the upstream provider."""


class ProviderGameNotFoundError(ProviderError):
    """Requested game does not exist in the provider's catalogue."""


class ProviderSessionError(ProviderError):
    """Failed to create or validate a game session."""


class ProviderBetError(ProviderError):
    """Bet was rejected by the provider (invalid amount, game state, etc.)."""


class ProviderSettlementError(ProviderError):
    """Round could not be settled (already settled, cancelled round, etc.)."""


class ProviderRefundError(ProviderError):
    """Refund was rejected by the provider."""


class ProviderMaintenanceError(ProviderError):
    """Provider or game is temporarily unavailable for maintenance."""


class ProviderBalanceMismatchError(ProviderError):
    """Provider's reported balance does not match the platform ledger."""


class ProviderUnsupportedError(ProviderError):
    """Operation is not supported by this provider."""
