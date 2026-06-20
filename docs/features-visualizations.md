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
Simple SVG bar chart showing a single value against a scale.

**Configuration:**
```json
{
  "visualization_type": "bar_chart",
  "visualization_config": {
    "min": 0,
    "max": 100,
    "unit": "%",
    "thresholds": [
      { "value": 33, "color": "#10b981" },
      { "value": 66, "color": "#fbbf24" },
      { "value": 100, "color": "#ef4444" }
    ]
  }
}
```

**Use Cases:**
- Usage percentages
- Load metrics
- Signal strength
- Resource utilization

### 6. **Line Chart**
Simple SVG line chart with trend visualization.

**Configuration:**
```json
{
  "visualization_type": "line_chart",
  "visualization_config": {
    "min": 0,
    "max": 50,
    "unit": "°C",
    "decimals": 1,
    "thresholds": [
      { "value": 25, "color": "#3b82f6" },
      { "value": 40, "color": "#ef4444" }
    ]
  }
}
```

**Use Cases:**
- Temperature trends
- Time-series data
- Signal variations
- Performance metrics

## Configuration

Visualizations are configured per module variable through:

1. **JSON Path**: Specifies where in the module output JSON to find the data
2. **Display Name**: Human-readable label for the visualization
3. **Visualization Type**: One of the types listed above
4. **Visualization Config**: Type-specific configuration (min, max, unit, thresholds, decimals)

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

Thresholds allow dynamic color changes based on value:

```json
{
  "thresholds": [
    { "value": 0,  "color": "#6b7280" },    // Gray below 0
    { "value": 25, "color": "#3b82f6" },   // Blue 25-40
    { "value": 40, "color": "#fbbf24" },   // Yellow 40-35
    { "value": 35, "color": "#f87171" }    // Red above 35
  ]
}
```

Colors are matched inclusively - the highest threshold below the current value determines the color.

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
