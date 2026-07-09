"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, ChartColumnBig, Layers2, ShoppingBasket, Sigma } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { StatusCard } from "@/components/app/status-card";
import { OrderTicket, type OrderTicketDraft } from "@/components/trading/order-ticket";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  fetchOptionChain,
  formatCompact,
  formatOptionNumber,
  optionExpiries,
  optionSymbol,
  type OptionChain,
  type OptionStrike,
  type OptionUnderlying
} from "@/lib/options-chain";

const underlyings: OptionUnderlying[] = ["NIFTY", "BANKNIFTY"];
const BASKET_STORAGE_KEY = "tradepilot.paper.option_basket";

type BasketItem = {
  id: string;
  symbol: string;
  side: "CE" | "PE";
  strikePrice: string;
  price: string;
  underlying: string;
  expiry: string;
};

function getAtmStrike(chain: OptionChain | null) {
  if (!chain?.strikes.length) {
    return null;
  }
  const spot = Number(chain.spot_price);
  return chain.strikes.reduce((nearest, strike) =>
    Math.abs(Number(strike.strike_price) - spot) < Math.abs(Number(nearest.strike_price) - spot) ? strike : nearest
  );
}

function pcr(chain: OptionChain | null) {
  if (!chain) {
    return "0.00";
  }
  const putOi = chain.strikes.reduce((sum, strike) => sum + strike.pe_oi, 0);
  const callOi = chain.strikes.reduce((sum, strike) => sum + strike.ce_oi, 0);
  return callOi ? (putOi / callOi).toFixed(2) : "0.00";
}

export default function OptionChainPage() {
  const [underlying, setUnderlying] = useState<OptionUnderlying>("NIFTY");
  const [expiry, setExpiry] = useState(optionExpiries[0]);
  const [chain, setChain] = useState<OptionChain | null>(null);
  const [ticketDraft, setTicketDraft] = useState<OrderTicketDraft | null>(null);
  const [basket, setBasket] = useState<BasketItem[]>([]);
  const [basketMessage, setBasketMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedBasket = window.localStorage.getItem(BASKET_STORAGE_KEY);
    if (storedBasket) {
      try {
        setBasket(JSON.parse(storedBasket) as BasketItem[]);
      } catch {
        window.localStorage.removeItem(BASKET_STORAGE_KEY);
      }
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(BASKET_STORAGE_KEY, JSON.stringify(basket));
  }, [basket]);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setErrorMessage(null);

    async function loadChain() {
      try {
        const data = await fetchOptionChain(underlying, expiry);
        if (isMounted) {
          setChain(data);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Unable to load option chain.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadChain();
    return () => {
      isMounted = false;
    };
  }, [underlying, expiry]);

  const atmStrike = useMemo(() => getAtmStrike(chain), [chain]);
  const highestOi = useMemo(() => {
    if (!chain) {
      return "-";
    }
    let best = { label: "-", oi: 0 };
    for (const strike of chain.strikes) {
      if (strike.ce_oi > best.oi) {
        best = { label: `${formatOptionNumber(strike.strike_price, 0)} CE`, oi: strike.ce_oi };
      }
      if (strike.pe_oi > best.oi) {
        best = { label: `${formatOptionNumber(strike.strike_price, 0)} PE`, oi: strike.pe_oi };
      }
    }
    return best.label;
  }, [chain]);

  function addToTicket(strike: OptionStrike, side: "CE" | "PE") {
    if (!chain) {
      return;
    }
    setTicketDraft({
      symbol: optionSymbol(chain.underlying, chain.expiry, strike.strike_price, side),
      exchange: "NFO",
      segment: "FNO",
      side: "BUY",
      price: side === "CE" ? strike.ce_ask : strike.pe_ask
    });
  }

  function addToBasket(strike: OptionStrike, side: "CE" | "PE") {
    if (!chain) {
      return;
    }
    const symbol = optionSymbol(chain.underlying, chain.expiry, strike.strike_price, side);
    const item: BasketItem = {
      id: `${symbol}-${Date.now()}`,
      symbol,
      side,
      strikePrice: strike.strike_price,
      price: side === "CE" ? strike.ce_ask : strike.pe_ask,
      underlying: chain.underlying,
      expiry: chain.expiry
    };
    setBasket((current) => [item, ...current]);
    setBasketMessage(`${symbol} added to paper basket.`);
  }

  function basketToTicket(item: BasketItem) {
    setTicketDraft({
      symbol: item.symbol,
      exchange: "NFO",
      segment: "FNO",
      side: "BUY",
      price: item.price
    });
  }

  function removeBasketItem(id: string) {
    setBasket((current) => current.filter((item) => item.id !== id));
  }

  return (
    <AppShell title="Option Chain" description="Read-only option chain for paper analysis and manual terminal planning.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Underlying" value={chain ? `${chain.underlying} ${formatOptionNumber(chain.spot_price)}` : underlying} helper={chain?.source === "BROKER" ? "Broker read-only spot" : "Mock reference spot"} tone="blue" icon={ChartColumnBig} />
        <StatusCard title="ATM Strike" value={atmStrike ? formatOptionNumber(atmStrike.strike_price, 0) : "-"} helper="Nearest strike to spot" tone="green" icon={Sigma} />
        <StatusCard title="Highest OI" value={highestOi} helper="Mock option wall" tone="amber" icon={Layers2} />
        <StatusCard title="Data Source" value={chain?.source ?? "MOCK"} helper={chain?.source === "BROKER" ? "Read-only broker data" : "Fallback mock data"} tone={chain?.source === "BROKER" ? "green" : "amber"} trend="up" icon={Activity} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.45fr_0.8fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader className="border-b border-border">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <CardTitle>Option Chain</CardTitle>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <span>CE/PE ladder for paper-mode planning.</span>
                    {chain ? <Badge tone={chain.source === "BROKER" ? "green" : "amber"}>{chain.source}</Badge> : null}
                  </div>
                  {chain?.fallback_reason ? (
                    <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      {chain.fallback_reason}
                    </p>
                  ) : null}
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:w-[420px]">
                  <div className="space-y-1.5">
                    <Label htmlFor="underlying">Underlying</Label>
                    <Select id="underlying" value={underlying} onChange={(event) => setUnderlying(event.target.value as OptionUnderlying)}>
                      {underlyings.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="expiry">Expiry</Label>
                    <Select id="expiry" value={expiry} onChange={(event) => setExpiry(event.target.value)}>
                      {optionExpiries.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </Select>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="px-0 pb-0">
              {errorMessage ? <div className="p-4"><ErrorState title="Option chain unavailable" description={errorMessage} /></div> : null}
              {isLoading ? <div className="p-4"><LoadingState title="Loading option chain" description="Fetching mock option ladder." /></div> : null}
              {!isLoading && chain ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[1280px] text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th colSpan={9} className="border-r border-border px-4 py-2 text-center font-semibold text-sky-800">
                          CE
                        </th>
                        <th className="px-4 py-2 text-center font-semibold">Strike</th>
                        <th colSpan={9} className="border-l border-border px-4 py-2 text-center font-semibold text-emerald-800">
                          PE
                        </th>
                      </tr>
                      <tr>
                        {["LTP", "Bid", "Ask", "OI", "Vol", "IV", "Delta", "Greeks", "Actions"].map((header) => (
                          <th key={`ce-${header}`} className="px-3 py-2 text-right font-medium">
                            {header}
                          </th>
                        ))}
                        <th className="px-3 py-2 text-center font-medium">Strike</th>
                        {["LTP", "Bid", "Ask", "OI", "Vol", "IV", "Delta", "Greeks", "Actions"].map((header) => (
                          <th key={`pe-${header}`} className="px-3 py-2 text-right font-medium">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {chain.strikes.map((strike) => {
                        const isAtm = atmStrike?.strike_price === strike.strike_price;
                        return (
                          <tr key={strike.strike_price} className={isAtm ? "bg-amber-50" : "bg-white"}>
                            <td className="px-3 py-3 text-right font-medium">{formatOptionNumber(strike.ce_ltp)}</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.ce_bid)}</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.ce_ask)}</td>
                            <td className="px-3 py-3 text-right">{formatCompact(strike.ce_oi)}</td>
                            <td className="px-3 py-3 text-right">{formatCompact(strike.ce_volume)}</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.ce_iv)}%</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.ce_delta, 3)}</td>
                            <td className="px-3 py-3 text-right text-xs">
                              G {formatOptionNumber(strike.ce_gamma, 4)} T {formatOptionNumber(strike.ce_theta)} V {formatOptionNumber(strike.ce_vega)}
                            </td>
                            <td className="px-3 py-3">
                              <div className="flex justify-end gap-2">
                                <Button size="sm" onClick={() => addToTicket(strike, "CE")}>Ticket</Button>
                                <Button size="sm" variant="secondary" onClick={() => addToBasket(strike, "CE")}>
                                  <ShoppingBasket className="h-4 w-4" />
                                  Basket
                                </Button>
                              </div>
                            </td>
                            <td className="border-x border-border px-3 py-3 text-center">
                              <span className={isAtm ? "rounded-md bg-amber-200 px-2 py-1 font-bold text-amber-950" : "font-semibold"}>
                                {formatOptionNumber(strike.strike_price, 0)}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-right font-medium">{formatOptionNumber(strike.pe_ltp)}</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.pe_bid)}</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.pe_ask)}</td>
                            <td className="px-3 py-3 text-right">{formatCompact(strike.pe_oi)}</td>
                            <td className="px-3 py-3 text-right">{formatCompact(strike.pe_volume)}</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.pe_iv)}%</td>
                            <td className="px-3 py-3 text-right">{formatOptionNumber(strike.pe_delta, 3)}</td>
                            <td className="px-3 py-3 text-right text-xs">
                              G {formatOptionNumber(strike.pe_gamma, 4)} T {formatOptionNumber(strike.pe_theta)} V {formatOptionNumber(strike.pe_vega)}
                            </td>
                            <td className="px-3 py-3">
                              <div className="flex justify-end gap-2">
                                <Button size="sm" onClick={() => addToTicket(strike, "PE")}>Ticket</Button>
                                <Button size="sm" variant="secondary" onClick={() => addToBasket(strike, "PE")}>
                                  <ShoppingBasket className="h-4 w-4" />
                                  Basket
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </CardContent>
          </Card>
          {basketMessage ? (
            <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">{basketMessage}</div>
          ) : null}
          <Card>
            <CardHeader className="border-b border-border">
              <div className="flex items-center justify-between gap-3">
                <CardTitle>Paper Basket</CardTitle>
                <Button size="sm" variant="secondary" onClick={() => setBasket([])} disabled={basket.length === 0}>
                  Clear
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {basket.length === 0 ? (
                <div className="px-5 py-6 text-sm text-muted-foreground">No basket legs yet. Add CE or PE contracts from the option chain.</div>
              ) : (
                <div className="divide-y divide-border">
                  {basket.map((item) => (
                    <div key={item.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div className="font-semibold">{item.symbol}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {item.underlying} {item.expiry} | {item.side} {formatOptionNumber(item.strikePrice, 0)} | Ask {formatOptionNumber(item.price)}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => basketToTicket(item)}>
                          Ticket
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => removeBasketItem(item.id)}>
                          Remove
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <OrderTicket draft={ticketDraft} />
      </section>
    </AppShell>
  );
}
