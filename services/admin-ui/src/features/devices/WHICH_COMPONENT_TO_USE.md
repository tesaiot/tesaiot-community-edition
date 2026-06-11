# Device Management Components Guide

## Active Component (DO NOT CHANGE)
**Primary Component**: `DeviceManagementWithCerts.tsx`
- Used in: `/devices` route (see routing/TesaRouting.tsx)
- Purpose: Full device management with certificate features
- Last updated: June 1, 2025

## Deprecated Components (DO NOT USE)
1. `DeviceManagement.tsx` - OLD VERSION, not used
2. `CompleteDeviceManagement.tsx` - Test version, not in routing

## Data Mapping Requirements
All device components MUST map API response fields:
```typescript
{
  id: device.device_id || device._id || device.id,
  device_id: device.device_id || device._id || device.id,
  // ... other fields
}
```

## API Response Format
```json
{
  "_id": "683b2291f21bc6af35ad8767",
  "device_id": "BDH-Test-Device-001",
  "name": "Device Name",
  // ... other fields
}
```

## CRITICAL: Before editing any device component, CHECK THE ROUTING!