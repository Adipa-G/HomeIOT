interface Props {
  offset: number;
  limit: number;
  total: number;
  onChange: (offset: number) => void;
}

export function Pagination({ offset, limit, total, onChange }: Props) {
  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="flex items-center justify-between border-t border-gray-200 px-1 pt-3 text-sm text-gray-600">
      <span>
        {total === 0
          ? 'No results'
          : `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
      </span>
      <div className="flex gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onChange(offset - limit)}
          className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
        >
          Prev
        </button>
        <button
          disabled={page >= totalPages}
          onClick={() => onChange(offset + limit)}
          className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
