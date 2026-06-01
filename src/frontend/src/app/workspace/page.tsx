"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function WorkspacePage() {
  const { user, setToken, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        Loading...
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-xl font-bold text-gray-900">Smartshark</h1>
              <div className="flex gap-4">
                <span className="text-gray-700 hover:text-gray-900 cursor-pointer">
                  Workspace
                </span>
                {user.role === "admin" && (
                  <span
                    className="text-gray-700 hover:text-gray-900 cursor-pointer"
                    onClick={() => router.push("/admin/settings")}
                  >
                    Admin
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">
                {user.username} ({user.role})
              </span>
              <button
                onClick={() => {
                  setToken(null);
                  router.push("/login");
                }}
                className="rounded-md bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h2 className="text-lg font-semibold text-gray-900">Workspace</h2>
        <p className="mt-2 text-sm text-gray-600">
          No capture artifacts loaded. Upload a PCAP to begin analysis.
        </p>
      </main>
    </div>
  );
}
