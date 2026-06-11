/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Info, Heart, Factory, Building, Zap, Leaf } from 'lucide-react';
import { industrySchemaService, INDUSTRIES, IndustrySchema } from '@/services/api/industrySchemaService';

// Lazy load industry-specific components for better performance
const HealthMedicalFields = lazy(() => import('./industry-fields/HealthMedicalFields'));
const Industry40Fields = lazy(() => import('./industry-fields/Industry40Fields'));
const SmartCityFields = lazy(() => import('./industry-fields/SmartCityFields'));
const SmartEnergyFields = lazy(() => import('./industry-fields/SmartEnergyFields'));
const SmartFarmFields = lazy(() => import('./industry-fields/SmartFarmFields'));

interface IndustrySpecificTabProps {
  formData: any;
  onChange: (data: any) => void;
  errors?: Record<string, string>;
  mode?: 'create' | 'edit';
  deviceId?: string;
}

export const IndustrySpecificTab: React.FC<IndustrySpecificTabProps> = ({
  formData,
  onChange,
  errors = {},
  mode = 'create',
  deviceId
}) => {
  const [selectedIndustry, setSelectedIndustry] = useState<string>(formData.industry || '');
  const [industrySchema, setIndustrySchema] = useState<IndustrySchema | null>(null);
  const [loading, setLoading] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);

  // Update selectedIndustry when formData.industry changes (for edit mode)
  useEffect(() => {
    if (formData.industry && formData.industry !== selectedIndustry) {
      setSelectedIndustry(formData.industry);
    }
  }, [formData.industry]);

  // Auto-detect industry in edit mode only if no industry is set
  useEffect(() => {
    if (mode === 'edit' && !formData.industry && formData) {
      const detectedIndustry = industrySchemaService.detectIndustryFromDevice(formData);
      if (detectedIndustry) {
        setSelectedIndustry(detectedIndustry);
        onChange({ ...formData, industry: detectedIndustry });
      }
    }
  }, [mode]);

  // Load industry schema when industry changes
  useEffect(() => {
    if (selectedIndustry) {
      loadIndustrySchema(selectedIndustry);
    }
  }, [selectedIndustry]);

  const loadIndustrySchema = async (industryId: string) => {
    setLoading(true);
    setSchemaError(null);
    
    try {
      const schema = await industrySchemaService.getSchemaForIndustry(industryId);
      setIndustrySchema(schema);
    } catch (error) {
      console.error('Failed to load industry schema:', error);
      setSchemaError('Failed to load industry configuration. Using default fields.');
      // Use static schema as fallback
      const staticSchema = INDUSTRIES.find(i => i.id === industryId);
      setIndustrySchema(staticSchema || null);
    } finally {
      setLoading(false);
    }
  };

  const handleIndustryChange = (industry: string) => {
    setSelectedIndustry(industry);
    
    // Update form data with industry
    onChange({
      ...formData,
      industry,
      // Clear previous industry-specific data when changing industry
      industrySpecificData: {}
    });
  };

  const handleFieldChange = (fieldData: any) => {
    onChange({
      ...formData,
      industrySpecificData: fieldData
    });
  };

  const renderIndustryFields = () => {
    if (!selectedIndustry || loading) {
      return null;
    }

    const industryData = formData.industrySpecificData || {};
    const fieldErrors = errors.industrySpecificData || {};

    // Common props for all industry field components
    const fieldProps = {
      data: industryData,
      onChange: handleFieldChange,
      errors: fieldErrors,
      mode,
      schema: industrySchema
    };

    return (
      <Suspense fallback={
        <div className="flex items-center justify-center p-8">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading industry fields...</span>
        </div>
      }>
        {selectedIndustry === 'health_medical' && <HealthMedicalFields {...fieldProps} />}
        {selectedIndustry === 'industry_40' && <Industry40Fields {...fieldProps} />}
        {selectedIndustry === 'smart_city' && <SmartCityFields {...fieldProps} />}
        {selectedIndustry === 'smart_energy' && <SmartEnergyFields {...fieldProps} />}
        {selectedIndustry === 'smart_farm' && <SmartFarmFields {...fieldProps} />}
      </Suspense>
    );
  };

  return (
    <div className="space-y-6">
      {/* Industry Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Industry Domain</CardTitle>
          <CardDescription>
            Choose your industry to load specific configuration fields tailored to your device requirements
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="industry-select">Industry Type</Label>
              <SearchableSelect
                options={INDUSTRIES.map(industry => ({
                  value: industry.id,
                  label: industry.name,
                  description: industry.description,
                  icon: industry.id === 'health_medical' ? <Heart className="h-4 w-4 text-red-500" /> :
                        industry.id === 'industry_40' ? <Factory className="h-4 w-4 text-blue-500" /> :
                        industry.id === 'smart_city' ? <Building className="h-4 w-4 text-purple-500" /> :
                        industry.id === 'smart_energy' ? <Zap className="h-4 w-4 text-yellow-500" /> :
                        industry.id === 'smart_farm' ? <Leaf className="h-4 w-4 text-green-500" /> :
                        <Info className="h-4 w-4 text-gray-500" />
                }))}
                value={selectedIndustry}
                onValueChange={handleIndustryChange}
                placeholder="Choose your industry domain..."
                searchable={true}
                searchPlaceholder="Search industries..."
                disabled={loading}
                size="md"
                className="mt-2"
                aria-label="Industry Type"
              />
            </div>

            {selectedIndustry && industrySchema && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <strong>{industrySchema.name}</strong> configuration loaded. 
                  {industrySchema.requiredFields.length > 0 && (
                    <span> This industry requires {industrySchema.requiredFields.length} mandatory fields.</span>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {schemaError && (
              <Alert variant="destructive">
                <AlertDescription>{schemaError}</AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Industry-Specific Fields */}
      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin mr-2" />
            <span>Loading industry configuration...</span>
          </CardContent>
        </Card>
      ) : (
        renderIndustryFields()
      )}

      {/* Help Section */}
      {selectedIndustry && !loading && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Need Help?</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground space-y-2">
              <p>
                Industry-specific fields help ensure your device meets regulatory requirements 
                and follows best practices for your domain.
              </p>
              <p>
                Fields marked with * are required for compliance. Hover over field labels 
                for additional help and guidance.
              </p>
              {mode === 'edit' && (
                <p className="text-amber-600">
                  <strong>Note:</strong> Changing the industry type may affect existing configurations. 
                  Ensure all required fields are properly updated.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};