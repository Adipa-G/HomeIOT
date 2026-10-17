import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TextDisplayVisualization } from '../../../components/visualizations/TextDisplayVisualization';
import type { VisualizationConfig } from '../../../lib/visualization';

describe('TextDisplayVisualization', () => {
  it('renders a numeric string', () => {
    render(<TextDisplayVisualization value="123" />);
    expect(screen.getByText('123')).toBeInTheDocument();
  });

  it('renders a number', () => {
    render(<TextDisplayVisualization value={42} />);
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('formats numeric string with decimals', () => {
    render(<TextDisplayVisualization value="45.6789" config={{ decimals: 2 }} />);
    expect(screen.getByText('45.68')).toBeInTheDocument();
  });

  it('renders non-numeric strings as text', () => {
    render(<TextDisplayVisualization value="online" />);
    expect(screen.getByText('online')).toBeInTheDocument();
  });

  it('renders a dash for null', () => {
    render(<TextDisplayVisualization value={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('colours numeric values using configured thresholds', () => {
    render(
      <TextDisplayVisualization
        value={70}
        config={{ thresholds: [{ value: 25, color: '#10b981' }, { value: 60, color: '#fbbf24' }, { value: 85, color: '#ef4444' }] }}
      />,
    );
    expect(screen.getByText('70')).toHaveStyle({ color: '#fbbf24' });
  });

  it('does not colour non-numeric values', () => {
    render(<TextDisplayVisualization value="online" config={{ thresholds: [{ value: 0, color: '#ef4444' }] }} />);
    expect(screen.getByText('online').getAttribute('style')).toBeNull();
  });

  it('formats numeric strings with decimals and unit', () => {
    const config: VisualizationConfig = { decimals: 2, unit: 'kB/s' };

    const { rerender } = render(<TextDisplayVisualization value="123.456" config={config} />);
    expect(screen.getByText('123.46 kB/s')).toBeInTheDocument();

    rerender(<TextDisplayVisualization value="78.901" config={config} />);
    expect(screen.getByText('78.90 kB/s')).toBeInTheDocument();
  });
});
