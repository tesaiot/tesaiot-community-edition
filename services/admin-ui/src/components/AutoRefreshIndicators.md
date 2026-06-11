# Auto-Refresh Visual Indicators

This document describes the visual indicators for auto-refresh functionality in telemetry dashboards.

## Overview

The auto-refresh visual indicators provide clear, unmistakable feedback to users about the real-time data refresh status. These components ensure users always know when data is being fetched, when the next refresh will occur, and if there are any issues.

## Visual Components

### 1. **LiveIndicator**
Shows the current refresh status with color-coded badges:
- **LIVE** (green with pulse) - Auto-refresh is active
- **PAUSED** (gray) - Auto-refresh is paused
- **ERROR** (red) - There's a problem with data fetching

```tsx
<LiveIndicator 
  isActive={isAutoRefresh} 
  isLoading={isLoading} 
  hasError={!!fetchError}
/>
```

### 2. **RefreshCountdown**
Displays a real-time countdown showing seconds until the next refresh:

```tsx
<RefreshCountdown 
  nextRefreshIn={nextRefreshIn} 
  isActive={isAutoRefresh} 
/>
```

### 3. **DataFetchSpinner**
Shows an animated spinner with "Fetching data..." text during loading:

```tsx
<DataFetchSpinner isLoading={isLoading} />
```

### 4. **DataUpdateFlash**
Creates a green flash effect when new data arrives:

```tsx
<DataUpdateFlash trigger={dataUpdateTrigger} />
```

### 5. **RefreshProgressBar**
Shows a visual progress bar that fills up between refreshes:

```tsx
<RefreshProgressBar
  nextRefreshIn={nextRefreshIn}
  refreshInterval={refreshInterval}
  isActive={isAutoRefresh}
/>
```

### 6. **LastUpdateTimestamp**
Displays the exact time of the last successful update:

```tsx
<LastUpdateTimestamp timestamp={lastUpdate} showSeconds={true} />
```

### 7. **AutoRefreshStatusBar**
A complete status bar combining multiple indicators:

```tsx
<AutoRefreshStatusBar
  isActive={isAutoRefresh}
  isLoading={isLoading}
  lastUpdate={lastUpdate}
  nextRefreshIn={nextRefreshIn}
  refreshInterval={refreshInterval}
  onToggle={() => setIsAutoRefresh(!isAutoRefresh)}
  hasError={!!fetchError}
  errorMessage={fetchError}
  dataCount={telemetryData.length}
/>
```

## Implementation Steps

### 1. Import Components

```tsx
import { 
  AutoRefreshStatusBar,
  DataUpdateFlash,
  RefreshProgressBar,
  LiveIndicator,
  RefreshCountdown,
  DataFetchSpinner,
  LastUpdateTimestamp,
  logRefreshEvent
} from '@/components/AutoRefreshIndicators';
```

### 2. Add Required State

```tsx
const [isAutoRefresh, setIsAutoRefresh] = useState(true);
const [isLoading, setIsLoading] = useState(false);
const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
const [dataUpdateTrigger, setDataUpdateTrigger] = useState(0);
const [fetchError, setFetchError] = useState<string | null>(null);
const nextRefreshTimeRef = useRef<number>(0);
```

### 3. Calculate Next Refresh Time

```tsx
const nextRefreshIn = useMemo(() => {
  if (!isAutoRefresh || !nextRefreshTimeRef.current) return 0;
  const now = Date.now();
  const timeSinceLastRefresh = now - nextRefreshTimeRef.current;
  return Math.max(0, refreshInterval - timeSinceLastRefresh);
}, [isAutoRefresh, refreshInterval, dataUpdateTrigger]);
```

### 4. Update Fetch Function

```tsx
const fetchData = async () => {
  setIsLoading(true);
  logRefreshEvent('Fetching data', { deviceId });
  
  try {
    const response = await fetch('/api/telemetry');
    const data = await response.json();
    
    // Trigger flash effect for new data
    setDataUpdateTrigger(prev => prev + 1);
    setLastUpdate(new Date());
    setFetchError(null);
    
    logRefreshEvent('Data received', { records: data.length });
  } catch (error) {
    setFetchError(error.message);
    logRefreshEvent('Fetch error', { error });
  } finally {
    setIsLoading(false);
  }
};
```

### 5. Set Up Auto-Refresh

```tsx
useEffect(() => {
  if (intervalRef.current) {
    clearInterval(intervalRef.current);
  }

  if (isAutoRefresh) {
    nextRefreshTimeRef.current = Date.now();
    fetchData();
    
    intervalRef.current = setInterval(() => {
      nextRefreshTimeRef.current = Date.now();
      fetchData();
    }, refreshInterval);
  }

  return () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };
}, [isAutoRefresh, fetchData, refreshInterval]);
```

## Visual Indicators in Action

### Header Section
```tsx
<div className="flex items-center justify-between">
  <div className="flex items-center gap-4">
    <h2>Telemetry Dashboard</h2>
    <LiveIndicator isActive={isAutoRefresh} isLoading={isLoading} />
  </div>
  <RefreshCountdown nextRefreshIn={nextRefreshIn} isActive={isAutoRefresh} />
</div>
```

### Status Bar
```tsx
<AutoRefreshStatusBar
  isActive={isAutoRefresh}
  isLoading={isLoading}
  lastUpdate={lastUpdate}
  nextRefreshIn={nextRefreshIn}
  refreshInterval={5000}
  onToggle={() => setIsAutoRefresh(!isAutoRefresh)}
  dataCount={data.length}
/>
```

### Data Cards with Flash
```tsx
<Card className="relative overflow-hidden">
  <DataUpdateFlash trigger={dataUpdateTrigger} />
  <CardContent>
    {/* Your content */}
  </CardContent>
</Card>
```

## Console Logging

Use `logRefreshEvent` for debugging:

```tsx
logRefreshEvent('Starting auto-refresh', { interval: 5000 });
logRefreshEvent('Fetching data', { deviceId: 'device-123' });
logRefreshEvent('New data received', { records: 50 });
logRefreshEvent('Pausing auto-refresh', { reason: 'User action' });
```

## Best Practices

1. **Always show loading state**: Use `DataFetchSpinner` or loading indicators
2. **Flash on new data only**: Only trigger flash when data actually changes
3. **Clear error display**: Show errors prominently in the status bar
4. **Consistent countdown**: Update countdown every second for smooth UX
5. **Console logging**: Log all refresh events for debugging
6. **Graceful degradation**: Handle errors without breaking the UI
7. **Visual hierarchy**: Use size and color to indicate importance

## Color Scheme

- **Green**: Active, live, success states
- **Red**: Errors, stopped states  
- **Yellow/Orange**: Warnings, degraded performance
- **Gray**: Paused, inactive states
- **Blue**: Informational states

## Animation Guidelines

- **Pulse**: For live indicators (1s duration)
- **Spin**: For loading states (1s rotation)
- **Flash**: For data updates (500ms fade)
- **Progress**: Linear fill for countdown

## Accessibility

- All indicators include text labels
- Color is not the only differentiator
- Animations respect prefers-reduced-motion
- Status changes are announced to screen readers