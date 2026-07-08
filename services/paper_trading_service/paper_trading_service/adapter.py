from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from broker_core import (
    BrokerAdapter,
    BrokerName,
    BrokerOrderRejectedError,
    BrokerProfile,
    BrokerSession,
    Exchange,
    Funds,
    NormalizedOrderStatus,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderResponseDTO,
    OrderStatusDTO,
    OrderType,
    PositionDTO,
    ProductType,
    Segment,
    TickDTO,
    TransactionType,
)


@dataclass(frozen=True)
class PaperMarketQuote:
    symbol: str
    ltp: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    exchange: Exchange = Exchange.NSE
    segment: Segment = Segment.EQ
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OrderEvent:
    order_id: str
    event_type: str
    old_status: NormalizedOrderStatus | None
    new_status: NormalizedOrderStatus
    message: str
    raw_payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PaperOrder:
    broker_order_id: str
    request: OrderRequestDTO
    status: NormalizedOrderStatus
    filled_quantity: int = 0
    average_price: Decimal | None = None
    message: str | None = None
    events: list[OrderEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def pending_quantity(self) -> int:
        return self.request.quantity - self.filled_quantity


@dataclass
class PaperPosition:
    broker_name: BrokerName
    exchange: Exchange
    segment: Segment
    symbol: str
    product_type: ProductType
    quantity: int = 0
    average_price: Decimal = Decimal("0")
    last_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")

    @property
    def unrealized_pnl(self) -> Decimal:
        return (self.last_price - self.average_price) * Decimal(self.quantity)


class PaperTradingBrokerAdapter(BrokerAdapter):
    def __init__(
        self,
        *,
        slippage_bps: Decimal = Decimal("5"),
        brokerage_rate: Decimal = Decimal("0.0003"),
    ) -> None:
        self.slippage_bps = slippage_bps
        self.brokerage_rate = brokerage_rate
        self._orders: dict[str, PaperOrder] = {}
        self._positions: dict[tuple[str, ProductType], PaperPosition] = {}
        self._quotes: dict[str, PaperMarketQuote] = {}

    def login_url(self) -> str:
        return "paper://login"

    def exchange_token(self, request_token: str) -> BrokerSession:
        return BrokerSession(
            broker_name=BrokerName.PAPER,
            access_token=f"paper_session_{request_token}",
        )

    def get_profile(self) -> BrokerProfile:
        return BrokerProfile(
            broker_name=BrokerName.PAPER,
            broker_user_id="paper-user",
            full_name="Paper Trading User",
            email=None,
        )

    def get_funds(self) -> Funds:
        return Funds(
            broker_name=BrokerName.PAPER,
            available_cash=Decimal("1000000"),
            collateral=Decimal("0"),
            utilized_margin=Decimal("0"),
            net=Decimal("1000000"),
        )

    def get_positions(self) -> list[PositionDTO]:
        return [
            PositionDTO(
                broker_name=position.broker_name,
                exchange=position.exchange,
                segment=position.segment,
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                last_price=position.last_price,
                product_type=position.product_type,
                realized_pnl=position.realized_pnl,
                unrealized_pnl=position.unrealized_pnl,
            )
            for position in self._positions.values()
            if position.quantity != 0 or position.realized_pnl != Decimal("0")
        ]

    def get_orders(self) -> list[OrderStatusDTO]:
        return [self._to_status(order) for order in self._orders.values()]

    def place_order(self, order: OrderRequestDTO) -> OrderResponseDTO:
        broker_order_id = f"paper_{uuid4().hex}"
        initial_status = (
            NormalizedOrderStatus.TRIGGER_PENDING
            if order.order_type == OrderType.SL_LIMIT
            else NormalizedOrderStatus.OPEN
        )
        paper_order = PaperOrder(
            broker_order_id=broker_order_id,
            request=order,
            status=NormalizedOrderStatus.CREATED,
        )
        self._orders[broker_order_id] = paper_order
        self._set_status(paper_order, initial_status, f"Paper order {initial_status.value.lower()}")
        self._try_process_order(paper_order)
        return self._to_response(paper_order)

    def modify_order(self, order_id: str, changes: OrderModifyRequestDTO) -> OrderResponseDTO:
        order = self._get_order(order_id)
        if order.status == NormalizedOrderStatus.FILLED:
            raise BrokerOrderRejectedError("Filled paper order cannot be modified")
        if order.status == NormalizedOrderStatus.CANCELLED:
            raise BrokerOrderRejectedError("Cancelled paper order cannot be modified")

        update_data = {
            key: value
            for key, value in {
                "quantity": changes.quantity,
                "price": changes.price,
                "trigger_price": changes.trigger_price,
            }.items()
            if value is not None
        }
        order.request = OrderRequestDTO(**{**order.request.model_dump(), **update_data})
        order.updated_at = datetime.now(timezone.utc)
        self._add_event(
            order,
            "ORDER_MODIFIED",
            order.status,
            order.status,
            "Paper order modified",
            {"changes": update_data},
        )
        self._try_process_order(order)
        return self._to_response(order)

    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        order = self._get_order(order_id)
        if order.status == NormalizedOrderStatus.FILLED:
            raise BrokerOrderRejectedError("Filled paper order cannot be cancelled")
        if order.status != NormalizedOrderStatus.CANCELLED:
            self._set_status(order, NormalizedOrderStatus.CANCELLED, "Paper order cancelled")
        return self._to_response(order)

    def subscribe_market_data(self, instruments: list[str]) -> list[TickDTO]:
        ticks: list[TickDTO] = []
        for symbol in instruments:
            quote = self._quotes.get(symbol)
            if quote is None:
                continue
            ticks.append(self._quote_to_tick(quote))
        return ticks

    def update_market_data(
        self,
        symbol: str,
        *,
        ltp: Decimal,
        bid_price: Decimal | None = None,
        ask_price: Decimal | None = None,
        exchange: Exchange = Exchange.NSE,
        segment: Segment = Segment.EQ,
    ) -> list[OrderEvent]:
        quote = PaperMarketQuote(
            symbol=symbol,
            ltp=ltp,
            bid_price=bid_price,
            ask_price=ask_price,
            exchange=exchange,
            segment=segment,
        )
        self._quotes[symbol] = quote

        before = self.get_order_events()
        for order in self._orders.values():
            if order.request.symbol == symbol:
                self._try_process_order(order)
        after = self.get_order_events()
        return after[len(before) :]

    def get_order_events(self, order_id: str | None = None) -> list[OrderEvent]:
        if order_id is not None:
            return list(self._get_order(order_id).events)
        events: list[OrderEvent] = []
        for order in self._orders.values():
            events.extend(order.events)
        return events

    def _try_process_order(self, order: PaperOrder) -> None:
        if order.status in {NormalizedOrderStatus.CANCELLED, NormalizedOrderStatus.FILLED}:
            return

        if order.request.order_type == OrderType.SL_LIMIT and order.status == NormalizedOrderStatus.TRIGGER_PENDING:
            if not self._trigger_touched(order):
                return
            self._set_status(order, NormalizedOrderStatus.OPEN, "SL_LIMIT trigger touched")

        if order.status != NormalizedOrderStatus.OPEN:
            return

        fill_price = self._limit_fill_price(order)
        if fill_price is None:
            return

        self._fill(order, fill_price)

    def _trigger_touched(self, order: PaperOrder) -> bool:
        quote = self._quotes.get(order.request.symbol)
        if quote is None or order.request.trigger_price is None:
            return False

        if order.request.transaction_type == TransactionType.BUY:
            observed_price = quote.ask_price or quote.ltp
            return observed_price >= order.request.trigger_price

        observed_price = quote.bid_price or quote.ltp
        return observed_price <= order.request.trigger_price

    def _limit_fill_price(self, order: PaperOrder) -> Decimal | None:
        quote = self._quotes.get(order.request.symbol)
        if quote is None or order.request.price is None:
            return None

        if order.request.transaction_type == TransactionType.BUY:
            ask = quote.ask_price or self._apply_slippage(quote.ltp, TransactionType.BUY)
            if ask <= order.request.price:
                return ask
            return None

        bid = quote.bid_price or self._apply_slippage(quote.ltp, TransactionType.SELL)
        if bid >= order.request.price:
            return bid
        return None

    def _fill(self, order: PaperOrder, fill_price: Decimal) -> None:
        if order.status == NormalizedOrderStatus.CANCELLED:
            return

        brokerage = self._brokerage_estimate(fill_price, order.request.quantity)
        order.filled_quantity = order.request.quantity
        order.average_price = fill_price
        order.message = "Paper order filled"
        self._apply_position_fill(order.request, fill_price)
        self._set_status(
            order,
            NormalizedOrderStatus.FILLED,
            "Paper order filled",
            {"fill_price": fill_price, "brokerage_estimate": brokerage},
        )

    def _apply_position_fill(self, request: OrderRequestDTO, fill_price: Decimal) -> None:
        key = (request.symbol, request.product_type)
        position = self._positions.get(key)
        if position is None:
            position = PaperPosition(
                broker_name=BrokerName.PAPER,
                exchange=request.exchange,
                segment=request.segment,
                symbol=request.symbol,
                product_type=request.product_type,
                last_price=fill_price,
            )
            self._positions[key] = position

        signed_quantity = request.quantity if request.transaction_type == TransactionType.BUY else -request.quantity
        previous_quantity = position.quantity
        position.last_price = fill_price

        if previous_quantity == 0 or (previous_quantity > 0 and signed_quantity > 0) or (previous_quantity < 0 and signed_quantity < 0):
            new_quantity = previous_quantity + signed_quantity
            total_cost = (position.average_price * Decimal(abs(previous_quantity))) + (
                fill_price * Decimal(abs(signed_quantity))
            )
            position.quantity = new_quantity
            position.average_price = total_cost / Decimal(abs(new_quantity))
            return

        closing_quantity = min(abs(previous_quantity), abs(signed_quantity))
        if previous_quantity > 0:
            position.realized_pnl += (fill_price - position.average_price) * Decimal(closing_quantity)
        else:
            position.realized_pnl += (position.average_price - fill_price) * Decimal(closing_quantity)

        new_quantity = previous_quantity + signed_quantity
        position.quantity = new_quantity
        if new_quantity == 0:
            position.average_price = Decimal("0")
        elif (previous_quantity > 0 and new_quantity > 0) or (previous_quantity < 0 and new_quantity < 0):
            pass
        else:
            position.average_price = fill_price

    def _set_status(
        self,
        order: PaperOrder,
        new_status: NormalizedOrderStatus,
        message: str,
        raw_payload: dict | None = None,
    ) -> None:
        old_status = order.status
        order.status = new_status
        order.message = message
        order.updated_at = datetime.now(timezone.utc)
        self._add_event(order, "ORDER_STATUS_CHANGED", old_status, new_status, message, raw_payload or {})

    def _add_event(
        self,
        order: PaperOrder,
        event_type: str,
        old_status: NormalizedOrderStatus | None,
        new_status: NormalizedOrderStatus,
        message: str,
        raw_payload: dict,
    ) -> None:
        order.events.append(
            OrderEvent(
                order_id=order.broker_order_id,
                event_type=event_type,
                old_status=old_status,
                new_status=new_status,
                message=message,
                raw_payload={key: str(value) for key, value in raw_payload.items()},
            )
        )

    def _apply_slippage(self, ltp: Decimal, side: TransactionType) -> Decimal:
        slippage = ltp * self.slippage_bps / Decimal("10000")
        if side == TransactionType.BUY:
            return ltp + slippage
        return ltp - slippage

    def _brokerage_estimate(self, fill_price: Decimal, quantity: int) -> Decimal:
        return fill_price * Decimal(quantity) * self.brokerage_rate

    def _get_order(self, order_id: str) -> PaperOrder:
        order = self._orders.get(order_id)
        if order is None:
            raise BrokerOrderRejectedError("Paper order not found")
        return order

    def _to_response(self, order: PaperOrder) -> OrderResponseDTO:
        return OrderResponseDTO(
            broker_order_id=order.broker_order_id,
            status=order.status.value,
            normalized_status=order.status,
            message=order.message,
            correlation_id=order.request.correlation_id,
            raw_payload={
                "adapter": "paper",
                "filled_quantity": order.filled_quantity,
                "pending_quantity": order.pending_quantity,
            },
        )

    def _to_status(self, order: PaperOrder) -> OrderStatusDTO:
        return OrderStatusDTO(
            broker_order_id=order.broker_order_id,
            broker_status=order.status.value,
            normalized_status=order.status,
            filled_quantity=order.filled_quantity,
            pending_quantity=order.pending_quantity,
            average_price=order.average_price,
            message=order.message,
            updated_at=order.updated_at,
        )

    def _quote_to_tick(self, quote: PaperMarketQuote) -> TickDTO:
        return TickDTO(
            exchange=quote.exchange,
            segment=quote.segment,
            symbol=quote.symbol,
            last_price=quote.ltp,
            bid_price=quote.bid_price,
            ask_price=quote.ask_price,
            last_trade_time=quote.timestamp,
        )
