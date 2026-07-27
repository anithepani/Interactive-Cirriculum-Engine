"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as yup from "yup";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, CheckCircle, AlertCircle, Github, ArrowLeft } from "lucide-react";
import { setTokens, oauthUrl } from "@/lib/auth";
import { InteractiveAvatar } from "@/components/InteractiveAvatar";

const schema = yup.object({
  name: yup.string().min(2, "Name must be at least 2 characters").required("Name is required"),
  email: yup.string().email("Invalid email").required("Email is required"),
  password: yup.string().min(8, "Password must be at least 8 characters").required("Password is required"),
  terms: yup.boolean().oneOf([true], "You must agree to the terms"),
});

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<"signup" | "verify" | "success">("signup");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm({
    resolver: yupResolver(schema),
  });

  const emailValue = watch("email") || "";

  const onSubmit = async (data: any) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || "Signup failed");
      }
      setEmail(data.email);
      setStep("verify");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async () => {
    if (code.length < 6) {
      setError("Please enter the 6-digit verification code");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });
      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || "Verification failed");
      }
      setTokens(result.access_token, result.refresh_token);
      setStep("success");
      setTimeout(() => router.push("/dashboard"), 1500);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resendCode = async () => {
    setError("");
    try {
      const res = await fetch(`/api/v1/auth/resend-code?email=${encodeURIComponent(email)}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to resend code");
      setError("New code sent!");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const googleLogin = () => {
    window.location.href = oauthUrl("google");
  };

  const githubLogin = () => {
    window.location.href = oauthUrl("github");
  };

  return (
    <div className="h-screen w-full flex items-center justify-center bg-canvas relative overflow-hidden px-4">
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-indigo-500/10 blur-[120px] dark:bg-indigo-500/20" />
        <div className="absolute top-[60%] -right-[10%] w-[40%] h-[60%] rounded-full bg-purple-500/10 blur-[120px] dark:bg-purple-500/20" />
      </div>

      {/* Back Button */}
      <Link 
        href="/" 
        className="absolute top-6 left-6 md:top-8 md:left-8 flex items-center gap-2 text-sm font-medium text-ink-soft hover:text-ink transition z-20"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </Link>

      <div className="w-full max-w-md bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl rounded-[2rem] shadow-2xl p-6 sm:p-8 border border-ink/10 relative z-10 max-h-[95vh] overflow-y-auto custom-scrollbar">
        
        {step === "signup" && (
          <div className="flex justify-center mb-4">
            <InteractiveAvatar 
              isPasswordFocused={isPasswordFocused} 
              emailLength={emailValue.length} 
            />
          </div>
        )}

        <div className="text-center mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-ink font-display tracking-tight">
            {step === "signup" ? "Create an account" : step === "verify" ? "Check your email" : "Welcome aboard!"}
          </h1>
          <p className="text-sm text-ink-soft mt-1">
            {step === "signup" ? "Join us to escape tutorial hell" : step === "verify" ? `We sent a code to ${email}` : "Redirecting to your dashboard..."}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-xl flex items-center gap-3 text-sm text-rose-600 dark:text-rose-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {step === "signup" && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div>
              <label className="block text-sm font-semibold text-ink mb-1">Full name</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-soft/50" />
                <input
                  {...register("name")}
                  type="text"
                  placeholder="John Doe"
                  className="w-full pl-11 pr-4 py-2.5 bg-canvas border border-ink/10 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-ink placeholder:text-ink-soft/40 text-sm"
                />
              </div>
              {errors.name && <p className="text-xs text-rose-500 mt-1 ml-1">{errors.name.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-ink mb-1">Email address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-soft/50" />
                <input
                  {...register("email")}
                  type="email"
                  placeholder="you@example.com"
                  className="w-full pl-11 pr-4 py-2.5 bg-canvas border border-ink/10 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-ink placeholder:text-ink-soft/40 text-sm"
                />
              </div>
              {errors.email && <p className="text-xs text-rose-500 mt-1 ml-1">{errors.email.message}</p>}
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-sm font-semibold text-ink">Password</label>
              </div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-soft/50" />
                <input
                  {...register("password")}
                  type="password"
                  placeholder="••••••••"
                  onFocus={() => setIsPasswordFocused(true)}
                  onBlur={() => setIsPasswordFocused(false)}
                  className="w-full pl-11 pr-4 py-2.5 bg-canvas border border-ink/10 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-ink placeholder:text-ink-soft/40 text-sm"
                />
              </div>
              {errors.password && <p className="text-xs text-rose-500 mt-1 ml-1">{errors.password.message}</p>}
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                {...register("terms")}
                type="checkbox"
                id="terms"
                className="w-4 h-4 text-indigo-600 bg-canvas border-ink/20 rounded focus:ring-indigo-500"
              />
              <label htmlFor="terms" className="text-xs text-ink-soft">
                I agree to the <a href="#" className="text-indigo-600 hover:text-indigo-500 hover:underline">Terms & Conditions</a>
              </label>
            </div>
            {errors.terms && <p className="text-xs text-rose-500 ml-1">{errors.terms.message}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 mt-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-xl shadow-indigo-600/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100"
            >
              {loading ? "Sending..." : "Create account"}
            </button>
          </form>
        )}

        {step === "verify" && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-ink mb-2 text-center">Verification code</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                className="w-full px-4 py-4 bg-canvas border border-ink/10 rounded-2xl text-center text-3xl font-display font-bold tracking-[0.5em] focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-ink placeholder:text-ink-soft/30"
                maxLength={6}
              />
              <p className="text-xs text-ink-soft mt-3 text-center">Check your inbox and spam folder</p>
            </div>

            <button
              onClick={verifyCode}
              disabled={loading || code.length < 6}
              className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-2xl shadow-xl shadow-indigo-600/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100"
            >
              {loading ? "Verifying..." : "Verify email"}
            </button>

            <button
              onClick={resendCode}
              className="w-full py-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 transition"
            >
              Didn&apos;t receive the code? Resend
            </button>
          </div>
        )}

        {step === "success" && (
          <div className="text-center py-10">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-emerald-500/10 text-emerald-500 mb-6">
              <CheckCircle className="w-10 h-10" />
            </div>
            <p className="text-ink font-medium text-lg animate-pulse">Redirecting to dashboard...</p>
          </div>
        )}

        {step === "signup" && (
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-ink/10"></div>
              </div>
              <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-semibold">
                <span className="px-3 bg-white dark:bg-zinc-900 text-ink-soft/60">Or continue with</span>
              </div>
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={googleLogin}
                className="flex-1 py-2 bg-canvas border border-ink/10 rounded-xl hover:border-ink/20 hover:bg-ink/5 transition flex items-center justify-center gap-2 text-sm font-medium text-ink"
              >
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Google
              </button>
              <button
                onClick={githubLogin}
                className="flex-1 py-2 bg-canvas border border-ink/10 rounded-xl hover:border-ink/20 hover:bg-ink/5 transition flex items-center justify-center gap-2 text-sm font-medium text-ink"
              >
                <Github size={18} />
                GitHub
              </button>
            </div>
          </div>
        )}

        {step === "signup" && (
          <p className="text-center text-xs text-ink-soft mt-5">
            Already have an account?{" "}
            <Link href="/login" className="text-indigo-600 hover:text-indigo-500 font-semibold hover:underline">
              Log in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}