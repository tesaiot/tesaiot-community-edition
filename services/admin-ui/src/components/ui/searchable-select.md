# SearchableSelect Component

A comprehensive, production-ready searchable dropdown component built with Tailwind CSS for the TESA IoT Platform. This component provides a drop-in replacement for standard select elements with advanced features including search, keyboard navigation, multi-select, async data loading, and more.

## Features

### ✅ Core Features
- **Search Functionality**: Instant filtering with debounced search for async data
- **Keyboard Navigation**: Full arrow key, enter, and escape support
- **Single & Multi-Select**: Support for both selection modes
- **Loading States**: Built-in loading indicators and error handling
- **Accessibility**: ARIA attributes and screen reader support

### ✅ Advanced Features
- **Virtual Scrolling**: Optimized for large datasets (1000+ items)
- **Recent Selections**: Remembers recently selected items
- **Custom Rendering**: Custom option and selected value rendering
- **Size Variants**: sm, md, lg sizes matching existing UI patterns
- **Grouped Options**: Support for categorized option groups
- **Async Search**: Debounced search with async data fetching

### ✅ Design Features
- **Tailwind CSS**: Fully styled with Tailwind utility classes
- **Consistent Design**: Matches existing TESA platform design patterns
- **Responsive**: Works on all screen sizes
- **Dark Mode**: Full dark mode support
- **Animations**: Smooth open/close animations

## Installation

The component is already included in the TESA IoT Platform UI library. Simply import it:

```tsx
import { SearchableSelect } from '@/components/ui/searchable-select';
```

## Basic Usage

### Simple Single Select

```tsx
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';

const options: SelectOption[] = [
  { value: 'option1', label: 'Option 1' },
  { value: 'option2', label: 'Option 2' },
  { value: 'option3', label: 'Option 3' },
];

function MyComponent() {
  const [value, setValue] = useState('');

  return (
    <SearchableSelect
      options={options}
      value={value}
      onValueChange={setValue}
      placeholder="Select an option..."
    />
  );
}
```

### Multi-Select

```tsx
function MultiSelectExample() {
  const [values, setValues] = useState<string[]>([]);

  return (
    <SearchableSelect
      options={options}
      value={values}
      onValueChange={setValues}
      multiple
      placeholder="Select multiple options..."
    />
  );
}
```

### With Icons and Descriptions

```tsx
const enhancedOptions: SelectOption[] = [
  {
    value: 'sensor',
    label: 'IoT Sensor',
    description: 'Temperature and humidity sensors',
    icon: <Thermometer className="size-4" />
  },
  {
    value: 'gateway',
    label: 'IoT Gateway',
    description: 'Network connectivity device',
    icon: <Wifi className="size-4" />
  },
];

<SearchableSelect
  options={enhancedOptions}
  value={value}
  onValueChange={setValue}
  placeholder="Select device type..."
/>
```

## Advanced Usage

### Grouped Options

```tsx
const groups: SelectGroup[] = [
  {
    label: 'Administration',
    options: [
      { value: 'admin', label: 'Administrator', description: 'Full access' },
      { value: 'moderator', label: 'Moderator', description: 'Limited admin' },
    ]
  },
  {
    label: 'Users',
    options: [
      { value: 'user', label: 'Standard User', description: 'Basic access' },
      { value: 'viewer', label: 'Viewer', description: 'Read-only' },
    ]
  }
];

<SearchableSelect
  groups={groups}
  value={selectedRoles}
  onValueChange={setSelectedRoles}
  multiple
  placeholder="Select user roles..."
/>
```

### Async Search

```tsx
function AsyncSearchExample() {
  const [options, setOptions] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (query: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/search?q=${query}`);
      const data = await response.json();
      setOptions(data.results);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SearchableSelect
      options={options}
      loading={loading}
      onSearch={handleSearch}
      searchDebounceMs={300}
      placeholder="Search for items..."
      searchPlaceholder="Type to search..."
    />
  );
}
```

### Custom Rendering

```tsx
const renderOption = (option: SelectOption, isSelected: boolean) => (
  <div className="flex items-center justify-between w-full">
    <div className="flex items-center gap-2">
      {option.icon}
      <div>
        <div className="font-medium">{option.label}</div>
        <div className="text-xs text-muted-foreground">{option.description}</div>
      </div>
    </div>
    {isSelected && <Badge variant="secondary">Selected</Badge>}
  </div>
);

const renderSelectedValue = (options: SelectOption[]) => {
  if (options.length === 0) return null;
  const option = options[0];
  return (
    <div className="flex items-center gap-2">
      {option.icon}
      <span>{option.label}</span>
    </div>
  );
};

<SearchableSelect
  options={options}
  renderOption={renderOption}
  renderSelectedValue={renderSelectedValue}
  placeholder="Custom rendering..."
/>
```

### Virtual Scrolling for Large Datasets

```tsx
<SearchableSelect
  options={largeDataset} // 1000+ items
  virtualScrolling
  maxHeight={300}
  placeholder="Search large dataset..."
  searchPlaceholder="Type to filter 1000+ items..."
/>
```

## Props Reference

### Core Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `options` | `SelectOption[]` | `[]` | Array of options to display |
| `groups` | `SelectGroup[]` | `[]` | Grouped options (alternative to options) |
| `value` | `string \| string[]` | - | Controlled value |
| `defaultValue` | `string \| string[]` | - | Default value for uncontrolled usage |
| `onValueChange` | `(value: string \| string[]) => void` | - | Value change handler |
| `onSelect` | `(option: SelectOption) => void` | - | Option select handler |

### Behavior Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `multiple` | `boolean` | `false` | Enable multi-select mode |
| `searchable` | `boolean` | `true` | Enable search functionality |
| `clearable` | `boolean` | `true` | Show clear button |
| `disabled` | `boolean` | `false` | Disable the component |
| `loading` | `boolean` | `false` | Show loading state |

### Async Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `onSearch` | `(query: string) => void \| Promise<void>` | - | Async search handler |
| `searchDebounceMs` | `number` | `300` | Search debounce delay |

### UI Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `placeholder` | `string` | `"Select an option..."` | Trigger placeholder text |
| `searchPlaceholder` | `string` | `"Search items..."` | Search input placeholder |
| `emptyMessage` | `string` | `"No options found"` | Empty state message |
| `loadingMessage` | `string` | `"Loading..."` | Loading state message |
| `size` | `"sm" \| "md" \| "lg"` | `"md"` | Component size variant |

### Advanced Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `virtualScrolling` | `boolean` | `false` | Enable virtual scrolling |
| `maxHeight` | `number` | `300` | Maximum dropdown height (px) |
| `rememberRecentSelections` | `boolean` | `false` | Remember recent selections |
| `maxRecentSelections` | `number` | `5` | Max recent selections to remember |

### Custom Rendering Props

| Prop | Type | Description |
|------|------|-------------|
| `renderOption` | `(option: SelectOption, isSelected: boolean) => ReactNode` | Custom option renderer |
| `renderSelectedValue` | `(options: SelectOption[]) => ReactNode` | Custom selected value renderer |

### Accessibility Props

| Prop | Type | Description |
|------|------|-------------|
| `aria-label` | `string` | Accessible label |
| `aria-describedby` | `string` | ID of describing element |

## Types

### SelectOption

```tsx
interface SelectOption {
  value: string;           // Unique option value
  label: string;           // Display label
  description?: string;    // Optional description
  icon?: React.ReactNode;  // Optional icon
  disabled?: boolean;      // Disable this option
  group?: string;          // Group label (auto-set for grouped options)
}
```

### SelectGroup

```tsx
interface SelectGroup {
  label: string;           // Group label
  options: SelectOption[]; // Options in this group
}
```

## Size Variants

The component supports three size variants that match the existing TESA platform design:

- **`sm`**: Height 28px (7 * 0.25rem), text-xs, compact padding
- **`md`**: Height 34px (8.5 * 0.25rem), text-sm, standard padding (default)
- **`lg`**: Height 40px (10 * 0.25rem), text-base, generous padding

## Keyboard Navigation

- **Arrow Down/Up**: Navigate through options
- **Enter**: Select highlighted option
- **Escape**: Close dropdown
- **Tab**: Normal tab navigation
- **Type to search**: When search is enabled

## Accessibility

The component is fully accessible with:

- ARIA labels and descriptions
- Proper focus management
- Keyboard navigation
- Screen reader support
- High contrast support
- Role and state attributes

## Best Practices

### Performance

1. **Use virtual scrolling** for datasets > 100 items
2. **Implement async search** for server-side filtering
3. **Debounce search queries** to reduce API calls
4. **Memoize options** when possible

```tsx
const memoizedOptions = useMemo(() => 
  computeExpensiveOptions(data), [data]
);
```

### UX Guidelines

1. **Provide clear placeholders** that indicate what to select
2. **Use icons and descriptions** for complex options
3. **Group related options** for better organization
4. **Show loading states** for async operations
5. **Handle empty states** gracefully

### Error Handling

```tsx
<SearchableSelect
  options={options}
  loading={loading}
  onSearch={async (query) => {
    try {
      await searchData(query);
    } catch (error) {
      // Handle error - could set error state
      console.error('Search failed:', error);
    }
  }}
  emptyMessage={error ? "Search failed. Please try again." : "No results found"}
/>
```

## Integration Examples

### Device Management

```tsx
// Device type selection in TESA IoT Platform
<SearchableSelect
  options={deviceTypes}
  value={selectedDeviceType}
  onValueChange={setSelectedDeviceType}
  placeholder="Select device type..."
  size="md"
  aria-label="Device type selection"
/>
```

### User Role Assignment

```tsx
// Multi-select for user roles
<SearchableSelect
  groups={roleGroups}
  value={assignedRoles}
  onValueChange={setAssignedRoles}
  multiple
  placeholder="Assign user roles..."
  searchPlaceholder="Search roles..."
  maxHeight={250}
/>
```

### Organization Selection

```tsx
// Organization picker with custom rendering
<SearchableSelect
  options={organizations}
  value={selectedOrg}
  onValueChange={setSelectedOrg}
  renderSelectedValue={(options) => (
    <div className="flex items-center gap-2">
      <Building className="size-4" />
      {options[0]?.label}
    </div>
  )}
  placeholder="Select organization..."
/>
```

## Styling Customization

The component uses Tailwind CSS classes and can be customized through:

1. **Class overrides**: Pass custom `className`
2. **CSS variables**: Modify design tokens
3. **Tailwind config**: Extend theme
4. **Custom variants**: Add new size variants

```tsx
// Custom styling example
<SearchableSelect
  className="border-primary focus-within:ring-primary/30"
  options={options}
  placeholder="Custom styled select..."
/>
```

## Troubleshooting

### Common Issues

1. **Options not showing**: Check that `options` or `groups` prop is provided
2. **Search not working**: Ensure `searchable={true}` (default)
3. **Keyboard navigation broken**: Check for event handler conflicts
4. **Styling issues**: Verify Tailwind CSS is properly configured
5. **Performance with large lists**: Enable `virtualScrolling`

### Debug Mode

Add debug logging to understand component behavior:

```tsx
<SearchableSelect
  options={options}
  onValueChange={(value) => {
    console.log('Value changed:', value);
    setValue(value);
  }}
  onSelect={(option) => {
    console.log('Option selected:', option);
  }}
  onSearch={(query) => {
    console.log('Search query:', query);
  }}
/>
```

## Migration from Standard Select

### From HTML Select

```html
<!-- Before: HTML select -->
<select>
  <option value="1">Option 1</option>
  <option value="2">Option 2</option>
</select>
```

```tsx
// After: SearchableSelect
<SearchableSelect
  options={[
    { value: '1', label: 'Option 1' },
    { value: '2', label: 'Option 2' },
  ]}
  value={value}
  onValueChange={setValue}
/>
```

### From Radix Select

```tsx
// Before: Radix UI Select
<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select..." />
  </SelectTrigger>
  <SelectContent>
    {options.map(option => (
      <SelectItem key={option.value} value={option.value}>
        {option.label}
      </SelectItem>
    ))}
  </SelectContent>
</Select>

// After: SearchableSelect (much simpler!)
<SearchableSelect
  options={options}
  value={value}
  onValueChange={setValue}
  placeholder="Select..."
/>
```

## Contributing

When contributing to this component:

1. Follow existing code patterns
2. Add TypeScript types for new props
3. Update this documentation
4. Add tests for new features
5. Ensure accessibility compliance

## License

This component is part of the TESA IoT Platform and is licensed under the dual Apache-2.0/Commercial license. See the component header for details.