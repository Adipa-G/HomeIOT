interface Props {
  text: string;
  variant?: 'green' | 'yellow' | 'red' | 'gray' | 'blue';
}

const colors: Record<string, string> = {
  green: 'bg-green-100 text-green-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
  gray: 'bg-gray-100 text-gray-700',
  blue: 'bg-blue-100 text-blue-800',
};

export function StatusBadge({ text, variant = 'gray' }: Props) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colors[variant]}`}>
      {text}
    </span>
  );
}
