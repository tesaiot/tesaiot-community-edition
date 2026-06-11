# Certificate Management Hooks

This directory contains custom React hooks for managing certificate-related functionality in the TESA IoT Platform.

## Available Hooks

### `useCertificates`
Main hook for certificate management operations.

**Features:**
- Load and manage certificate list
- Search and filter certificates
- Handle certificate operations (renew, revoke, export)
- Calculate certificate statistics
- Track expiring certificates

**Usage:**
```typescript
const {
  certificates,
  loading,
  searchTerm,
  setSearchTerm,
  filteredCertificates,
  handleRenewCertificate,
  handleRevokeCertificate,
  certStats
} = useCertificates();
```

### `useCertificateAlerts`
Manages certificate expiration alerts and auto-renewal settings.

**Features:**
- Configure alert thresholds (90, 60, 30, 7 days)
- Manage email recipients for notifications
- Configure webhook integrations
- Set up auto-renewal policies
- Track expiring certificates

**Usage:**
```typescript
const {
  alertSettings,
  alertsEnabled,
  setAlertsEnabled,
  saveAlertSettings,
  addEmailRecipient,
  updateAutoRenewalSettings,
  getExpiringCertificates
} = useCertificateAlerts();
```

### `useCertificateAudit`
Handles certificate audit trail and activity logging.

**Features:**
- Load and filter audit events
- Export audit logs (CSV/JSON)
- Search audit history
- Track recent certificate activity
- Format event displays

**Usage:**
```typescript
const {
  auditTrail,
  loadingAudit,
  auditFilter,
  setAuditFilter,
  loadAuditTrail,
  exportAuditLog,
  searchAuditLog
} = useCertificateAudit();
```

### `useAcmeSettings`
Manages ACME (Automated Certificate Management Environment) integration.

**Features:**
- Configure ACME provider settings
- Manage ACME-enabled domains
- Auto-renewal for Let's Encrypt certificates
- Test ACME connections
- Add/remove domains

**Usage:**
```typescript
const {
  acmeEnabled,
  setAcmeEnabled,
  acmeConfig,
  acmeCertificates,
  saveAcmeConfig,
  toggleAutoRenew,
  renewAcmeCertificate,
  addAcmeDomain
} = useAcmeSettings();
```

### `useBulkOperations`
Handles bulk certificate operations.

**Features:**
- Select multiple certificates
- Bulk renew certificates
- Bulk revoke certificates
- Track operation progress
- Handle selection state

**Usage:**
```typescript
const {
  selectedCertificates,
  bulkAction,
  setBulkAction,
  toggleCertificateSelection,
  toggleSelectAll,
  handleBulkOperation,
  isSelected,
  canPerformBulkAction
} = useBulkOperations(onComplete);
```

### `useApiExplorer`
Provides API exploration and testing functionality.

**Features:**
- List available certificate API endpoints
- Execute API calls with parameters
- Copy endpoints as cURL commands
- View response data and timing
- Handle authentication automatically

**Usage:**
```typescript
const {
  apiEndpoints,
  selectedEndpoint,
  setSelectedEndpoint,
  apiResponse,
  executeApiCall,
  copyEndpointAsCurl,
  updateApiParam
} = useApiExplorer();
```

### `useCertificateAnalytics`
Provides certificate analytics and insights.

**Features:**
- Calculate certificate statistics
- Track algorithm usage distribution
- Monitor performance metrics
- Generate health and compliance scores
- Analyze certificate trends

**Usage:**
```typescript
const {
  certStats,
  distribution,
  performanceMetrics,
  getHealthScore,
  getHealthStatus,
  getComplianceScore,
  getTrends
} = useCertificateAnalytics(certificates);
```

## Best Practices

1. **Error Handling**: All hooks include built-in error handling with toast notifications
2. **Loading States**: Each hook provides loading states for async operations
3. **Memoization**: Callbacks are memoized using `useCallback` for performance
4. **Type Safety**: All hooks are fully typed with TypeScript
5. **Separation of Concerns**: Each hook focuses on a specific domain

## Integration Example

```typescript
import {
  useCertificates,
  useCertificateAlerts,
  useBulkOperations
} from '@/features/certificates/hooks';

function CertificateManagementComponent() {
  const { certificates, loading, handleRenewCertificate } = useCertificates();
  const { alertsEnabled, getExpiringCertificates } = useCertificateAlerts();
  const { selectedCertificates, handleBulkOperation } = useBulkOperations(() => {
    // Refresh certificates after bulk operation
    loadCertificates();
  });

  const expiringCerts = getExpiringCertificates(certificates);

  // Component implementation...
}
```

## Dependencies

These hooks depend on:
- `@/services/api/tesaApi` - API service for backend communication
- `sonner` - Toast notification library
- React hooks: `useState`, `useEffect`, `useCallback`