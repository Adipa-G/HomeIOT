import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GaugeVisualization } from '../../../components/visualizations/GaugeVisualization';
import type { VisualizationConfig } from '../../../lib/visualization';

describe('GaugeVisualization', () => {
  const thresholdConfig: VisualizationConfig = {
    min: 0,
    max: 100,
    unit: 'C',
    decimals: 1,
    thresholds: [
      { value: 0, color: '#3b82f6' },
      { value: 10, color: '#f59e0b' },
      { value: 80, color: '#ef4444' },
    ],
  };

  it('renders value and range', () => {
    render(<GaugeVisualization value={50} config={{ min: 0, max: 100 }} />);
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('Range: 0 — 100')).toBeInTheDocument();
  });

  it('defaults to a 0–100 range when no config is provided', () => {
    render(<GaugeVisualization value={50} />);
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('Range: 0 — 100')).toBeInTheDocument();
  });

  it('formats value with decimals and unit', () => {
    render(<GaugeVisualization value={72.5} config={{ min: 0, max: 100, decimals: 1, unit: '°C' }} />);
    expect(screen.getByText('72.5 °C')).toBeInTheDocument();
  });

  it('renders without error when value is outside min/max', () => {
    const { container } = render(<GaugeVisualization value={150} config={{ min: 0, max: 100 }} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('formats values across all threshold bands', () => {
    const { rerender } = render(<GaugeVisualization value={5} config={thresholdConfig} />);
    expect(screen.getByText('5.0 C')).toBeInTheDocument();
    expect(screen.getByText('Range: 0 — 100')).toBeInTheDocument();

    rerender(<GaugeVisualization value={50} config={thresholdConfig} />);
    expect(screen.getByText('50.0 C')).toBeInTheDocument();

    rerender(<GaugeVisualization value={95} config={thresholdConfig} />);
    expect(screen.getByText('95.0 C')).toBeInTheDocument();
  });

  it('renders the needle and centre point', () => {
    const { container } = render(<GaugeVisualization value={85} config={thresholdConfig} />);
    expect(container.querySelectorAll('svg line').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('svg circle').length).toBeGreaterThan(0);
    expect(screen.getByText('85.0 C')).toBeInTheDocument();
  });
});
