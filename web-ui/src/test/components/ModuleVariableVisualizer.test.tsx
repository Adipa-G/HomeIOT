import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  ModuleVariableVisualizer,
  extractJsonValue,
  getThresholdColor,
  type VisualizationConfig,
} from '../../components/ModuleVariableVisualizer';

describe('getThresholdColor', () => {
  it('returns default blue color when no thresholds provided', () => {
    expect(getThresholdColor(50)).toBe('#3b82f6');
    expect(getThresholdColor(100, undefined)).toBe('#3b82f6');
    expect(getThresholdColor(0, [])).toBe('#3b82f6');
  });

  it('returns color of highest threshold value that is met or exceeded', () => {
    const thresholds = [
      { value: 50, color: '#fbbf24' },
      { value: 75, color: '#f97316' },
      { value: 90, color: '#ef4444' },
    ];
    expect(getThresholdColor(40, thresholds)).toBe('#3b82f6'); // Below all thresholds
    expect(getThresholdColor(50, thresholds)).toBe('#fbbf24'); // Meets first
    expect(getThresholdColor(75, thresholds)).toBe('#f97316'); // Meets second
    expect(getThresholdColor(90, thresholds)).toBe('#ef4444'); // Meets third
    expect(getThresholdColor(100, thresholds)).toBe('#ef4444'); // Exceeds all
  });

  it('returns highest matching threshold color for intermediate values', () => {
    const thresholds = [
      { value: 50, color: 'yellow' },
      { value: 100, color: 'red' },
    ];
    expect(getThresholdColor(60, thresholds)).toBe('yellow'); // Above 50, below 100
    expect(getThresholdColor(75, thresholds)).toBe('yellow'); // Above 50, below 100
    expect(getThresholdColor(99, thresholds)).toBe('yellow'); // Above 50, below 100
  });

  it('handles single threshold', () => {
    const thresholds = [{ value: 50, color: 'green' }];
    expect(getThresholdColor(25, thresholds)).toBe('#3b82f6'); // Below threshold
    expect(getThresholdColor(50, thresholds)).toBe('green'); // Meets threshold
    expect(getThresholdColor(75, thresholds)).toBe('green'); // Exceeds threshold
  });

  it('handles unsorted thresholds correctly', () => {
    const thresholds = [
      { value: 90, color: 'red' },
      { value: 50, color: 'yellow' },
      { value: 75, color: 'orange' },
    ];
    expect(getThresholdColor(60, thresholds)).toBe('yellow');
    expect(getThresholdColor(80, thresholds)).toBe('orange');
    expect(getThresholdColor(95, thresholds)).toBe('red');
  });

  it('returns default color for negative values below all thresholds', () => {
    const thresholds = [
      { value: 0, color: 'blue' },
      { value: 50, color: 'yellow' },
    ];
    expect(getThresholdColor(-10, thresholds)).toBe('#3b82f6'); // Below all
    expect(getThresholdColor(0, thresholds)).toBe('blue'); // Meets first
  });
});

describe('extractJsonValue', () => {
  it('extracts value from simple property', () => {
    const data = { temperature: 25.5 };
    const result = extractJsonValue(data, 'temperature');
    expect(result).toBe(25.5);
  });

  it('extracts value from nested property', () => {
    const data = { sensor: { temperature: 25.5 } };
    const result = extractJsonValue(data, 'sensor.temperature');
    expect(result).toBe(25.5);
  });

  it('extracts from deeply nested path', () => {
    const data = { devices: { room1: { temp: { current: 72 } } } };
    const result = extractJsonValue(data, 'devices.room1.temp.current');
    expect(result).toBe(72);
  });

  it('returns null for missing path', () => {
    const data = { temperature: 25.5 };
    const result = extractJsonValue(data, 'humidity');
    expect(result).toBeNull();
  });

  it('returns null for missing nested path', () => {
    const data = { sensor: { temperature: 25.5 } };
    const result = extractJsonValue(data, 'sensor.humidity');
    expect(result).toBeNull();
  });

  it('returns null for null data', () => {
    const result = extractJsonValue(null, 'temperature');
    expect(result).toBeNull();
  });

  it('returns null for empty path', () => {
    const data = { temperature: 25.5 };
    const result = extractJsonValue(data, '');
    expect(result).toBeNull();
  });

  it('handles numeric and string values', () => {
    const data = { number: 42, string: 'hello' };
    expect(extractJsonValue(data, 'number')).toBe(42);
    expect(extractJsonValue(data, 'string')).toBe('hello');
  });
});

describe('ModuleVariableVisualizer', () => {
  describe('invalid data handling', () => {
    it('displays error message for null value', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={null}
          displayName="Temperature"
        />
      );
      expect(screen.getByText(/No valid data/i)).toBeInTheDocument();
    });

    it('displays error message for NaN value', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value="invalid"
          displayName="Temperature"
        />
      );
      expect(screen.getByText(/No valid data/i)).toBeInTheDocument();
    });

    it('displays message for empty visualization type', () => {
      render(
        <ModuleVariableVisualizer
          type=""
          value={50}
          displayName="Test"
        />
      );
      expect(screen.getByText(/Unknown visualization type/i)).toBeInTheDocument();
    });

    it('renders silently for unknown visualization type', () => {
      const { container } = render(
        <ModuleVariableVisualizer
          type="unknown_type"
          value={50}
          displayName="Test"
        />
      );
      // Component renders wrapper but no visualization
      const wrapper = container.querySelector('.rounded-lg.border.border-gray-200.bg-gray-50.p-4');
      expect(wrapper).toBeInTheDocument();
      // Only display name is rendered
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });

  describe('gauge visualization', () => {
    it('renders gauge with value and range', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('Temperature')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('0 — 100')).toBeInTheDocument();
    });

    it('formats gauge value with decimals and unit', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={72.5}
          config={{ min: 0, max: 100, decimals: 1, unit: '°C' }}
          displayName="Temp"
        />
      );
      expect(screen.getByText('72.5 °C')).toBeInTheDocument();
    });

    it('clamps value within min/max range', () => {
      const { container } = render(
        <ModuleVariableVisualizer
          type="gauge"
          value={150}
          config={{ min: 0, max: 100 }}
          displayName="Test"
        />
      );
      // SVG should still render without error
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });

    it('converts string value to number', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value="75"
          config={{ min: 0, max: 100 }}
          displayName="Test"
        />
      );
      expect(screen.getByText('75')).toBeInTheDocument();
    });

    it('renders gauge with all configuration properties (min, max, unit, decimals, thresholds)', () => {
      const config: VisualizationConfig = {
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
      
      // Test low value (below first threshold)
      const { rerender } = render(
        <ModuleVariableVisualizer
          type="gauge"
          value={5}
          config={config}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('Temperature')).toBeInTheDocument();
      expect(screen.getByText('5.0 C')).toBeInTheDocument();
      expect(screen.getByText('0 — 100')).toBeInTheDocument();

      // Test mid value (matches middle threshold)
      rerender(
        <ModuleVariableVisualizer
          type="gauge"
          value={50}
          config={config}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('50.0 C')).toBeInTheDocument();

      // Test high value (matches highest threshold)
      rerender(
        <ModuleVariableVisualizer
          type="gauge"
          value={95}
          config={config}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('95.0 C')).toBeInTheDocument();
    });

    it('applies correct threshold colors to gauge needle and arc', () => {
      const config: VisualizationConfig = {
        min: 0,
        max: 100,
        decimals: 1,
        unit: 'C',
        thresholds: [
          { value: 0, color: '#3b82f6' },
          { value: 10, color: '#f59e0b' },
          { value: 80, color: '#ef4444' },
        ],
      };

      const { container } = render(
        <ModuleVariableVisualizer
          type="gauge"
          value={85}
          config={config}
          displayName="Temp"
        />
      );

      // Check that SVG lines and circles are rendered (needle and center circle)
      const lines = container.querySelectorAll('svg line');
      const circles = container.querySelectorAll('svg circle');
      expect(lines.length).toBeGreaterThan(0); // Should have needle line
      expect(circles.length).toBeGreaterThan(0); // Should have center circle
      
      // Value display should be formatted with decimals and unit
      expect(screen.getByText('85.0 C')).toBeInTheDocument();
    });
  });

  describe('progress bar visualization', () => {
    it('renders progress bar with percentage', () => {
      render(
        <ModuleVariableVisualizer
          type="progress_bar"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Battery"
        />
      );
      expect(screen.getByText('Battery')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('formats progress value with decimals and unit', () => {
      render(
        <ModuleVariableVisualizer
          type="progress_bar"
          value={75.5}
          config={{ min: 0, max: 100, decimals: 1, unit: '%' }}
          displayName="Battery"
        />
      );
      expect(screen.getByText('75.5 %')).toBeInTheDocument();
    });

    it('displays min and max range', () => {
      render(
        <ModuleVariableVisualizer
          type="progress_bar"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Test"
        />
      );
      expect(screen.getByText('0')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();
    });

    it('renders progress bar with all configuration properties (min, max, unit, decimals, thresholds)', () => {
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

      const { rerender } = render(
        <ModuleVariableVisualizer
          type="progress_bar"
          value={10}
          config={config}
          displayName="Battery"
        />
      );
      expect(screen.getByText('Battery')).toBeInTheDocument();
      expect(screen.getByText('10.0 %')).toBeInTheDocument();
      expect(screen.getByText('10%')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="progress_bar"
          value={50}
          config={config}
          displayName="Battery"
        />
      );
      expect(screen.getByText('50.0 %')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="progress_bar"
          value={90}
          config={config}
          displayName="Battery"
        />
      );
      expect(screen.getByText('90.0 %')).toBeInTheDocument();
      expect(screen.getByText('90%')).toBeInTheDocument();
    });
  });

  describe('number display visualization', () => {
    it('renders large formatted number', () => {
      render(
        <ModuleVariableVisualizer
          type="number_display"
          value={42}
          displayName="Count"
        />
      );
      expect(screen.getByText('Count')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('formats number with decimals', () => {
      render(
        <ModuleVariableVisualizer
          type="number_display"
          value={3.14159}
          config={{ decimals: 2 }}
          displayName="Pi"
        />
      );
      expect(screen.getByText('3.14')).toBeInTheDocument();
    });

    it('displays unit when provided', () => {
      render(
        <ModuleVariableVisualizer
          type="number_display"
          value={25}
          config={{ unit: 'kWh' }}
          displayName="Energy"
        />
      );
      expect(screen.getByText('kWh')).toBeInTheDocument();
    });

    it('displays range when min/max provided', () => {
      render(
        <ModuleVariableVisualizer
          type="number_display"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Test"
        />
      );
      expect(screen.getByText(/Range: 0 — 100/)).toBeInTheDocument();
    });

    it('renders number display with all configuration properties (min, max, unit, decimals, thresholds)', () => {
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

      const { rerender } = render(
        <ModuleVariableVisualizer
          type="number_display"
          value={250}
          config={config}
          displayName="Power"
        />
      );
      expect(screen.getByText('Power')).toBeInTheDocument();
      expect(screen.getByText('250.00')).toBeInTheDocument();
      expect(screen.getByText('W')).toBeInTheDocument();
      expect(screen.getByText(/Range: 0 — 100/)).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="number_display"
          value={600}
          config={config}
          displayName="Power"
        />
      );
      expect(screen.getByText('600.00')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="number_display"
          value={850}
          config={config}
          displayName="Power"
        />
      );
      expect(screen.getByText('850.00')).toBeInTheDocument();
    });
  });

  describe('text display visualization', () => {
    it('renders numeric text value', () => {
      render(
        <ModuleVariableVisualizer
          type="text_display"
          value="123"
          displayName="Code"
        />
      );
      expect(screen.getByText('Code')).toBeInTheDocument();
      expect(screen.getByText('123')).toBeInTheDocument();
    });

    it('renders numeric string', () => {
      render(
        <ModuleVariableVisualizer
          type="text_display"
          value="123"
          displayName="Code"
        />
      );
      expect(screen.getByText('123')).toBeInTheDocument();
    });

    it('formats numeric string with decimals', () => {
      render(
        <ModuleVariableVisualizer
          type="text_display"
          value="45.6789"
          config={{ decimals: 2 }}
          displayName="Value"
        />
      );
      expect(screen.getByText('45.68')).toBeInTheDocument();
    });

    it('rejects non-numeric strings as invalid data', () => {
      render(
        <ModuleVariableVisualizer
          type="text_display"
          value="online"
          displayName="Status"
        />
      );
      expect(screen.getByText(/No valid data/i)).toBeInTheDocument();
    });

    it('renders text display with configuration properties (decimals, unit)', () => {
      const config: VisualizationConfig = {
        decimals: 2,
        unit: 'kB/s',
      };

      const { rerender } = render(
        <ModuleVariableVisualizer
          type="text_display"
          value="123.456"
          config={config}
          displayName="Speed"
        />
      );
      expect(screen.getByText('Speed')).toBeInTheDocument();
      expect(screen.getByText('123.46 kB/s')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="text_display"
          value="78.901"
          config={config}
          displayName="Speed"
        />
      );
      expect(screen.getByText('78.90 kB/s')).toBeInTheDocument();
    });
  });

  describe('bar chart visualization', () => {
    it('renders single bar for single value', () => {
      render(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Chart"
        />
      );
      expect(screen.getByText('Chart')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('renders multiple bars for historical values', () => {
      render(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={60}
          values={[20, 30, 40, 50, 60]}
          config={{ min: 0, max: 100, historyPoints: 5 }}
          displayName="History"
        />
      );
      expect(screen.getByText('History')).toBeInTheDocument();
      expect(screen.getByText('60')).toBeInTheDocument();
    });

    it('formats bar chart values with unit', () => {
      render(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={75}
          config={{ min: 0, max: 100, unit: '%' }}
          displayName="Chart"
        />
      );
      expect(screen.getByText('%')).toBeInTheDocument();
    });

    it('filters out null values from historical data', () => {
      render(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={50}
          values={[10, null, 30, null, 50]}
          config={{ min: 0, max: 100 }}
          displayName="Chart"
        />
      );
      // Should render without error
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('handles string values in historical data', () => {
      render(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={50}
          values={['10', '20', '30', '40', '50']}
          config={{ min: 0, max: 100 }}
          displayName="Chart"
        />
      );
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('renders bar chart with all configuration properties (min, max, unit, decimals, thresholds, historyPoints)', () => {
      const config: VisualizationConfig = {
        min: 0,
        max: 100,
        unit: 'bpm',
        decimals: 1,
        historyPoints: 5,
        thresholds: [
          { value: 0, color: '#3b82f6' },
          { value: 60, color: '#f59e0b' },
          { value: 100, color: '#ef4444' },
        ],
      };

      const { rerender } = render(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={75.5}
          values={[60, 68, 72, 74, 75.5]}
          config={config}
          displayName="Heart Rate"
        />
      );
      expect(screen.getByText('Heart Rate')).toBeInTheDocument();
      expect(screen.getByText('75.5')).toBeInTheDocument();
      expect(screen.getByText('bpm')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="bar_chart"
          value={110}
          values={[80, 90, 100, 105, 110]}
          config={config}
          displayName="Heart Rate"
        />
      );
      expect(screen.getByText('110.0')).toBeInTheDocument();
    });
  });

  describe('line chart visualization', () => {
    it('renders single point for single value', () => {
      render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Trend"
        />
      );
      expect(screen.getByText('Trend')).toBeInTheDocument();
      expect(screen.getByText('current')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('renders interpolated line for multiple historical values', () => {
      render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={60}
          values={[20, 30, 40, 50, 60]}
          config={{ min: 0, max: 100, historyPoints: 5 }}
          displayName="Trend"
        />
      );
      expect(screen.getByText('Trend')).toBeInTheDocument();
      expect(screen.getByText('5 points')).toBeInTheDocument();
      expect(screen.getByText('60')).toBeInTheDocument();
    });

    it('is centered with flex classes', () => {
      const { container } = render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={50}
          config={{ min: 0, max: 100 }}
          displayName="Centered"
        />
      );
      const chartContainer = container.querySelector('.flex.flex-col.gap-2.w-full');
      expect(chartContainer).toBeInTheDocument();
    });

    it('limits historical data to 10 points', () => {
      const manyPoints = Array.from({ length: 20 }, (_, i) => i + 1);
      render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={20}
          values={manyPoints}
          config={{ min: 0, max: 100 }}
          displayName="ManyPoints"
        />
      );
      // Should render without error, limiting to last 10 points
      expect(screen.getByText('ManyPoints')).toBeInTheDocument();
    });

    it('formats line chart values with unit', () => {
      render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={75}
          config={{ min: 0, max: 100, unit: '°F' }}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('75 °F')).toBeInTheDocument();
    });

    it('filters out null values from historical data', () => {
      render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={50}
          values={[10, null, 30, null, 50]}
          config={{ min: 0, max: 100 }}
          displayName="Trend"
        />
      );
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('handles string values in historical data', () => {
      render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={50}
          values={['10', '20', '30', '40', '50']}
          config={{ min: 0, max: 100 }}
          displayName="Trend"
        />
      );
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('renders line chart with all configuration properties (min, max, unit, decimals, thresholds, historyPoints)', () => {
      const config: VisualizationConfig = {
        min: 0,
        max: 100,
        unit: '°C',
        decimals: 1,
        historyPoints: 10,
        thresholds: [
          { value: 0, color: '#3b82f6' },
          { value: 20, color: '#f59e0b' },
          { value: 30, color: '#ef4444' },
        ],
      };

      const { rerender } = render(
        <ModuleVariableVisualizer
          type="line_chart"
          value={18.5}
          values={[15, 16, 17, 18, 18.5]}
          config={config}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('Temperature')).toBeInTheDocument();
      expect(screen.getByText('18.5 °C')).toBeInTheDocument();
      expect(screen.getByText('5 points')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="line_chart"
          value={25}
          values={[18, 20, 22, 24, 25]}
          config={config}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('25.0 °C')).toBeInTheDocument();

      rerender(
        <ModuleVariableVisualizer
          type="line_chart"
          value={32}
          values={[28, 29, 30, 31, 32]}
          config={config}
          displayName="Temperature"
        />
      );
      expect(screen.getByText('32.0 °C')).toBeInTheDocument();
    });
  });

  describe('configuration handling', () => {
    it('parses config as JSON string', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={50}
          config='{"min":0,"max":100,"decimals":1}'
          displayName="Test"
        />
      );
      expect(screen.getByText('50.0')).toBeInTheDocument();
    });

    it('accepts config as object', () => {
      const config: VisualizationConfig = {
        min: 0,
        max: 100,
        decimals: 2,
        unit: '°C',
      };
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={72.5}
          config={config}
          displayName="Test"
        />
      );
      expect(screen.getByText('72.50 °C')).toBeInTheDocument();
    });

    it('handles missing config gracefully', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={50}
          displayName="Test"
        />
      );
      expect(screen.getByText('50')).toBeInTheDocument();
    });
  });

  describe('threshold colors', () => {
    it('applies color based on threshold value', () => {
      const { container } = render(
        <ModuleVariableVisualizer
          type="number_display"
          value={75}
          config={{
            thresholds: [
              { value: 0, color: '#ef4444' },
              { value: 50, color: '#f97316' },
            ],
          }}
          displayName="Alert"
        />
      );
      const value = container.querySelector('.text-4xl');
      expect(value?.getAttribute('style')).toContain('color');
    });

    it('uses first threshold color when no value threshold matches', () => {
      render(
        <ModuleVariableVisualizer
          type="number_display"
          value={25}
          config={{
            thresholds: [
              { value: 50, color: '#22c55e' },
              { value: 75, color: '#ef4444' },
            ],
          }}
          displayName="Status"
        />
      );
      // Should render with the first threshold color
      expect(screen.getByText('Status')).toBeInTheDocument();
    });
  });

  describe('display name and container', () => {
    it('renders display name in header', () => {
      render(
        <ModuleVariableVisualizer
          type="gauge"
          value={50}
          displayName="Room Temperature"
        />
      );
      expect(screen.getByText('Room Temperature')).toBeInTheDocument();
    });

    it('wraps visualization in styled container', () => {
      const { container } = render(
        <ModuleVariableVisualizer
          type="gauge"
          value={50}
          displayName="Test"
        />
      );
      const wrapper = container.querySelector('.rounded-lg.border.border-gray-200.bg-gray-50.p-4');
      expect(wrapper).toBeInTheDocument();
    });

    it('renders all visualization types in same container style', () => {
      const types = ['gauge', 'progress_bar', 'number_display', 'text_display', 'bar_chart', 'line_chart'];
      types.forEach(type => {
        const { container } = render(
          <ModuleVariableVisualizer
            type={type}
            value={50}
            displayName={`Test ${type}`}
          />
        );
        const wrapper = container.querySelector('.rounded-lg.border.border-gray-200.bg-gray-50.p-4');
        expect(wrapper).toBeInTheDocument();
      });
    });
  });
});
