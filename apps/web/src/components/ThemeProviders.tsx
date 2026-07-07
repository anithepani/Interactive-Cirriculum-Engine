"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { ThemeProvider, createTheme, CssBaseline, PaletteMode } from "@mui/material";

interface ThemeModeContextValue {
  mode: PaletteMode;
  toggleColorMode: () => void;
}

const ThemeModeContext = createContext<ThemeModeContextValue>({
  mode: "dark",
  toggleColorMode: () => {},
});

export function useThemeMode() {
  return useContext(ThemeModeContext);
}

export default function ThemeProviders({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<PaletteMode>("dark");

  useEffect(() => {
    const storedMode = window.localStorage.getItem("ice-theme") as PaletteMode | null;
    if (storedMode === "light" || storedMode === "dark") {
      setMode(storedMode);
      return;
    }
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setMode(prefersDark ? "dark" : "light");
  }, []);

  const colorMode = useMemo(
    () => ({
      mode,
      toggleColorMode: () => {
        setMode((prevMode) => {
          const nextMode = prevMode === "light" ? "dark" : "light";
          window.localStorage.setItem("ice-theme", nextMode);
          return nextMode;
        });
      },
    }),
    [mode]
  );

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: {
            main: "#6366f1",
          },
          secondary: {
            main: "#22d3ee",
          },
          background: {
            default: mode === "dark" ? "#020617" : "#f8fafc",
            paper: mode === "dark" ? "rgba(15, 23, 42, 0.9)" : "#ffffff",
          },
          text: {
            primary: mode === "dark" ? "#f8fafc" : "#111827",
            secondary: mode === "dark" ? "#94a3b8" : "#4b5563",
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
    [mode]
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
