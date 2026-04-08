import { useState, type ReactNode } from 'react';

interface Props {
  title: string;
  description?: string;
  confirmLabel?: string;
  onConfirm: () => void | Promise<void>;
  children: (open: () => void) => ReactNode;
}

export function ConfirmModal({ title, description, confirmLabel = 'Delete', onConfirm, children }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
    } finally {
      setLoading(false);
      setOpen(false);
    }
  };

  return (
    <>
      {children(() => setOpen(true))}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            {description && <p className="mt-2 text-sm text-gray-600">{description}</p>}
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setOpen(false)}
                className="rounded border border-gray-300 px-4 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading}
                className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                {loading ? 'Deleting…' : confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
