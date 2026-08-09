export type PrimaryAreaId = "dashboard" | "auto-trading" | "portfolio";

export type PrimaryArea = {
  id: PrimaryAreaId;
  label: string;
  path: `/${PrimaryAreaId}` | "/dashboard" | "/auto-trading" | "/portfolio";
  isDefaultEntry: boolean;
};

export const PRIMARY_AREAS: readonly PrimaryArea[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    path: "/dashboard",
    isDefaultEntry: true,
  },
  {
    id: "auto-trading",
    label: "Auto Trading",
    path: "/auto-trading",
    isDefaultEntry: false,
  },
  {
    id: "portfolio",
    label: "Portfolio",
    path: "/portfolio",
    isDefaultEntry: false,
  },
] as const;

export const DEFAULT_ENTRY_PATH = "/dashboard";

/** Resolve application root to the canonical Dashboard route. */
export function resolveRootToDashboard(): string {
  return DEFAULT_ENTRY_PATH;
}

export function isPrimaryAreaPath(pathname: string): boolean {
  return PRIMARY_AREAS.some((area) => area.path === pathname);
}
