"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as yup from "yup";
import Link from "next/link";
import { Mail, AlertCircle, CheckCircle, ArrowLeft } from "lucide-react";

const schema = yup.object({
  email: yup.string().email("Invalid email").required("Email is required"),
});

export default function ForgotPasswordPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: yupResolver(schema),
  });

  const onSubmit = async (data: any) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || "Request failed");
      }
      setSuccess(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-full flex items-center justify-center bg-canvas relative overflow-hidden px-4">
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-indigo-500/10 blur-[120px] dark:bg-indigo-500/20" />
        <div className="absolute top-[60%] -right-[10%] w-[40%] h-[60%] rounded-full bg-purple-500/10 blur-[120px] dark:bg-purple-500/20" />
      </div>

      <Link 
        href="/login" 
        className="absolute top-6 left-6 md:top-8 md:left-8 flex items-center gap-2 text-sm font-medium text-ink-soft hover:text-ink transition z-20"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Login
      </Link>

      <div className="w-full max-w-md bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl rounded-[2rem] shadow-2xl p-6 sm:p-8 border border-ink/10 relative z-10">
        
        <div className="text-center mb-6">
          <div className="mx-auto w-12 h-12 bg-indigo-100 dark:bg-indigo-500/20 rounded-full flex items-center justify-center mb-4">
            <Mail className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-ink font-display tracking-tight">Forgot password?</h1>
          <p className="text-sm text-ink-soft mt-2">No worries, we'll send you reset instructions.</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-xl flex items-center gap-3 text-sm text-rose-600 dark:text-rose-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {success ? (
          <div className="space-y-4">
            <div className="p-4 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-xl flex items-start gap-3 text-sm text-emerald-700 dark:text-emerald-400">
              <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p>If an account exists for that email, we have sent password reset instructions. Please check your email.</p>
            </div>
            <Link
              href="/reset-password"
              className="block text-center w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-xl shadow-indigo-600/20 transition-all active:scale-[0.98]"
            >
              Enter Reset Code
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 mt-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-xl shadow-indigo-600/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100"
            >
              {loading ? "Sending..." : "Reset password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
