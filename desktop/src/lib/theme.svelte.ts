// The window's colours: as the system's, or dark or light by the player's choice (kept per
// machine in the web view's storage, as it concerns only this window).

export type ThemeChoice = "system" | "dark" | "light";
const KEY = "rnw.theme";

function stored(): ThemeChoice {
  try {
    const value = localStorage.getItem(KEY);
    return value === "dark" || value === "light" ? value : "system";
  } catch {
    return "system";
  }
}

export const theme = $state<{ choice: ThemeChoice }>({ choice: stored() });

export function applyTheme(): void {
  const root = document.documentElement;
  if (theme.choice === "system") delete root.dataset.theme;
  else root.dataset.theme = theme.choice;
}

export function setTheme(choice: ThemeChoice): void {
  theme.choice = choice;
  try {
    localStorage.setItem(KEY, choice);
  } catch {
    // Storage is a convenience.
  }
  applyTheme();
}
