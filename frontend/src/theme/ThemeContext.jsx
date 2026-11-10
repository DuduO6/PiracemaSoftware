import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "piracema-theme";
const ThemeContext = createContext(null);

function storedPreference() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return ["light", "dark", "system"].includes(value) ? value : "system";
  } catch {
    return "system";
  }
}

function systemTheme() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(preference) {
  const resolved = preference === "system" ? systemTheme() : preference;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePreference = preference;
  document.querySelector('meta[name="theme-color"]')?.setAttribute(
    "content",
    resolved === "dark" ? "#080F16" : "#F8FAFC",
  );
  return resolved;
}

export function ThemeProvider({ children }) {
  const [preference, setPreferenceState] = useState(storedPreference);
  const [resolvedTheme, setResolvedTheme] = useState(
    () => document.documentElement.dataset.theme || applyTheme(storedPreference()),
  );

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const update = () => setResolvedTheme(applyTheme(preference));
    update();
    if (preference === "system") media?.addEventListener?.("change", update);
    return () => media?.removeEventListener?.("change", update);
  }, [preference]);

  const setPreference = (value) => {
    if (!["light", "dark", "system"].includes(value)) return;
    try { localStorage.setItem(STORAGE_KEY, value); } catch { /* armazenamento pode estar indisponível */ }
    setPreferenceState(value);
  };

  const value = useMemo(
    () => ({ preference, resolvedTheme, setPreference }),
    [preference, resolvedTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme deve ser usado dentro de ThemeProvider");
  return context;
}
