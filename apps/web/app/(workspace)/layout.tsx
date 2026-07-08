import { ProtectedRoute } from "@/components/app/protected-route";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
