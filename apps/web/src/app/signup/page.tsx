"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as yup from "yup";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, CheckCircle, AlertCircle, Github } from "lucide-react";
import { setTokens, oauthUrl } from "@/lib/auth";

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

  const { register, handleSubmit, watch, formState: { errors } } = useForm({
    resolver: yupResolver(schema),
  });

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 to-purple-50 p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-8 border border-indigo-100">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 font-display">
            {step === "signup" ? "Create an account" : step === "verify" ? "Verify your email" : "Welcome!"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {step === "signup" && "Start your interactive learning journey"}
            {step === "verify" && `We sent a code to ${email}`}
            {step === "success" && "Your account is ready!"}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-sm text-red-600">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {step === "signup" && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  {...register("name")}
                  type="text"
                  placeholder="Enter your name"
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                />
              </div>
              {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  {...register("email")}
                  type="email"
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                />
              </div>
              {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  {...register("password")}
                  type="password"
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                />
              </div>
              {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
            </div>

            <div className="flex items-center gap-2">
              <input
                {...register("terms")}
                type="checkbox"
                id="terms"
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="terms" className="text-sm text-gray-600">
                I agree to the <a href="#" className="text-indigo-600 hover:underline">Terms & Conditions</a>
              </label>
            </div>
            {errors.terms && <p className="text-xs text-red-500">{errors.terms.message}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium rounded-xl hover:shadow-lg transition-all disabled:opacity-50"
            >
              {loading ? "Sending..." : "Create account"}
            </button>
          </form>
        )}

        {step === "verify" && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Verification code</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="Enter 6-digit code"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-center text-2xl tracking-widest focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                maxLength={6}
              />
              <p className="text-xs text-gray-500 mt-2">Enter the code sent to your email</p>
            </div>

            <button
              onClick={verifyCode}
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium rounded-xl hover:shadow-lg transition-all disabled:opacity-50"
            >
              {loading ? "Verifying..." : "Verify email"}
            </button>

            <button
              onClick={resendCode}
              className="w-full py-2 text-sm text-indigo-600 hover:text-indigo-800 transition"
            >
              Didn't receive the code? Resend
            </button>
          </div>
        )}

        {step === "success" && (
          <div className="text-center py-8">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-gray-600">Redirecting to dashboard...</p>
          </div>
        )}

        {step === "signup" && (
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">Or continue with</span>
              </div>
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={googleLogin}
                className="flex-1 py-3 border border-gray-200 rounded-xl hover:bg-gray-50 transition flex items-center justify-center gap-2"
              >
                <svg width="20" height="20" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Google
              </button>
              <button
                onClick={githubLogin}
                className="flex-1 py-3 border border-gray-200 rounded-xl hover:bg-gray-50 transition flex items-center justify-center gap-2"
              >
                <Github size={20} />
                GitHub
              </button>
            </div>
          </div>
        )}

        {step === "signup" && (
          <p className="text-center text-sm text-gray-500 mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-indigo-600 hover:underline font-medium">
              Log in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}