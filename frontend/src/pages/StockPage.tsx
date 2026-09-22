import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { describeApiError, fetchPrices, runAnalysis } from "../api/client";
import AnalysisPanel from "../components/AnalysisPanel";
import PriceChart from "../components/PriceChart";
import type { AnalysisResponse } from "../types/analysis";
import type { PriceResponse, SupportedPeriod } from "../types/prices";
import { formatCompact, formatCurrency, formatPercent } from "../utils/format";

const PERIODS: SupportedPeriod[] = ["1m", "3m", "6m", "1y", "5y"];

export default function StockPage() {
  const params = useParams();
  const ticker = (params.ticker ?? "NVDA").toUpperCase();
  const [period, setPeriod] = useState<SupportedPeriod>("6m");
  const [data, setData] = useState<PriceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => {
    setAnalysis(null);
    setAnalysisError(null);
  }, [ticker]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchPrices(ticker, "1d", period)
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(describeApiError(reason));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker, period]);

  // Not run automatically: it spends model calls and records a row to be scored later.
  function analyse() {
    setAnalysing(true);
    setAnalysisError(null);
    runAnalysis(ticker)
      .then(setAnalysis)
      .catch((reason: unknown) => setAnalysisError(describeApiError(reason)))
      .finally(() => setAnalysing(false));
  }

  return (
    <main className="app-shell">
      <section className="workspace dense">
        <header className="page-header">
          <Link to="/" className="icon-link" title="Back">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <p className="eyebrow">Market data</p>
            <h1>{ticker}</h1>
          </div>
          <div className="period-tabs">
            {PERIODS.map((item) => (
              <button key={item} className={item === period ? "active" : ""} type="button" onClick={() => setPeriod(item)}>
                {item.toUpperCase()}
              </button>
            ))}
          </div>
        </header>

        {loading && (
          <div className="state-row">
            <RefreshCw size={18} className="spin" />
            <span>Collecting market data</span>
          </div>
        )}

        {error && (
          <div className="state-row error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {data && !loading && (
          <>
            <section className="metrics-grid">
              <Metric label="Current Price" value={formatCurrency(data.snapshot?.current_price)} />
              <Metric label="1D Return" value={formatPercent(data.snapshot?.return_1d)} />
              <Metric label="5D Return" value={formatPercent(data.snapshot?.return_5d)} />
              <Metric label="20D Return" value={formatPercent(data.snapshot?.return_20d)} />
              <Metric label="Volume" value={formatCompact(data.snapshot?.volume)} />
              <Metric label="RSI 14" value={data.snapshot?.rsi_14?.toFixed(1) ?? "-"} />
            </section>

            <PriceChart prices={data.prices} />

            <AnalysisPanel
              analysis={analysis}
              loading={analysing}
              error={analysisError}
              onRun={analyse}
            />

            <section className="detail-grid">
              <div className="detail-panel">
                <h2>Price Structure</h2>
                <dl>
                  <Detail label="Trend" value={data.price_structure?.trend ?? "-"} />
                  <Detail label="Volume" value={data.price_structure?.volume_state ?? "-"} />
                  <Detail label="Setup" value={data.price_structure?.breakout_state ?? "-"} />
                  <Detail label="Support" value={formatLevels(data.price_structure?.support_levels)} />
                  <Detail label="Resistance" value={formatLevels(data.price_structure?.resistance_levels)} />
                </dl>
              </div>
              <div className="detail-panel">
                <h2>Data Source</h2>
                <dl>
                  <Detail label="Provider" value={data.provider} />
                  <Detail label="Available" value={data.data_quality.providers_available.join(", ") || "-"} />
                  <Detail label="Failed" value={data.data_quality.providers_failed.join(", ") || "-"} />
                  <Detail label="Bars" value={data.prices.length.toString()} />
                </dl>
              </div>
            </section>
          </>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function formatLevels(levels: number[] | undefined): string {
  if (!levels?.length) return "-";
  return levels.map((level) => formatCurrency(level)).join(", ");
}
