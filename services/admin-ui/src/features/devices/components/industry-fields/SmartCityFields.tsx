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
import { Building2, Info, MapPin, Network, Home, Globe, Wrench, Wifi, TreePine, Car } from 'lucide-react';
import { INDUSTRY_FIELDS_CONFIG, validateFieldValue } from '@/config/industryFieldsConfig';

interface SmartCityFieldsProps {
  data: any;
  onChange: (data: any) => void;
  errors?: Record<string, string>;
  mode?: 'create' | 'edit';
  schema?: any;
}

const SmartCityFields: React.FC<SmartCityFieldsProps> = ({
  data,
  onChange,
  errors = {},
  mode = 'create'
}) => {
  const industryConfig = INDUSTRY_FIELDS_CONFIG.smart_city;
  const [expandedSections, setExpandedSections] = useState(['location']);

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
            <Label htmlFor={field.name}>
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

      case 'number':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
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

      case 'date':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
            </Label>
            <Input
              id={field.name}
              type="date"
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={error ? 'border-red-500' : ''}
            />
            {(field.helperText || error) && (
              <p className={`text-sm ${error ? 'text-red-500' : 'text-muted-foreground'}`}>
                {error || field.helperText}
              </p>
            )}
          </div>
        );

      default:
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
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
      case 'location':
        return <MapPin className="h-4 w-4" />;
      case 'urban_integration':
        return <Globe className="h-4 w-4" />;
      case 'building_automation':
        return <Home className="h-4 w-4" />;
      case 'communication_network':
        return <Network className="h-4 w-4" />;
      case 'maintenance':
        return <Wrench className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getFieldIcon = (fieldName: string, value: string) => {
    // Icons based on field name and value
    if (fieldName.includes('service') || fieldName.includes('city')) {
      return <Building2 className="h-4 w-4" />;
    }
    if (fieldName.includes('district') || fieldName.includes('zone')) {
      return <MapPin className="h-4 w-4" />;
    }
    if (fieldName.includes('network') || fieldName.includes('mesh')) {
      return <Wifi className="h-4 w-4" />;
    }
    if (fieldName.includes('building') || fieldName.includes('automation')) {
      return <Home className="h-4 w-4" />;
    }
    if (fieldName.includes('environment') || fieldName.includes('green')) {
      return <TreePine className="h-4 w-4" />;
    }
    if (fieldName.includes('traffic') || fieldName.includes('transport')) {
      return <Car className="h-4 w-4" />;
    }
    return <Globe className="h-4 w-4" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="h-5 w-5" />
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
              <li>Register building IDs with city authorities before deployment</li>
              <li>Map city services to ISO 37120 standard categories</li>
              <li>Obtain energy efficiency certification for building automation</li>
              <li>Document mesh network topology and participation</li>
              <li>Ensure compliance with local building codes and privacy regulations</li>
              <li>Prepare district and neighborhood mapping for service integration</li>
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
                    <div key={field.name}>
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
              <strong>Required Compliance:</strong> Smart City devices must comply with:
              <ul className="mt-1 ml-4 list-disc">
                <li>Local building codes and zoning regulations</li>
                <li>Energy efficiency directives (EU: 2010/31/EU, US: ASHRAE 90.1)</li>
                <li>Privacy regulations (GDPR for EU, local privacy laws)</li>
                <li>Accessibility standards (ADA, EN 301 549)</li>
                <li>Smart city interoperability standards (oneM2M, FIWARE)</li>
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default SmartCityFields;