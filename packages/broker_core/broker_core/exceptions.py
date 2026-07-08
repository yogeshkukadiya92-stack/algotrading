class BrokerError(Exception):
    """Base exception for normalized broker adapter errors."""


class BrokerAuthError(BrokerError):
    """Raised when authentication or token exchange fails."""


class BrokerRateLimitError(BrokerError):
    """Raised when a broker rejects a request due to rate limiting."""


class BrokerOrderRejectedError(BrokerError):
    """Raised when the broker explicitly rejects an order."""


class BrokerNetworkError(BrokerError):
    """Raised when a network or transport problem prevents broker access."""


class BrokerNotImplementedError(BrokerError):
    """Raised by adapters that intentionally leave a capability unimplemented."""
