import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { resolveRootToDashboard } from "./config/primaryAreas";
import { AutoTradingPage } from "./pages/AutoTradingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PortfolioPage } from "./pages/PortfolioPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          path="/"
          element={<Navigate to={resolveRootToDashboard()} replace />}
        />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/auto-trading" element={<AutoTradingPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
