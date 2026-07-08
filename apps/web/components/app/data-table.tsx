import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Column<T> = {
  key: string;
  header: string;
  align?: "left" | "center" | "right";
  render: (row: T) => React.ReactNode;
};

export function DataTable<T>({
  title,
  description,
  columns,
  rows
}: {
  title: string;
  description?: string;
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <Card>
      <CardHeader className="border-b border-border/80">
        <div>
          <CardTitle>{title}</CardTitle>
          {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-muted-foreground">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={cn(
                      "px-5 py-3 font-semibold tracking-[0.04em]",
                      column.align === "center" && "text-center",
                      column.align === "right" ? "text-right" : "text-left"
                    )}
                  >
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/80">
              {rows.map((row, index) => (
                <tr key={index} className="bg-white transition-colors hover:bg-slate-50/80">
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn(
                        "px-5 py-3.5 align-middle text-slate-700",
                        column.align === "center" && "text-center",
                        column.align === "right" ? "text-right" : "text-left"
                      )}
                    >
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
