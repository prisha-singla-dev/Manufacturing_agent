export default function TableRenderer({ rows }: { rows: Record<string, any>[] }) {
  if (!rows || rows.length === 0) return <p className="text-sm text-[var(--color-slate)] mt-2">No rows.</p>;
  const columns = Object.keys(rows[0]);

  return (
    <div className="overflow-x-auto mt-2 border rounded-lg" style={{ borderColor: "var(--color-border)" }}>
      <table className="min-w-full text-sm">
        <thead style={{ background: "var(--color-bg)" }}>
          <tr>
            {columns.map((col) => (
              <th key={col} className="text-left px-3 py-2 font-medium text-[var(--color-steel)] whitespace-nowrap text-xs">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-[var(--color-surface)]">
          {rows.map((row, i) => (
            <tr key={i} className="border-t" style={{ borderColor: "var(--color-border)" }}>
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 whitespace-nowrap font-mono-data text-xs">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
