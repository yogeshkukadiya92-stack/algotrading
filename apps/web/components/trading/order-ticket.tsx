"use client";

import { FormEvent, useEffect, useState } from "react";
import { AlertTriangle, Lock, Send } from "lucide-react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  createOrder,
  getDefaultPaperBrokerAccountId,
  orderRiskMessage,
  type Exchange,
  type OrderSide,
  type OrderType,
  type ProductType,
  type Segment,
  type TradingOrder
} from "@/lib/trading-api";

export type OrderTicketDraft = {
  symbol: string;
  exchange: Exchange;
  segment: Segment;
  side: OrderSide;
  price?: string;
};

export function OrderTicket({
  draft,
  onSubmitted
}: {
  draft?: OrderTicketDraft | null;
  onSubmitted?: (order: TradingOrder) => void;
}) {
  const [symbol, setSymbol] = useState("NIFTY");
  const [exchange, setExchange] = useState<Exchange>("NSE");
  const [segment, setSegment] = useState<Segment>("EQ");
  const [side, setSide] = useState<OrderSide>("BUY");
  const [quantity, setQuantity] = useState("1");
  const [orderType, setOrderType] = useState<OrderType>("LIMIT");
  const [price, setPrice] = useState("");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [productType, setProductType] = useState<ProductType>("MIS");
  const [mode, setMode] = useState<"paper" | "live">("paper");
  const [liveConfirmOpen, setLiveConfirmOpen] = useState(false);
  const [liveConfirmationText, setLiveConfirmationText] = useState("");
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const liveModeVisible = process.env.NEXT_PUBLIC_ENABLE_MANUAL_LIVE_TRADING === "true";

  useEffect(() => {
    if (!draft) {
      return;
    }
    setSymbol(draft.symbol);
    setExchange(draft.exchange);
    setSegment(draft.segment);
    setSide(draft.side);
    if (draft.price) {
      setPrice(draft.price);
    }
  }, [draft]);

  function validateDraft() {
    setMessage(null);

    const numericQuantity = Number(quantity);
    const trimmedPrice = price.trim();
    const trimmedTriggerPrice = triggerPrice.trim();

    if (!symbol.trim()) {
      setMessage({ tone: "error", text: "Symbol is required." });
      return null;
    }
    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0) {
      setMessage({ tone: "error", text: "Quantity must be greater than zero." });
      return null;
    }
    if (!trimmedPrice) {
      setMessage({ tone: "error", text: "Price is required for LIMIT and SL_LIMIT orders." });
      return null;
    }
    if (orderType === "SL_LIMIT" && !trimmedTriggerPrice) {
      setMessage({ tone: "error", text: "Trigger price is required for SL_LIMIT orders." });
      return null;
    }
    return { numericQuantity, trimmedPrice, trimmedTriggerPrice };
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validated = validateDraft();
    if (!validated) {
      return;
    }
    if (mode === "live") {
      setLiveConfirmOpen(true);
      return;
    }
    await submitValidatedOrder(null, validated.numericQuantity, validated.trimmedPrice, validated.trimmedTriggerPrice);
  }

  async function submitValidatedOrder(
    confirmationText: string | null,
    numericQuantity = Number(quantity),
    trimmedPrice = price.trim(),
    trimmedTriggerPrice = triggerPrice.trim(),
  ) {
    setIsSubmitting(true);
    try {
      const response = await createOrder({
        broker_account_id: getDefaultPaperBrokerAccountId(),
        symbol: symbol.trim().toUpperCase(),
        exchange,
        segment,
        transaction_type: side,
        product_type: productType,
        order_type: orderType,
        quantity: numericQuantity,
        price: trimmedPrice,
        trigger_price: orderType === "SL_LIMIT" ? trimmedTriggerPrice : null,
        source: "manual",
        mode,
        lot_size: 1,
        confirmation_text: confirmationText
      });
      const riskMessage = orderRiskMessage(response.order);
      if (riskMessage) {
        setMessage({ tone: "error", text: riskMessage });
      } else {
        setMessage({ tone: "success", text: `${response.order.mode.toUpperCase()} order ${response.order.status.toLowerCase()} for ${response.order.symbol}.` });
      }
      onSubmitted?.(response.order);
    } catch (error) {
      const text = error instanceof Error ? error.message : "Unable to submit order.";
      setMessage({
        tone: "error",
        text:
          text === "Broker account not found"
            ? "Paper broker account was not found for this user. Configure a paper broker account before submitting."
            : text
      });
    } finally {
      setIsSubmitting(false);
      setLiveConfirmOpen(false);
      setLiveConfirmationText("");
    }
  }

  return (
    <Card>
      <CardHeader className="border-b border-border">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>Order Ticket</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Manual orders default to paper mode.</p>
          </div>
          <div className="flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">
            <Lock className="h-3.5 w-3.5" />
            Live locked
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-5">
        <form className="grid gap-4" onSubmit={submitOrder}>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="ticket-symbol">Symbol</Label>
              <Input id="ticket-symbol" value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-side">Buy/Sell</Label>
              <Select id="ticket-side" value={side} onChange={(event) => setSide(event.target.value as OrderSide)}>
                <option value="BUY">Buy</option>
                <option value="SELL">Sell</option>
              </Select>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ticket-exchange">Exchange</Label>
              <Select id="ticket-exchange" value={exchange} onChange={(event) => setExchange(event.target.value as Exchange)}>
                <option value="NSE">NSE</option>
                <option value="NFO">NFO</option>
                <option value="BSE">BSE</option>
                <option value="BFO">BFO</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-segment">Segment</Label>
              <Select id="ticket-segment" value={segment} onChange={(event) => setSegment(event.target.value as Segment)}>
                <option value="EQ">EQ</option>
                <option value="FNO">FNO</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-product">Product type</Label>
              <Select id="ticket-product" value={productType} onChange={(event) => setProductType(event.target.value as ProductType)}>
                <option value="MIS">MIS</option>
                <option value="NRML">NRML</option>
                <option value="CNC">CNC</option>
              </Select>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ticket-quantity">Quantity</Label>
              <Input id="ticket-quantity" inputMode="numeric" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-order-type">Order type</Label>
              <Select id="ticket-order-type" value={orderType} onChange={(event) => setOrderType(event.target.value as OrderType)}>
                <option value="LIMIT">LIMIT</option>
                <option value="SL_LIMIT">SL_LIMIT</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-price">Price</Label>
              <Input id="ticket-price" inputMode="decimal" value={price} onChange={(event) => setPrice(event.target.value)} />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ticket-trigger">Trigger price</Label>
              <Input
                id="ticket-trigger"
                inputMode="decimal"
                value={triggerPrice}
                disabled={orderType !== "SL_LIMIT"}
                onChange={(event) => setTriggerPrice(event.target.value)}
                placeholder={orderType === "SL_LIMIT" ? "Required" : "Disabled"}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-mode">Mode</Label>
              <Select
                id="ticket-mode"
                value={mode}
                disabled={!liveModeVisible}
                onChange={(event) => setMode(event.target.value as "paper" | "live")}
              >
                <option value="paper">PAPER</option>
                {liveModeVisible ? <option value="live">LIVE</option> : null}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ticket-source">Source</Label>
              <Select id="ticket-source" value="manual" disabled>
                <option value="manual">MANUAL</option>
              </Select>
            </div>
          </div>

          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            LIVE mode requires backend safety gates, static IP verification, risk approval, and typed confirmation. MARKET orders are not available here.
          </div>

          {message ? (
            <div
              className={
                message.tone === "success"
                  ? "rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
                  : "flex gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
              }
            >
              {message.tone === "error" ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> : null}
              <span>{message.text}</span>
            </div>
          ) : null}

          <Button type="submit" disabled={isSubmitting}>
            <Send className="h-4 w-4" />
            {isSubmitting ? "Submitting..." : `Submit ${mode.toUpperCase()} order`}
          </Button>
        </form>
      </CardContent>
      <ConfirmDialog
        open={liveConfirmOpen}
        title="Confirm live order"
        description={`Broker: selected account. Symbol: ${symbol}. Side: ${side}. Quantity: ${quantity}. Price: ${price}. Max risk: order value ${Number(quantity || 0) * Number(price || 0)}.`}
        confirmLabel="Submit live order"
        onConfirm={() => {
          if (liveConfirmationText !== "CONFIRM LIVE ORDER") {
            setMessage({ tone: "error", text: "Type CONFIRM LIVE ORDER to submit a live order." });
            setLiveConfirmOpen(false);
            return;
          }
          void submitValidatedOrder(liveConfirmationText);
        }}
        onCancel={() => setLiveConfirmOpen(false)}
      />
      {liveConfirmOpen ? (
        <div className="fixed inset-x-4 bottom-6 z-[60] mx-auto max-w-md rounded-md border border-red-200 bg-white p-4 shadow-xl">
          <Label htmlFor="live-confirmation">Type CONFIRM LIVE ORDER</Label>
          <Input
            id="live-confirmation"
            className="mt-2"
            value={liveConfirmationText}
            onChange={(event) => setLiveConfirmationText(event.target.value)}
          />
        </div>
      ) : null}
    </Card>
  );
}
