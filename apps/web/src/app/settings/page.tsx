"use client";

import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { getCurrentUser, authFetch, type AuthUser } from "@/lib/auth";
import { Save, AlertTriangle, CheckCircle2 } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function SettingsPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [name, setName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    getCurrentUser().then((u) => {
      setUser(u);
      if (u) setName(u.name);
      setLoading(false);
    });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload: any = { name };
      if (newPassword) {
        if (!currentPassword) {
          throw new Error("Current password is required to set a new password.");
        }
        if (newPassword.length < 8) {
          throw new Error("New password must be at least 8 characters.");
        }
        payload.current_password = currentPassword;
        payload.new_password = newPassword;
      }

      const res = await authFetch("/api/v1/auth/me", {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to update settings");
      }

      const updatedUser = await res.json();
      setUser(updatedUser);
      setSuccess("Settings updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      
      // Dispatch event so AppLayout updates its banner/header instantly
      window.dispatchEvent(new Event("userUpdated"));
      
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl">
        <h1 className="font-display text-3xl font-bold text-ink mb-8">Settings</h1>

        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <LoadingSpinner size={32} />
          </div>
        ) : (
          <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
            <h2 className="font-display text-xl font-semibold text-ink mb-6">Profile & Security</h2>
            
            {error && (
              <div className="mb-6 flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
                {error}
              </div>
            )}
            
            {success && (
              <div className="mb-6 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                {success}
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-6">
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-soft">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-xl border border-ink/10 bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  required
                />
              </div>

              <div className="pt-4">
                <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-ink-soft">Change Password</h3>
                <div className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm font-medium text-ink-soft">Current Password</label>
                    <input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="w-full rounded-xl border border-ink/10 bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      placeholder="Leave blank if not changing"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-ink-soft">New Password</label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full rounded-xl border border-ink/10 bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      placeholder="Leave blank if not changing"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-full bg-indigo-600 px-8 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50"
                >
                  {saving ? <LoadingSpinner size={16} /> : <Save className="h-4 w-4" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
