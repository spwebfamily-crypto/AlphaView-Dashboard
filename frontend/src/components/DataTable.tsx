import type { ReactNode } from "react";

type DataTableProps = {
  columns: string[];
  rows: ReactNode[][];
  caption?: string;
  footnote?: string;
};

export function DataTable({ columns, rows, caption, footnote }: DataTableProps) {
  if (rows.length === 0) {
    return <div className="empty-state">No rows available.</div>;
  }

  return (
    <div className="table-wrap">
      {caption ? (
        <div className="table-caption">
          <strong>{caption}</strong>
          <small>{rows.length} rows</small>
        </div>
      ) : null}
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`cell-${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {footnote ? <div className="table-footnote">{footnote}</div> : null}
    </div>
  );
}
