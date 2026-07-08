"use client";

import { useEffect, useMemo, useState } from "react";
import { BriefcaseBusiness, KeyRound, Link2, ShieldCheck } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { StatusCard } from "@/components/app/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { setActiveBrokerSelection } from "@/lib/active-broker";
import {
  connectBroker,
  fetchBrokerAccounts,
  fetchBrokerFunds,
  fetchBrokerOrders,
  fetchBrokerPositions,
  formatMoney,
  type BrokerAccount,
  type BrokerFunds,
  type BrokerOrder,
  type BrokerPosition,
  type SupportedBroker
} from "@/lib/brokers-api";

export default function BrokersPage() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [funds, setFunds] = useState<BrokerFunds | null>(null);
  const [positions, setPositions] = useState<BrokerPosition[]>([]);
  const [orders, setOrders] = useState<BrokerOrder[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.id === selectedAccountId) ?? accounts[0] ?? null,
    [accounts, selectedAccountId]
  );

  useEffect(() => {
    void loadAccounts();
  }, []);

  useEffect(() => {
    if (selectedAccount) {
      void loadReadOnlyData(selectedAccount.id);
    } else {
      setFunds(null);
      setPositions([]);
      setOrders([]);
    }
  }, [selectedAccount?.id]);

  async function loadAccounts() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchBrokerAccounts();
      setAccounts(data);
      setSelectedAccountId((current) => current ?? data[0]?.id ?? null);
      if (data[0] && !currentSelectionExists(data, selectedAccountId)) {
        setActiveBrokerSelection({
          id: data[0].id,
          broker_name: data[0].broker_name,
          display_name: data[0].display_name
        });
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load broker accounts.");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadReadOnlyData(accountId: string) {
    setErrorMessage(null);
    try {
      const [fundsData, positionsData, ordersData] = await Promise.all([
        fetchBrokerFunds(accountId),
        fetchBrokerPositions(accountId),
        fetchBrokerOrders(accountId)
      ]);
      setFunds(fundsData);
      setPositions(positionsData);
      setOrders(ordersData);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load broker read-only data.");
      setFunds(null);
      setPositions([]);
      setOrders([]);
    }
  }

  async function handleConnect(brokerName: SupportedBroker) {
    setIsConnecting(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      const response = await connectBroker(brokerName);
      setMessage(`${response.message} Login URL generated for read-only setup.`);
      await loadAccounts();
      setSelectedAccountId(response.account.id);
      setActiveBrokerSelection({
        id: response.account.id,
        broker_name: response.account.broker_name,
        display_name: response.account.display_name
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to connect broker.");
    } finally {
      setIsConnecting(false);
    }
  }

  function selectActiveAccount(account: BrokerAccount) {
    setSelectedAccountId(account.id);
    setActiveBrokerSelection({
      id: account.id,
      broker_name: account.broker_name,
      display_name: account.display_name
    });
    setMessage(`${account.display_name} is now the active broker view.`);
  }

  return (
    <AppShell title="Brokers" description="Read-only broker adapter status and account snapshots.">
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
        Read-only broker mode. Live order placement disabled.
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Connected Brokers" value={`${accounts.length} read-only`} helper="Live order actions locked" tone="blue" icon={BriefcaseBusiness} />
        <StatusCard title="Credential Source" value="Env only" helper="No API keys in code" tone="green" icon={KeyRound} />
        <StatusCard title="Adapter Health" value={selectedAccount ? "Connected" : "Not connected"} helper="Read APIs only" tone={selectedAccount ? "green" : "amber"} icon={Link2} />
        <StatusCard title="Safety Policy" value="Locked" helper="place/modify/cancel disabled" tone="red" icon={ShieldCheck} />
      </section>

      <Card>
        <CardHeader className="border-b border-border">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Broker Account</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">Multiple read-only brokers supported. Paper trading still works with no broker connected.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => handleConnect("zerodha")} disabled={isConnecting}>
                {isConnecting ? "Connecting..." : "Add Zerodha"}
              </Button>
              <Button variant="secondary" onClick={() => handleConnect("upstox")} disabled={isConnecting}>
                {isConnecting ? "Connecting..." : "Add Upstox"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-5">
          {message ? <div className="mb-4 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">{message}</div> : null}
          {errorMessage ? <ErrorState title="Broker data unavailable" description={errorMessage} /> : null}
          {isLoading ? <LoadingState title="Loading broker accounts" description="Checking read-only broker connections." /> : null}
          {!isLoading && !accounts.length && !errorMessage ? (
            <EmptyState title="No broker accounts connected" description="Add a read-only Zerodha account to view mocked profile, funds, positions, and orders." />
          ) : null}
          {accounts.length ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {accounts.map((account) => (
                <button
                  key={account.id}
                  className={
                    account.id === selectedAccount?.id
                      ? "rounded-md border border-primary bg-sky-50 p-4 text-left"
                      : "rounded-md border border-border bg-white p-4 text-left hover:bg-muted"
                  }
                  onClick={() => selectActiveAccount(account)}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold">{account.display_name}</div>
                    <div className="flex items-center gap-2">
                      {account.id === selectedAccount?.id ? <Badge tone="blue">ACTIVE</Badge> : null}
                      <Badge tone={account.is_active ? "green" : "amber"}>{account.status}</Badge>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-muted-foreground">{account.broker_name.toUpperCase()}</div>
                  <div className="mt-3 text-xs text-muted-foreground">Static IP verified: {account.static_ip_verified ? "Yes" : "No"}</div>
                </button>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader className="border-b border-border">
            <CardTitle>Funds</CardTitle>
          </CardHeader>
          <CardContent className="pt-5">
            {funds ? (
              <dl className="grid gap-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Available cash</dt>
                  <dd className="font-semibold">₹{formatMoney(funds.available_cash)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Collateral</dt>
                  <dd className="font-semibold">₹{formatMoney(funds.collateral)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Utilized margin</dt>
                  <dd className="font-semibold">₹{formatMoney(funds.utilized_margin)}</dd>
                </div>
                <div className="flex justify-between gap-3 border-t border-border pt-3">
                  <dt className="text-muted-foreground">Net</dt>
                  <dd className="font-semibold">₹{formatMoney(funds.net)}</dd>
                </div>
              </dl>
            ) : (
              <EmptyState title="No funds snapshot" description="Connect a read-only account to load funds." />
            )}
          </CardContent>
        </Card>

        <div className="xl:col-span-2">
          <DataTable
            title="Broker Positions"
            description="Read-only normalized positions from the broker adapter."
            rows={positions}
            columns={[
              { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
              { key: "quantity", header: "Qty", align: "right", render: (row) => row.quantity },
              { key: "average_price", header: "Avg", align: "right", render: (row) => `₹${formatMoney(row.average_price)}` },
              { key: "last_price", header: "LTP", align: "right", render: (row) => `₹${formatMoney(row.last_price)}` },
              { key: "unrealized_pnl", header: "Unrealized", align: "right", render: (row) => `₹${formatMoney(row.unrealized_pnl)}` }
            ]}
          />
        </div>
      </section>

      <DataTable
        title="Latest Broker Orders"
        description="Read-only normalized broker order book. New live orders remain disabled."
        rows={orders}
        columns={[
          { key: "broker_order_id", header: "Broker Order ID", render: (row) => <span className="font-semibold">{row.broker_order_id}</span> },
          { key: "broker_status", header: "Broker Status", render: (row) => row.broker_status },
          { key: "normalized_status", header: "Normalized", render: (row) => <Badge tone="blue">{row.normalized_status}</Badge> },
          { key: "filled_quantity", header: "Filled", align: "right", render: (row) => row.filled_quantity },
          { key: "pending_quantity", header: "Pending", align: "right", render: (row) => row.pending_quantity },
          { key: "average_price", header: "Avg", align: "right", render: (row) => (row.average_price ? `₹${formatMoney(row.average_price)}` : "-") }
        ]}
      />
    </AppShell>
  );
}

function currentSelectionExists(accounts: BrokerAccount[], selectedAccountId: string | null) {
  return Boolean(selectedAccountId && accounts.some((account) => account.id === selectedAccountId));
}
