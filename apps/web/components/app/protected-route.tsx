"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { LoadingState } from "@/components/app/loading-state";
import { clearAuthToken, fetchCurrentUser, getAuthToken } from "@/lib/auth";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function validateSession() {
      const token = getAuthToken();
      if (!token) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }

      try {
        await fetchCurrentUser(token);
        if (isMounted) {
          setIsAuthorized(true);
        }
      } catch {
        clearAuthToken();
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      }
    }

    void validateSession();

    return () => {
      isMounted = false;
    };
  }, [pathname, router]);

  if (!isAuthorized) {
    return (
      <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <LoadingState title="Checking session" description="Verifying your paper trading workspace access." />
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
