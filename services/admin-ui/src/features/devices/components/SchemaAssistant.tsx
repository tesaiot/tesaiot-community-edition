/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { toast } from 'sonner';
import {
  Search,
  Filter,
  Sparkles,
  Plus,
  X,
  Code,
  Eye,
  Save,
  Package,
  ChevronRight,
  Info,
  Zap,
  CheckCircle2,
  AlertCircle,
  Copy,
  Download,
  Upload,
  Trash2,
  Clock,
  Tag,
  Edit2,
  Calendar
} from 'lucide-react';
import { 
  sensorCatalog, 
  searchSensors, 
  getSensorById,
  mergeSensorSchemas,
  sensorIcons,
  type SensorTemplate,
  type SensorCategory
} from '../services/sensorCatalog';
import { RJSFSchema, UiSchema } from '@rjsf/utils';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/utils/dateFormatting';

// Helper function to format full date/time
const formatFullDateTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

interface SchemaAssistantProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSchemaGenerated: (schema: {
    schema: RJSFSchema;
    uiSchema: UiSchema;
    formData: Record<string, any>;
    metadata?: {
      name?: string;
      description?: string;
      sensors?: string[];
      tags?: string[];
    };
  }) => void;
  currentSchema?: RJSFSchema;
  deviceType?: string;
}

interface SelectedSensor {
  sensor: SensorTemplate;
  order: number;
  namespace?: string;
}

interface SavedTemplate {
  id: string;
  name: string;
  description?: string;
  sensors: string[];
  schema: RJSFSchema;
  uiSchema: UiSchema;
  tags: string[];
  createdAt: string;
  modifiedAt: string;
}

export const SchemaAssistant: React.FC<SchemaAssistantProps> = ({
  open,
  onOpenChange,
  onSchemaGenerated,
  currentSchema,
  deviceType
}) => {
  const [activeTab, setActiveTab] = useState<'browse' | 'selected' | 'preview' | 'saved'>('browse');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSensors, setSelectedSensors] = useState<SelectedSensor[]>([]);
  const [mergeMode, setMergeMode] = useState<'nested' | 'flat'>('flat');
  const [includeTimestamp, setIncludeTimestamp] = useState(true);
  const [namespacePrefix, setNamespacePrefix] = useState(false);
  const [schemaName, setSchemaName] = useState('');
  const [schemaDescription, setSchemaDescription] = useState('');
  const [schemaTags, setSchemaTags] = useState<string[]>([]);
  const [currentTag, setCurrentTag] = useState('');
  const [savedTemplates, setSavedTemplates] = useState<SavedTemplate[]>([]);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);

  // Load saved templates from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('tesa_schema_templates');
    if (saved) {
      try {
        setSavedTemplates(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load saved templates:', e);
      }
    }
  }, []);

  // Filter sensors based on search and category
  const filteredSensors = useMemo(() => {
    // If a category is explicitly selected, start from that category's list
    let base = selectedCategory !== 'all'
      ? (sensorCatalog.find(cat => cat.id === selectedCategory)?.sensors || [])
      : sensorCatalog.flatMap(cat => cat.sensors);

    // Apply search within the base set
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      base = base.filter(s =>
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags.some(t => t.toLowerCase().includes(q))
      );
    }
    return base;
  }, [searchQuery, selectedCategory, sensorCatalog]);

  // Handle sensor selection
  const toggleSensorSelection = (sensor: SensorTemplate) => {
    const existing = selectedSensors.find(s => s.sensor.id === sensor.id);
    
    if (existing) {
      setSelectedSensors(selectedSensors.filter(s => s.sensor.id !== sensor.id));
    } else {
      setSelectedSensors([
        ...selectedSensors,
        {
          sensor,
          order: selectedSensors.length + 1,
          namespace: sensor.id
        }
      ]);
    }
  };

  // Check if sensor is selected
  const isSensorSelected = (sensorId: string): boolean => {
    return selectedSensors.some(s => s.sensor.id === sensorId);
  };

  // Get sensor selection order
  const getSensorOrder = (sensorId: string): number | null => {
    const selected = selectedSensors.find(s => s.sensor.id === sensorId);
    return selected ? selected.order : null;
  };

  // Generate merged schema
  const generateMergedSchema = () => {
    if (selectedSensors.length === 0) {
      toast.error('Please select at least one sensor');
      return;
    }

    const sensors = selectedSensors.map(s => s.sensor);
    const { schema, uiSchema } = mergeSensorSchemas(sensors, {
      namespacePrefix,
      includeTimestamp,
      mergeMode
    });

    // Add metadata
    const enrichedSchema = {
      ...schema,
      title: schemaName || `Combined ${sensors.map(s => s.name).join(' + ')} Schema`,
      description: schemaDescription || `Schema combining ${sensors.length} sensor(s)`
    };

    return {
      schema: enrichedSchema,
      uiSchema,
      formData: {},
      metadata: {
        name: schemaName,
        description: schemaDescription,
        sensors: sensors.map(s => s.id),
        tags: schemaTags
      }
    };
  };

  // Handle schema generation
  const handleGenerateSchema = () => {
    const generated = generateMergedSchema();
    if (generated) {
      onSchemaGenerated(generated);
      toast.success('Schema generated successfully!', {
        description: `Combined ${selectedSensors.length} sensor(s) into a single schema`
      });
      onOpenChange(false);
    }
  };

  // Save current selection as template
  const saveAsTemplate = () => {
    if (selectedSensors.length === 0) {
      toast.error('Please select at least one sensor');
      return;
    }

    if (!schemaName) {
      toast.error('Please provide a name for the template');
      return;
    }

    const generated = generateMergedSchema();
    if (!generated) return;

    let updatedTemplates: SavedTemplate[];
    
    if (editingTemplateId) {
      // Update existing template
      const existingTemplate = savedTemplates.find(t => t.id === editingTemplateId);
      if (!existingTemplate) {
        toast.error('Template not found');
        return;
      }

      const updatedTemplate: SavedTemplate = {
        ...existingTemplate,
        name: schemaName,
        description: schemaDescription,
        sensors: selectedSensors.map(s => s.sensor.id),
        schema: generated.schema,
        uiSchema: generated.uiSchema,
        tags: schemaTags,
        modifiedAt: new Date().toISOString()
      };

      updatedTemplates = savedTemplates.map(t => 
        t.id === editingTemplateId ? updatedTemplate : t
      );
      
      toast.success('Template updated successfully!');
      setEditingTemplateId(null); // Clear edit mode
    } else {
      // Create new template
      const template: SavedTemplate = {
        id: `template_${Date.now()}`,
        name: schemaName,
        description: schemaDescription,
        sensors: selectedSensors.map(s => s.sensor.id),
        schema: generated.schema,
        uiSchema: generated.uiSchema,
        tags: schemaTags,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString()
      };

      updatedTemplates = [...savedTemplates, template];
      toast.success('Template saved successfully!');
    }

    setSavedTemplates(updatedTemplates);
    localStorage.setItem('tesa_schema_templates', JSON.stringify(updatedTemplates));
    setActiveTab('saved');
  };

  // Load saved template
  const loadTemplate = (template: SavedTemplate) => {
    // Load sensors from template
    const sensors: SelectedSensor[] = [];
    template.sensors.forEach((sensorId, index) => {
      const sensor = getSensorById(sensorId);
      if (sensor) {
        sensors.push({
          sensor,
          order: index + 1,
          namespace: sensor.id
        });
      }
    });
    
    setSelectedSensors(sensors);
    setSchemaName(template.name);
    setSchemaDescription(template.description || '');
    setSchemaTags(template.tags || []);
    setActiveTab('selected');
    
    toast.success(`Template "${template.name}" loaded`);
  };

  // Edit saved template
  const editTemplate = (template: SavedTemplate) => {
    // Load sensors from template
    const sensors: SelectedSensor[] = [];
    template.sensors.forEach((sensorId, index) => {
      const sensor = getSensorById(sensorId);
      if (sensor) {
        sensors.push({
          sensor,
          order: index + 1,
          namespace: sensor.id
        });
      }
    });
    
    setSelectedSensors(sensors);
    setSchemaName(template.name);
    setSchemaDescription(template.description || '');
    setSchemaTags(template.tags || []);
    setEditingTemplateId(template.id); // Set edit mode
    setActiveTab('selected');
    
    toast.success(`Editing template "${template.name}"`);
  };

  // Delete saved template
  const deleteTemplate = (templateId: string) => {
    const updatedTemplates = savedTemplates.filter(t => t.id !== templateId);
    setSavedTemplates(updatedTemplates);
    localStorage.setItem('tesa_schema_templates', JSON.stringify(updatedTemplates));
    toast.success('Template deleted');
  };

  // Duplicate saved template
  const duplicateTemplate = (template: SavedTemplate) => {
    const duplicatedTemplate: SavedTemplate = {
      id: `template_${Date.now()}`,
      name: `${template.name} (Copy)`,
      description: template.description,
      sensors: [...template.sensors],
      schema: { ...template.schema },
      uiSchema: { ...template.uiSchema },
      tags: [...template.tags],
      createdAt: new Date().toISOString(),
      modifiedAt: new Date().toISOString()
    };

    const updatedTemplates = [...savedTemplates, duplicatedTemplate];
    setSavedTemplates(updatedTemplates);
    localStorage.setItem('tesa_schema_templates', JSON.stringify(updatedTemplates));
    
    toast.success('Template duplicated successfully!', {
      description: `Created "${duplicatedTemplate.name}"`
    });
  };

  // Add tag
  const addTag = () => {
    if (currentTag && !schemaTags.includes(currentTag)) {
      setSchemaTags([...schemaTags, currentTag]);
      setCurrentTag('');
    }
  };

  // Remove tag
  const removeTag = (tag: string) => {
    setSchemaTags(schemaTags.filter(t => t !== tag));
  };

  // Export schema
  const exportSchema = () => {
    const generated = generateMergedSchema();
    if (!generated) return;

    const exportData = {
      ...generated,
      exportedAt: new Date().toISOString(),
      version: '1.0.0'
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${schemaName || 'schema'}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('Schema exported successfully');
  };

  // Preview of merged schema
  const schemaPreview = useMemo(() => {
    if (selectedSensors.length === 0) return null;
    return generateMergedSchema();
  }, [selectedSensors, mergeMode, namespacePrefix, includeTimestamp]);

  // Get icons representing the dominant sensor types in a schema
  const getSchemaIcons = (sensorIds: string[]): Array<{ icon: React.FC<any> | null; category: string }> => {
    const categoryCount: Record<string, { count: number; icon: React.FC<any> | null; displayName: string }> = {};
    
    // Count sensors by category
    sensorIds.forEach(sensorId => {
      const sensor = getSensorById(sensorId);
      if (sensor) {
        const category = sensor.category;
        if (!categoryCount[category]) {
          // Get category icon and display name
          const categoryInfo = sensorCatalog.find(cat => cat.id === category);
          categoryCount[category] = {
            count: 0,
            icon: categoryInfo?.icon || null,
            displayName: categoryInfo?.name || category
          };
        }
        categoryCount[category].count++;
      }
    });
    
    // Sort categories by count and get top 3
    const sortedCategories = Object.entries(categoryCount)
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 3)
      .map(([category, info]) => ({
        icon: info.icon,
        category: info.displayName
      }));
    
    // If only one category, show just that icon
    // If multiple categories, show up to 3 icons
    return sortedCategories;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl h-[90vh] flex flex-col p-0 gap-0">
        <DialogHeader className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
              <div>
                <DialogTitle className="text-xl">Data Schema Assistant</DialogTitle>
                <DialogDescription>
                  Create IoT-optimized device schemas with integer enums and flat structures for embedded firmware
                </DialogDescription>
              </div>
            </div>
            <Badge variant="secondary" className="text-sm">
              {selectedSensors.length} sensor{selectedSensors.length !== 1 ? 's' : ''} selected
            </Badge>
          </div>
        </DialogHeader>

        <div className="flex-1 flex overflow-hidden">
          <div className="w-full">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <div className="border-b px-6">
                <TabsList className="h-12 w-full justify-start rounded-none bg-transparent p-0">
                  <TabsTrigger 
                    value="browse" 
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary rounded-none px-4"
                  >
                    <Search className="h-4 w-4 mr-2" />
                    Browse Sensors
                  </TabsTrigger>
                  <TabsTrigger 
                    value="selected"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary rounded-none px-4"
                  >
                    <Package className="h-4 w-4 mr-2" />
                    Selected ({selectedSensors.length})
                  </TabsTrigger>
                  <TabsTrigger 
                    value="preview"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary rounded-none px-4"
                    disabled={selectedSensors.length === 0}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Preview
                  </TabsTrigger>
                  <TabsTrigger 
                    value="saved"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary rounded-none px-4"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Saved Templates ({savedTemplates.length})
                  </TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 min-h-0">
                <TabsContent value="browse" className="h-full m-0">
                  <div className="h-full flex">
                    {/* Sidebar with categories */}
                    <div className="w-72 border-r p-3 flex flex-col min-h-0">
                      <div className="flex-shrink-0 mb-2">
                        <Label className="text-xs font-medium mb-1">Search Sensors</Label>
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            placeholder="Search by name or tag..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9"
                          />
                        </div>
                      </div>

                      <div className="flex-1 overflow-y-auto flex flex-col min-h-0">
                        <Label className="text-sm font-medium mb-1 flex-shrink-0">Categories</Label>
                        <RadioGroup value={selectedCategory} onValueChange={setSelectedCategory} className="flex-1 overflow-y-auto pr-1">
                          <div className="space-y-1">
                            <Label className="flex items-center space-x-1.5 cursor-pointer py-0.5">
                              <RadioGroupItem value="all" className="h-3.5 w-3.5" />
                              <span className="text-sm">All Categories</span>
                            </Label>
                            {sensorCatalog.map(category => (
                              <Label key={category.id} className="flex items-center space-x-1.5 cursor-pointer py-0.5">
                                <RadioGroupItem value={category.id} className="h-3.5 w-3.5" />
                                <span className="text-sm flex items-center gap-1">
                                  {category.icon ? (
                                    <category.icon width={16} height={16} className="flex-shrink-0" />
                                  ) : (
                                    <span>📡</span>
                                  )}
                                  {category.name}
                                </span>
                              </Label>
                            ))}
                          </div>
                        </RadioGroup>
                      </div>
                    </div>

                    {/* Sensor grid */}
                    <ScrollArea className="flex-1 p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredSensors.map(sensor => {
                          const isSelected = isSensorSelected(sensor.id);
                          const order = getSensorOrder(sensor.id);
                          
                          return (
                            <Card 
                              key={sensor.id}
                              className={cn(
                                "cursor-pointer transition-all hover:shadow-md relative",
                                isSelected && "border-primary bg-primary/5"
                              )}
                              onClick={() => toggleSensorSelection(sensor)}
                            >
                              {isSelected && order && (
                                <div className="absolute -top-1 -right-1 h-6 w-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold z-10">
                                  {order}
                                </div>
                              )}
                              <div className="absolute top-4 right-4">
                                <Checkbox 
                                  checked={isSelected}
                                  onCheckedChange={() => {}}
                                  onClick={(e) => e.stopPropagation()}
                                />
                              </div>
                              <CardHeader className="pb-3 pt-6">
                                <CardTitle className="text-base flex items-center justify-between">
                                  <span className="flex items-center gap-2">
                                    {sensor.icon ? (
                                      <sensor.icon width={32} height={32} className="flex-shrink-0" />
                                    ) : (
                                      <span className="text-xl">📡</span>
                                    )}
                                    {sensor.name}
                                  </span>
                                </CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-sm text-muted-foreground mb-2">
                                  {sensor.description}
                                </p>
                                
                                {/* Schema Properties Preview */}
                                <div className="mb-3 p-2 bg-muted/50 rounded-md">
                                  <div className="text-xs font-medium mb-1">Schema Fields:</div>
                                  <div className="grid grid-cols-2 gap-1 text-xs">
                                    {Object.entries(sensor.schema.properties || {}).slice(0, 4).map(([key, prop]: [string, any]) => {
                                      const isRequired = (sensor.schema.required || []).includes(key);
                                      return (
                                        <div key={key} className="flex items-center gap-1">
                                          <span className={cn(
                                            "truncate", 
                                            isRequired ? "font-medium text-primary" : "text-muted-foreground"
                                          )}>
                                            {key}
                                          </span>
                                          {isRequired && (
                                            <Badge 
                                              variant="destructive" 
                                              className="text-[10px] px-1 py-0 h-4"
                                            >
                                              required
                                            </Badge>
                                          )}
                                        </div>
                                      );
                                    })}
                                    {Object.keys(sensor.schema.properties || {}).length > 4 && (
                                      <div className="text-xs text-muted-foreground">
                                        +{Object.keys(sensor.schema.properties || {}).length - 4} more
                                      </div>
                                    )}
                                  </div>
                                  
                                  {/* Required Fields Summary */}
                                  {sensor.schema.required && sensor.schema.required.length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-border">
                                      <div className="text-xs font-medium text-destructive">
                                        Required: {sensor.schema.required.join(', ')}
                                      </div>
                                    </div>
                                  )}
                                </div>
                                
                                <div className="flex flex-wrap gap-1">
                                  {sensor.tags.slice(0, 3).map(tag => (
                                    <Badge key={tag} variant="outline" className="text-xs">
                                      {tag}
                                    </Badge>
                                  ))}
                                  {sensor.tags.length > 3 && (
                                    <Badge variant="outline" className="text-xs">
                                      +{sensor.tags.length - 3}
                                    </Badge>
                                  )}
                                </div>
                                {sensor.standards && sensor.standards.length > 0 && (
                                  <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                                    <CheckCircle2 className="h-3 w-3" />
                                    {sensor.standards.join(', ')}
                                  </div>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    </ScrollArea>
                  </div>
                </TabsContent>

                <TabsContent value="selected" className="h-full m-0 p-6">
                  <ScrollArea className="h-full">
                    <div className="space-y-6">
                      {/* Schema metadata */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold">Schema Information</h3>
                          {editingTemplateId && (
                            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                              <Edit2 className="h-3 w-3 mr-1" />
                              Editing Template
                            </Badge>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label htmlFor="schema-name">Schema Name</Label>
                            <Input
                              id="schema-name"
                              placeholder="e.g., Environmental Monitoring Schema"
                              value={schemaName}
                              onChange={(e) => setSchemaName(e.target.value)}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="schema-description">Description</Label>
                            <Input
                              id="schema-description"
                              placeholder="Brief description of the schema purpose"
                              value={schemaDescription}
                              onChange={(e) => setSchemaDescription(e.target.value)}
                            />
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <Label>Tags</Label>
                          <div className="flex items-center gap-2">
                            <Input
                              placeholder="Add tag..."
                              value={currentTag}
                              onChange={(e) => setCurrentTag(e.target.value)}
                              onKeyPress={(e) => e.key === 'Enter' && addTag()}
                              className="flex-1"
                            />
                            <Button onClick={addTag} size="sm">
                              <Plus className="h-4 w-4" />
                            </Button>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {schemaTags.map(tag => (
                              <Badge key={tag} variant="secondary">
                                {tag}
                                <button
                                  onClick={() => removeTag(tag)}
                                  className="ml-1 hover:text-destructive"
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>

                      <Separator />

                      {/* Selected sensors */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold">Selected Sensors</h3>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedSensors([])}
                            disabled={selectedSensors.length === 0}
                          >
                            <Trash2 className="h-4 w-4 mr-1" />
                            Clear All
                          </Button>
                        </div>
                        
                        {selectedSensors.length === 0 ? (
                          <Alert>
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>
                              No sensors selected. Go to the Browse tab to select sensors for your schema.
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <div className="space-y-3">
                            {selectedSensors.map((selected, index) => (
                              <Card key={selected.sensor.id}>
                                <CardContent className="p-4">
                                  <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold">
                                        {selected.order}
                                      </div>
                                      <div>
                                        <div className="flex items-center gap-2">
                                          {selected.sensor.icon ? (
                                            <selected.sensor.icon width={24} height={24} className="flex-shrink-0" />
                                          ) : (
                                            <span>📡</span>
                                          )}
                                          <span className="font-medium">{selected.sensor.name}</span>
                                        </div>
                                        <p className="text-sm text-muted-foreground">
                                          {selected.sensor.description}
                                        </p>
                                      </div>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => toggleSensorSelection(selected.sensor)}
                                    >
                                      <X className="h-4 w-4" />
                                    </Button>
                                  </div>
                                  
                                  {/* Detailed Schema View for Selected Sensors */}
                                  <div className="mt-3 p-3 bg-muted/30 rounded-md border">
                                    <div className="text-xs font-medium mb-2">Schema Fields:</div>
                                    <div className="space-y-1">
                                      {Object.entries(selected.sensor.schema.properties || {}).map(([key, prop]: [string, any]) => {
                                        const isRequired = (selected.sensor.schema.required || []).includes(key);
                                        return (
                                          <div key={key} className="flex items-center justify-between text-xs">
                                            <div className="flex items-center gap-2">
                                              <span className={cn(
                                                "font-mono",
                                                isRequired ? "font-medium text-primary" : "text-muted-foreground"
                                              )}>
                                                {key}
                                              </span>
                                              {isRequired && (
                                                <Badge 
                                                  variant="destructive" 
                                                  className="text-[9px] px-1 py-0 h-3"
                                                >
                                                  required
                                                </Badge>
                                              )}
                                            </div>
                                            <span className="text-[10px] text-muted-foreground font-mono">
                                              {prop.type}
                                              {prop.minimum !== undefined && prop.maximum !== undefined && 
                                                ` (${prop.minimum}-${prop.maximum})`
                                              }
                                            </span>
                                          </div>
                                        );
                                      })}
                                    </div>
                                    
                                    {/* Required Fields Summary */}
                                    {selected.sensor.schema.required && selected.sensor.schema.required.length > 0 && (
                                      <div className="mt-3 pt-2 border-t border-border">
                                        <div className="text-xs">
                                          <span className="font-medium text-destructive">Required fields: </span>
                                          <span className="font-mono text-destructive">
                                            {selected.sensor.schema.required.join(', ')}
                                          </span>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        )}
                      </div>

                      <Separator />

                      {/* Merge options */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold">Merge Options</h3>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <Label htmlFor="merge-mode" className="flex items-center gap-2">
                              Schema Structure
                              <Info className="h-4 w-4 text-muted-foreground" />
                            </Label>
                            <RadioGroup 
                              value={mergeMode} 
                              onValueChange={(value) => setMergeMode(value as 'nested' | 'flat')}
                              className="flex gap-4"
                            >
                              <Label className="flex items-center gap-2 cursor-pointer">
                                <RadioGroupItem value="nested" />
                                <span>Nested</span>
                              </Label>
                              <Label className="flex items-center gap-2 cursor-pointer">
                                <RadioGroupItem value="flat" />
                                <span>Flat</span>
                              </Label>
                            </RadioGroup>
                          </div>

                          <div className="flex items-center justify-between">
                            <Label htmlFor="namespace-prefix" className="flex items-center gap-2">
                              Use Namespace Prefix
                              <Info className="h-4 w-4 text-muted-foreground" />
                            </Label>
                            <Checkbox
                              id="namespace-prefix"
                              checked={namespacePrefix}
                              onCheckedChange={(checked) => setNamespacePrefix(!!checked)}
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <Label htmlFor="include-timestamp" className="flex items-center gap-2">
                              Include Timestamp Field
                              <Info className="h-4 w-4 text-muted-foreground" />
                            </Label>
                            <Checkbox
                              id="include-timestamp"
                              checked={includeTimestamp}
                              onCheckedChange={(checked) => setIncludeTimestamp(!!checked)}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="preview" className="h-full m-0 p-6">
                  <ScrollArea className="h-full">
                    {schemaPreview && (
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold">Generated Schema Preview</h3>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText(JSON.stringify(schemaPreview, null, 2));
                                toast.success('Schema copied to clipboard');
                              }}
                            >
                              <Copy className="h-4 w-4 mr-1" />
                              Copy
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={exportSchema}
                            >
                              <Download className="h-4 w-4 mr-1" />
                              Export
                            </Button>
                          </div>
                        </div>

                        {/* Schema Summary */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm">Total Fields</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="text-2xl font-bold">
                                {Object.keys(schemaPreview.schema.properties || {}).length}
                              </div>
                            </CardContent>
                          </Card>
                          
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm">Required Fields</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="text-2xl font-bold text-destructive">
                                {schemaPreview.schema.required?.length || 0}
                              </div>
                            </CardContent>
                          </Card>
                          
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm">Sensors Used</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="text-2xl font-bold text-primary">
                                {selectedSensors.length}
                              </div>
                            </CardContent>
                          </Card>
                        </div>

                        {/* Required Fields Detail */}
                        {schemaPreview.schema.required && schemaPreview.schema.required.length > 0 && (
                          <div className="mb-6">
                            <h4 className="text-md font-semibold mb-3">Required Fields Summary</h4>
                            <div className="p-4 bg-destructive/5 border border-destructive/20 rounded-lg">
                              <div className="flex flex-wrap gap-2">
                                {schemaPreview.schema.required.map((field: string) => (
                                  <Badge key={field} variant="destructive" className="font-mono">
                                    {field}
                                  </Badge>
                                ))}
                              </div>
                              <div className="mt-3 text-sm text-muted-foreground">
                                All these fields must be provided when using this schema
                              </div>
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <Label>JSON Schema</Label>
                            <div className="border rounded-lg bg-muted/50 p-4 font-mono text-sm overflow-auto max-h-[400px]">
                              <pre>{JSON.stringify(schemaPreview.schema, null, 2)}</pre>
                            </div>
                          </div>
                          
                          <div className="space-y-2">
                            <Label>UI Schema</Label>
                            <div className="border rounded-lg bg-muted/50 p-4 font-mono text-sm overflow-auto max-h-[400px]">
                              <pre>{JSON.stringify(schemaPreview.uiSchema, null, 2)}</pre>
                            </div>
                          </div>
                        </div>

                        <Alert>
                          <Info className="h-4 w-4" />
                          <AlertDescription>
                            This preview shows how your selected sensors will be combined. 
                            You can adjust merge options in the Selected tab to change the structure.
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="saved" className="h-full m-0 p-6">
                  <ScrollArea className="h-full">
                    <div className="space-y-4">
                      {savedTemplates.length === 0 ? (
                        <Alert>
                          <Save className="h-4 w-4" />
                          <AlertDescription>
                            No saved templates yet. Create and save templates from the Selected tab.
                          </AlertDescription>
                        </Alert>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {savedTemplates.map(template => {
                            const schemaIcons = getSchemaIcons(template.sensors);
                            
                            return (
                              <Card key={template.id} className="overflow-hidden">
                                <div className="relative">
                                  {/* Schema type icons header */}
                                  <div className={cn(
                                    "h-20 flex items-center justify-center gap-3 p-4",
                                    "bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800"
                                  )}>
                                    {schemaIcons.map((IconInfo, index) => {
                                      const IconComponent = IconInfo.icon;
                                      return IconComponent ? (
                                        <div
                                          key={index}
                                          className={cn(
                                            "rounded-lg bg-white dark:bg-slate-900 shadow-sm",
                                            schemaIcons.length === 1 ? "p-3" : "p-2"
                                          )}
                                        >
                                          <IconComponent 
                                            width={schemaIcons.length === 1 ? 40 : 28} 
                                            height={schemaIcons.length === 1 ? 40 : 28}
                                            className="opacity-80"
                                          />
                                        </div>
                                      ) : null;
                                    })}
                                  </div>
                                  
                                  <CardHeader className="pb-3">
                                    <CardTitle className="text-base flex items-center justify-between">
                                      {template.name}
                                      <Badge variant="secondary">
                                        {template.sensors.length} sensors
                                      </Badge>
                                    </CardTitle>
                                  </CardHeader>
                                </div>
                                
                                <CardContent>
                                  <p className="text-sm text-muted-foreground mb-3">
                                    {template.description || 'No description'}
                                  </p>
                                  
                                  {/* Display sensor types */}
                                  <div className="flex flex-wrap gap-1 mb-3">
                                    {schemaIcons.map((iconInfo, index) => (
                                      <Badge key={index} variant="outline" className="text-xs">
                                        {iconInfo.category}
                                      </Badge>
                                    ))}
                                  </div>
                                  
                                  <div className="flex flex-wrap gap-1 mb-3">
                                    {template.tags.map(tag => (
                                      <Badge key={tag} variant="outline" className="text-xs">
                                        <Tag className="h-3 w-3 mr-1" />
                                        {tag}
                                      </Badge>
                                    ))}
                                  </div>
                                  <div className="text-xs text-muted-foreground mb-3 space-y-1">
                                    <div className="flex items-center gap-1">
                                      <Clock className="h-3 w-3" />
                                      Created: {new Date(template.createdAt).toLocaleDateString()}
                                    </div>
                                    {template.modifiedAt !== template.createdAt && (
                                      <div className="flex items-center gap-1">
                                        <Edit2 className="h-3 w-3" />
                                        Modified: {new Date(template.modifiedAt).toLocaleDateString()}
                                      </div>
                                    )}
                                  </div>
                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => loadTemplate(template)}
                                    className="flex-1"
                                  >
                                    <Upload className="h-4 w-4 mr-1" />
                                    Load
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => editTemplate(template)}
                                    className="flex-1"
                                  >
                                    <Edit2 className="h-4 w-4 mr-1" />
                                    Edit
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => duplicateTemplate(template)}
                                    title="Duplicate template"
                                  >
                                    <Copy className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => deleteTemplate(template.id)}
                                    title="Delete template"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </div>
                              </CardContent>
                            </Card>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </div>

        <DialogFooter className="px-6 py-4 border-t">
          <div className="flex items-center justify-between w-full">
            <div className="flex gap-2">
              {activeTab === 'selected' && selectedSensors.length > 0 && (
                <>
                  {editingTemplateId && (
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setEditingTemplateId(null);
                        toast.info('Edit mode cancelled');
                      }}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel Edit
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={saveAsTemplate}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {editingTemplateId ? 'Update Template' : 'Save as Template'}
                  </Button>
                </>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => {
                setEditingTemplateId(null); // Clear edit mode when closing
                onOpenChange(false);
              }}>
                Cancel
              </Button>
              <Button 
                onClick={handleGenerateSchema}
                disabled={selectedSensors.length === 0}
              >
                <Zap className="h-4 w-4 mr-2" />
                Generate Schema
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
