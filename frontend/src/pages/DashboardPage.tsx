import { CandleChart } from "../features/market-data/CandleChart";
import { MarketQuotePanel } from "../features/market-data/MarketQuotePanel";
import { PairSelector } from "../features/market-data/PairSelector";
import { useMarketData } from "../features/market-data/useMarketData";

export function DashboardPage() {
  const market = useMarketData();

  return (
    <section className="page dashboard-page" aria-labelledby="dashboard-title">
      <h1 id="dashboard-title">Dashboard</h1>
      <p className="note">
        Public XT Spot market data (USDT pairs). Manual refresh updates the
        selected pair. This screen does not place trades or show portfolio
        balances.
      </p>

      <div className="dashboard-market" data-testid="dashboard-market">
        <PairSelector
          pairs={market.pairs}
          selectedSymbol={market.selectedSymbol}
          favorites={market.favorites}
          search={market.search}
          onSearchChange={market.setSearch}
          onSelect={market.selectSymbol}
          onToggleFavorite={market.toggleFavoriteSymbol}
        />

        <div className="dashboard-market__main">
          <MarketQuotePanel
            quote={market.quote}
            status={market.status}
            lastError={market.quoteError}
            onRefresh={market.refresh}
            refreshing={market.refreshing}
          />
          <CandleChart
            candles={market.candles?.candles ?? []}
            interval={market.interval}
            onIntervalChange={market.setInterval}
            loading={market.historyLoading}
            statusMessage={market.historyError}
          />
        </div>
      </div>
    </section>
  );
}
