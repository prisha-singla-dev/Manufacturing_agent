"use client";

import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const COLORS = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#0891b2", "#ca8a04"];

type ChartSpec = { chart_type: string; x_key: string; y_key: string; data: Record<string, any>[] };

export default function ChartRenderer({ chart }: { chart: ChartSpec }) {
  const { chart_type, x_key, y_key, data } = chart;

  return (
    <div className="mt-2 border rounded-lg p-2 bg-white" style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        {chart_type === "line" ? (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={x_key} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey={y_key} stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        ) : chart_type === "pie" ? (
          <PieChart>
            <Pie data={data} dataKey={y_key} nameKey={x_key} outerRadius={110} label>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={x_key} tick={{ fontSize: 10 }} interval={0} angle={-30} textAnchor="end" height={80} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey={y_key} fill="#2563eb" />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
