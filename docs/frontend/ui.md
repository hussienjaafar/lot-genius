# Frontend UI Guide

Next.js web interface with real-time streaming, calibration analysis, and responsive components.

## Overview

The Lot Genius frontend provides:

- **Lot Optimization**: Upload manifests and configure optimization parameters
- **Real-time Streaming**: SSE progress updates during processing
- **Calibration Analysis**: Client-side prediction vs outcome analysis
- **Multiple Upload Modes**: Proxy and direct backend connectivity
- **Responsive Design**: Works on desktop and mobile devices

**Tech Stack**: Next.js 14, TypeScript, Tailwind CSS, inline SVG charts

## Upload Modes

### Proxy Mode (Default)

Routes requests through Next.js API route `/api/pipeline/upload/stream`:

- **Advantages**: CORS handling, request validation, unified error handling
- **Use case**: Standard development and most production scenarios
- **Configuration**: No additional setup required

### Direct Mode

Connects directly to FastAPI backend `/v1/pipeline/upload/stream`:

- **Advantages**: Reduced latency, direct backend communication
- **Use case**: Performance-critical scenarios or backend-only deployments
- **Configuration**: Set environment variables

**Environment Setup for Direct Mode:**

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8787
NEXT_PUBLIC_API_KEY=your_secret_key_here
```

### Authentication

When `LOTGENIUS_API_KEY` is set on backend:

- **Proxy Mode**: Automatically handled by Next.js API route
- **Direct Mode**: Requires `X-API-Key` header (set via `NEXT_PUBLIC_API_KEY`)

### CORS Configuration

Backend allows these origins in development:

- `http://localhost:3000` (Next.js default)
- `http://localhost:3001` (Alternative port)

Configured via FastAPI `CORSMiddleware`.

## Pages

### Home Page (`/`)

Main optimization interface with two primary modes:

#### Optimize Lot Tab

**Purpose**: Standard lot optimization with results display

**Features**:

- File upload with drag-and-drop support
- Optimizer configuration via JSON textarea
- Optional calibration logging path
- Results visualization with metric cards
- Progress tracking during processing

**Workflow**:

1. Upload items CSV file
2. Configure optimization parameters (optional)
3. Set calibration logging path (optional)
4. Click "Optimize Lot"
5. View results in metrics grid

**Example Configuration**:

```json
{
  "roi_target": 1.25,
  "risk_threshold": 0.8,
  "sims": 2000,
  "calibration_log_path": "logs/predictions.jsonl"
}
```

#### Pipeline (SSE) Tab

**Purpose**: Real-time streaming with detailed progress monitoring

**Features**:

- Same file upload interface
- Live SSE event console
- Real-time ping monitoring
- Detailed processing stages

**SSE Event Types**:

- `start` - Processing initiated with input validation
- `parse` - Manifest parsing and header mapping complete
- `validate` - Data validation and coverage checks complete
- `enrich_keepa` - ID resolution and Keepa enrichment complete
- `price` - Price estimation and ensemble modeling complete
- `sell` - Sell-through probability estimation complete
- `optimize` - ROI optimization and bid calculation complete
- `render_report` - Report generation complete
- `done` - All processing finished successfully
- `error` - Processing failed with error details (ASCII-safe, truncated to 200 chars)
- `ping` - Keep-alive signals to maintain connection

**Event Data Structure**:

```json
{
  "event": "optimize",
  "data": {
    "stage": "optimization",
    "message": "ROI optimization complete",
    "progress": 85,
    "details": {
      "bid": 1250.5,
      "roi_p50": 1.34,
      "core_items": 45
    }
  }
}
```

### Results Display

**Purpose**: Show optimization results with optional confidence and cache metrics

#### Optimization Results Section

**Standard Metrics** (always displayed):

- **Optimal Bid**: Recommended maximum bid amount
- **Expected ROI**: 50th percentile return on investment
- **60-Day Cash**: Expected cash flow at 60 days
- **Items Count**: Number of items analyzed
- **Meets Constraints**: Whether lot meets risk constraints
- **ROI Target Probability**: Progress bar showing probability

#### Product Confidence Section

**Display Conditions**: Appears when `confidence_samples` array is present in API response

**Features**:

- **Average Confidence**: Computed from available confidence samples (0-1 range)
- **Sample Count**: Number of items with product matching data
- **Visual Styling**: Green-themed section with clear confidence value

**Example Display**:

```
Product Confidence
Average Confidence: 0.74
Based on 6 items with product matching data
```

#### Cache Metrics Section

**Display Conditions**: Appears when `cache_stats` object is present in API response

**Features**:

- **Per-Cache Breakdown**: Individual stats for each cache (Keepa, eBay, etc.)
- **Hit/Miss Counts**: Raw operation numbers
- **Hit Ratio**: Percentage of successful cache hits
- **Total Operations**: Combined hits, misses, stores, evictions
- **Visual Styling**: Blue-themed section with performance data

**Example Display**:

```
Cache Performance

Keepa Cache: Hits: 120  Misses: 25  Hit Ratio: 82.8%  Total: 145
Ebay Cache:  Hits: 45   Misses: 8   Hit Ratio: 84.9%  Total: 53
```

**ASCII-Only Text**: All display text uses ASCII characters for universal compatibility

#### Copy Report Path Section

**Display Conditions**: Appears when `markdown_path` is present in API response

**Features**:

- **Report Path Display**: Shows full path where report was saved
- **Copy Button**: One-click clipboard copy with visual feedback
- **ASCII Confirmation**: "Copied!" message with 2-second timeout
- **Visual Styling**: Gray-themed section with path and action button

**Example Display**:

```
Report Generated
Report saved to: C:/Users/Husse/lot-genius/reports/lot_analysis_20240126_143022.md
[Copy Report Path]
```

**Behavior**:

- Button text changes to "Copied!" on click
- Automatic reset to original text after 2 seconds
- Uses Clipboard API for reliable copying
- Data testid: `copy-report-path` for E2E testing

### Calibration Page (`/calibration`)

**Purpose**: Analyze prediction accuracy using historical outcomes

#### File Upload Section

**Required Files**:

- **Predictions JSONL**: Logged predictions from previous runs
- **Outcomes CSV**: Realized results with matching `sku_local` keys

**Upload Methods**:

- Drag-and-drop interface
- Click to browse files
- File validation with error feedback

#### Analysis Engine (Client-Side)

**Processing Steps**:

1. Parse JSONL predictions file
2. Parse CSV outcomes file
3. Join on `sku_local` field
4. Compute calibration metrics
5. Generate visualization

**No Backend Required**: All computation happens in the browser for fast feedback.

#### Metrics Computed

**Probability Calibration**:

- **Brier Score**: Overall accuracy (lower = better)
- **Calibration Bins**: 10 bins from 0.0-0.1 to 0.9-1.0
- **Bias Analysis**: Overconfidence vs underconfidence patterns

**Price Accuracy**:

- **MAE**: Mean Absolute Error
- **RMSE**: Root Mean Square Error
- **MAPE**: Mean Absolute Percentage Error
- **Sample Count**: Valid price comparisons

#### Visualization

**Calibration Chart**: Interactive bar chart showing:

- Predicted probability (average per bin)
- Actual outcome rate (realized)
- Bias overlay (red = overconfident, green = underconfident)
- Sample counts per bin

**Data Table**: Detailed bin-by-bin breakdown with:

- Probability ranges
- Sample counts
- Predicted vs actual rates
- Bias calculations with color coding

#### Export Features

**JSON Report Download**:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "calibration_metrics": {
    "brier_score": 0.1847,
    "samples": 1247,
    "price_metrics": {
      "mae": 8.32,
      "rmse": 12.15,
      "mape": 24.7,
      "samples": 892
    }
  },
  "calibration_bins": [...]
}
```

## UI Components (Step 6)

### MetricCard

**Purpose**: Display key performance indicators with context

**Props**:

- `label` - Metric name
- `value` - Formatted value (string or number)
- `hint` - Tooltip explanation
- `delta` - Change indicator (optional)
- `className` - Additional CSS classes

**Example**:

```jsx
<MetricCard
  label="Optimal Bid"
  value="$1,250.50"
  hint="Recommended maximum bid amount"
  delta="+5.2%"
/>
```

### ProgressBar

**Purpose**: Visual progress indicator with label

**Props**:

- `value` - Progress value (0-1 or 0-100)
- `label` - Description text
- `className` - Styling customization

**Features**:

- Responsive width scaling
- Accessibility labels
- Smooth animations

### SparkArea

**Purpose**: Compact trend visualization using SVG

**Props**:

- `data` - Array of {x, y} points
- `width`, `height` - Dimensions
- `color` - Fill color

**Use Cases**:

- ROI trend over time
- Price distribution curves
- Confidence intervals

### BinBarChart

**Purpose**: Calibration bin visualization with bias overlay

**Props**:

- `bins` - Array of calibration bin objects
- `width`, `height` - Chart dimensions

**Features**:

- Dual-axis display (predicted vs actual)
- Bias color overlay (red/green)
- Grid lines and axis labels
- Responsive scaling

**Data Format**:

```javascript
const bins = [
  {
    label: "0.0-0.1",
    count: 125,
    pred: 0.052, // Average predicted
    actual: 0.048, // Actual rate
    bias: 0.004, // Difference
  },
];
```

### Section

**Purpose**: Content container with title and description

**Props**:

- `title` - Section heading
- `description` - Explanatory text
- `actions` - Optional action buttons
- `children` - Content area

**Layout**:

- Responsive grid system
- Consistent spacing
- Optional action buttons in header

### FilePicker

**Purpose**: File upload with drag-and-drop support

**Props**:

- `label` - Upload area label
- `accept` - File type filter
- `onFiles` - File selection callback

**Features**:

- Visual drag-and-drop feedback
- File type validation
- Error state handling
- Progress indication

### SseConsole

**Purpose**: Real-time event stream display

**Props**:

- `events` - Array of SSE event objects

**Features**:

- Auto-scrolling to latest events
- Event type icons and colors
- Timestamp formatting
- Collapsible/expandable view

**Event Format**:

```javascript
const events = [
  {
    ts: "2024-01-15T10:30:15Z",
    stage: "parse",
    message: "Parsed 1,247 items with 95% header coverage",
  },
];
```

## Server-Sent Events (SSE)

### Implementation

**Frontend Streaming**:

```javascript
async function streamReport(formData, onEvent) {
  const response = await fetch("/api/pipeline/upload/stream", {
    method: "POST",
    body: formData,
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    buffer += chunk;

    // Parse SSE frames
    const frames = buffer.split("\n\n");
    for (let frame of frames.slice(0, -1)) {
      const event = parseSSEFrame(frame);
      onEvent(event);
    }
    buffer = frames[frames.length - 1];
  }
}
```

**Event Processing**:

- Frame parsing with `event:` and `data:` lines
- JSON data extraction with error handling
- Message normalization across event types
- Real-time UI updates

### Connection Management

**Ping Monitoring**:

- Server sends periodic ping events
- Client tracks ping count and timing
- "Last ping N seconds ago" display
- Connection health indicators

**Error Handling**:

- Network timeout detection
- Reconnection attempts (manual)
- Graceful degradation to polling
- User-friendly error messages
- Pipeline error events with cleanup
- Automatic stream termination on errors
- ASCII-safe error messages with truncation

## CSV Parser Limitations

### Simple Parser Constraints

! **No Quoted Fields**: Cannot handle embedded commas in quoted CSV fields
! **Basic Splitting**: Uses simple `split(',')` without escape handling
! **Header Required**: First row must contain column names

**Warning Display**:

> CSV Limitation: This simple parser expects comma-separated values without quoted commas. For complex CSV files with quoted fields, please ensure they are properly formatted or pre-processed.

### Workarounds

**For Complex CSV Files**:

1. **Pre-process**: Remove commas from text fields
2. **Alternative Delimiters**: Use semicolon or tab separators
3. **Backend Upload**: Use API upload endpoints instead

**Validation Checks**:

- Column count consistency across rows
- Required column presence
- Data type validation

## Responsive Design

### Breakpoints (Tailwind)

- **Mobile**: < 640px (sm)
- **Tablet**: 640px - 1024px (md/lg)
- **Desktop**: > 1024px (xl/2xl)

### Component Adaptations

**MetricCard Grid**:

- Mobile: Single column
- Tablet: 2 columns
- Desktop: 3-4 columns

**FilePicker**:

- Mobile: Stacked layout
- Desktop: Side-by-side layout

**Charts**:

- Responsive SVG viewBox scaling
- Mobile-optimized touch interactions
- Simplified displays on small screens

### Navigation

**Header Navigation**:

- Logo and title (always visible)
- Page links (Home, Calibration)
- Hamburger menu on mobile (if expanded)

**Tab Navigation**:

- Horizontal tabs on desktop
- Stacked/dropdown on mobile

## Performance Considerations

### Client-Side Processing

**Calibration Analysis**:

- JavaScript-only computation
- No server round-trips
- Large file support (tested to 10MB+)
- Progress indicators for slow devices

**Memory Usage**:

- Streaming file reading
- Chunked processing for large datasets
- Garbage collection between operations

### Chart Rendering

**SVG Benefits**:

- Vector scaling (crisp at all sizes)
- No external dependencies
- Small bundle size impact
- Accessibility support

**Performance**:

- Inline SVG (no network requests)
- Simple geometries (fast rendering)
- Static generation (no animation overhead)

## Accessibility

### Keyboard Navigation

- **Tab Order**: Logical flow through interface
- **Focus Indicators**: Clear visual focus states
- **Enter/Space**: Activate buttons and controls

### Screen Reader Support

- **ARIA Labels**: Descriptive labels for charts and controls
- **Live Regions**: Announce status changes
- **Semantic HTML**: Proper heading structure

### Visual Design

- **Color Contrast**: WCAG AA compliant
- **Font Sizes**: Minimum 14px, scalable
- **Focus States**: High-contrast outlines

## Extension Guide

### Adding New Components

**Component Structure**:

```typescript
interface NewComponentProps {
  // Define props with TypeScript
}

export default function NewComponent({ prop1, prop2 }: NewComponentProps) {
  return (
    <div className="tailwind-classes">
      {/* Component content */}
    </div>
  );
}
```

**Integration Steps**:

1. Create component in `frontend/components/`
2. Export from appropriate page
3. Add to documentation
4. Include in TypeScript builds

### Custom Charts

**SVG Template**:

```jsx
function CustomChart({ data, width = 400, height = 200 }) {
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {/* Chart elements */}
      <path d="..." fill="blue" />
      <text x="10" y="20">
        Label
      </text>
    </svg>
  );
}
```

**Best Practices**:

- Use viewBox for responsive scaling
- Include axis labels and legends
- Add hover states for interactivity
- Maintain consistent color schemes

### API Integration

**New Endpoints**:

```typescript
export async function newApiCall(data: RequestType): Promise<ResponseType> {
  const response = await fetch("/api/new-endpoint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}
```

---

**Next**: [Development Runbook](../operations/runbooks/dev.md) for local setup and workflows
