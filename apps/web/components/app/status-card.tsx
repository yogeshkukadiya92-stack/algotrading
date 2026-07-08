import { ArrowDownRight, ArrowUpRight, LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function StatusCard({
  title,
  value,
  helper,
  tone = "neutral",
  trend,
  icon: Icon
}: {
  title: string;
  value: string;
  helper: string;
  tone?: "neutral" | "green" | "amber" | "red" | "blue";
  trend?: "up" | "down" | "steady";
  icon?: LucideIcon;
}) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <div className="flex items-center gap-2">
          {Icon ? (
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-muted text-foreground">
              <Icon className="h-4 w-4" />
            </div>
          ) : null}
          <CardTitle>{title}</CardTitle>
        </div>
        <Badge tone={tone}>{tone === "neutral" ? "Stable" : tone}</Badge>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
        <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
          {trend === "up" ? <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600" /> : null}
          {trend === "down" ? <ArrowDownRight className="h-3.5 w-3.5 text-red-600" /> : null}
          <span>{helper}</span>
        </div>
      </CardContent>
    </Card>
  );
}

