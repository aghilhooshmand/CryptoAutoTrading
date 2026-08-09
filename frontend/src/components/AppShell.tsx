import { Outlet } from "react-router-dom";

import { PrimaryNav } from "./PrimaryNav";

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">CryptoAutoTrading</div>
        <PrimaryNav />
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
