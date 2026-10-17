import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBarVisualization } from '../../../components/visualizations/ProgressBarVisualization';
import type { VisualizationConfig } from '../../../lib/visualization';

describe('ProgressBarVisualization', () => {
  it('renders value and percentage', () => {
    render(<ProgressBarVisualization value={50} config={{ min: 0, max: 100 }} />);
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('formats value with decimals and unit', () => {
    render(<ProgressBarVisualization value={75.5} config={{ min: 0, max: 100, decimals: 1, unit: '%' }} />);
    expect(screen.getByText('75.5 %')).toBeInTheDocument();
  });

  it('displays min and max range', () => {
    render(<ProgressBarVisualization value={50} config={{ min: 0, max: 100 }} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('computes percentage relative to a custom range', () => {
    render(<ProgressBarVisualization value={15} config={{ min: 10, max: 20 }} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('clamps percentage to the configured range', () => {
    render(<ProgressBarVisualization value={150} config={{ min: 0, max: 100 }} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('formats values across all threshold bands', () => {
    const config: VisualizationConfig = {
      min: 0,
      max: 100,
      unit: '%',
      decimals: 1,
      thresholds: [
        { value: 0, color: '#3b82f6' },
        { value: 25, color: '#f59e0b' },
        { value: 75, color: '#ef4444' },
      ],
    };

    const { rerender } = render(<ProgressBarVisualization value={10} config={config} />);
    expect(screen.getByText('10.0 %')).toBeInTheDocument();
    expect(screen.getByText('10%')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();

    rerender(<ProgressBarVisualization value={50} config={config} />);
    expect(screen.getByText('50.0 %')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();

    rerender(<ProgressBarVisualization value={90} config={config} />);
    expect(screen.getByText('90.0 %')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
  });
});
