"use client";

import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { getCurrentUser, authFetch, type AuthUser } from "@/lib/auth";
import { Save, AlertTriangle, CheckCircle2, Flame } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";

const AVATARS = [
  "https://api.dicebear.com/9.x/micah/svg?seed=Felix&backgroundColor=f0fdf4",
  "https://api.dicebear.com/9.x/micah/svg?seed=Aneka&backgroundColor=fff1f2",
  "https://api.dicebear.com/9.x/micah/svg?seed=Mimi&backgroundColor=eef2ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Jasper&backgroundColor=fffbeb",
  "https://api.dicebear.com/9.x/micah/svg?seed=Zoey&backgroundColor=faf5ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Oscar&backgroundColor=f8fafc",
  "https://api.dicebear.com/9.x/micah/svg?seed=Luna&backgroundColor=ecfeff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Leo&backgroundColor=fff7ed",
  "https://api.dicebear.com/9.x/micah/svg?seed=Cleo&backgroundColor=fdf4ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Max&backgroundColor=f0f9ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Lola&backgroundColor=fdf4ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Charlie&backgroundColor=f0fdfa",
  "https://api.dicebear.com/9.x/micah/svg?seed=Bella&backgroundColor=ffedd5",
  "https://api.dicebear.com/9.x/micah/svg?seed=Lucy&backgroundColor=fae8ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Daisy&backgroundColor=fef2f2",
  "https://api.dicebear.com/9.x/micah/svg?seed=Milo&backgroundColor=f5f3ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Buddy&backgroundColor=eff6ff",
  "https://api.dicebear.com/9.x/micah/svg?seed=Oliver&backgroundColor=f0fdf4",
  "https://api.dicebear.com/9.x/micah/svg?seed=Chloe&backgroundColor=fff1f2",
  "https://api.dicebear.com/9.x/micah/svg?seed=Jack&backgroundColor=fffbeb"
];

const STREAK_COLORS = [
  { id: "emerald", hex: "bg-emerald-500", ring: "ring-emerald-500", text: "text-emerald-500", name: "Emerald Glow" },
  { id: "rose", hex: "bg-rose-500", ring: "ring-rose-500", text: "text-rose-500", name: "Rose Glow" },
  { id: "indigo", hex: "bg-indigo-500", ring: "ring-indigo-500", text: "text-indigo-500", name: "Indigo Glow" },
  { id: "amber", hex: "bg-amber-500", ring: "ring-amber-500", text: "text-amber-500", name: "Amber Glow" },
  { id: "purple", hex: "bg-purple-500", ring: "ring-purple-500", text: "text-purple-500", name: "Purple Glow" },
  { id: "cyan", hex: "bg-cyan-500", ring: "ring-cyan-500", text: "text-cyan-500", name: "Cyan Glow" },
  { id: "fuchsia", hex: "bg-fuchsia-500", ring: "ring-fuchsia-500", text: "text-fuchsia-500", name: "Fuchsia Glow" },
  { id: "orange", hex: "bg-orange-500", ring: "ring-orange-500", text: "text-orange-500", name: "Orange Glow" },
  { id: "blue", hex: "bg-blue-500", ring: "ring-blue-500", text: "text-blue-500", name: "Blue Glow" },
];

export default function SettingsPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [name, setName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [streakColor, setStreakColor] = useState("emerald");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    getCurrentUser().then((u) => {
      setUser(u);
      if (u) {
        setName(u.name);
        setAvatarUrl(u.avatar_url || AVATARS[0]);
        setStreakColor(u.streak_color || "emerald");
      }
      setLoading(false);
    });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload: any = { 
        name,
        avatar_url: avatarUrl,
        streak_color: streakColor
      };
      
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

  const currentRingClass = STREAK_COLORS.find(c => c.id === streakColor)?.ring || "ring-emerald-500";
  const currentHexClass = STREAK_COLORS.find(c => c.id === streakColor)?.hex || "bg-emerald-500";

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl">
        <h1 className="font-display text-3xl font-bold text-ink mb-8">Settings</h1>

        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <LoadingSpinner size={32} />
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-8">
            
            {error && (
              <div className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-sm">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
                {error}
              </div>
            )}
            
            {success && (
              <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 shadow-sm">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                {success}
              </div>
            )}

            {/* Customization Section */}
            <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="font-display text-xl font-semibold text-ink">Appearance & Avatar</h2>
                  <p className="text-sm text-ink-soft">Choose how you appear to others on your learning journey.</p>
                </div>
                {/* Preview Avatar */}
                <div className="flex flex-col items-center gap-1">
                  <div className={`relative h-16 w-16 rounded-full bg-canvas shadow-sm ring-4 ring-offset-2 ${currentRingClass}`}>
                    <img src={avatarUrl} alt="Avatar Preview" className="h-full w-full rounded-full object-cover" />
                    <div className={`absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-white ${STREAK_COLORS.find(c => c.id === streakColor)?.text || 'text-emerald-500'} shadow-sm`}>
                      <Flame className="h-3 w-3 fill-current" />
                    </div>
                  </div>
                  <span className="text-[10px] font-bold text-ink-soft uppercase tracking-wider mt-1">Preview</span>
                </div>
              </div>

              <div className="space-y-6">
                {/* Avatar Grid */}
                <div>
                  <label className="mb-3 block text-sm font-semibold text-ink">Select an Avatar</label>
                  <div className="grid grid-cols-5 gap-4 sm:grid-cols-10">
                    {AVATARS.map((url, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setAvatarUrl(url)}
                        className={`group relative aspect-square overflow-hidden rounded-2xl border-2 transition-all hover:scale-105 focus-visible:outline-none ${
                          avatarUrl === url ? "border-indigo-500 shadow-md ring-2 ring-indigo-100 ring-offset-1" : "border-transparent bg-canvas hover:border-ink/20"
                        }`}
                      >
                        <img src={url} alt={`Avatar ${i+1}`} className="h-full w-full object-cover p-1" />
                        {avatarUrl === url && (
                          <div className="absolute inset-0 bg-indigo-500/10 pointer-events-none" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Streak Color */}
                <div>
                  <label className="mb-3 block text-sm font-semibold text-ink">Daily Streak Color</label>
                  <div className="flex flex-wrap gap-3">
                    {STREAK_COLORS.map((color) => (
                      <button
                        key={color.id}
                        type="button"
                        onClick={() => setStreakColor(color.id)}
                        className={`flex items-center gap-2 rounded-full border-2 px-3 py-1.5 transition-all ${
                          streakColor === color.id ? "border-ink bg-white shadow-sm" : "border-transparent bg-canvas hover:bg-ink/5"
                        }`}
                      >
                        <div className={`h-4 w-4 rounded-full shadow-inner ${color.hex}`} />
                        <span className="text-xs font-medium text-ink">{color.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Profile & Security Section */}
            <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
              <h2 className="font-display text-xl font-semibold text-ink mb-6">Profile & Security</h2>
              
              <div className="space-y-6">
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
              </div>
            </div>
            
            {/* Save Button */}
            <div className="flex justify-end sticky bottom-6 pb-6">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-full bg-indigo-600 px-10 py-4 text-base font-semibold text-white shadow-xl shadow-indigo-600/20 transition hover:bg-indigo-700 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50"
              >
                {saving ? <LoadingSpinner size={18} /> : <Save className="h-5 w-5" />}
                Save All Settings
              </button>
            </div>
            
          </form>
        )}
      </div>
    </AppLayout>
  );
}
