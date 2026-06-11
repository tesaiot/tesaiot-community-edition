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
import { Sprout, Info, Tractor, Droplets, Thermometer, MapPin, Settings, Wrench, Wheat, Bug, Cloud } from 'lucide-react';
import { INDUSTRY_FIELDS_CONFIG, validateFieldValue } from '@/config/industryFieldsConfig';

interface SmartFarmFieldsProps {
  data: any;
  onChange: (data: any) => void;
  errors?: Record<string, string>;
  mode?: 'create' | 'edit';
  schema?: any;
}

const SmartFarmFields: React.FC<SmartFarmFieldsProps> = ({
  data,
  onChange,
  errors = {},
  mode = 'create'
}) => {
  const industryConfig = INDUSTRY_FIELDS_CONFIG.smart_farm;
  const [expandedSections, setExpandedSections] = useState(['isobus_identity']);

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
            <Label htmlFor={field.name} >
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
      case 'isobus_identity':
        return <Tractor className="h-4 w-4" />;
      case 'task_management':
        return <Settings className="h-4 w-4" />;
      case 'agricultural_operations':
        return <Sprout className="h-4 w-4" />;
      case 'field_and_crop':
        return <MapPin className="h-4 w-4" />;
      case 'environmental_sensors':
        return <Thermometer className="h-4 w-4" />;
      case 'maintenance':
        return <Wrench className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getFieldIcon = (fieldName: string, value: string) => {
    // Icons based on field name and value
    if (fieldName.includes('tractor') || fieldName.includes('implement')) {
      return <Tractor className="h-4 w-4" />;
    }
    if (fieldName.includes('crop') || fieldName.includes('plant')) {
      return <Sprout className="h-4 w-4" />;
    }
    if (fieldName.includes('irrigation') || fieldName.includes('water')) {
      return <Droplets className="h-4 w-4" />;
    }
    if (fieldName.includes('field') || fieldName.includes('boundary')) {
      return <MapPin className="h-4 w-4" />;
    }
    if (fieldName.includes('weather') || fieldName.includes('climate')) {
      return <Cloud className="h-4 w-4" />;
    }
    if (fieldName.includes('harvest') || fieldName.includes('grain')) {
      return <Wheat className="h-4 w-4" />;
    }
    if (fieldName.includes('pest') || fieldName.includes('disease')) {
      return <Bug className="h-4 w-4" />;
    }
    if (fieldName.includes('sensor') || fieldName.includes('temperature')) {
      return <Thermometer className="h-4 w-4" />;
    }
    return <Settings className="h-4 w-4" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sprout className="h-5 w-5" />
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
              <li>Calculate ISO NAME according to ISO 11783-5 standard</li>
              <li>Obtain AEF (Agricultural Electronics Foundation) manufacturer code</li>
              <li>Verify ISOXML compatibility with your task controller version</li>
              <li>Prepare field boundaries and mapping data</li>
              <li>Document implement specifications and working widths</li>
              <li>Ensure sensor calibration records are up to date</li>
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
              <strong>Required Compliance:</strong> Smart Farm devices must comply with:
              <ul className="mt-1 ml-4 list-disc">
                <li>AEF (Agricultural Electronics Foundation) ISOBUS certification</li>
                <li>Environmental regulations for pesticide/fertilizer application</li>
                <li>Organic certification requirements (if applicable)</li>
                <li>GPS accuracy standards for precision agriculture</li>
                <li>Water usage regulations and reporting requirements</li>
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default SmartFarmFields;