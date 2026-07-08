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
  const toneClass =
    tone === "green"
      ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
      : tone === "amber"
        ? "bg-amber-50 text-amber-700 ring-amber-100"
        : tone === "red"
          ? "bg-red-50 text-red-700 ring-red-100"
          : tone === "blue"
            ? "bg-sky-50 text-sky-700 ring-sky-100"
            : "bg-slate-50 text-slate-700 ring-slate-100";

  return (
    <Card className="transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_1px_2px_rgba(15,23,42,0.04),0_18px_40px_rgba(15,23,42,0.08)]">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          {Icon ? (
            <div className={`flex h-9 w-9 items-center justify-center rounded-md ring-1 ${toneClass}`}>
              <Icon className="h-4 w-4" />
            </div>
          ) : null}
          <CardTitle>{title}</CardTitle>
        </div>
        <Badge tone={tone}>{tone === "neutral" ? "Stable" : tone}</Badge>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tracking-tight text-slate-950">{value}</div>
        <div className="mt-2 flex items-center gap-2 text-xs leading-5 text-muted-foreground">
          {trend === "up" ? <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600" /> : null}
          {trend === "down" ? <ArrowDownRight className="h-3.5 w-3.5 text-red-600" /> : null}
          <span>{helper}</span>
        </div>
      </CardContent>
    </Card>
  );
}
