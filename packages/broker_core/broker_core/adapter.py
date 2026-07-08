from __future__ import annotations

from abc import ABC, abstractmethod

from broker_core.models import (
    BrokerProfile,
    BrokerSession,
    Funds,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderResponseDTO,
    OrderStatusDTO,
    PositionDTO,
    TickDTO,
)


class BrokerAdapter(ABC):
    @abstractmethod
    def login_url(self) -> str:
        """Return the broker login URL used to start an auth session."""

    @abstractmethod
    def exchange_token(self, request_token: str) -> BrokerSession:
        """Exchange a broker request token or auth code for a session."""

    @abstractmethod
    def get_profile(self) -> BrokerProfile:
        """Fetch the normalized broker profile."""

    @abstractmethod
    def get_funds(self) -> Funds:
        """Fetch the normalized funds or margin snapshot."""

    @abstractmethod
    def get_positions(self) -> list[PositionDTO]:
        """Fetch the normalized positions list."""

    @abstractmethod
    def get_orders(self) -> list[OrderStatusDTO]:
        """Fetch the normalized order book."""

    @abstractmethod
    def place_order(self, order: OrderRequestDTO) -> OrderResponseDTO:
        """Place exactly one order. Callers must not auto-retry blindly."""

    @abstractmethod
    def modify_order(self, order_id: str, changes: OrderModifyRequestDTO) -> OrderResponseDTO:
        """Modify exactly one order with explicit user or system intent."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        """Cancel exactly one broker order."""

    @abstractmethod
    def subscribe_market_data(self, instruments: list[str]) -> list[TickDTO]:
        """Subscribe to broker market data for the requested instruments."""
