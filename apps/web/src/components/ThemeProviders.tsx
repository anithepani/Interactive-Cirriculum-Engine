"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { ThemeProvider, createTheme, CssBaseline, PaletteMode } from "@mui/material";

interface ThemeModeContextValue {
  mode: PaletteMode;
  toggleColorMode: () => void;
}

const ThemeModeContext = createContext<ThemeModeContextValue>({
  mode: "light",
  toggleColorMode: () => {},
});

export function useThemeMode() {
  return useContext(ThemeModeContext);
}

export default function ThemeProviders({ children }: { children: React.ReactNode }) {
  // The app is a light-first Tailwind design (bg-canvas / text-ink). MUI's
  // CssBaseline was defaulting to DARK, which set body color to near-white
  // (#f8fafc) and made text on the light pages invisible until selected
  // (Issue 1). Default to light; users can still opt into dark via the stored
  // preference below.
  const [mode, setMode] = useState<PaletteMode>("light");

  const pathname = usePathname();
  const isLandingPage = pathname === "/";

  useEffect(() => {
    const storedMode = window.localStorage.getItem("ice-theme") as PaletteMode | null;
    const initial: PaletteMode =
      storedMode === "light" || storedMode === "dark" ? storedMode : "light";
    setMode(initial);
    
    if (isLandingPage) {
      document.documentElement.classList.remove("dark");
    } else {
      document.documentElement.classList.toggle("dark", initial === "dark");
    }
  }, [isLandingPage]);

  const colorMode = useMemo(
    () => ({
      mode: isLandingPage ? "light" : mode,
      toggleColorMode: () => {
        setMode((prevMode) => {
          const nextMode = prevMode === "light" ? "dark" : "light";
          window.localStorage.setItem("ice-theme", nextMode);
          if (!isLandingPage) {
            document.documentElement.classList.toggle("dark", nextMode === "dark");
          }
          return nextMode;
        });
      },
    }),
    [mode, isLandingPage]
  );

  const activeMode = isLandingPage ? "light" : mode;

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: activeMode,
          primary: {
            main: "#6366f1",
          },
          secondary: {
            main: "#22d3ee",
          },
          background: {
            default: activeMode === "dark" ? "#020617" : "#f8fafc",
            paper: activeMode === "dark" ? "rgba(15, 23, 42, 0.9)" : "#ffffff",
          },
          text: {
            primary: activeMode === "dark" ? "#f8fafc" : "#111827",
            secondary: activeMode === "dark" ? "#94a3b8" : "#4b5563",
          },
          divider: "rgba(148, 163, 184, 0.18)",
          action: {
            hover: "rgba(99, 102, 241, 0.08)",
          },
        },
        typography: {
          fontFamily: ["Inter", "system-ui", "sans-serif"].join(", "),
          h1: { fontWeight: 700 },
          h2: { fontWeight: 700 },
          h3: { fontWeight: 700 },
          h4: { fontWeight: 700 },
          h5: { fontWeight: 600 },
          h6: { fontWeight: 600 },
        },
        shape: {
          borderRadius: 20,
        },
      }),
    [activeMode]
  );

  return (
    <ThemeModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}
