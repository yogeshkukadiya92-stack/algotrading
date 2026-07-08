import Link from "next/link";
import { ArrowRight, LayoutDashboard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function TradingDashboard() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <Card className="w-full max-w-xl">
        <CardContent className="px-6 py-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <LayoutDashboard className="h-5 w-5" />
          </div>
          <h1 className="mt-4 text-2xl font-semibold">TradePilot India</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            The workspace now lives in the route-based app shell with mock-only paper trading screens.
          </p>
          <div className="mt-6">
            <Link href="/dashboard">
              <Button>
                Open dashboard
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

