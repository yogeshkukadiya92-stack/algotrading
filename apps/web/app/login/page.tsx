"use client";

import { FormEvent, useState } from "react";
import { BarChart3, CheckCircle2, Lock, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginWithPassword, storeAuthToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await loginWithPassword(email, password);
      storeAuthToken(response.access_token);
      const nextPath =
        typeof window === "undefined"
          ? "/dashboard"
          : new URLSearchParams(window.location.search).get("next") || "/dashboard";
      router.replace(nextPath);
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8 sm:py-10">
      <div className="w-full max-w-6xl space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm text-amber-950 shadow-sm">
          <span className="font-semibold">Paper mode active. Live trading disabled.</span>
        </div>
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950 px-6 py-8 text-slate-50 shadow-[0_24px_70px_rgba(15,23,42,0.24)] sm:px-8 sm:py-10">
            <div className="flex items-center justify-between gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-md bg-cyan-600 text-white shadow-sm">
              <BarChart3 className="h-5 w-5" />
              </div>
              <Badge tone="green">
                <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                Risk gated
              </Badge>
            </div>
            <h1 className="mt-7 max-w-xl text-4xl font-bold tracking-tight sm:text-5xl">TradePilot India</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
              A paper-first Indian trading workspace for manual execution, simulated portfolios, risk visibility, and broker readiness.
            </p>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {[
                ["Manual terminal", "Ready"],
                ["Paper strategies", "3 active"],
                ["Live execution", "Locked"]
              ].map(([label, value]) => (
                <div key={label} className="rounded-md border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
                  <div className="text-xs uppercase text-slate-400">{label}</div>
                  <div className="mt-2 text-lg font-semibold">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-8 grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
              {["No live broker orders by default", "Every order passes risk checks"].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-cyan-300" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </section>
          <Card>
            <CardContent className="px-6 py-6 sm:px-7 sm:py-7">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold tracking-tight text-slate-950">Sign in</h2>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">Use your TradePilot India account to enter the paper workspace.</p>
                </div>
                <Badge tone="red">
                  <Lock className="mr-1 h-3.5 w-3.5" />
                  Paper only
                </Badge>
              </div>
              <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="trader@tradepilot.in"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                    required
                  />
                </div>
                {errorMessage ? <p className="text-sm text-red-700">{errorMessage}</p> : null}
                <Button className="h-10 w-full" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Signing in..." : "Enter paper workspace"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
