import { Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

const POPULAR_TICKERS = ["NVDA", "AAPL", "MSFT", "META", "AMD", "TSLA", "GOOGL", "AMZN"];

export default function App() {
  const [ticker, setTicker] = useState("NVDA");
  const navigate = useNavigate();

  function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = ticker.trim().toUpperCase();
    if (normalized) {
      navigate(`/stocks/${normalized}`);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <div className="masthead">
          <div>
            <p className="eyebrow">Stock AI</p>
            <h1>Multi-source market analysis</h1>
          </div>
          <form className="ticker-form" onSubmit={submit}>
            <input
              aria-label="Ticker"
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
              placeholder="NVDA"
            />
            <button type="submit" title="Analyze ticker">
              <Search size={18} />
              <span>Analyze</span>
            </button>
          </form>
        </div>
        <div className="ticker-row">
          {POPULAR_TICKERS.map((item) => (
            <button key={item} type="button" onClick={() => navigate(`/stocks/${item}`)}>
              {item}
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
