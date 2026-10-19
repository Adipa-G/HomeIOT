import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ModuleVariableVisualizer } from '../../components/ModuleVariableVisualizer';
import type { VisualizationConfig } from '../../lib/visualization';
import { samplesSeries } from '../chartSeriesFixtures';

const CONTAINER_SELECTOR = '.rounded-lg.border.border-gray-200.bg-gray-50.p-4';

describe('ModuleVariableVisualizer', () => {
  describe('invalid data handling', () => {
    it('displays error message for null value', () => {
      render(<ModuleVariableVisualizer type="gauge" value={null} displayName="Temperature" />);
      expect(screen.getByText(/No valid data/i)).toBeInTheDocument();
    });

    it('displays error message for non-numeric value', () => {
      render(<ModuleVariableVisualizer type="gauge" value="invalid" displayName="Temperature" />);
      expect(screen.getByText(/No valid data/i)).toBeInTheDocument();
    });

    it('displays message for empty visualization type', () => {
      render(<ModuleVariableVisualizer type="" value={50} displayName="Test" />);
      expect(screen.getByText(/Unknown visualization type/i)).toBeInTheDocument();
    });

    it('renders only the header for an unknown visualization type', () => {
      const { container } = render(<ModuleVariableVisualizer type="unknown_type" value={50} displayName="Test" />);
      expect(container.querySelector(CONTAINER_SELECTOR)).toBeInTheDocument();
      expect(screen.getByText('Test')).toBeInTheDocument();
      expect(container.querySelector('svg')).not.toBeInTheDocument();
    });
  });

  describe('routing by type', () => {
    it('renders a gauge', () => {
      render(<ModuleVariableVisualizer type="gauge" value={50} config={{ min: 0, max: 100 }} displayName="G" />);
      expect(screen.getByText('Range: 0 — 100')).toBeInTheDocument();
    });

    it('renders a progress bar', () => {
      render(<ModuleVariableVisualizer type="progress_bar" value={50} config={{ min: 0, max: 100 }} displayName="P" />);
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('renders a number display', () => {
      render(<ModuleVariableVisualizer type="number_display" value={42} config={{ unit: 'kWh' }} displayName="N" />);
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('kWh')).toBeInTheDocument();
    });

    it('renders a text display, including non-numeric values', () => {
      render(<ModuleVariableVisualizer type="text_display" value="online" displayName="T" />);
      expect(screen.getByText('online')).toBeInTheDocument();
    });

    it('renders a bar chart with its series', () => {
      render(<ModuleVariableVisualizer type="bar_chart" value={3} series={samplesSeries([1, 2, 3])} displayName="B" />);
      expect(screen.getAllByTestId('chart-bar')).toHaveLength(3);
    });

    it('renders a line chart with its series', () => {
      render(<ModuleVariableVisualizer type="line_chart" value={2} series={samplesSeries([1, 2], 5)} displayName="L" />);
      expect(screen.getByTestId('chart-line')).toBeInTheDocument();
      expect(screen.getAllByTestId('chart-x-label')).toHaveLength(2);
    });

    it('passes compact through to charts', () => {
      const { container: normal } = render(<ModuleVariableVisualizer type="bar_chart" value={1} displayName="A" />);
      const { container: compact } = render(<ModuleVariableVisualizer type="bar_chart" value={1} displayName="B" compact />);
      const height = (c: HTMLElement) => Number(c.querySelector('svg')?.getAttribute('height'));
      expect(height(compact)).toBeLessThan(height(normal));
    });

    it('passes compact through to gauges and tightens padding', () => {
      const { container } = render(<ModuleVariableVisualizer type="gauge" value={50} displayName="G" compact />);
      expect(screen.getByTestId('gauge-svg').getAttribute('class')).toContain('max-w-32');
      expect(container.firstElementChild?.className).toContain('p-2');
    });
  });

  describe('value parsing', () => {
    it('converts a numeric string value to a number', () => {
      render(<ModuleVariableVisualizer type="gauge" value="75" config={{ min: 0, max: 100 }} displayName="Test" />);
      expect(screen.getByText('75')).toBeInTheDocument();
    });
  });

  describe('configuration handling', () => {
    it('parses config as JSON string', () => {
      render(<ModuleVariableVisualizer type="gauge" value={50} config='{"min":0,"max":100,"decimals":1}' displayName="Test" />);
      expect(screen.getByText('50.0')).toBeInTheDocument();
    });

    it('accepts config as object', () => {
      const config: VisualizationConfig = { min: 0, max: 100, decimals: 2, unit: '°C' };
      render(<ModuleVariableVisualizer type="gauge" value={72.5} config={config} displayName="Test" />);
      expect(screen.getByText('72.50 °C')).toBeInTheDocument();
    });

    it('handles missing config gracefully', () => {
      render(<ModuleVariableVisualizer type="gauge" value={50} displayName="Test" />);
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('falls back to defaults for an invalid JSON config string', () => {
      render(<ModuleVariableVisualizer type="gauge" value={50} config="not json" displayName="Test" />);
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('Range: 0 — 100')).toBeInTheDocument();
    });
  });

  describe('display name and container', () => {
    it('renders display name in header', () => {
      render(<ModuleVariableVisualizer type="gauge" value={50} displayName="Room Temperature" />);
      expect(screen.getByText('Room Temperature')).toBeInTheDocument();
    });

    it('wraps every visualization type in the same styled container', () => {
      const types = ['gauge', 'progress_bar', 'number_display', 'text_display', 'bar_chart', 'line_chart'];
      types.forEach((type) => {
        const { container, unmount } = render(<ModuleVariableVisualizer type={type} value={50} displayName={`Test ${type}`} />);
        expect(container.querySelector(CONTAINER_SELECTOR)).toBeInTheDocument();
        expect(screen.getByText(`Test ${type}`)).toBeInTheDocument();
        unmount();
      });
    });
  });
});
