import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NumberDisplayVisualization } from '../../../components/visualizations/NumberDisplayVisualization';
import type { VisualizationConfig } from '../../../lib/visualization';

describe('NumberDisplayVisualization', () => {
  it('renders the number', () => {
    render(<NumberDisplayVisualization value={42} />);
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('formats number with decimals', () => {
    render(<NumberDisplayVisualization value={3.14159} config={{ decimals: 2 }} />);
    expect(screen.getByText('3.14')).toBeInTheDocument();
  });

  it('displays unit when provided', () => {
    render(<NumberDisplayVisualization value={25} config={{ unit: 'kWh' }} />);
    expect(screen.getByText('kWh')).toBeInTheDocument();
  });

  it('displays range when min/max provided', () => {
    render(<NumberDisplayVisualization value={50} config={{ min: 0, max: 100 }} />);
    expect(screen.getByText(/Range: 0 — 100/)).toBeInTheDocument();
  });

  it('omits range when only one of min/max is provided', () => {
    render(<NumberDisplayVisualization value={50} config={{ min: 0 }} />);
    expect(screen.queryByText(/Range:/)).not.toBeInTheDocument();
  });

  it('colours the value using the matching threshold', () => {
    render(
      <NumberDisplayVisualization
        value={75}
        config={{ thresholds: [{ value: 0, color: '#ef4444' }, { value: 50, color: '#f97316' }] }}
      />,
    );
    expect(screen.getByText('75')).toHaveStyle({ color: '#f97316' });
  });

  it('uses the default colour when the value is below every threshold', () => {
    render(
      <NumberDisplayVisualization
        value={25}
        config={{ thresholds: [{ value: 50, color: '#22c55e' }, { value: 75, color: '#ef4444' }] }}
      />,
    );
    expect(screen.getByText('25')).toHaveStyle({ color: '#3b82f6' });
  });

  it('formats values across all threshold bands', () => {
    const config: VisualizationConfig = {
      min: 0,
      max: 100,
      unit: 'W',
      decimals: 2,
      thresholds: [
        { value: 0, color: '#3b82f6' },
        { value: 500, color: '#f59e0b' },
        { value: 800, color: '#ef4444' },
      ],
    };

    const { rerender } = render(<NumberDisplayVisualization value={250} config={config} />);
    expect(screen.getByText('250.00')).toBeInTheDocument();
    expect(screen.getByText('W')).toBeInTheDocument();
    expect(screen.getByText(/Range: 0 — 100/)).toBeInTheDocument();

    rerender(<NumberDisplayVisualization value={600} config={config} />);
    expect(screen.getByText('600.00')).toBeInTheDocument();

    rerender(<NumberDisplayVisualization value={850} config={config} />);
    expect(screen.getByText('850.00')).toBeInTheDocument();
  });
});
