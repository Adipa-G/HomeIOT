# Module Variable Visualizations

## Overview

The HomeIOT system now supports rich visual representations of module output data. Visualizations allow you to display temperature readings, sensor data, and other metrics in easy-to-understand graphical formats using pure CSS and SVG—no heavy charting libraries required.

## Supported Visualization Types

### 1. **Gauge** 
Circular gauge display showing a value within a range.

**Configuration:**
```json
{
  "visualization_type": "gauge",
  "visualization_config": {
    "min": 0,
    "max": 100,
    "unit": "°C",
    "decimals": 1,
    "thresholds": [
      { "value": 30, "color": "#fbbf24" },
      { "value": 40, "color": "#f87171" }
    ]
  }
}
```

**Use Cases:**
- Temperature readings
- Humidity levels
- Pressure sensors
- Battery percentage

### 2. **Progress Bar**
Horizontal progress bar with percentage fill.

**Configuration:**
```json
{
  "visualization_type": "progress_bar",
  "visualization_config": {
    "min": 0,
    "max": 100,
    "unit": "%",
    "thresholds": [
      { "value": 50, "color": "#fbbf24" },
      { "value": 80, "color": "#f87171" }
    ]
  }
}
```

**Use Cases:**
- Memory usage
- Storage percentage
- Battery percentage
- Progress indicators

### 3. **Number Display**
Large, formatted number with optional min/max range display.

**Configuration:**
```json
{
  "visualization_type": "number_display",
  "visualization_config": {
    "min": 0,
    "max": 50,
    "unit": "°C",
    "decimals": 1
  }
}
```

**Use Cases:**
- Temperature readings
- Sensor counts
- Status codes
- Any numeric value

### 4. **Text Display**
Simple text representation of any value.

**Configuration:**
```json
{
  "visualization_type": "text_display",
  "visualization_config": {
    "decimals": 2,
    "unit": "m/s"
  }
}
```

**Use Cases:**
- Status messages
- Device names
- Any string value
- Formatted numeric text

### 5. **Bar Chart**
Simple SVG bar chart showing historical values with automatic width scaling.

**Features:**
- Displays multiple data points with consistent spacing
- Bar width automatically scales based on number of points (1-80px)
- Supports unlimited historical values
- Applies threshold colors to each bar

**Configuration:**
```json
{
  "visualization_type": "bar_chart",
  "visualization_config": {
    "min": 0,
    "max": 100,
    "unit": "%",
    "decimals": 1,
    "thresholds": [
      { "value": 33, "color": "#10b981" },
      { "value": 66, "color": "#fbbf24" },
      { "value": 100, "color": "#ef4444" }
    ]
  }
}
```

**Example with Historical Data:**
```json
{
  "visualization_type": "bar_chart",
  "visualization_config": {
    "min": 0,
    "max": 100,
    "unit": "bpm",
    "decimals": 0,
    "thresholds": [
      { "value": 60, "color": "#3b82f6" },
      { "value": 100, "color": "#fbbf24" },
      { "value": 130, "color": "#ef4444" }
    ]
  }
}
```

**Use Cases:**
- Usage percentages over time
- Load metrics (historical)
- Heart rate patterns
- Resource utilization trends
- Signal strength history

### 6. **Line Chart**
Simple SVG line chart with trend visualization and historical data display.

**Features:**
- Shows last N data points as configured by `historyPoints`
- Fills area under the curve for visual emphasis
- Applies threshold colors based on the latest data point
- Scales horizontally to fit all points
- Limits display to configurable number of points (default: 10, max recommended: 50)

**Configuration:**
```json
{
  "visualization_type": "line_chart",
  "visualization_config": {
    "min": 0,
    "max": 50,
    "unit": "°C",
    "decimals": 1,
    "historyPoints": 10,
    "thresholds": [
      { "value": 25, "color": "#3b82f6" },
      { "value": 40, "color": "#ef4444" }
    ]
  }
}
```

**Example with Extended History:**
```json
{
  "visualization_type": "line_chart",
  "visualization_config": {
    "min": 0,
    "max": 100,
    "unit": "%",
    "decimals": 0,
    "historyPoints": 24,
    "thresholds": [
      { "value": 30, "color": "#10b981" },
      { "value": 60, "color": "#fbbf24" },
      { "value": 80, "color": "#ef4444" }
    ]
  }
}
```

**Configuration Parameters:**
- `historyPoints`: Maximum number of historical points to display (default: 10)
  - Each point represents one data value
  - Displays last N values from the historical data
  - Recommended: 10-20 for optimal readability

**Use Cases:**
- Temperature trends over time
- Time-series data visualization
- Signal strength variations
- Performance metrics over time
- CPU/memory usage trends
- Hourly/daily readings

## Configuration

Visualizations are configured per module variable through:

1. **JSON Path**: Specifies where in the module output JSON to find the data
2. **Display Name**: Human-readable label for the visualization
3. **Visualization Type**: One of the types listed above
4. **Visualization Config**: Type-specific configuration

### Visualization Config Properties

All visualizations support these optional properties:

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `min` | number | Minimum value for range-based visualizations | 0 |
| `max` | number | Maximum value for range-based visualizations | 100 |
| `unit` | string | Unit label to display (e.g., "°C", "%", "bpm") | none |
| `decimals` | number | Number of decimal places to display | auto |
| `thresholds` | array | Color thresholds based on value | none |
| `historyPoints` | number | Max historical points for bar/line charts | 10 |

### JSON Path Examples

```json
// Direct field
"json_path": "temp"

// Nested object
"json_path": "data.temperature"

// Array index
"json_path": "readings[0].value"

// Deep nesting
"json_path": "device.sensors.temp.value"
```

## Adding Visualizations via API

```bash
POST /api/admin/modules/{moduleId}/variables/{varName}/visualizations

Content-Type: application/json

{
  "json_path": "temp",
  "display_name": "Temperature Reading",
  "visualization_type": "gauge",
  "visualization_config": {
    "min": 0,
    "max": 50,
    "unit": "°C",
    "decimals": 1,
    "thresholds": [
      { "value": 30, "color": "#fbbf24" },
      { "value": 40, "color": "#f87171" }
    ]
  }
}
```

## Threshold Color Support

Thresholds allow dynamic color changes based on value. The **highest threshold that the current value meets or exceeds** determines the color.

**How Color Matching Works:**

When a value is evaluated against thresholds, the system finds the highest threshold value that the current value is >= to, and uses that threshold's color.

**Example:**
```json
{
  "thresholds": [
    { "value": 0,  "color": "#3b82f6" },    // Blue: 0 and above
    { "value": 25, "color": "#10b981" },   // Green: 25 and above
    { "value": 50, "color": "#fbbf24" },   // Yellow: 50 and above
    { "value": 75, "color": "#ef4444" }    // Red: 75 and above
  ]
}
```

**Color Assignment by Value:**
- Value `10` → matches threshold `0` → **Blue** (#3b82f6)
- Value `30` → matches threshold `25` → **Green** (#10b981) 
- Value `60` → matches threshold `50` → **Yellow** (#fbbf24)
- Value `85` → matches threshold `75` → **Red** (#ef4444)

**Key Points:**
- Thresholds should be in ascending order for clarity
- All visualizations (gauge, progress bar, number display, bar chart, line chart) use the same threshold color logic
- Each data point in bar/line charts is colored independently based on its value
- Default color (blue: #3b82f6) is used if value is below all thresholds

## Implementation Details

### Component: ModuleVariableVisualizer

Located at `web-ui/src/components/ModuleVariableVisualizer.tsx`

**Features:**
- Pure CSS and SVG rendering (no external chart libraries)
- Lightweight and performant
- Responsive design
- Color theming with thresholds
- Proper decimal formatting
- Unit display support

### Integration in Device Detail Page

Visualizations automatically render on the Device Detail page under the Modules tab:

1. Navigate to Devices
2. Click on a device
3. View the "Modules" tab
4. Visualizations appear below the module output JSON if configured

### Utility Functions

**extractJsonValue(data, path)**
```typescript
// Extract value from JSON using dot notation
const temp = extractJsonValue(moduleOutput, "temp");
const nested = extractJsonValue(output, "data.temperature");
```

## Example: Temperature Sensor Module

### Module Configuration

**Variable Definition:**
- Name: `temp`
- Type: `number`
- Description: Temperature reading in Celsius

**Visualization:**
```json
{
  "json_path": "temp",
  "display_name": "Current Temperature",
  "visualization_type": "gauge",
  "visualization_config": {
    "min": 0,
    "max": 50,
    "unit": "°C",
    "decimals": 1,
    "thresholds": [
      { "value": 15, "color": "#60a5fa" },
      { "value": 25, "color": "#10b981" },
      { "value": 35, "color": "#f59e0b" },
      { "value": 40, "color": "#ef4444" }
    ]
  }
}
```

### Module Output
```json
{
  "temp": 28.5,
  "status": "ok",
  "timestamp": "2026-06-20T21:30:00Z"
}
```

### Display Result
A circular gauge showing 28.5°C with a green indicator (between 25 and 35 threshold)

## Best Practices

1. **Keep JSON paths simple** - Use direct field names when possible
2. **Set appropriate ranges** - min/max should bracket expected values
3. **Use meaningful units** - Help users understand the data
4. **Configure thresholds** - Provide visual feedback for important values
5. **Test extraction** - Verify json_path matches your output structure
6. **Document variables** - Add descriptions in variable definitions

## Performance Notes

- All visualizations use pure CSS and SVG
- No external charting libraries (React, D3, Chart.js, etc.)
- Lightweight rendering suitable for resource-constrained devices
- Single-value visualizations (not time-series history)
- Real-time updates via query invalidation

## Future Enhancements

Potential future additions:
- Time-series history visualization
- Custom color schemes
- Animation support
- Additional chart types
- Export/screenshot functionality
- Customizable threshold warnings

## Files Modified

- `web-ui/src/components/ModuleVariableVisualizer.tsx` - New visualization component
- `web-ui/src/pages/DeviceDetailPage.tsx` - Integration with device detail view
- `web-ui/src/types/api.ts` - Type definitions (already had visualization types)

## Troubleshooting

**Visualizations not showing:**
1. Verify `visualization_type` is one of the supported types
2. Check that `json_path` correctly points to data in module output
3. Ensure variable definition has `visualizations` array populated
4. Check browser console for errors

**Colors not changing:**
1. Verify thresholds are sorted by value (ascending)
2. Check that values are within threshold ranges
3. Ensure threshold colors are valid hex codes

**Values not displaying:**
1. Verify module output JSON is valid
2. Check `json_path` matches actual field names
3. Ensure value can be parsed as number (for numeric visualizations)

---

## Related Documentation

- **[Main README](../README.md)** — System overview and architecture
- **[Web UI Component Docs](../web-ui/README.md#modulevisualizationvisualizer)** — Component usage and testing
- **[Module System Guide](features-modules.md)** — How to create modules with visualization-enabled variables
- **[Dashboard Guide](features-dashboard.md)** — Real-time system monitoring and metrics
- **[Device Management Guide](features-devices.md)** — Device setup and variable monitoring
