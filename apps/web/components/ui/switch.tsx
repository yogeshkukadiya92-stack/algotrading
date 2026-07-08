import * as React from "react";

import { cn } from "@/lib/utils";

export function Switch({
  checked,
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { checked?: boolean }) {
  return (
    <input
      type="checkbox"
      checked={checked}
      className={cn(
        "h-5 w-9 cursor-pointer appearance-none rounded-full border border-border bg-muted transition checked:bg-emerald-500 before:block before:h-4 before:w-4 before:translate-x-0.5 before:translate-y-0.5 before:rounded-full before:bg-white before:shadow-sm before:transition checked:before:translate-x-4 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
}

