"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { setTokens, safeRedirectPath } from "@/lib/auth";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (!accessToken || !refreshToken) {
      setError("Authentication failed. No tokens received.");
      return;
    }

    let cancelled = false;

    // The session cookie must exist before navigating, otherwise middleware
    // bounces this fresh OAuth login back to /login.
    (async () => {
      const sessionReady = await setTokens(accessToken, refreshToken);
      if (cancelled) return;

      if (!sessionReady) {
        setError("Signed in, but the session could not be started. Please try again.");
        return;
      }

      router.replace(safeRedirectPath(searchParams.get("redirect")));
      router.refresh();
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={() => router.push("/login")}
          className="text-indigo-600 hover:underline font-medium"
        >
          Back to login
        </button>
      </div>
    );
  }

  return (
    <div className="text-center">
      <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mx-auto mb-4" />
      <p className="text-gray-600">Completing sign in...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 to-purple-50 p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-8 border border-indigo-100">
        <div className="text-center mb-6">
          <CheckCircle className="w-12 h-12 text-indigo-500 mx-auto mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 font-display">Signing you in</h1>
        </div>
        <Suspense
          fallback={
            <div className="text-center">
              <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mx-auto" />
            </div>
          }
        >
          <CallbackHandler />
        </Suspense>
      </div>
    </div>
  );
}
