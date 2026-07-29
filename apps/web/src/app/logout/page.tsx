"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { removeTokens } from "@/lib/auth";
import { CheckCircle2, Loader2, Sparkles } from "lucide-react";

export default function LogoutPage() {
  const router = useRouter();
  const [loggedOut, setLoggedOut] = useState(false);

  useEffect(() => {
    let cancelled = false;

    // Await cookie deletion: only then is the session actually gone as far as
    // middleware is concerned. Reporting success earlier would be a lie.
    (async () => {
      await removeTokens();
      if (cancelled) return;
      setLoggedOut(true);
      // Drop any cached RSC payload rendered for the previous session.
      router.refresh();
    })();

    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas p-4 relative overflow-hidden">
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[10%] left-[20%] w-[40%] h-[40%] rounded-full bg-indigo-500/10 blur-[120px] dark:bg-indigo-500/20" />
        <div className="absolute bottom-[10%] right-[20%] w-[30%] h-[30%] rounded-full bg-rose-500/10 blur-[120px] dark:bg-rose-500/20" />
      </div>

      <div className="w-full max-w-md bg-white/80 dark:bg-zinc-900/80 backdrop-blur-2xl rounded-[2rem] shadow-2xl p-8 sm:p-12 border border-ink/10 relative z-10 flex flex-col items-center text-center transform transition-all duration-700">
        
        <div className="mb-8 relative">
          <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full" />
          <div className="relative w-20 h-20 bg-canvas border border-ink/10 rounded-2xl flex items-center justify-center shadow-inner">
            {!loggedOut ? (
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            ) : (
              <CheckCircle2 className="w-10 h-10 text-emerald-500 animate-in zoom-in duration-300" />
            )}
          </div>
        </div>

        <h1 className="text-3xl font-display font-bold text-ink mb-3 tracking-tight">
          {!loggedOut ? "Signing out..." : "Signed out securely"}
        </h1>
        
        <p className="text-ink-soft mb-8 max-w-xs text-sm leading-relaxed">
          {!loggedOut 
            ? "We are securely wrapping up your session. Please hold on a moment." 
            : "Thank you for using Interactive Curriculum Engine. Have a great day!"}
        </p>

        <div className={`w-full transition-all duration-500 ${loggedOut ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
          <Link 
            href="/login"
            className="group w-full flex items-center justify-center gap-2 py-4 bg-ink hover:bg-ink/90 text-canvas font-semibold rounded-2xl shadow-xl shadow-ink/10 transition-all active:scale-[0.98]"
          >
            <span>Log back in</span>
            <Sparkles className="w-4 h-4 text-lime group-hover:animate-pulse" />
          </Link>
          
          <Link 
            href="/"
            className="block w-full text-center mt-4 text-sm font-medium text-ink-soft hover:text-ink transition-colors"
          >
            Return to Homepage
          </Link>
        </div>
      </div>
    </div>
  );
}
