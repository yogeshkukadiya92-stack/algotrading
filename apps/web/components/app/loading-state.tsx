import { RefreshCcw } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function LoadingState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 px-6 py-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-100 ring-1 ring-slate-200">
          <RefreshCcw className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="mt-1 text-sm text-muted-foreground">{description}</div>
        </div>
      </CardContent>
    </Card>
  );
}
