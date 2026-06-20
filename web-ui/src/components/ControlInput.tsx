import React from 'react';

interface ControlInputProps {
  label?: string;
  controlType?: string | null;
  controlOptions?: unknown | null;
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

export const ControlInput: React.FC<ControlInputProps> = ({
  label,
  controlType,
  controlOptions,
  value,
  onChange,
  disabled = false,
}) => {
  if (!controlType) {
    return (
      <div className="w-full">
        {label && <label className="mb-1 block text-xs text-gray-600">{label}</label>}
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
        />
      </div>
    );
  }

  if (controlType === 'dropdown') {
    let options: string[] = [];
    try {
      if (Array.isArray(controlOptions)) {
        options = controlOptions as string[];
      } else if (controlOptions && typeof controlOptions === 'object') {
        options = Object.values(controlOptions as Record<string, unknown>).filter((v): v is string => typeof v === 'string');
      }
    } catch {
      // Fallback to text input if options are invalid
    }

    if (options.length === 0) {
      return (
        <div className="w-full">
          {label && <label className="mb-1 block text-xs text-gray-600">{label}</label>}
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
          />
        </div>
      );
    }

    return (
      <div className="w-full">
        {label && <label className="mb-1 block text-xs text-gray-600">{label}</label>}
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
        >
          <option value="">— select —</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (controlType === 'toggle') {
    return (
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={value === 'true' || value === '1' || value === 'yes'}
          onChange={(e) => onChange(e.target.checked ? 'true' : 'false')}
          disabled={disabled}
          className="rounded border-gray-300 disabled:opacity-50"
        />
        {label && <label className="text-sm text-gray-600">{label}</label>}
      </div>
    );
  }

  // Default to text input for unknown types
  return (
    <div className="w-full">
      {label && <label className="mb-1 block text-xs text-gray-600">{label}</label>}
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
      />
    </div>
  );
};
