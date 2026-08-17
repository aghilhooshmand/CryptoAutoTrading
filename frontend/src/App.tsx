import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { resolveRootToDashboard } from "./config/primaryAreas";
import { AutoTradingPage } from "./pages/AutoTradingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { RealAccountPage } from "./pages/RealAccountPage";
import { RealXtAccountPage } from "./pages/RealXtAccountPage";
import { SimulationSessionDetailPage } from "./features/simulation/SimulationSessionDetailPage";

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
        <Route
          path="/auto-trading/simulation/:sessionId"
          element={<SimulationSessionDetailPage />}
        />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/portfolio/real-account" element={<RealAccountPage />} />
        <Route path="/portfolio/real-xt" element={<RealXtAccountPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
