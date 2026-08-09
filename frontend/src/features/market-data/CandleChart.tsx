import { useEffect, useRef } from "react";
import { ColorType, createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";

import type { Candlestick as Candle, CandleInterval } from "../../services/marketDataApi";
import { ALLOWED_INTERVALS } from "./prefs";

interface Props {
  candles: Candle[];
  interval: CandleInterval;
  onIntervalChange: (interval: CandleInterval) => void;
  statusMessage?: string | null;
  loading?: boolean;
}

export function CandleChart({
  candles,
  interval,
  onIntervalChange,
  statusMessage,
  loading,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "#f7f4ef" },
        textColor: "#1c1917",
      },
      width: el.clientWidth || 320,
      height: 280,
      grid: {
        vertLines: { color: "#e7e5e4" },
        horzLines: { color: "#e7e5e4" },
      },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#15803d",
      downColor: "#b91c1c",
      borderVisible: false,
      wickUpColor: "#15803d",
      wickDownColor: "#b91c1c",
    });
    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth || 320,
        });
      }
    });
    observer.observe(el);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    if (loading || statusMessage || candles.length === 0) {
      seriesRef.current.setData([]);
      return;
    }
    const data = candles.map((c) => ({
      time: Math.floor(c.openTime / 1000) as never,
      open: Number(c.open),
      high: Number(c.high),
      low: Number(c.low),
      close: Number(c.close),
    }));
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [candles, loading, statusMessage]);

  const showChart = !loading && !statusMessage && candles.length > 0;

  return (
    <section className="candle-chart" aria-labelledby="candle-chart-title">
      <div className="candle-chart__header">
        <h2 id="candle-chart-title">Price history</h2>
        <div className="candle-intervals" role="group" aria-label="Candle interval">
          {ALLOWED_INTERVALS.map((value) => (
            <button
              key={value}
              type="button"
              className={
                value === interval
                  ? "candle-interval candle-interval--active"
                  : "candle-interval"
              }
              onClick={() => onIntervalChange(value)}
              aria-pressed={value === interval}
            >
              {value}
            </button>
          ))}
        </div>
      </div>
      {loading ? <p>Loading history…</p> : null}
      {statusMessage ? (
        <p className="market-error" role="status">
          {statusMessage}
        </p>
      ) : null}
      {!loading && !statusMessage && candles.length === 0 ? (
        <p>No candlestick data available.</p>
      ) : null}
      <div
        ref={containerRef}
        className="candle-chart__canvas"
        data-testid="candle-chart"
        hidden={!showChart}
      />
    </section>
  );
}
