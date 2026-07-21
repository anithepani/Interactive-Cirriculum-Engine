"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { authFetch } from "@/lib/auth";
import Toast from "@/components/Toast";

export type AppNotification = {
  id: string | number;
  title?: string;
  message?: string;
  read?: boolean;
  is_read?: boolean;
  created_at?: string;
  payload?: { curriculum_id?: string | number; [k: string]: unknown };
  [k: string]: unknown;
};

type NotificationsContextValue = {
  notifications: AppNotification[];
  unreadCount: number;
  markRead: (id: string | number) => void;
  loading: boolean;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(
  null
);

export function useNotifications(): NotificationsContextValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) {
    return {
      notifications: [],
      unreadCount: 0,
      markRead: () => {},
      loading: false,
    };
  }
  return ctx;
}

const isUnread = (n: AppNotification) =>
  (n.read ?? n.is_read) !== true;

const extractList = (data: unknown): AppNotification[] => {
  if (Array.isArray(data)) return data as AppNotification[];
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (Array.isArray(obj.items)) return obj.items as AppNotification[];
    if (Array.isArray(obj.notifications))
      return obj.notifications as AppNotification[];
  }
  return [];
};

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [toastSeverity, setToastSeverity] = useState<
    "success" | "error" | "info" | "warning"
  >("info");

  const showToast = (
    message: string,
    severity: "success" | "error" | "info" | "warning"
  ) => {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  };

  useEffect(() => {
    let cancelled = false;
    let es: EventSource | null = null;

    const init = async () => {
      // 1. Initial fetch of existing notifications
      try {
        const res = await authFetch("/api/v1/notifications", {
          method: "GET",
        });
        if (!res.ok) {
          if (!cancelled) setLoading(false);
          return;
        }
        const data = await res.json();
        if (cancelled) return;
        setNotifications(extractList(data));
        setLoading(false);
      } catch {
        if (!cancelled) setLoading(false);
        return;
      }

      // 2. Fetch SSE token, then open stream
      try {
        const tokenRes = await authFetch("/api/v1/events/token", {
          method: "POST",
        });
        if (!tokenRes.ok) return;
        const tokenData = await tokenRes.json();
        const token =
          tokenData.token ||
          tokenData.access_token ||
          tokenData.events_token;
        if (!token || cancelled) return;

        es = new EventSource(
          `/api/v1/events/stream?token=${encodeURIComponent(token)}`
        );

        es.onmessage = (ev) => {
          try {
            const parsed = JSON.parse(ev.data);
            const n: AppNotification =
              parsed.data ?? parsed.notification ?? parsed;
            if (!n || n.id === undefined) return;
            setNotifications((prev) =>
              prev.some((x) => x.id === n.id) ? prev : [n, ...prev]
            );
            showToast(n.message || n.title || "New notification", "info");
          } catch {
            /* ignore malformed payloads */
          }
        };

        es.onerror = () => {
          // EventSource auto-reconnects; nothing to do here
        };
      } catch {
        /* SSE is best-effort */
      }
    };

    init();

    return () => {
      cancelled = true;
      if (es) es.close();
    };
  }, []);

  const markRead = (id: string | number) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, read: true, is_read: true } : n
      )
    );
    authFetch(`/api/v1/notifications/${id}/read`, {
      method: "PATCH",
    }).catch(() => {});
  };

  const unreadCount = notifications.filter(isUnread).length;

  return (
    <NotificationsContext.Provider
      value={{ notifications, unreadCount, markRead, loading }}
    >
      {children}
      <Toast
        open={toastOpen}
        message={toastMessage}
        severity={toastSeverity}
        onClose={() => setToastOpen(false)}
      />
    </NotificationsContext.Provider>
  );
}
