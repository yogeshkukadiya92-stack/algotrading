import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-md border border-input bg-white px-3 text-sm outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-cyan-600 focus:ring-4 focus:ring-cyan-100",
        className
      )}
      {...props}
    />
  );
}
