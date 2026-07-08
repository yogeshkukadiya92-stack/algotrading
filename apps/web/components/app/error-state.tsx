import { AlertTriangle } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function ErrorState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="border-red-200 bg-red-50">
      <CardContent className="flex items-start gap-3 px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-red-700">
          <AlertTriangle className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-semibold text-red-900">{title}</div>
          <div className="mt-1 text-sm text-red-800">{description}</div>
        </div>
      </CardContent>
    </Card>
  );
}

