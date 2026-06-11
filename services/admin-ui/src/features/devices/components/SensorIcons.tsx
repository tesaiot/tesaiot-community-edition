/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';

interface IconProps {
  width?: number;
  height?: number;
  className?: string;
}

// Environmental Sensors
export const TemperatureIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Thermometer body */}
    <rect x="35" y="15" width="30" height="55" rx="15" fill="#f8f9fa" stroke="#495057" strokeWidth="2"/>
    {/* Mercury bulb */}
    <circle cx="50" cy="75" r="15" fill="#dc3545"/>
    {/* Mercury column */}
    <rect x="45" y="30" width="10" height="40" fill="#dc3545"/>
    {/* Scale markings */}
    <g stroke="#495057" strokeWidth="2" strokeLinecap="round">
      <line x1="25" y1="25" x2="30" y2="25"/>
      <line x1="25" y1="35" x2="30" y2="35"/>
      <line x1="25" y1="45" x2="30" y2="45"/>
      <line x1="25" y1="55" x2="30" y2="55"/>
    </g>
    {/* Temperature label */}
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">°C</text>
  </svg>
);

export const HumidityIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Water drop shape */}
    <path d="M50 15 C50 15 25 35 25 55 C25 70 35 80 50 80 C65 80 75 70 75 55 C75 35 50 15 50 15 Z" 
          fill="#0ea5e9" stroke="#0284c7" strokeWidth="2"/>
    {/* Water waves inside */}
    <path d="M35 50 Q45 45 55 50 Q65 55 75 50" fill="none" stroke="white" strokeWidth="2" opacity="0.7"/>
    <path d="M30 60 Q40 55 50 60 Q60 65 70 60" fill="none" stroke="white" strokeWidth="2" opacity="0.5"/>
    {/* Humidity percentage */}
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#0284c7" fontWeight="bold">%RH</text>
  </svg>
);

export const PressureIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="45" r="30" fill="#9775fa" stroke="#7950f2" strokeWidth="2"/>
    <circle cx="50" cy="45" r="22" fill="none" stroke="white" strokeWidth="2"/>
    <line x1="50" y1="45" x2="50" y2="28" stroke="white" strokeWidth="3" strokeLinecap="round"/>
    <line x1="50" y1="45" x2="62" y2="35" stroke="white" strokeWidth="3" strokeLinecap="round"/>
    <circle cx="50" cy="45" r="3" fill="white"/>
  </svg>
);

export const CO2Icon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* CO2 sensor housing */}
    <rect x="15" y="25" width="70" height="45" rx="8" fill="#f8f9fa" stroke="#495057" strokeWidth="2"/>
    {/* Sensor elements */}
    <circle cx="30" cy="47" r="8" fill="#fbbf24"/>
    <circle cx="50" cy="47" r="8" fill="#f59e0b"/>
    <circle cx="70" cy="47" r="8" fill="#d97706"/>
    {/* CO2 molecules visualization */}
    <g stroke="#6b7280" strokeWidth="1" fill="none">
      <circle cx="25" cy="15" r="3" fill="#ef4444"/>
      <circle cx="35" cy="15" r="3" fill="#6b7280"/>
      <circle cx="45" cy="15" r="3" fill="#ef4444"/>
      <circle cx="60" cy="15" r="3" fill="#ef4444"/>
      <circle cx="70" cy="15" r="3" fill="#6b7280"/>
      <circle cx="80" cy="15" r="3" fill="#ef4444"/>
    </g>
    <text x="50" y="88" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">CO₂</text>
  </svg>
);

export const VOCIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* VOC sensor housing */}
    <rect x="20" y="25" width="60" height="40" rx="8" fill="#fd7e14" stroke="#e8590c" strokeWidth="2"/>
    {/* Detection chambers */}
    <circle cx="35" cy="45" r="6" fill="#e8590c"/>
    <circle cx="50" cy="45" r="6" fill="#e8590c"/>
    <circle cx="65" cy="45" r="6" fill="#e8590c"/>
    {/* Gas molecules rising */}
    <g stroke="#ffa94d" strokeWidth="2" fill="none" opacity="0.8">
      <path d="M30 25 Q30 15 35 15 Q40 15 40 25"/>
      <path d="M45 25 Q45 15 50 15 Q55 15 55 25"/>
      <path d="M60 25 Q60 15 65 15 Q70 15 70 25"/>
    </g>
    {/* Gas molecules */}
    <g fill="#ffa94d" opacity="0.6">
      <circle cx="32" cy="12" r="2"/>
      <circle cx="38" cy="8" r="1.5"/>
      <circle cx="47" cy="10" r="2"/>
      <circle cx="53" cy="6" r="1.5"/>
      <circle cx="62" cy="9" r="2"/>
      <circle cx="68" cy="5" r="1.5"/>
    </g>
    <text x="50" y="85" textAnchor="middle" fontSize="10" fill="#e8590c" fontWeight="bold">VOC</text>
  </svg>
);

export const PMSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* PM sensor housing */}
    <rect x="20" y="25" width="60" height="45" rx="5" fill="#ced4da" stroke="#868e96" strokeWidth="2"/>
    {/* Air intake */}
    <rect x="15" y="40" width="8" height="20" rx="2" fill="#868e96"/>
    <rect x="77" y="40" width="8" height="20" rx="2" fill="#868e96"/>
    {/* Particle detection area */}
    <rect x="30" y="35" width="40" height="30" rx="3" fill="#f8f9fa" stroke="#868e96" strokeWidth="1"/>
    {/* Particles of different sizes */}
    <g fill="#6c757d">
      <circle cx="38" cy="45" r="4" opacity="0.8"/>
      <circle cx="50" cy="50" r="6" opacity="0.9"/>
      <circle cx="62" cy="43" r="3" opacity="0.7"/>
      <circle cx="55" cy="57" r="2" opacity="0.6"/>
      <circle cx="43" cy="55" r="3" opacity="0.8"/>
      <circle cx="35" cy="52" r="2" opacity="0.5"/>
      <circle cx="65" cy="52" r="2" opacity="0.6"/>
    </g>
    {/* Laser beam indicator */}
    <line x1="25" y1="50" x2="75" y2="50" stroke="#ff6b6b" strokeWidth="1" opacity="0.6" strokeDasharray="2,2"/>
    <text x="50" y="88" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">PM2.5</text>
  </svg>
);

// Motion & Position Sensors
export const AccelerometerIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Accelerometer chip */}
    <rect x="25" y="25" width="50" height="50" rx="8" fill="#fa5252" stroke="#c92a2a" strokeWidth="2"/>
    {/* Internal MEMS structure */}
    <rect x="35" y="35" width="30" height="30" rx="3" fill="#c92a2a" stroke="#a61e1e" strokeWidth="1"/>
    <circle cx="50" cy="50" r="8" fill="#ff6b6b"/>
    {/* X-axis arrow */}
    <line x1="75" y1="50" x2="90" y2="50" stroke="#0c8599" strokeWidth="4" markerEnd="url(#arrowX)"/>
    {/* Y-axis arrow */}
    <line x1="50" y1="25" x2="50" y2="10" stroke="#087f5b" strokeWidth="4" markerEnd="url(#arrowY)"/>
    {/* Z-axis arrow (diagonal to show 3D) */}
    <line x1="65" y1="65" x2="78" y2="78" stroke="#862e9c" strokeWidth="4" markerEnd="url(#arrowZ)"/>
    <defs>
      <marker id="arrowX" markerWidth="12" markerHeight="12" refX="10" refY="4" orient="auto" fill="#0c8599">
        <polygon points="0 0, 12 4, 0 8"/>
      </marker>
      <marker id="arrowY" markerWidth="12" markerHeight="12" refX="4" refY="10" orient="auto" fill="#087f5b">
        <polygon points="0 12, 4 0, 8 12"/>
      </marker>
      <marker id="arrowZ" markerWidth="12" markerHeight="12" refX="10" refY="4" orient="auto" fill="#862e9c">
        <polygon points="0 0, 12 4, 0 8"/>
      </marker>
    </defs>
    <text x="92" y="55" fontSize="14" fill="#0c8599" fontWeight="bold">X</text>
    <text x="46" y="8" fontSize="14" fill="#087f5b" fontWeight="bold">Y</text>
    <text x="82" y="85" fontSize="14" fill="#862e9c" fontWeight="bold">Z</text>
  </svg>
);

export const GyroscopeIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Outer gyroscope housing */}
    <circle cx="50" cy="50" r="40" fill="none" stroke="#7950f2" strokeWidth="3"/>
    {/* Gyroscope rings showing 3-axis rotation */}
    <ellipse cx="50" cy="50" rx="32" ry="15" fill="none" stroke="#7950f2" strokeWidth="2" opacity="0.8"/>
    <ellipse cx="50" cy="50" rx="15" ry="32" fill="none" stroke="#5f3dc4" strokeWidth="2" opacity="0.8"/>
    <ellipse cx="50" cy="50" rx="25" ry="25" fill="none" stroke="#6741d9" strokeWidth="2" transform="rotate(45 50 50)" opacity="0.6"/>
    {/* Central rotor */}
    <circle cx="50" cy="50" r="12" fill="#5f3dc4" stroke="#4c2a85" strokeWidth="2"/>
    <circle cx="50" cy="50" r="6" fill="white"/>
    <circle cx="50" cy="50" r="2" fill="#5f3dc4"/>
    {/* Rotation indicators */}
    <g stroke="#7950f2" strokeWidth="2" fill="none" opacity="0.5">
      <path d="M35 20 Q20 35 35 50" strokeDasharray="3,3"/>
      <path d="M65 80 Q80 65 65 50" strokeDasharray="3,3"/>
      <path d="M80 35 Q65 20 50 35" strokeDasharray="3,3"/>
    </g>
    <text x="50" y="92" textAnchor="middle" fontSize="10" fill="#5f3dc4" fontWeight="bold">GYRO</text>
  </svg>
);

export const PIRMotionIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* PIR sensor dome */}
    <circle cx="50" cy="45" r="35" fill="#f8f9fa" stroke="#868e96" strokeWidth="2"/>
    {/* Fresnel lens pattern */}
    <g fill="none" stroke="#adb5bd" strokeWidth="1" opacity="0.6">
      <circle cx="50" cy="45" r="25"/>
      <circle cx="50" cy="45" r="20"/>
      <circle cx="50" cy="45" r="15"/>
      <circle cx="50" cy="45" r="10"/>
    </g>
    {/* Detection zones */}
    <path d="M50 45 L25 20 A30 30 0 0 1 75 20 Z" fill="#ff6b6b" opacity="0.4"/>
    <path d="M50 45 L25 70 A30 30 0 0 0 75 70 Z" fill="#ff6b6b" opacity="0.4"/>
    {/* Central sensor */}
    <circle cx="50" cy="45" r="8" fill="#c92a2a"/>
    <circle cx="50" cy="45" r="4" fill="#ff6b6b"/>
    {/* Motion waves */}
    <g stroke="#ff6b6b" strokeWidth="2" fill="none" opacity="0.7">
      <path d="M15 75 Q30 65 45 70 Q60 65 85 75" strokeDasharray="4,4"/>
      <path d="M20 80 Q35 70 50 75 Q65 70 80 80" strokeDasharray="4,4"/>
    </g>
    {/* Human figure */}
    <g fill="#495057" opacity="0.6">
      <circle cx="30" cy="25" r="3"/>
      <rect x="28" y="28" width="4" height="8" rx="1"/>
      <rect x="26" y="32" width="2" height="6" rx="1"/>
      <rect x="32" y="32" width="2" height="6" rx="1"/>
    </g>
    <text x="50" y="93" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">PIR</text>
  </svg>
);

// Light & Optical Sensors
export const LightSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Light sensor photodiode */}
    <circle cx="50" cy="45" r="25" fill="#ffd43b" stroke="#fab005" strokeWidth="3"/>
    <circle cx="50" cy="45" r="18" fill="#fff3cd" stroke="#fab005" strokeWidth="1"/>
    <circle cx="50" cy="45" r="10" fill="#fab005"/>
    {/* Light rays */}
    <g stroke="#fab005" strokeWidth="4" strokeLinecap="round">
      <line x1="50" y1="10" x2="50" y2="2"/>
      <line x1="50" y1="80" x2="50" y2="88"/>
      <line x1="15" y1="45" x2="7" y2="45"/>
      <line x1="85" y1="45" x2="93" y2="45"/>
      <line x1="25" y1="20" x2="18" y2="13"/>
      <line x1="75" y1="70" x2="82" y2="77"/>
      <line x1="75" y1="20" x2="82" y2="13"/>
      <line x1="25" y1="70" x2="18" y2="77"/>
    </g>
    {/* Additional diagonal rays */}
    <g stroke="#ffc107" strokeWidth="3" strokeLinecap="round" opacity="0.7">
      <line x1="35" y1="15" x2="32" y2="12"/>
      <line x1="65" y1="15" x2="68" y2="12"/>
      <line x1="35" y1="75" x2="32" y2="78"/>
      <line x1="65" y1="75" x2="68" y2="78"/>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#fab005" fontWeight="bold">LUX</text>
  </svg>
);

export const UVSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* UV sensor detector */}
    <circle cx="50" cy="40" r="30" fill="#e599f7" stroke="#9c36b5" strokeWidth="3"/>
    <circle cx="50" cy="40" r="22" fill="#f3e5f5" stroke="#9c36b5" strokeWidth="1"/>
    <circle cx="50" cy="40" r="12" fill="#9c36b5"/>
    {/* UV wavelength patterns */}
    <g stroke="#f783ac" strokeWidth="3" strokeLinecap="round" fill="none">
      <path d="M25 25 Q40 15 55 25 Q70 15 85 25"/>
      <path d="M25 35 Q40 25 55 35 Q70 25 85 35"/>
      <path d="M25 45 Q40 35 55 45 Q70 35 85 45"/>
      <path d="M25 55 Q40 45 55 55 Q70 45 85 55"/>
    </g>
    {/* UV radiation indicators */}
    <g fill="#e91e63" opacity="0.6">
      <circle cx="30" cy="20" r="2"/>
      <circle cx="70" cy="20" r="2"/>
      <circle cx="20" cy="40" r="2"/>
      <circle cx="80" cy="40" r="2"/>
      <circle cx="30" cy="60" r="2"/>
      <circle cx="70" cy="60" r="2"/>
    </g>
    {/* Warning symbol */}
    <g stroke="#ff9800" strokeWidth="2" fill="none">
      <circle cx="50" cy="75" r="8"/>
      <path d="M47 70 L53 70 L52 78 L48 78 Z" fill="#ff9800"/>
      <circle cx="50" cy="82" r="1" fill="#ff9800"/>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="12" fill="#9c36b5" fontWeight="bold">UV</text>
  </svg>
);

export const ColorSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Color sensor housing */}
    <rect x="20" y="20" width="60" height="60" rx="8" fill="#868e96" stroke="#495057" strokeWidth="2"/>
    <rect x="25" y="25" width="50" height="50" rx="5" fill="#f8f9fa"/>
    {/* RGB photodiodes */}
    <circle cx="38" cy="38" r="10" fill="#ff6b6b" stroke="#dc3545" strokeWidth="2"/>
    <circle cx="62" cy="38" r="10" fill="#51cf66" stroke="#28a745" strokeWidth="2"/>
    <circle cx="50" cy="62" r="10" fill="#339af0" stroke="#007bff" strokeWidth="2"/>
    {/* Light sensor in center */}
    <circle cx="50" cy="45" r="6" fill="#495057" stroke="#212529" strokeWidth="1"/>
    <circle cx="50" cy="45" r="3" fill="#fff"/>
    {/* Color mixing visualization */}
    <g opacity="0.4">
      <ellipse cx="45" cy="42" rx="8" ry="6" fill="#ff6b6b" transform="rotate(-30 45 42)"/>
      <ellipse cx="55" cy="42" rx="8" ry="6" fill="#51cf66" transform="rotate(30 55 42)"/>
      <ellipse cx="50" cy="52" rx="8" ry="6" fill="#339af0"/>
    </g>
    <text x="50" y="93" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">RGB</text>
  </svg>
);

// Distance & Proximity Sensors
export const UltrasonicIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Ultrasonic sensor housing */}
    <rect x="10" y="30" width="25" height="40" rx="5" fill="#495057" stroke="#212529" strokeWidth="2"/>
    {/* Transmitter and receiver */}
    <circle cx="18" cy="45" r="10" fill="#e9ecef" stroke="#868e96" strokeWidth="2"/>
    <circle cx="27" cy="55" r="10" fill="#e9ecef" stroke="#868e96" strokeWidth="2"/>
    {/* Transducer patterns */}
    <g fill="#495057">
      <circle cx="18" cy="45" r="6"/>
      <circle cx="27" cy="55" r="6"/>
      <circle cx="18" cy="45" r="3" fill="#6c757d"/>
      <circle cx="27" cy="55" r="3" fill="#6c757d"/>
    </g>
    {/* Ultrasonic waves */}
    <g stroke="#339af0" strokeWidth="3" fill="none" opacity="0.8">
      <path d="M35 50 Q50 45 65 40" strokeDasharray="3,3"/>
      <path d="M35 50 Q50 50 65 50" strokeDasharray="3,3"/>
      <path d="M35 50 Q50 55 65 60" strokeDasharray="3,3"/>
    </g>
    <g stroke="#74c0fc" strokeWidth="2" fill="none" opacity="0.6">
      <path d="M35 50 Q55 40 75 30" strokeDasharray="4,4"/>
      <path d="M35 50 Q55 50 75 50" strokeDasharray="4,4"/>
      <path d="M35 50 Q55 60 75 70" strokeDasharray="4,4"/>
    </g>
    {/* Target/obstacle */}
    <rect x="75" y="35" width="6" height="30" rx="2" fill="#ff6b6b" stroke="#dc3545" strokeWidth="2"/>
    {/* Echo return waves */}
    <g stroke="#28a745" strokeWidth="2" fill="none" opacity="0.5" strokeDasharray="2,2">
      <path d="M75 40 Q55 45 35 50"/>
      <path d="M75 50 Q55 50 35 50"/>
      <path d="M75 60 Q55 55 35 50"/>
    </g>
    <text x="50" y="93" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">US</text>
  </svg>
);

export const LIDARIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* LIDAR housing */}
    <circle cx="50" cy="50" r="35" fill="#212529" stroke="#495057" strokeWidth="3"/>
    <circle cx="50" cy="50" r="25" fill="#495057" stroke="#6c757d" strokeWidth="2"/>
    <circle cx="50" cy="50" r="15" fill="#6c757d"/>
    {/* Laser emitter */}
    <circle cx="50" cy="50" r="8" fill="#ff6b6b" stroke="#dc3545" strokeWidth="2"/>
    <circle cx="50" cy="50" r="4" fill="#fff"/>
    {/* Rotating laser beams */}
    <g stroke="#ff6b6b" strokeWidth="3" opacity="0.8">
      <line x1="50" y1="50" x2="50" y2="15" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="75" y2="25" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="85" y2="50" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="75" y2="75" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="50" y2="85" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="25" y2="75" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="15" y2="50" strokeDasharray="3,3"/>
      <line x1="50" y1="50" x2="25" y2="25" strokeDasharray="3,3"/>
    </g>
    {/* Additional scanning beams */}
    <g stroke="#ffc107" strokeWidth="2" opacity="0.5">
      <line x1="50" y1="50" x2="62" y2="19" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="81" y2="38" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="81" y2="62" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="62" y2="81" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="38" y2="81" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="19" y2="62" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="19" y2="38" strokeDasharray="2,2"/>
      <line x1="50" y1="50" x2="38" y2="19" strokeDasharray="2,2"/>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">LIDAR</text>
  </svg>
);

// Water & Liquid Sensors
export const pHSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* pH probe body */}
    <rect x="35" y="15" width="30" height="55" rx="15" fill="#e9ecef" stroke="#868e96" strokeWidth="2"/>
    {/* Cable */}
    <rect x="42" y="70" width="16" height="25" fill="#495057"/>
    {/* Glass electrode */}
    <rect x="40" y="25" width="20" height="35" rx="10" fill="#74c0fc" stroke="#0ea5e9" strokeWidth="2"/>
    {/* pH indicator liquid */}
    <rect x="42" y="30" width="16" height="25" rx="8" fill="#ff6b6b" opacity="0.7"/>
    {/* Measurement tip */}
    <ellipse cx="50" cy="58" rx="8" ry="4" fill="#495057"/>
    {/* pH scale */}
    <g fill="#495057" fontSize="10" fontWeight="bold" textAnchor="middle">
      <text x="20" y="25">0</text>
      <text x="20" y="40">7</text>
      <text x="20" y="55">14</text>
    </g>
    {/* Scale lines */}
    <g stroke="#868e96" strokeWidth="1">
      <line x1="25" y1="22" x2="30" y2="22"/>
      <line x1="25" y1="37" x2="30" y2="37"/>
      <line x1="25" y1="52" x2="30" y2="52"/>
    </g>
    {/* Digital display */}
    <rect x="70" y="30" width="25" height="15" rx="2" fill="#212529" stroke="#495057" strokeWidth="1"/>
    <text x="82" y="40" textAnchor="middle" fontSize="8" fill="#51cf66" fontFamily="monospace">7.4</text>
    <text x="50" y="95" textAnchor="middle" fontSize="12" fill="#495057" fontWeight="bold">pH</text>
  </svg>
);

export const FlowSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Flow sensor pipe */}
    <rect x="10" y="35" width="80" height="30" rx="15" fill="#e9ecef" stroke="#868e96" strokeWidth="3"/>
    {/* Inner pipe */}
    <rect x="15" y="40" width="70" height="20" rx="10" fill="#74c0fc" opacity="0.3"/>
    {/* Turbine/impeller */}
    <circle cx="50" cy="50" r="18" fill="#495057" stroke="#212529" strokeWidth="2"/>
    {/* Turbine blades */}
    <g fill="white" stroke="#212529" strokeWidth="1">
      <path d="M50 32 L58 45 L50 50 L42 45 Z"/>
      <path d="M68 50 L55 58 L50 50 L55 42 Z"/>
      <path d="M50 68 L42 55 L50 50 L58 55 Z"/>
      <path d="M32 50 L45 42 L50 50 L45 58 Z"/>
    </g>
    {/* Flow direction arrows */}
    <g fill="#339af0">
      <path d="M15 50 L25 45 L25 47 L30 47 L30 53 L25 53 L25 55 Z"/>
      <path d="M70 47 L80 47 L80 53 L75 53 L75 55 L85 50 L75 45 L75 47 Z"/>
    </g>
    {/* Flow lines */}
    <g stroke="#339af0" strokeWidth="2" fill="none" opacity="0.6">
      <path d="M20 45 Q30 42 40 45" strokeDasharray="3,3"/>
      <path d="M60 45 Q70 42 80 45" strokeDasharray="3,3"/>
      <path d="M20 55 Q30 58 40 55" strokeDasharray="3,3"/>
      <path d="M60 55 Q70 58 80 55" strokeDasharray="3,3"/>
    </g>
    {/* Sensor housing */}
    <rect x="42" y="20" width="16" height="15" rx="3" fill="#495057" stroke="#212529" strokeWidth="1"/>
    <text x="50" y="93" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">FLOW</text>
  </svg>
);

export const WaterLevelIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Water tank */}
    <rect x="25" y="15" width="50" height="70" rx="5" fill="none" stroke="#868e96" strokeWidth="3"/>
    {/* Water level */}
    <rect x="25" y="45" width="50" height="40" fill="#74c0fc" opacity="0.8"/>
    {/* Water surface waves */}
    <path d="M25 45 Q35 42 45 45 Q55 48 65 45 Q75 42 75 45" fill="none" stroke="#0ea5e9" strokeWidth="2"/>
    {/* Level sensor probe */}
    <rect x="48" y="10" width="4" height="75" fill="#495057"/>
    <circle cx="50" cy="10" r="3" fill="#ff6b6b"/>
    {/* Level markings */}
    <g stroke="#495057" strokeWidth="2">
      <line x1="18" y1="25" x2="23" y2="25"/>
      <line x1="18" y1="35" x2="23" y2="35"/>
      <line x1="18" y1="45" x2="23" y2="45"/>
      <line x1="18" y1="55" x2="23" y2="55"/>
      <line x1="18" y1="65" x2="23" y2="65"/>
      <line x1="18" y1="75" x2="23" y2="75"/>
    </g>
    {/* Level indicators */}
    <g fill="#495057" fontSize="8" textAnchor="end">
      <text x="16" y="28">100%</text>
      <text x="16" y="48">50%</text>
      <text x="16" y="78">0%</text>
    </g>
    {/* Current level indicator */}
    <circle cx="20" cy="45" r="3" fill="#28a745"/>
    {/* Ultrasonic level sensor */}
    <rect x="40" y="8" width="20" height="8" rx="2" fill="#6c757d" stroke="#495057" strokeWidth="1"/>
    <circle cx="45" cy="12" r="2" fill="#e9ecef"/>
    <circle cx="55" cy="12" r="2" fill="#e9ecef"/>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">LEVEL</text>
  </svg>
);

// Power & Electrical Sensors
export const CurrentSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Current transformer housing */}
    <circle cx="50" cy="50" r="35" fill="#fab005" stroke="#f59f00" strokeWidth="3"/>
    <circle cx="50" cy="50" r="25" fill="#fff3cd" stroke="#f59f00" strokeWidth="2"/>
    {/* Wire passing through */}
    <rect x="20" y="45" width="60" height="10" rx="5" fill="#495057"/>
    {/* Current flow indication */}
    <g fill="#212529">
      <path d="M30 50 L35 47 L35 53 Z"/>
      <path d="M40 50 L45 47 L45 53 Z"/>
      <path d="M55 50 L60 47 L60 53 Z"/>
      <path d="M65 50 L70 47 L70 53 Z"/>
    </g>
    {/* Current transformer coil */}
    <g fill="none" stroke="#f59f00" strokeWidth="2">
      <circle cx="50" cy="50" r="18"/>
      <circle cx="50" cy="50" r="15"/>
    </g>
    {/* Lightning bolt symbol */}
    <path d="M45 35 L52 42 L48 42 L55 52 L48 45 L52 45 L45 35" fill="#212529"/>
    {/* Digital display */}
    <rect x="58" y="25" width="30" height="12" rx="2" fill="#212529" stroke="#495057" strokeWidth="1"/>
    <text x="73" y="33" textAnchor="middle" fontSize="8" fill="#51cf66" fontFamily="monospace">12.5A</text>
    <text x="50" y="93" textAnchor="middle" fontSize="12" fill="#495057" fontWeight="bold">A</text>
  </svg>
);

export const PowerMeterIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Power meter housing */}
    <rect x="15" y="20" width="70" height="55" rx="8" fill="#495057" stroke="#212529" strokeWidth="3"/>
    {/* LCD display */}
    <rect x="25" y="30" width="50" height="30" rx="3" fill="#212529" stroke="#343a40" strokeWidth="1"/>
    {/* Digital readout */}
    <g fill="#51cf66" fontSize="14" fontFamily="monospace" textAnchor="middle">
      <text x="50" y="45">1250.7</text>
      <text x="50" y="55" fontSize="10">kWh</text>
    </g>
    {/* Control buttons */}
    <g fill="#6c757d" stroke="#495057" strokeWidth="1">
      <circle cx="30" cy="67" r="3"/>
      <circle cx="50" cy="67" r="3"/>
      <circle cx="70" cy="67" r="3"/>
    </g>
    {/* LED indicators */}
    <g fill="#28a745">
      <circle cx="25" cy="37" r="2"/>
      <circle cx="25" cy="43" r="2" fill="#ffc107"/>
      <circle cx="25" cy="49" r="2" fill="#dc3545"/>
    </g>
    {/* Power symbol */}
    <g fill="#868e96" fontSize="8">
      <text x="75" y="40">kW</text>
      <text x="75" y="50">V</text>
      <text x="75" y="60">A</text>
    </g>
    {/* Current measurement clamp */}
    <rect x="10" y="10" width="80" height="6" rx="3" fill="#e9ecef" stroke="#868e96" strokeWidth="2"/>
    <text x="50" y="93" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">POWER</text>
  </svg>
);

// Actuators
export const RelayIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Relay housing */}
    <rect x="20" y="25" width="60" height="45" rx="8" fill="#868e96" stroke="#495057" strokeWidth="3"/>
    {/* Contact terminals */}
    <circle cx="30" cy="45" r="6" fill="#ff6b6b" stroke="#dc3545" strokeWidth="2"/>
    <circle cx="70" cy="45" r="6" fill="#ff6b6b" stroke="#dc3545" strokeWidth="2"/>
    <circle cx="50" cy="35" r="6" fill="#ffc107" stroke="#f59e0b" strokeWidth="2"/>
    {/* Relay contacts */}
    <g stroke="#212529" strokeWidth="3" strokeLinecap="round">
      <line x1="30" y1="45" x2="46" y2="32"/>
      <circle cx="30" cy="45" r="2" fill="#212529"/>
      <circle cx="70" cy="45" r="2" fill="#212529"/>
      <circle cx="50" cy="35" r="2" fill="#212529"/>
    </g>
    {/* Coil */}
    <rect x="40" y="50" width="20" height="15" rx="3" fill="#6c757d" stroke="#495057" strokeWidth="2"/>
    <g fill="none" stroke="#495057" strokeWidth="1">
      <path d="M42 57 Q45 55 48 57 Q51 59 54 57 Q57 55 58 57"/>
    </g>
    {/* Connection wires */}
    <g stroke="#495057" strokeWidth="2">
      <line x1="25" y1="45" x2="15" y2="45"/>
      <line x1="75" y1="45" x2="85" y2="45"/>
      <line x1="40" y1="57" x2="30" y2="57"/>
      <line x1="60" y1="57" x2="70" y2="57"/>
    </g>
    <text x="50" y="92" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">RELAY</text>
  </svg>
);

export const MotorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Motor housing */}
    <circle cx="50" cy="50" r="35" fill="#495057" stroke="#212529" strokeWidth="3"/>
    <circle cx="50" cy="50" r="25" fill="#868e96" stroke="#495057" strokeWidth="2"/>
    {/* Stator windings */}
    <g fill="#6c757d">
      <circle cx="35" cy="35" r="4"/>
      <circle cx="65" cy="35" r="4"/>
      <circle cx="65" cy="65" r="4"/>
      <circle cx="35" cy="65" r="4"/>
    </g>
    {/* Rotor */}
    <circle cx="50" cy="50" r="15" fill="#adb5bd" stroke="#6c757d" strokeWidth="2"/>
    {/* Rotor blades/poles */}
    <g fill="#212529">
      <rect x="48" y="35" width="4" height="30" rx="2"/>
      <rect x="35" y="48" width="30" height="4" rx="2"/>
    </g>
    {/* Shaft */}
    <circle cx="50" cy="50" r="6" fill="#495057" stroke="#212529" strokeWidth="2"/>
    <circle cx="50" cy="50" r="2" fill="#212529"/>
    {/* Motor terminals */}
    <g fill="#ff6b6b">
      <rect x="45" y="12" width="4" height="8" rx="2"/>
      <rect x="51" y="12" width="4" height="8" rx="2"/>
      <rect x="57" y="12" width="4" height="8" rx="2"/>
    </g>
    {/* Rotation indicator */}
    <g stroke="#28a745" strokeWidth="2" fill="none" opacity="0.7">
      <path d="M25 30 Q20 40 25 50" strokeDasharray="3,3"/>
      <path d="M75 70 Q80 60 75 50" strokeDasharray="3,3"/>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">MOTOR</text>
  </svg>
);

export const LEDIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* LED dome */}
    <path d="M50 20 C35 20 25 30 25 42 L25 58 L75 58 L75 42 C75 30 65 20 50 20 Z" 
          fill="#ff6b6b" stroke="#c92a2a" strokeWidth="3"/>
    {/* LED die/chip */}
    <rect x="46" y="35" width="8" height="8" rx="1" fill="#ffd43b" stroke="#f59e0b" strokeWidth="1"/>
    {/* Anode and cathode leads */}
    <rect x="38" y="58" width="24" height="10" rx="2" fill="#495057"/>
    <rect x="40" y="68" width="6" height="12" rx="1" fill="#495057"/>
    <rect x="54" y="68" width="6" height="12" rx="1" fill="#495057"/>
    {/* Lead markings */}
    <g fill="#e9ecef" fontSize="8" textAnchor="middle">
      <text x="43" y="75">+</text>
      <text x="57" y="75">-</text>
    </g>
    {/* Light rays */}
    <g stroke="#ffd43b" strokeWidth="3" strokeLinecap="round" opacity="0.8">
      <line x1="50" y1="10" x2="50" y2="2"/>
      <line x1="30" y1="15" x2="22" y2="7"/>
      <line x1="70" y1="15" x2="78" y2="7"/>
      <line x1="20" y1="35" x2="12" y2="35"/>
      <line x1="80" y1="35" x2="88" y2="35"/>
    </g>
    {/* Additional light beams */}
    <g stroke="#ffc107" strokeWidth="2" strokeLinecap="round" opacity="0.6">
      <line x1="35" y1="12" x2="30" y2="7"/>
      <line x1="65" y1="12" x2="70" y2="7"/>
      <line x1="25" y1="25" x2="18" y2="18"/>
      <line x1="75" y1="25" x2="82" y2="18"/>
    </g>
    {/* Light diffusion */}
    <ellipse cx="50" cy="30" rx="20" ry="8" fill="#fff3cd" opacity="0.4"/>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">LED</text>
  </svg>
);

export const ValveIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Valve body pipe */}
    <rect x="15" y="40" width="70" height="20" rx="10" fill="#868e96" stroke="#495057" strokeWidth="3"/>
    {/* Valve ports */}
    <g fill="none" stroke="#495057" strokeWidth="3">
      <path d="M35 40 L35 20 L65 20 L65 40"/>
      <path d="M35 60 L35 80 L65 80 L65 60"/>
    </g>
    {/* Valve stem */}
    <rect x="47" y="10" width="6" height="35" fill="#495057"/>
    {/* Valve handle/actuator */}
    <circle cx="50" cy="10" r="10" fill="#ff6b6b" stroke="#c92a2a" strokeWidth="3"/>
    <rect x="45" y="5" width="10" height="10" fill="#c92a2a"/>
    {/* Flow direction indicators */}
    <g fill="#339af0">
      <path d="M10 50 L20 47 L20 53 Z"/>
      <path d="M80 50 L90 47 L90 53 Z"/>
    </g>
    {/* Valve disc/gate */}
    <rect x="46" y="42" width="8" height="16" rx="2" fill="#6c757d" stroke="#495057" strokeWidth="2"/>
    {/* Connection flanges */}
    <g fill="#adb5bd" stroke="#868e96" strokeWidth="1">
      <rect x="12" y="42" width="8" height="16" rx="2"/>
      <rect x="80" y="42" width="8" height="16" rx="2"/>
    </g>
    {/* Position indicator */}
    <g fill="#28a745" fontSize="8" textAnchor="middle">
      <circle cx="50" cy="25" r="3"/>
      <text x="50" y="28">●</text>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">VALVE</text>
  </svg>
);

export const ServoIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Servo housing */}
    <rect x="20" y="30" width="60" height="35" rx="8" fill="#495057" stroke="#212529" strokeWidth="3"/>
    {/* Servo gear assembly */}
    <circle cx="50" cy="47" r="15" fill="#868e96" stroke="#495057" strokeWidth="2"/>
    <circle cx="50" cy="47" r="10" fill="#adb5bd" stroke="#6c757d" strokeWidth="1"/>
    {/* Servo arm/horn */}
    <g stroke="#ff6b6b" strokeWidth="4" strokeLinecap="round">
      <line x1="50" y1="47" x2="50" y2="32"/>
      <circle cx="50" cy="32" r="3" fill="#ff6b6b"/>
    </g>
    {/* Central shaft */}
    <circle cx="50" cy="47" r="4" fill="#212529"/>
    {/* Connection pins */}
    <g fill="#ffc107" stroke="#f59e0b" strokeWidth="1">
      <rect x="22" y="67" width="4" height="8" rx="1"/>
      <rect x="37" y="67" width="4" height="8" rx="1"/>
      <rect x="59" y="67" width="4" height="8" rx="1"/>
      <rect x="74" y="67" width="4" height="8" rx="1"/>
    </g>
    {/* Wire connections */}
    <g stroke="#6c757d" strokeWidth="2">
      <line x1="24" y1="75" x2="24" y2="80"/>
      <line x1="39" y1="75" x2="39" y2="80"/>
      <line x1="61" y1="75" x2="61" y2="80"/>
      <line x1="76" y1="75" x2="76" y2="80"/>
    </g>
    {/* Position indicators */}
    <g fontSize="8" fill="#e9ecef" textAnchor="middle" fontWeight="bold">
      <text x="30" y="60">0°</text>
      <text x="50" y="60">90°</text>
      <text x="70" y="60">180°</text>
    </g>
    {/* Movement arc */}
    <g stroke="#28a745" strokeWidth="2" fill="none" opacity="0.6">
      <path d="M35 32 Q50 25 65 32" strokeDasharray="2,2"/>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">SERVO</text>
  </svg>
);

// Additional icons for new sensors
export const MicrophoneIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Microphone capsule */}
    <rect x="35" y="20" width="30" height="40" rx="15" fill="#495057" stroke="#212529" strokeWidth="2"/>
    {/* Microphone grille */}
    <g stroke="#6c757d" strokeWidth="1">
      <line x1="40" y1="30" x2="60" y2="30"/>
      <line x1="40" y1="35" x2="60" y2="35"/>
      <line x1="40" y1="40" x2="60" y2="40"/>
      <line x1="40" y1="45" x2="60" y2="45"/>
      <line x1="40" y1="50" x2="60" y2="50"/>
    </g>
    {/* Microphone stand */}
    <rect x="47" y="60" width="6" height="15" fill="#495057"/>
    {/* Base */}
    <rect x="35" y="75" width="30" height="8" rx="4" fill="#6c757d"/>
    {/* Sound waves */}
    <g stroke="#28a745" strokeWidth="2" fill="none" opacity="0.7">
      <path d="M25 35 Q20 40 25 45" strokeDasharray="2,2"/>
      <path d="M75 35 Q80 40 75 45" strokeDasharray="2,2"/>
      <path d="M20 30 Q12 40 20 50" strokeDasharray="2,2"/>
      <path d="M80 30 Q88 40 80 50" strokeDasharray="2,2"/>
    </g>
    <text x="50" y="95" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">MIC</text>
  </svg>
);

export const TDSSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* TDS probe */}
    <rect x="40" y="15" width="20" height="50" rx="10" fill="#495057" stroke="#212529" strokeWidth="2"/>
    {/* Electrodes */}
    <g fill="#ffc107">
      <rect x="42" y="25" width="16" height="3" rx="1"/>
      <rect x="42" y="35" width="16" height="3" rx="1"/>
      <rect x="42" y="45" width="16" height="3" rx="1"/>
      <rect x="42" y="55" width="16" height="3" rx="1"/>
    </g>
    {/* Cable */}
    <rect x="47" y="65" width="6" height="20" fill="#6c757d"/>
    {/* Water with dissolved particles */}
    <rect x="25" y="70" width="50" height="25" rx="5" fill="#74c0fc" opacity="0.6"/>
    {/* Dissolved particles */}
    <g fill="#ffc107" opacity="0.8">
      <circle cx="35" cy="80" r="2"/>
      <circle cx="45" cy="85" r="1.5"/>
      <circle cx="55" cy="78" r="2"/>
      <circle cx="65" cy="88" r="1.5"/>
      <circle cx="40" cy="90" r="1"/>
      <circle cx="60" cy="82" r="1"/>
    </g>
    <text x="50" y="18" textAnchor="middle" fontSize="10" fill="#495057" fontWeight="bold">TDS</text>
  </svg>
);

// Radar Sensor Icon (for Infineon BGT60 and mmWave sensors)
export const RadarSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Radar dome/antenna */}
    <path d="M35 20 Q50 15 65 20 L60 35 Q50 30 40 35 Z" fill="#2c3e50" stroke="#34495e" strokeWidth="2"/>
    {/* Radar base */}
    <rect x="47" y="35" width="6" height="8" fill="#34495e"/>
    
    {/* Radar waves - concentric arcs */}
    <g fill="none" stroke="#3498db" strokeWidth="2" strokeLinecap="round">
      {/* Inner wave */}
      <path d="M35 50 Q50 35 65 50" opacity="0.9"/>
      {/* Middle wave */}
      <path d="M30 55 Q50 35 70 55" opacity="0.7"/>
      {/* Outer wave */}
      <path d="M25 60 Q50 35 75 60" opacity="0.5"/>
      {/* Far wave */}
      <path d="M20 65 Q50 35 80 65" opacity="0.3"/>
    </g>
    
    {/* Detection beams */}
    <g stroke="#e74c3c" strokeWidth="1.5" fill="none" opacity="0.6">
      <line x1="50" y1="35" x2="35" y2="50"/>
      <line x1="50" y1="35" x2="50" y2="55"/>
      <line x1="50" y1="35" x2="65" y2="50"/>
    </g>
    
    {/* Human figure being detected */}
    <g fill="#2c3e50" stroke="none">
      {/* Head */}
      <circle cx="50" cy="70" r="4"/>
      {/* Body */}
      <rect x="47" y="74" width="6" height="12" rx="1"/>
      {/* Arms */}
      <rect x="42" y="76" width="4" height="2" rx="1"/>
      <rect x="54" y="76" width="4" height="2" rx="1"/>
      {/* Legs */}
      <rect x="46" y="86" width="3" height="8" rx="1"/>
      <rect x="51" y="86" width="3" height="8" rx="1"/>
    </g>
    
    {/* Detection indicators around person */}
    <g fill="#e74c3c" opacity="0.7">
      <circle cx="42" cy="70" r="1"/>
      <circle cx="58" cy="72" r="1"/>
      <circle cx="46" cy="65" r="0.8"/>
      <circle cx="54" cy="67" r="0.8"/>
    </g>
    
    {/* Label */}
    <text x="50" y="98" textAnchor="middle" fontSize="9" fill="#2c3e50" fontWeight="bold">RADAR</text>
  </svg>
);

// Infineon XENSIV™ Brand Icon
export const XensivSensorIcon: React.FC<IconProps> = ({ width = 24, height = 24, className }) => (
  <svg width={width} height={height} viewBox="0 0 100 100" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Circuit board background */}
    <rect x="10" y="15" width="80" height="70" rx="5" fill="#2c3e50" stroke="#34495e" strokeWidth="2"/>
    {/* Central processor/sensor chip */}
    <rect x="35" y="35" width="30" height="30" rx="3" fill="#3498db" stroke="#2980b9" strokeWidth="2"/>
    {/* XENSIV branding area */}
    <rect x="37" y="37" width="26" height="26" rx="2" fill="#ecf0f1" stroke="#bdc3c7" strokeWidth="1"/>
    {/* Circuit traces */}
    <g stroke="#95a5a6" strokeWidth="1.5" fill="none">
      <path d="M10 25 L35 25 L35 40"/>
      <path d="M90 35 L65 35 L65 45"/>
      <path d="M35 60 L25 60 L25 75 L10 75"/>
      <path d="M65 55 L75 55 L75 65 L90 65"/>
      <path d="M50 15 L50 35"/>
      <path d="M50 65 L50 85"/>
    </g>
    {/* Connection pads */}
    <g fill="#f39c12">
      <circle cx="20" cy="25" r="2"/>
      <circle cx="80" cy="35" r="2"/>
      <circle cx="20" cy="75" r="2"/>
      <circle cx="80" cy="65" r="2"/>
      <circle cx="50" cy="20" r="2"/>
      <circle cx="50" cy="80" r="2"/>
    </g>
    {/* XENSIV logo representation */}
    <g fontSize="8" fill="#2c3e50" textAnchor="middle" fontWeight="bold">
      <text x="50" y="48">X</text>
      <text x="50" y="57">ENSIV</text>
    </g>
    {/* Infineon label */}
    <text x="50" y="95" textAnchor="middle" fontSize="9" fill="#2980b9" fontWeight="bold">INFINEON</text>
  </svg>
);

// Map sensor IDs to their corresponding icons
export const sensorIconMap: Record<string, React.FC<IconProps>> = {
  // Environmental
  'temperature_basic': TemperatureIcon,
  'temperature_humidity': HumidityIcon,
  'pressure_temperature': PressureIcon,
  'pressure_sensor': PressureIcon,
  'co2_sensor': CO2Icon,
  'voc_sensor': VOCIcon,
  'pm_dust_sensor': PMSensorIcon,
  'pm_sensor': PMSensorIcon,
  'microphone_sensor': MicrophoneIcon,
  'tds_sensor': TDSSensorIcon,
  'xensiv_sensor': XensivSensorIcon,
  
  // Motion
  'accelerometer': AccelerometerIcon,
  'gyroscope': GyroscopeIcon,
  'pir_motion': PIRMotionIcon,
  'radar_sensor': RadarSensorIcon,
  
  // Optical
  'light_intensity': LightSensorIcon,
  'uv_sensor': UVSensorIcon,
  'color_sensor': ColorSensorIcon,
  
  // Distance
  'ultrasonic_distance': UltrasonicIcon,
  'lidar_sensor': LIDARIcon,
  
  // Water
  'ph_sensor': pHSensorIcon,
  'flow_rate': FlowSensorIcon,
  'water_level': WaterLevelIcon,
  
  // Electrical
  'current_sensor': CurrentSensorIcon,
  'energy_monitor': PowerMeterIcon,
  
  // Actuators
  'relay_control': RelayIcon,
  'motor_control': MotorIcon,
  'led_control': LEDIcon,
  'valve_control': ValveIcon,
  'servo_control': ServoIcon
};

// Get icon component by sensor ID
export const getSensorIcon = (sensorId: string): React.FC<IconProps> | null => {
  return sensorIconMap[sensorId] || null;
};

// Category icons
export const categoryIcons: Record<string, React.FC<IconProps>> = {
  'environmental': TemperatureIcon,
  'motion': AccelerometerIcon,
  'optical': LightSensorIcon,
  'distance': UltrasonicIcon,
  'water': WaterLevelIcon,
  'electrical': CurrentSensorIcon,
  'actuator': RelayIcon
};