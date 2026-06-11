# Certificate Management Utilities

This directory contains utility functions and types for the Certificate Management feature.

## Structure

```
utils/
├── alertSettings.ts      # Alert configuration types and utilities
├── apiEndpoints.ts       # API endpoint configurations
├── certificateOperations.ts  # Certificate operations (download, copy, execute)
├── certificateStats.ts   # Certificate statistics calculations
├── certificateStatus.ts  # Certificate status utilities and badges
├── index.ts             # Central export point
└── README.md            # This file
```

## Modules

### certificateStatus.ts
Utilities for certificate status display and calculations:
- `getStatusBadge()` - Returns a React badge component for certificate status
- `getDaysUntilExpiry()` - Calculates days until certificate expiry
- `getExpiryBadge()` - Returns a React badge component for expiry date
- `formatDate()` - Formats date strings
- `isExpiringSoon()` - Checks if certificate expires within 30 days

### certificateStats.ts
Utilities for calculating certificate statistics:
- `calculateCertificateStats()` - Calculates comprehensive certificate statistics
- `calculatePercentage()` - Calculates percentage with fixed decimal
- `getExpiringCertificates()` - Filters certificates expiring within threshold
- `groupByAlgorithm()` - Groups certificates by algorithm type
- `filterCertificates()` - Filters certificates by search term and status

### certificateOperations.ts
Utilities for certificate operations:
- `downloadCertificateBundle()` - Downloads certificate bundle as ZIP
- `copyCurlCommand()` - Copies cURL command to clipboard
- `executeApiRequest()` - Executes API requests with timing
- `formatBytes()` - Formats byte values to human-readable sizes

### apiEndpoints.ts
API endpoint configurations:
- `certificateApiEndpoints` - Array of certificate API endpoint definitions
- `getBaseUrl()` - Returns the base URL for API requests
- `getCurlExamples()` - Generates cURL command examples

### alertSettings.ts
Alert settings types and utilities:
- Types: `AlertSettings`, `AlertThresholds`, `AutoRenewalSettings`, `AcmeSettings`, `AcmeConfig`
- `defaultAlertSettings` - Default alert configuration
- `defaultAcmeSettings` - Default ACME configuration
- `saveAlertSettingsToLocalStorage()` - Saves alert settings
- `loadAlertSettingsFromLocalStorage()` - Loads alert settings

## Usage

Import utilities from the central export point:

```typescript
import {
  getStatusBadge,
  calculateCertificateStats,
  downloadCertificateBundle,
  certificateApiEndpoints,
  defaultAlertSettings
} from './utils';
```

Or import from specific modules:

```typescript
import { getStatusBadge } from './utils/certificateStatus';
import { calculateCertificateStats } from './utils/certificateStats';
```

## Type Safety

All utilities are written in TypeScript with proper type annotations. Types are exported alongside the utility functions for use in consuming components.

## Testing

When adding new utilities, ensure they:
1. Have proper TypeScript types
2. Handle edge cases gracefully
3. Are pure functions when possible
4. Have clear, descriptive names
5. Include JSDoc comments for documentation