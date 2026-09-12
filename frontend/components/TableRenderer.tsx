export default function TableRenderer({ rows }: { rows: Record<string, any>[] }) {
  if (!rows || rows.length === 0) return <p className="text-sm text-gray-500">No rows.</p>;
  const columns = Object.keys(rows[0]);

  return (
    <div className="overflow-x-auto mt-2 border rounded-lg">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-100">
          <tr>
            {columns.map((col) => (
              <th key={col} className="text-left px-3 py-2 font-medium text-gray-700 whitespace-nowrap">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 whitespace-nowrap">
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
