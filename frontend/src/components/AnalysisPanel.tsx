import { AlertTriangle, Scale, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import type { AnalysisCase, AnalysisLevel, AnalysisResponse } from "../types/analysis";
import { formatCurrency } from "../utils/format";

interface AnalysisPanelProps {
  analysis: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
  onRun: () => void;
}

const ACTION_LABELS: Record<string, string> = {
  buy: "Buy",
  accumulate_on_pullback: "Accumulate on pullback",
  hold: "Hold",
  reduce: "Reduce",
  avoid: "Avoid",
};

export default function AnalysisPanel({ analysis, loading, error, onRun }: AnalysisPanelProps) {
  return (
    <section className="analysis">
      <header className="analysis-header">
        <div>
          <p className="eyebrow">Agent analysis</p>
          <h2>Bull, bear and judge</h2>
        </div>
        <button type="button" className="run-analysis" onClick={onRun} disabled={loading}>
          <Sparkles size={16} />
          <span>{loading ? "Running three agents…" : analysis ? "Run again" : "Run analysis"}</span>
        </button>
      </header>

      {error && (
        <div className="state-row error">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {!analysis && !loading && !error && (
        <p className="analysis-empty">
          Two agents argue the same evidence and a third decides. Prices come from the chart, never
          from the model.
        </p>
      )}

      {analysis && (
        <>
          <div className="verdict">
            <div className="verdict-call">
              <span className={`pill action-${analysis.action}`}>
                {ACTION_LABELS[analysis.action] ?? analysis.action}
              </span>
              <span className={`pill confidence-${analysis.confidence}`}>
                {analysis.confidence} confidence
              </span>
              <span className="pill muted">{analysis.horizon_days}-day horizon</span>
              {analysis.risk_reward !== null && (
                <span className="pill muted">{analysis.risk_reward.toFixed(2)}:1 reward/risk</span>
              )}
            </div>
            <div className="level-grid">
              <Level kind="Entry" level={analysis.entry} />
              <Level kind="Target" level={analysis.target} />
              <Level kind="Stop" level={analysis.stop} />
            </div>
          </div>

          <div className="cases">
            <CaseCard side="bull" body={analysis.bull} />
            <CaseCard side="bear" body={analysis.bear} />
          </div>

          <div className="detail-panel">
            <h3>Why</h3>
            <p>{analysis.reasoning}</p>
            <h3>
              <Scale size={15} /> Where the two disagreed
            </h3>
            <p>{analysis.disagreement}</p>
            <h3>What would mean this is wrong</h3>
            <p>{analysis.invalidation}</p>
            <p className="analysis-meta">
              {analysis.model} · {analysis.articles_considered} articles · priced at{" "}
              {formatCurrency(analysis.price_at_analysis)} ·{" "}
              {new Date(analysis.created_at).toLocaleString()}
            </p>
            <p className="disclaimer">{analysis.disclaimer}</p>
          </div>
        </>
      )}
    </section>
  );
}

function Level({ kind, level }: { kind: string; level: AnalysisLevel }) {
  return (
    <div className="level-card">
      <span>{kind}</span>
      <strong>{formatCurrency(level.price)}</strong>
      <small>{level.basis}</small>
    </div>
  );
}

function CaseCard({ side, body }: { side: "bull" | "bear"; body: AnalysisCase }) {
  const Icon = side === "bull" ? TrendingUp : TrendingDown;
  return (
    <div className={`case-card ${side}`}>
      <header>
        <Icon size={16} />
        <span>{side === "bull" ? "The case for" : "The case against"}</span>
        <span className={`pill strength-${body.case_strength}`}>{body.case_strength}</span>
      </header>
      <p>{body.summary}</p>
      <ul>
        {body.points.map((point, index) => (
          <li key={index}>
            <strong>{point.claim}</strong>
            <em>{point.evidence}</em>
          </li>
        ))}
      </ul>
      {body.filings_assessment && (
        <p className="counterpoint">
          <strong>On the SEC filings:</strong> {body.filings_assessment}
        </p>
      )}
      <p className="counterpoint">
        <strong>Strongest point against:</strong> {body.strongest_counterpoint}
      </p>
    </div>
  );
}
