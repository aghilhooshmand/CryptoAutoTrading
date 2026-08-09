import { Bot, LayoutDashboard, Wallet, type LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

import { PRIMARY_AREAS, type PrimaryAreaId } from "../config/primaryAreas";

const AREA_ICONS: Record<PrimaryAreaId, LucideIcon> = {
  dashboard: LayoutDashboard,
  "auto-trading": Bot,
  portfolio: Wallet,
};

export function PrimaryNav() {
  return (
    <nav className="primary-nav" aria-label="Primary">
      {PRIMARY_AREAS.map((area) => {
        const Icon = AREA_ICONS[area.id];
        return (
          <NavLink
            key={area.id}
            to={area.path}
            end={area.path === "/dashboard"}
          >
            <Icon
              className="primary-nav-icon"
              aria-hidden="true"
              focusable="false"
            />
            <span>{area.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
