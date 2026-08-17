import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchCandles,
  fetchPairs,
  fetchQuote,
  type CandleInterval,
  type CandlestickSeries,
  type MarketQuote,
  type TradingPair,
} from "../../services/marketDataApi";
import { isXtFormSymbol } from "../../services/productIdentity";
import { displayMarketStatus } from "./freshness";
import {
  loadFavorites,
  loadLastInterval,
  loadLastSymbol,
  resolveInitialSymbol,
  saveLastInterval,
  saveLastSymbol,
  toggleFavorite,
} from "./prefs";

interface MarketDataState {
  pairs: TradingPair[];
  selectedSymbol: string | null;
  interval: CandleInterval;
  favorites: string[];
  search: string;
  quote: MarketQuote | null;
  candles: CandlestickSeries | null;
  status: string;
  quoteError: string | null;
  historyError: string | null;
  pairsError: string | null;
  refreshing: boolean;
  historyLoading: boolean;
  setSearch: (value: string) => void;
  selectSymbol: (symbol: string) => void;
  setInterval: (interval: CandleInterval) => void;
  toggleFavoriteSymbol: (symbol: string) => void;
  refresh: () => void;
}

export function useMarketData(): MarketDataState {
  const [pairs, setPairs] = useState<TradingPair[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [interval, setIntervalState] = useState<CandleInterval>(loadLastInterval);
  const [favorites, setFavorites] = useState<string[]>(() => loadFavorites());
  const [search, setSearch] = useState("");
  const [quote, setQuote] = useState<MarketQuote | null>(null);
  const [candles, setCandles] = useState<CandlestickSeries | null>(null);
  const [status, setStatus] = useState("loading");
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [pairsError, setPairsError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [nowTick, setNowTick] = useState(() => Date.now());

  const requestIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setNowTick(Date.now()), 5_000);
    return () => window.clearInterval(id);
  }, []);

  const loadMarket = useCallback(async (symbol: string, nextInterval: CandleInterval) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = ++requestIdRef.current;

    setRefreshing(true);
    setHistoryLoading(true);
    setStatus("loading");
    setQuoteError(null);
    setHistoryError(null);
    // Invalidate prior OHLC immediately so a new pair/interval never keeps old candles visible.
    setCandles(null);

    try {
      const venue = isXtFormSymbol(symbol) ? "xt" : undefined;
      const [nextQuote, nextCandles] = await Promise.all([
        fetchQuote(symbol, controller.signal, venue),
        fetchCandles(symbol, nextInterval, controller.signal, venue),
      ]);
      if (requestId !== requestIdRef.current) return;
      setQuote(nextQuote);
      setCandles(nextCandles);
      setStatus(displayMarketStatus(nextQuote.status, nextQuote, Date.now()));
    } catch (error) {
      if (controller.signal.aborted || requestId !== requestIdRef.current) return;
      const err = error as Error & { code?: string; status?: number };
      const code = err.code ?? "error";
      // Never leave prior candles under a failed/newer selection.
      setCandles(null);
      if (code === "unsupported" || err.status === 404) {
        setStatus("unsupported");
        setQuote(null);
        setQuoteError(err.message || "Unsupported trading pair");
        setHistoryError(err.message || "Unsupported trading pair");
      } else {
        setStatus("error");
        setQuoteError(err.message || "Unable to load market quote");
        setHistoryError(err.message || "Unable to load history");
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setRefreshing(false);
        setHistoryLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetchPairs();
        if (cancelled) return;
        const available = response.pairs.map((p) => p.symbol);
        const supportedFavorites = loadFavorites().filter((f) =>
          available.some((a) => a.toUpperCase() === f.toUpperCase()),
        );
        setFavorites(supportedFavorites);
        setPairs(response.pairs);
        const initial = resolveInitialSymbol(available, loadLastSymbol());
        setSelectedSymbol(initial);
        if (initial) {
          saveLastSymbol(initial);
          await loadMarket(initial, loadLastInterval());
        } else {
          setStatus("unavailable");
          setPairsError("No tradable spot pairs available");
        }
      } catch (error) {
        if (cancelled) return;
        setStatus("unavailable");
        setPairsError(
          error instanceof Error ? error.message : "Unable to load pairs",
        );
      }
    })();
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [loadMarket]);

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol);
    saveLastSymbol(symbol);
    void loadMarket(symbol, interval);
  };

  const setInterval = (next: CandleInterval) => {
    setIntervalState(next);
    saveLastInterval(next);
    if (selectedSymbol) {
      void loadMarket(selectedSymbol, next);
    }
  };

  const toggleFavoriteSymbol = (symbol: string) => {
    setFavorites((current) => toggleFavorite(symbol, current));
  };

  const refresh = () => {
    if (selectedSymbol) {
      void loadMarket(selectedSymbol, interval);
    }
  };

  const effectiveStatus = displayMarketStatus(status, quote, nowTick);

  return {
    pairs,
    selectedSymbol,
    interval,
    favorites,
    search,
    quote,
    candles,
    status: effectiveStatus,
    quoteError: pairsError ?? quoteError,
    historyError,
    pairsError,
    refreshing,
    historyLoading,
    setSearch,
    selectSymbol,
    setInterval,
    toggleFavoriteSymbol,
    refresh,
  };
}
