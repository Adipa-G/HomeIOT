import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TimeSeriesChart } from '../../../components/visualizations/TimeSeriesChart';
import type { VisualizationConfig } from '../../../lib/visualization';
import { bucketSeries, samplesSeries } from '../../chartSeriesFixtures';

const tickLabels = () => screen.getAllByTestId('chart-y-tick').map((t) => t.textContent);
const currentValue = () => screen.getByTestId('chart-current-value').textContent;
const svgHeight = (container: HTMLElement) => container.querySelector('svg')?.getAttribute('height');
const titlesOf = (container: HTMLElement, selector: string) =>
  Array.from(container.querySelectorAll(`${selector} > title`)).map((t) => t.textContent ?? '');

const dayOfMinutes = samplesSeries(Array.from({ length: 1440 }, (_, i) => i % 60));

describe('TimeSeriesChart', () => {
  describe('common', () => {
    it('renders a shorter chart in compact mode', () => {
      const { container: normal } = render(<TimeSeriesChart kind="bar" value={1} series={samplesSeries([1, 2])} />);
      const { container: compact } = render(<TimeSeriesChart kind="bar" value={1} series={samplesSeries([1, 2])} compact />);
      expect(Number(svgHeight(compact))).toBeLessThan(Number(svgHeight(normal)));
    });

    it('labels the y-axis with ticks across the configured min/max', () => {
      render(<TimeSeriesChart kind="bar" value={50} config={{ min: 0, max: 100 }} />);
      expect(tickLabels()).toEqual(['0', '25', '50', '75', '100']);
    });

    it('shows first and last time labels for a series', () => {
      render(<TimeSeriesChart kind="line" value={3} series={samplesSeries([1, 2, 3])} />);
      expect(screen.getAllByTestId('chart-x-label')).toHaveLength(2);
    });

    it('omits x-axis time labels when there is no series', () => {
      render(<TimeSeriesChart kind="bar" value={2} />);
      expect(screen.queryByTestId('chart-x-label')).not.toBeInTheDocument();
    });

    it('falls back to the current value when every slot is empty', () => {
      render(<TimeSeriesChart kind="bar" value={9} series={samplesSeries([null, null])} />);
      expect(screen.getAllByTestId('chart-bar')).toHaveLength(1);
      expect(screen.getByText('current')).toBeInTheDocument();
    });

    it('lays out the chart as a full-width flex column', () => {
      const { container } = render(<TimeSeriesChart kind="line" value={50} config={{ min: 0, max: 100 }} />);
      expect(container.querySelector('.flex.flex-col.gap-2.w-full')).toBeInTheDocument();
    });
  });

  describe('fitting to width', () => {
    it('averages a day of samples into as many bars as fit', () => {
      render(<TimeSeriesChart kind="bar" value={1} series={dayOfMinutes} />);
      const bars = screen.getAllByTestId('chart-bar');
      expect(bars.length).toBeGreaterThan(10);
      expect(bars.length).toBeLessThanOrEqual(Math.floor((300 - 50) / 8));
      expect(screen.getByText(new RegExp(`^${bars.length} bars · 1440 samples$`))).toBeInTheDocument();
    });

    it('allows more line points than bars in the same width', () => {
      const { unmount } = render(<TimeSeriesChart kind="bar" value={1} series={dayOfMinutes} />);
      const bars = screen.getAllByTestId('chart-bar').length;
      unmount();
      render(<TimeSeriesChart kind="line" value={1} series={dayOfMinutes} />);
      expect(screen.getAllByTestId('chart-point').length).toBeGreaterThan(bars);
    });

    it('keeps every slot when the series already fits', () => {
      render(<TimeSeriesChart kind="bar" value={5} series={samplesSeries([1, 2, 3, 4, 5])} />);
      expect(screen.getAllByTestId('chart-bar')).toHaveLength(5);
      expect(screen.getByText('5 points')).toBeInTheDocument();
    });
  });

  describe('bar', () => {
    it('shows the current value as a single bar when there is no series', () => {
      render(<TimeSeriesChart kind="bar" value={50} config={{ min: 0, max: 100 }} />);
      expect(currentValue()).toBe('50');
      expect(screen.getAllByTestId('chart-bar')).toHaveLength(1);
    });

    it('formats the current value with unit', () => {
      render(<TimeSeriesChart kind="bar" value={75} config={{ min: 0, max: 100, unit: '%' }} />);
      expect(currentValue()).toBe('75 %');
    });

    it('leaves gaps for empty slots', () => {
      render(<TimeSeriesChart kind="bar" value={50} series={samplesSeries([10, null, 30, null, 50])} config={{ min: 0, max: 100 }} />);
      expect(screen.getAllByTestId('chart-bar')).toHaveLength(3);
    });

    it('includes zero on an auto-scaled y-axis', () => {
      render(<TimeSeriesChart kind="bar" value={22} series={samplesSeries([20, 22])} />);
      expect(tickLabels()[0]).toBe('0');
    });

    it('colours each bar by its own threshold', () => {
      const thresholds = [
        { value: 0, color: '#00ff00' },
        { value: 50, color: '#ff0000' },
      ];
      render(<TimeSeriesChart kind="bar" value={80} series={samplesSeries([10, 80])} config={{ min: 0, max: 100, thresholds }} />);
      expect(screen.getAllByTestId('chart-bar').map((b) => b.getAttribute('fill'))).toEqual(['#00ff00', '#ff0000']);
    });

    it('uses barColor when no thresholds are configured', () => {
      render(<TimeSeriesChart kind="bar" value={2} series={samplesSeries([1, 2])} config={{ barColor: '#123456' }} />);
      screen.getAllByTestId('chart-bar').forEach((b) => expect(b.getAttribute('fill')).toBe('#123456'));
    });

    it('draws min–max whiskers only for averaged slots', () => {
      const { container, unmount } = render(<TimeSeriesChart kind="bar" value={2} series={samplesSeries([1, 2])} />);
      expect(container.querySelector('[data-testid="chart-range"]')).toBeNull();
      unmount();

      render(
        <TimeSeriesChart
          kind="bar"
          value={5}
          series={bucketSeries([
            { avg: 4, min: 2, max: 6, count: 15 },
            { avg: 5, min: 5, max: 5, count: 15 },
          ])}
        />,
      );
      expect(screen.getAllByTestId('chart-range')).toHaveLength(1);
      expect(screen.getByText('2 bars · 30 samples')).toBeInTheDocument();
    });

    it('describes averaged slots in the tooltip', () => {
      const { container } = render(
        <TimeSeriesChart kind="bar" value={4} series={bucketSeries([{ avg: 4, min: 2, max: 6, count: 15 }])} config={{ unit: 'W' }} />,
      );
      expect(titlesOf(container, 'rect')[0]).toMatch(/^avg 4 W \(min 2 W \/ max 6 W, 15 samples\) · .+ – .+$/);
    });

    it('formats the current value with decimals and unit', () => {
      const config: VisualizationConfig = { min: 0, max: 100, unit: 'bpm', decimals: 1 };

      const { rerender } = render(<TimeSeriesChart kind="bar" value={75.5} series={samplesSeries([60, 68, 72, 74, 75.5])} config={config} />);
      expect(currentValue()).toBe('75.5 bpm');

      rerender(<TimeSeriesChart kind="bar" value={110} series={samplesSeries([80, 90, 100, 105, 110])} config={config} />);
      expect(currentValue()).toBe('110.0 bpm');
    });
  });

  describe('line', () => {
    it('plots the current value as a single point when there is no series', () => {
      render(<TimeSeriesChart kind="line" value={50} config={{ min: 0, max: 100 }} />);
      expect(screen.getAllByTestId('chart-point')).toHaveLength(1);
      expect(screen.queryByTestId('chart-line')).not.toBeInTheDocument();
      expect(screen.getByText('current')).toBeInTheDocument();
      expect(currentValue()).toBe('50');
    });

    it('draws a line through multiple values', () => {
      render(<TimeSeriesChart kind="line" value={60} series={samplesSeries([20, 30, 40, 50, 60])} config={{ min: 0, max: 100 }} />);
      expect(screen.getByTestId('chart-line')).toBeInTheDocument();
      expect(screen.getAllByTestId('chart-point')).toHaveLength(5);
      expect(screen.getByText('5 points')).toBeInTheDocument();
    });

    it('breaks the line at empty slots', () => {
      render(<TimeSeriesChart kind="line" value={5} series={samplesSeries([1, 2, null, 4, 5])} />);
      const d = screen.getByTestId('chart-line').getAttribute('d') ?? '';
      expect(d.match(/M/g)).toHaveLength(2);
      expect(screen.getAllByTestId('chart-point')).toHaveLength(4);
    });

    it('auto-scales the y-axis to the data when min/max are not set', () => {
      render(<TimeSeriesChart kind="line" value={22} series={samplesSeries([20, 21, 22])} config={{}} />);
      const ticks = tickLabels().map(Number);
      expect(Math.min(...ticks)).toBeGreaterThan(15);
      expect(Math.min(...ticks)).toBeLessThanOrEqual(20);
      expect(Math.max(...ticks)).toBeGreaterThanOrEqual(22);
      expect(Math.max(...ticks)).toBeLessThan(25);
    });

    it('uses lineColor and fillColor', () => {
      render(<TimeSeriesChart kind="line" value={2} series={samplesSeries([1, 2])} config={{ lineColor: '#abcdef', fillColor: '#fedcba' }} />);
      expect(screen.getByTestId('chart-line').getAttribute('stroke')).toBe('#abcdef');
      expect(screen.getByTestId('chart-area').getAttribute('fill')).toBe('#fedcba');
    });

    it('uses a threshold gradient for the line and per-point colours', () => {
      const thresholds = [
        { value: 0, color: '#00ff00' },
        { value: 50, color: '#ff0000' },
      ];
      const { container } = render(
        <TimeSeriesChart kind="line" value={80} series={samplesSeries([10, 80])} config={{ min: 0, max: 100, thresholds }} />,
      );
      expect(screen.getByTestId('chart-line').getAttribute('stroke')).toMatch(/^url\(#/);
      const stops = Array.from(container.querySelectorAll('stop')).map((s) => s.getAttribute('stop-color'));
      expect(stops).toContain('#00ff00');
      expect(stops).toContain('#ff0000');
      expect(screen.getAllByTestId('chart-point').map((p) => p.getAttribute('fill'))).toEqual(['#00ff00', '#ff0000']);
    });

    it('adds value tooltips to points', () => {
      const { container } = render(<TimeSeriesChart kind="line" value={2} series={samplesSeries([1, 2])} config={{ unit: 'W' }} />);
      const titles = titlesOf(container, 'circle');
      expect(titles).toHaveLength(2);
      expect(titles[0]).toMatch(/^1 W · /);
      expect(titles[1]).toMatch(/^2 W · /);
    });

    it('shows a min–max band instead of the area fill for averaged slots', () => {
      render(
        <TimeSeriesChart
          kind="line"
          value={5}
          series={bucketSeries([
            { avg: 4, min: 2, max: 30, count: 15 },
            { avg: 5, min: 4, max: 6, count: 15 },
          ])}
        />,
      );
      expect(screen.getByTestId('chart-range')).toBeInTheDocument();
      expect(screen.queryByTestId('chart-area')).not.toBeInTheDocument();
      expect(Math.max(...tickLabels().map(Number))).toBeGreaterThanOrEqual(30);
      expect(screen.getByText('2 points · 30 samples')).toBeInTheDocument();
    });

    it('formats the current value with decimals and unit', () => {
      const config: VisualizationConfig = { min: 0, max: 100, unit: '°C', decimals: 1 };

      const { rerender } = render(<TimeSeriesChart kind="line" value={18.5} series={samplesSeries([15, 16, 17, 18, 18.5])} config={config} />);
      expect(currentValue()).toBe('18.5 °C');

      rerender(<TimeSeriesChart kind="line" value={25} series={samplesSeries([18, 20, 22, 24, 25])} config={config} />);
      expect(currentValue()).toBe('25.0 °C');
    });
  });
});
