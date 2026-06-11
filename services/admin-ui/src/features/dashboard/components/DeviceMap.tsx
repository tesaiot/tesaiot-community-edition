/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { MapPin, Activity, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import 'leaflet/dist/leaflet.css';
import { tesaApi } from '@/services/api/tesaApi';
import { useAuth } from '@/hooks/useAuth';

// Fix for default Leaflet markers in React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom icons for different device states
const createDeviceIcon = (status: string) => {
  const color = status === 'active' ? '#22c55e' : status === 'error' ? '#ef4444' : '#6b7280';
  return L.divIcon({
    html: `<div style="
      width: 20px; 
      height: 20px; 
      border-radius: 50%; 
      background-color: ${color}; 
      border: 3px solid white; 
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        width: 8px; 
        height: 8px; 
        border-radius: 50%; 
        background-color: white;
        ${status === 'active' ? 'animation: pulse 2s infinite;' : ''}
      "></div>
    </div>
    <style>
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
    </style>`,
    className: 'custom-device-marker',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
};

interface Device {
  id: string;
  name: string;
  type: string;
  status: string;
  location?: {
    latitude?: number;
    longitude?: number;
    name?: string;
  };
  lastSeen: string;
  metadata?: any;
}

interface DeviceMapProps {
  devices: Device[];
}

export const DeviceMap: React.FC<DeviceMapProps> = ({ devices }) => {
  const { user } = useAuth();
  const [realDeviceLocations, setRealDeviceLocations] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Fetch real device locations from API
  useEffect(() => {
    const fetchDeviceLocations = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch devices with location data from the API
        const response = await tesaApi.get('/devices', {
          params: {
            include_location: true,
            limit: 100
          }
        });
        
        if (response.data?.data?.devices) {
          const devicesData = response.data.data.devices;
          
          // Filter devices with valid location data
          const devicesWithValidLocation = devicesData.filter((device: any) => 
            device.location?.coordinates?.latitude && 
            device.location?.coordinates?.longitude &&
            !isNaN(device.location.coordinates.latitude) &&
            !isNaN(device.location.coordinates.longitude)
          ).map((device: any) => ({
            ...device,
            location: {
              latitude: device.location.coordinates.latitude,
              longitude: device.location.coordinates.longitude,
              name: device.location.address || device.location.name || device.name
            }
          }));
          
          setRealDeviceLocations(devicesWithValidLocation);
        }
      } catch (err) {
        console.error('Failed to fetch device locations:', err);
        setError('Failed to load device locations');
      } finally {
        setLoading(false);
      }
    };
    
    fetchDeviceLocations();
    
    // Refresh locations every 5 minutes
    const interval = setInterval(fetchDeviceLocations, 300000);
    return () => clearInterval(interval);
  }, [user]);
  
  // Sample demo locations for TESA IoT Platform showcase
  const demoLocations = [
    // Thailand
    { lat: 13.7563, lng: 100.5018, name: "Bangkok, Thailand", country: "Thailand" },
    { lat: 18.7883, lng: 98.9853, name: "Chiang Mai, Thailand", country: "Thailand" },
    { lat: 7.8804, lng: 98.3923, name: "Phuket, Thailand", country: "Thailand" },
    { lat: 12.9236, lng: 100.8845, name: "Pattaya, Thailand", country: "Thailand" },
    
    // Singapore & Malaysia
    { lat: 1.3521, lng: 103.8198, name: "Singapore", country: "Singapore" },
    { lat: 3.1390, lng: 101.6869, name: "Kuala Lumpur, Malaysia", country: "Malaysia" },
    
    // ASEAN Countries
    { lat: 14.5995, lng: 120.9842, name: "Manila, Philippines", country: "Philippines" },
    { lat: -6.2088, lng: 106.8456, name: "Jakarta, Indonesia", country: "Indonesia" },
    { lat: 10.8231, lng: 106.6297, name: "Ho Chi Minh City, Vietnam", country: "Vietnam" },
    { lat: 21.0285, lng: 105.8542, name: "Hanoi, Vietnam", country: "Vietnam" },
    
    // EU Countries
    { lat: 52.3676, lng: 4.9041, name: "Amsterdam, Netherlands", country: "Netherlands" },
    { lat: 52.5200, lng: 13.4050, name: "Berlin, Germany", country: "Germany" },
    { lat: 48.8566, lng: 2.3522, name: "Paris, France", country: "France" },
    { lat: 41.9028, lng: 12.4964, name: "Rome, Italy", country: "Italy" },
    
    // USA
    { lat: 40.7128, lng: -74.0060, name: "New York, USA", country: "USA" },
    { lat: 37.7749, lng: -122.4194, name: "San Francisco, USA", country: "USA" },
    { lat: 34.0522, lng: -118.2437, name: "Los Angeles, USA", country: "USA" },
    { lat: 41.8781, lng: -87.6298, name: "Chicago, USA", country: "USA" }
  ];

  // Use real device locations if available, otherwise use provided devices
  let devicesWithLocation = realDeviceLocations.length > 0 ? realDeviceLocations : devices.filter(device => 
    device.location?.latitude && 
    device.location?.longitude &&
    !isNaN(device.location.latitude) &&
    !isNaN(device.location.longitude)
  );

  // If still no devices have location data, create demo devices with sample locations
  if (devicesWithLocation.length === 0 && devices.length > 0 && !loading) {
    devicesWithLocation = devices.slice(0, Math.min(devices.length, demoLocations.length)).map((device, index) => {
      const demoLocation = demoLocations[index];
      return {
        ...device,
        location: {
          latitude: demoLocation.lat + (Math.random() - 0.5) * 0.1, // Add small random offset
          longitude: demoLocation.lng + (Math.random() - 0.5) * 0.1,
          name: demoLocation.name
        }
      };
    });
  }

  // Center map on Thailand (TESA headquarters region)
  const thailandCenter: [number, number] = [13.7563, 100.5018];
  
  // Calculate center based on devices or use Thailand center
  const getMapCenter = (): [number, number] => {
    if (devicesWithLocation.length === 0) return thailandCenter;
    
    // If we have devices globally, center on Thailand but zoom out to show all
    const hasGlobalDevices = devicesWithLocation.some(device => 
      Math.abs(device.location!.latitude! - thailandCenter[0]) > 10 ||
      Math.abs(device.location!.longitude! - thailandCenter[1]) > 10
    );
    
    if (hasGlobalDevices) {
      return thailandCenter; // Keep Thailand as focal point
    }
    
    // If devices are regional, center on them
    const avgLat = devicesWithLocation.reduce((sum, device) => 
      sum + device.location!.latitude!, 0) / devicesWithLocation.length;
    const avgLng = devicesWithLocation.reduce((sum, device) => 
      sum + device.location!.longitude!, 0) / devicesWithLocation.length;
    
    return [avgLat, avgLng];
  };

  // Calculate appropriate zoom level for global view
  const getZoomLevel = (): number => {
    if (devicesWithLocation.length === 0) return 6; // Thailand view
    if (devicesWithLocation.length === 1) return 10;
    
    // Check if devices span globally
    const lats = devicesWithLocation.map(d => d.location!.latitude!);
    const lngs = devicesWithLocation.map(d => d.location!.longitude!);
    const latRange = Math.max(...lats) - Math.min(...lats);
    const lngRange = Math.max(...lngs) - Math.min(...lngs);
    const maxRange = Math.max(latRange, lngRange);
    
    // Global distribution
    if (maxRange > 50) return 2; // World view
    if (maxRange > 20) return 3; // Continental view
    if (maxRange > 10) return 4; // Regional view
    if (maxRange > 5) return 5;  // Country view
    if (maxRange > 1) return 6;  // Province view
    return 8; // City view
  };

  const mapCenter = getMapCenter();
  const zoomLevel = getZoomLevel();

  if (devicesWithLocation.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-muted rounded-lg p-6">
        <MapPin className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground text-center">
          No devices with location data found
        </p>
        <p className="text-sm text-muted-foreground text-center mt-2">
          Add latitude and longitude to device metadata to see them on the map
        </p>
      </div>
    );
  }

  return (
    <div className="h-full w-full rounded-lg overflow-hidden relative">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}
      
      {error && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-destructive/90 text-destructive-foreground px-4 py-2 rounded-md z-10">
          {error}
        </div>
      )}
      
      <MapContainer
        center={mapCenter}
        zoom={zoomLevel}
        className="h-full w-full"
        zoomControl={true}
      >
        {/* OpenStreetMap tile layer - Free, no API key required */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        
        {/* Device markers */}
        {devicesWithLocation.map((device) => (
          <Marker
            key={device.id}
            position={[device.location!.latitude!, device.location!.longitude!]}
            icon={createDeviceIcon(device.status)}
          >
            <Popup>
              <div className="p-2 min-w-[200px]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex items-center gap-1">
                    {device.status === 'active' ? (
                      <Activity className="h-4 w-4 text-green-600" />
                    ) : device.status === 'error' ? (
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                    ) : (
                      <div className="h-4 w-4 rounded-full bg-gray-400" />
                    )}
                  </div>
                  <h3 className="font-semibold text-sm">{device.name}</h3>
                </div>
                
                <div className="space-y-1 text-xs">
                  <p><span className="font-medium">Type:</span> {device.type}</p>
                  <p><span className="font-medium">Location:</span> {device.location?.name || 'Custom coordinates'}</p>
                  <p>
                    <span className="font-medium">Coordinates:</span> 
                    <br />
                    {device.location!.latitude!.toFixed(6)}, {device.location!.longitude!.toFixed(6)}
                  </p>
                  <p><span className="font-medium">Last seen:</span> {new Date(device.lastSeen).toLocaleString()}</p>
                  
                  <div className="mt-2">
                    <Badge variant={
                      device.status === 'active' ? 'default' : 
                      device.status === 'error' ? 'destructive' : 'secondary'
                    } className="text-xs">
                      {device.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      
      {/* Map info footer */}
      <div className="absolute bottom-2 left-2 bg-card/90 border border-border backdrop-blur-sm rounded px-2 py-1 text-xs text-muted-foreground">
        Showing {devicesWithLocation.length} of {devices.length} devices
      </div>
    </div>
  );
};
