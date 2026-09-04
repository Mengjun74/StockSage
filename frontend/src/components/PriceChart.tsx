import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "../types/prices";
import { formatCompact, formatCurrency } from "../utils/format";

interface PriceChartProps {
  prices: PricePoint[];
}

export default function PriceChart({ prices }: PriceChartProps) {
  const data = prices.map((point) => ({
    date: new Date(point.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    close: point.close,
    volume: point.volume,
  }));

  return (
    <div className="chart-panel">
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="rgba(117, 130, 153, 0.2)" vertical={false} />
          <XAxis dataKey="date" tickLine={false} axisLine={false} minTickGap={32} />
          <YAxis
            yAxisId="price"
            orientation="right"
            tickFormatter={(value) => formatCurrency(Number(value))}
            tickLine={false}
            axisLine={false}
            width={78}
          />
          <YAxis yAxisId="volume" hide />
          <Tooltip
            formatter={(value, name) =>
              name === "volume" ? [formatCompact(Number(value)), "Volume"] : [formatCurrency(Number(value)), "Close"]
            }
          />
          <Bar yAxisId="volume" dataKey="volume" fill="rgba(79, 70, 229, 0.22)" barSize={8} />
          <Area
            yAxisId="price"
            type="monotone"
            dataKey="close"
            stroke="#0f766e"
            fill="rgba(15, 118, 110, 0.14)"
            strokeWidth={2}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
