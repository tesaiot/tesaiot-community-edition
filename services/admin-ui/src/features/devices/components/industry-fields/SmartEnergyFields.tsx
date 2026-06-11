/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Zap, Info, Activity, Network, Gauge, Battery, Wrench, Sun, Wind, Waves } from 'lucide-react';
import { INDUSTRY_FIELDS_CONFIG, validateFieldValue } from '@/config/industryFieldsConfig';

interface SmartEnergyFieldsProps {
  data: any;
  onChange: (data: any) => void;
  errors?: Record<string, string>;
  mode?: 'create' | 'edit';
  schema?: any;
}

const SmartEnergyFields: React.FC<SmartEnergyFieldsProps> = ({
  data,
  onChange,
  errors = {},
  mode = 'create'
}) => {
  const industryConfig = INDUSTRY_FIELDS_CONFIG.smart_energy;
  const [expandedSections, setExpandedSections] = useState(['grid_integration']);

  const handleFieldChange = (fieldName: string, value: any) => {
    onChange({
      ...data,
      [fieldName]: value
    });
  };

  const renderField = (field: any) => {
    const value = data[field.name] || '';
    const error = errors[field.name] || validateFieldValue(field, value);

    switch (field.type) {
      case 'select':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name} >
              {field.label}
              {field.standard && (
                <Badge variant="outline" className="ml-2 text-xs">
                  {field.standard}
                </Badge>
              )}
            </Label>
            <SearchableSelect
              value={value}
              onValueChange={(val) => handleFieldChange(field.name, val)}
              options={field.validation?.options?.map((option: any) => ({
                value: option.value,
                label: option.label,
                description: option.description,
                icon: getFieldIcon(field.name, option.value)
              })) || []}
              placeholder={`Select ${field.label.toLowerCase()}`}
              searchable={field.validation?.options?.length > 5}
              size="md"
            />
            {(field.helperText || error) && (
              <p className={`text-sm ${error ? 'text-red-500' : 'text-muted-foreground'}`}>
                {error || field.helperText}
              </p>
            )}
          </div>
        );

      case 'boolean':
        return (
          <div className="flex items-center space-x-2 py-2">
            <Switch
              id={field.name}
              checked={value === true}
              onCheckedChange={(checked) => handleFieldChange(field.name, checked)}
            />
            <Label htmlFor={field.name} className="cursor-pointer">
              {field.label}
              {field.standard && (
                <Badge variant="outline" className="ml-2 text-xs">
                  {field.standard}
                </Badge>
              )}
              {field.helperText && (
                <span className="block text-sm text-muted-foreground">{field.helperText}</span>
              )}
            </Label>
          </div>
        );

      case 'number':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name} >
              {field.label}
              {field.standard && (
                <Badge variant="outline" className="ml-2 text-xs">
                  {field.standard}
                </Badge>
              )}
            </Label>
            <Input
              id={field.name}
              type="number"
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              min={field.validation?.min}
              max={field.validation?.max}
              className={error ? 'border-red-500' : ''}
              placeholder={field.helperText}
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
          </div>
        );

      default:
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name} >
              {field.label}
              {field.standard && (
                <Badge variant="outline" className="ml-2 text-xs">
                  {field.standard}
                </Badge>
              )}
            </Label>
            <Input
              id={field.name}
              type={field.type}
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={error ? 'border-red-500' : ''}
              placeholder={field.helperText}
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
          </div>
        );
    }
  };

  const getCategoryIcon = (categoryKey: string) => {
    switch (categoryKey) {
      case 'grid_integration':
        return <Zap className="h-4 w-4" />;
      case 'der_capabilities':
        return <Battery className="h-4 w-4" />;
      case 'communication':
        return <Network className="h-4 w-4" />;
      case 'metering':
        return <Gauge className="h-4 w-4" />;
      case 'maintenance':
        return <Wrench className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getFieldIcon = (fieldName: string, value: string) => {
    // Icons based on field name and value
    if (fieldName.includes('grid') || fieldName.includes('voltage')) {
      return <Zap className="h-4 w-4" />;
    }
    if (fieldName.includes('battery') || fieldName.includes('storage')) {
      return <Battery className="h-4 w-4" />;
    }
    if (fieldName.includes('solar') || fieldName.includes('pv')) {
      return <Sun className="h-4 w-4" />;
    }
    if (fieldName.includes('wind') || fieldName.includes('turbine')) {
      return <Wind className="h-4 w-4" />;
    }
    if (fieldName.includes('hydro') || fieldName.includes('water')) {
      return <Waves className="h-4 w-4" />;
    }
    if (fieldName.includes('meter') || fieldName.includes('measurement')) {
      return <Gauge className="h-4 w-4" />;
    }
    if (fieldName.includes('protocol') || fieldName.includes('communication')) {
      return <Network className="h-4 w-4" />;
    }
    return <Activity className="h-4 w-4" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          {industryConfig.name}
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Compliance Standards: {industryConfig.standards.join(', ')}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Data Preparation Guidelines:</strong>
            <ul className="mt-2 ml-4 list-disc space-y-1">
              <li>Follow IEC 61850 naming conventions (12 char max, uppercase)</li>
              <li>Register with grid operator and obtain connection agreements</li>
              <li>List all applicable grid codes for your region</li>
              <li>Ensure PTP/NTP infrastructure for microsecond time synchronization</li>
              <li>Document DER capabilities and grid support functions</li>
              <li>Prepare SCL (System Configuration Language) files if using IEC 61850</li>
            </ul>
          </AlertDescription>
        </Alert>

        <Accordion 
          type="multiple" 
          value={expandedSections}
          onValueChange={setExpandedSections}
          className="space-y-2"
        >
          {Object.entries(industryConfig.categories).map(([categoryKey, category]) => (
            <AccordionItem key={categoryKey} value={categoryKey}>
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2">
                  {getCategoryIcon(categoryKey)}
                  <span>{category.name}</span>
                  <Badge variant="secondary" className="ml-2">
                    {category.fields.length} optional
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
                  {category.fields.map((field) => (
                    <div key={field.name} className={field.type === 'boolean' ? 'md:col-span-2' : ''}>
                      {renderField(field)}
                    </div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>

        {mode === 'create' && (
          <Alert className="mt-4">
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>Required Grid Compliance:</strong> Smart Energy devices must comply with:
              <ul className="mt-1 ml-4 list-disc">
                <li>Grid codes: IEEE 1547 (US), VDE-AR-N 4105 (Germany), G98/G99 (UK)</li>
                <li>Communication: IEC 61850 for substation automation</li>
                <li>Smart Energy Profile: IEEE 2030.5 (SEP 2.0)</li>
                <li>Cybersecurity: NERC CIP (North America), NIS Directive (EU)</li>
                <li>Metering: IEC 62056 (DLMS/COSEM), ANSI C12 (US)</li>
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default SmartEnergyFields;