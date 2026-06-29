"""
Custom exceptions for the lottery system.
"""


class LotterySystemException(Exception):
    """Base exception for lottery system."""
    pass


class ValidationError(LotterySystemException):
    """Raised when validation fails."""
    pass


class PaymentError(LotterySystemException):
    """Raised when payment operations fail."""
    pass


class LotteryError(LotterySystemException):
    """Raised when lottery operations fail."""
    pass


class DrawError(LotterySystemException):
    """Raised when draw operations fail."""
    pass


class TicketPurchaseError(LotterySystemException):
    """Raised when ticket purchase fails."""
    pass


class ReferralError(LotterySystemException):
    """Raised when referral operations fail."""
    pass


class WithdrawalError(LotterySystemException):
    """Raised when withdrawal operations fail."""
    pass


class InsufficientBalanceError(PaymentError):
    """Raised when user has insufficient balance."""
    pass


class LotteryNotActiveError(LotteryError):
    """Raised when lottery is not active."""
    pass


class MaxTicketsExceededError(TicketPurchaseError):
    """Raised when user exceeds maximum tickets per lottery."""
    pass

