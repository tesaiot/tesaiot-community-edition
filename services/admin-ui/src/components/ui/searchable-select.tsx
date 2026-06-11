/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Check, ChevronDown, Search, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// Types and Interfaces
export interface SelectOption {
  value: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  group?: string;
}

export interface SelectGroup {
  label: string;
  options: SelectOption[];
}

export interface SearchableSelectProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  // Basic props
  options?: SelectOption[];
  groups?: SelectGroup[];
  value?: string | string[];
  defaultValue?: string | string[];
  onValueChange?: (value: string | string[]) => void;
  onSelect?: (option: SelectOption) => void;
  
  // Behavior props
  multiple?: boolean;
  searchable?: boolean;
  clearable?: boolean;
  disabled?: boolean;
  loading?: boolean;
  
  // Async props
  onSearch?: (query: string) => void | Promise<void>;
  searchDebounceMs?: number;
  
  // UI props
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  loadingMessage?: string;
  size?: 'sm' | 'md' | 'lg';
  
  // Advanced features
  virtualScrolling?: boolean;
  maxHeight?: number;
  rememberRecentSelections?: boolean;
  maxRecentSelections?: number;
  
  // Custom renderers
  renderOption?: (option: SelectOption, isSelected: boolean) => React.ReactNode;
  renderSelectedValue?: (options: SelectOption[]) => React.ReactNode;
  
  // Accessibility
  'aria-label'?: string;
  'aria-describedby'?: string;
}

// Component variants
const triggerVariants = cva(
  `
    flex bg-background w-full items-center justify-between outline-none border border-input shadow-xs shadow-black/5 
    transition-shadow text-foreground data-placeholder:text-muted-foreground focus-within:border-ring 
    focus-within:outline-none focus-within:ring-[3px] focus-within:ring-ring/30 
    disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1 
    aria-invalid:border-destructive/60 aria-invalid:ring-destructive/10 
    dark:aria-invalid:border-destructive dark:aria-invalid:ring-destructive/20
    hover:border-ring/60 cursor-pointer
  `,
  {
    variants: {
      size: {
        sm: 'h-7 px-2.5 text-xs gap-1 rounded-md',
        md: 'h-8.5 px-3 text-[0.8125rem] leading-[1.25rem] gap-1 rounded-md',
        lg: 'h-10 px-4 text-sm gap-1.5 rounded-md',
      },
      openState: {
        true: 'border-ring ring-[3px] ring-ring/30',
        false: '',
      },
    },
    defaultVariants: {
      size: 'md',
      openState: false,
    },
  },
);

const contentVariants = cva(
  `
    absolute z-50 min-w-[8rem] overflow-hidden rounded-md border border-border bg-popover 
    shadow-md shadow-black/5 text-popover-foreground 
    data-[state=open]:animate-in data-[state=closed]:animate-out 
    data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 
    data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 
    data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2
  `,
  {
    variants: {
      size: {
        sm: 'text-xs',
        md: 'text-[0.8125rem]',
        lg: 'text-sm',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  },
);

const optionVariants = cva(
  `
    relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 text-sm 
    outline-hidden text-foreground transition-colors
    hover:bg-accent focus:bg-accent data-disabled:pointer-events-none data-disabled:opacity-50
  `,
  {
    variants: {
      size: {
        sm: 'px-2 py-1 text-xs min-h-6',
        md: 'px-2.5 py-1.5 text-[0.8125rem] min-h-7',
        lg: 'px-3 py-2 text-sm min-h-8',
      },
      isSelected: {
        true: 'bg-accent/50',
        false: '',
      },
      isHighlighted: {
        true: 'bg-accent',
        false: '',
      },
    },
    defaultVariants: {
      size: 'md',
      isSelected: false,
      isHighlighted: false,
    },
  },
);

// Custom hooks
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

function useKeyboardNavigation(
  isOpen: boolean,
  filteredOptions: SelectOption[],
  onSelect: (option: SelectOption) => void,
  onClose: () => void,
) {
  const [highlightedIndex, setHighlightedIndex] = React.useState(-1);

  React.useEffect(() => {
    if (!isOpen) {
      setHighlightedIndex(-1);
    }
  }, [isOpen]);

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent) => {
      if (!isOpen) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setHighlightedIndex(prev => 
            prev < filteredOptions.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          event.preventDefault();
          setHighlightedIndex(prev => 
            prev > 0 ? prev - 1 : filteredOptions.length - 1
          );
          break;
        case 'Enter':
          event.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < filteredOptions.length) {
            const option = filteredOptions[highlightedIndex];
            if (!option.disabled) {
              onSelect(option);
            }
          }
          break;
        case 'Escape':
          event.preventDefault();
          onClose();
          break;
      }
    },
    [isOpen, filteredOptions, highlightedIndex, onSelect, onClose]
  );

  return { highlightedIndex, handleKeyDown };
}

// Main component
export const SearchableSelect = React.forwardRef<HTMLDivElement, SearchableSelectProps>(
  (
    {
      options = [],
      groups = [],
      value,
      defaultValue,
      onValueChange,
      onSelect,
      multiple = false,
      searchable = true,
      clearable = true,
      disabled = false,
      loading = false,
      onSearch,
      searchDebounceMs = 300,
      placeholder = 'Select an option...',
      searchPlaceholder = 'Search items...',
      emptyMessage = 'No options found',
      loadingMessage = 'Loading...',
      size = 'md',
      virtualScrolling = false,
      maxHeight = 300,
      rememberRecentSelections = false,
      maxRecentSelections = 5,
      renderOption,
      renderSelectedValue,
      className,
      'aria-label': ariaLabel,
      'aria-describedby': ariaDescribedBy,
      ...props
    },
    ref
  ) => {
    // State management
    const [openFlag, setOpenFlag] = React.useState(false);
    const [searchQuery, setSearchQuery] = React.useState('');
    const [internalValue, setInternalValue] = React.useState<string | string[]>(
      value ?? defaultValue ?? (multiple ? [] : '')
    );
    const [recentSelections, setRecentSelections] = React.useState<SelectOption[]>([]);

    // Refs
    const triggerRef = React.useRef<HTMLButtonElement>(null);
    const searchInputRef = React.useRef<HTMLInputElement>(null);
    const contentRef = React.useRef<HTMLDivElement>(null);

    // Debounced search
    const debouncedSearchQuery = useDebounce(searchQuery, searchDebounceMs);

    // Effect for external search
    React.useEffect(() => {
      if (onSearch && debouncedSearchQuery) {
        onSearch(debouncedSearchQuery);
      }
    }, [debouncedSearchQuery, onSearch]);

    // Sync internal value with external value
    React.useEffect(() => {
      if (value !== undefined) {
        setInternalValue(value);
      }
    }, [value]);

    // Flatten options from groups
    const allOptions = React.useMemo(() => {
      const flatOptions = [...options];
      groups.forEach(group => {
        flatOptions.push(...group.options.map(option => ({ ...option, group: group.label })));
      });
      return flatOptions;
    }, [options, groups]);

    // Filter options based on search
    const filteredOptions = React.useMemo(() => {
      if (!searchQuery.trim()) return allOptions;
      
      return allOptions.filter(option =>
        option.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        option.description?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }, [allOptions, searchQuery]);

    // Get selected options
    const selectedOptions = React.useMemo(() => {
      const selectedValues = Array.isArray(internalValue) ? internalValue : [internalValue];
      return allOptions.filter(option => selectedValues.includes(option.value));
    }, [allOptions, internalValue]);

    // Keyboard navigation
    const { highlightedIndex, handleKeyDown } = useKeyboardNavigation(
      openFlag,
      filteredOptions,
      handleOptionSelect,
      () => setOpenFlag(false)
    );

    // Handlers
    function handleOptionSelect(option: SelectOption) {
      if (option.disabled) return;

      let newValue: string | string[];
      
      if (multiple) {
        const currentValues = Array.isArray(internalValue) ? internalValue : [];
        if (currentValues.includes(option.value)) {
          newValue = currentValues.filter(v => v !== option.value);
        } else {
          newValue = [...currentValues, option.value];
        }
      } else {
        newValue = option.value;
        setOpenFlag(false);
      }

      setInternalValue(newValue);
      onValueChange?.(newValue);
      onSelect?.(option);

      // Update recent selections
      if (rememberRecentSelections) {
        setRecentSelections(prev => {
          const filtered = prev.filter(item => item.value !== option.value);
          return [option, ...filtered].slice(0, maxRecentSelections);
        });
      }
    }

    function handleClear() {
      const newValue = multiple ? [] : '';
      setInternalValue(newValue);
      onValueChange?.(newValue);
    }

    function handleToggle() {
      if (disabled) return;
      setOpenFlag(!openFlag);
      
      if (!openFlag && searchable) {
        // Focus search input when opening
        setTimeout(() => {
          searchInputRef.current?.focus();
        }, 0);
      }
    }

    // Click outside handler
    React.useEffect(() => {
      function handleClickOutside(event: MouseEvent) {
        if (
          contentRef.current &&
          !contentRef.current.contains(event.target as Node) &&
          triggerRef.current &&
          !triggerRef.current.contains(event.target as Node)
        ) {
          setOpenFlag(false);
        }
      }

      if (openFlag) {
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
      }
    }, [openFlag]);

    // Render selected value
    const renderTriggerContent = () => {
      if (renderSelectedValue) {
        return renderSelectedValue(selectedOptions);
      }

      if (selectedOptions.length === 0) {
        return <span className="text-muted-foreground">{placeholder}</span>;
      }

      if (multiple) {
        if (selectedOptions.length === 1) {
          return selectedOptions[0].label;
        }
        return `${selectedOptions.length} items selected`;
      }

      return selectedOptions[0]?.label;
    };

    // Render option content
    const renderOptionContent = (option: SelectOption, isSelected: boolean) => {
      if (renderOption) {
        return renderOption(option, isSelected);
      }

      return (
        <div className="flex items-center gap-2 w-full">
          {option.icon && <span className="shrink-0">{option.icon}</span>}
          <div className="flex-1 min-w-0">
            <div className="truncate">{option.label}</div>
            {option.description && (
              <div className="text-xs text-muted-foreground truncate">
                {option.description}
              </div>
            )}
          </div>
          {isSelected && (
            <Check className="size-4 text-primary shrink-0" />
          )}
        </div>
      );
    };

    return (
      <div ref={ref} className={cn('relative', className)} {...props}>
        {/* Trigger */}
        <button
          ref={triggerRef}
          type="button"
          onClick={handleToggle}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-expanded={openFlag}
          aria-haspopup="listbox"
          aria-label={ariaLabel}
          aria-describedby={ariaDescribedBy}
          className={cn(triggerVariants({ size, openState: openFlag }))}
        >
          <div className="flex-1 text-left">
            {renderTriggerContent()}
          </div>
          
          <div className="flex items-center gap-1">
            {loading && <Loader2 className="size-4 animate-spin" />}
            {clearable && selectedOptions.length > 0 && !loading && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="hover:bg-muted rounded p-0.5"
                aria-label="Clear selection"
              >
                <X className="size-3" />
              </button>
            )}
            <ChevronDown className={cn(
              "size-4 opacity-60 transition-transform",
              openFlag && "rotate-180"
            )} />
          </div>
        </button>

        {/* Dropdown Content */}
        {openFlag && (
          <div
            ref={contentRef}
            className={cn(
              contentVariants({ size }),
              "mt-1 w-full",
              virtualScrolling && "overflow-hidden"
            )}
            style={{ maxHeight: `${maxHeight}px` }}
            data-state="open"
          >
            {/* Search Input */}
            {searchable && (
              <div className="p-2 border-b border-border">
                <div className="relative">
                  <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 size-4 text-muted-foreground" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder={searchPlaceholder}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className={cn(
                      "w-full pl-8 pr-3 py-1.5 text-sm bg-transparent border border-input rounded-md",
                      "focus:outline-none focus:ring-2 focus:ring-ring/30 focus:border-ring",
                      "placeholder:text-muted-foreground"
                    )}
                    onKeyDown={handleKeyDown}
                  />
                </div>
              </div>
            )}

            {/* Options List */}
            <div 
              className={cn(
                "p-1.5 max-h-[400px] overflow-y-auto",
                virtualScrolling && "virtual-scroll-container"
              )}
              role="listbox"
              aria-multiselectable={multiple}
            >
              {loading ? (
                <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin mr-2" />
                  {loadingMessage}
                </div>
              ) : filteredOptions.length === 0 ? (
                <div className="py-6 text-center text-sm text-muted-foreground">
                  {emptyMessage}
                </div>
              ) : (
                filteredOptions.map((option, index) => {
                  const isSelected = Array.isArray(internalValue) 
                    ? internalValue.includes(option.value)
                    : internalValue === option.value;
                  const isHighlighted = index === highlightedIndex;

                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => handleOptionSelect(option)}
                      disabled={option.disabled}
                      role="option"
                      aria-selected={isSelected}
                      className={cn(
                        optionVariants({ 
                          size, 
                          isSelected, 
                          isHighlighted 
                        })
                      )}
                    >
                      {renderOptionContent(option, isSelected)}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    );
  }
);

SearchableSelect.displayName = 'SearchableSelect';

export default SearchableSelect;
