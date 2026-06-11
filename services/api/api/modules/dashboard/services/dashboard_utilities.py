# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Utilities Service Implementation
Purpose: Utility functions for dashboard operations
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 1
"""

import math
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

# Optional dependencies - will be set to None if not available
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

from ..interfaces import IDashboardUtilitiesService

# Optional service imports - handle gracefully if not available
try:
    from ...analytics.services import ModularAnalyticsService
    ANALYTICS_AVAILABLE = True
except ImportError:
    ModularAnalyticsService = None
    ANALYTICS_AVAILABLE = False

try:
    from ...security.services.certificate_service import CertificateService
    CERTIFICATE_SERVICE_AVAILABLE = True
except ImportError:
    CertificateService = None
    CERTIFICATE_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)


class DashboardUtilitiesService(IDashboardUtilitiesService):
    """Dashboard utilities service implementation"""
    
    def __init__(
        self,
        db_session: Optional[Any] = None,
        redis_client: Optional[Any] = None
    ):
        """
        Initialize dashboard utilities service
        
        Args:
            db_session: Database session
            redis_client: Redis client for caching
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.logger = logger
    
    def get_services(self) -> Dict[str, Any]:
        """
        Initialize and return modularized services
        
        Returns:
            Dict containing initialized services
        """
        try:
            # Import services that are available
            services = {}
            
            # Try to initialize stats service if available
            try:
                from ....services import StatsService
                if self.db_session and self.redis_client:
                    services['stats'] = StatsService(self.db_session, self.redis_client)
                else:
                    services['stats'] = None
            except ImportError as e:
                self.logger.warning(f"StatsService not available: {e}")
                services['stats'] = None
            
            # Try to initialize security analytics service if available
            try:
                from ....services import SecurityAnalyticsService
                if self.db_session and self.redis_client:
                    services['security'] = SecurityAnalyticsService(self.db_session, self.redis_client)
                else:
                    services['security'] = None
            except ImportError as e:
                self.logger.warning(f"SecurityAnalyticsService not available: {e}")
                services['security'] = None
            
            return services
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            return {
                'stats': None,
                'security': None,
            }
    
    def sanitize_numeric_value(
        self,
        value: Union[int, float, str, None],
        fallback: Union[int, float] = 0
    ) -> Union[int, float]:
        """
        Sanitize numeric values to prevent NaN/Infinity in JSON responses
        
        Args:
            value: Value to sanitize
            fallback: Fallback value if sanitization fails
            
        Returns:
            Sanitized numeric value
        """
        if value is None:
            return fallback
        
        try:
            num_val = float(value)
            if math.isnan(num_val) or math.isinf(num_val):
                return fallback
            return num_val
        except (ValueError, TypeError):
            return fallback
    
    def sanitize_response_data(self, data: Any) -> Any:
        """
        Recursively sanitize response data to prevent chart errors
        
        Args:
            data: Data to sanitize (dict, list, or primitive)
            
        Returns:
            Sanitized data structure
        """
        if isinstance(data, dict):
            return {key: self.sanitize_response_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_response_data(item) for item in data]
        elif isinstance(data, (int, float)):
            return self.sanitize_numeric_value(data)
        else:
            return data
    
    def validate_dashboard_request(
        self,
        request_data: Dict[str, Any],
        required_fields: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate dashboard request data
        
        Args:
            request_data: Request data to validate
            required_fields: Required field names
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if request_data is valid
            if not isinstance(request_data, dict):
                return False, "Request data must be a dictionary"
            
            # Check required fields
            missing_fields = []
            for field in required_fields:
                if field not in request_data:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Validate organization_id if present
            if 'organization_id' in request_data:
                org_id = request_data['organization_id']
                if not org_id or not isinstance(org_id, str):
                    return False, "organization_id must be a non-empty string"
            
            # Validate time ranges if present
            if 'start_date' in request_data and 'end_date' in request_data:
                try:
                    start_date = request_data['start_date']
                    end_date = request_data['end_date']
                    
                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    if isinstance(end_date, str):
                        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    
                    if start_date >= end_date:
                        return False, "start_date must be before end_date"
                        
                except (ValueError, TypeError) as e:
                    return False, f"Invalid date format: {str(e)}"
            
            # Validate pagination parameters if present
            if 'limit' in request_data:
                limit = request_data['limit']
                if not isinstance(limit, int) or limit <= 0 or limit > 10000:
                    return False, "limit must be a positive integer not exceeding 10000"
            
            if 'offset' in request_data:
                offset = request_data['offset']
                if not isinstance(offset, int) or offset < 0:
                    return False, "offset must be a non-negative integer"
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error validating request data: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def format_time_series_data(
        self,
        data: Any,  # Changed from pd.DataFrame to Any for flexibility
        time_column: str = 'timestamp',
        value_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Format time series data for dashboard charts
        
        Args:
            data: Raw time series data (pandas DataFrame if available, otherwise dict/list)
            time_column: Name of timestamp column
            value_columns: Columns to include in output
            
        Returns:
            Formatted data for chart rendering
        """
        try:
            # Handle case where pandas is not available
            if not PANDAS_AVAILABLE:
                self.logger.warning("Pandas not available, using fallback time series formatting")
                return self._format_time_series_fallback(data, time_column, value_columns)
            
            # Handle empty DataFrame
            if hasattr(data, 'empty') and data.empty:
                return {
                    "series": [],
                    "timestamps": [],
                    "metadata": {
                        "total_points": 0,
                        "time_range": None,
                        "columns": []
                    }
                }
            
            # Ensure timestamp column exists
            if time_column not in data.columns:
                if data.index.name == time_column or isinstance(data.index, pd.DatetimeIndex):
                    # Use index as timestamp
                    data = data.reset_index()
                    if data.index.name:
                        time_column = data.index.name
                    else:
                        data = data.rename(columns={data.columns[0]: time_column})
                else:
                    raise ValueError(f"Time column '{time_column}' not found in data")
            
            # Determine value columns
            if value_columns is None:
                value_columns = [col for col in data.columns if col != time_column]
            else:
                # Filter to only existing columns
                value_columns = [col for col in value_columns if col in data.columns]
            
            # Sort by timestamp
            data = data.sort_values(by=time_column)
            
            # Convert timestamps to ISO format
            timestamps = []
            for ts in data[time_column]:
                if isinstance(ts, str):
                    # Try to parse string timestamp
                    try:
                        ts = pd.to_datetime(ts)
                    except:
                        continue
                
                if pd.isna(ts):
                    continue
                    
                if hasattr(ts, 'isoformat'):
                    timestamps.append(ts.isoformat())
                else:
                    timestamps.append(str(ts))
            
            # Format series data
            series = []
            for column in value_columns:
                if column in data.columns:
                    values = []
                    for val in data[column]:
                        sanitized_val = self.sanitize_numeric_value(val)
                        values.append(sanitized_val)
                    
                    series.append({
                        "name": column,
                        "data": values,
                        "type": "line"  # Default chart type
                    })
            
            # Calculate metadata
            metadata = {
                "total_points": len(data),
                "time_range": {
                    "start": timestamps[0] if timestamps else None,
                    "end": timestamps[-1] if timestamps else None
                },
                "columns": value_columns,
                "sample_rate": self._calculate_sample_rate(data, time_column) if len(data) > 1 else None
            }
            
            return {
                "series": series,
                "timestamps": timestamps,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting time series data: {str(e)}")
            return {
                "series": [],
                "timestamps": [],
                "metadata": {
                    "total_points": 0,
                    "time_range": None,
                    "columns": [],
                    "error": str(e)
                }
            }
    
    def _calculate_sample_rate(self, data: Any, time_column: str) -> Optional[str]:
        """
        Calculate the sample rate of time series data
        
        Args:
            data: Time series data
            time_column: Name of timestamp column
            
        Returns:
            String description of sample rate
        """
        try:
            if not PANDAS_AVAILABLE:
                return self._calculate_sample_rate_fallback(data, time_column)
            
            if len(data) < 2:
                return None
            
            # Convert to datetime if needed
            timestamps = pd.to_datetime(data[time_column])
            
            # Calculate time differences
            time_diffs = timestamps.diff().dropna()
            
            if time_diffs.empty:
                return None
            
            # Get median time difference
            median_diff = time_diffs.median()
            
            # Convert to human-readable format
            seconds = median_diff.total_seconds()
            
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds / 60)}m"
            elif seconds < 86400:
                return f"{int(seconds / 3600)}h"
            else:
                return f"{int(seconds / 86400)}d"
                
        except Exception as e:
            self.logger.warning(f"Could not calculate sample rate: {str(e)}")
            return None
    
    def _calculate_sample_rate_fallback(self, data: Any, time_column: str) -> Optional[str]:
        """
        Fallback sample rate calculation when pandas is not available
        
        Args:
            data: Time series data (list of dicts or similar)
            time_column: Name of timestamp column
            
        Returns:
            String description of sample rate
        """
        try:
            if not isinstance(data, list) or len(data) < 2:
                return None
            
            # Extract timestamps
            timestamps = []
            for item in data:
                if isinstance(item, dict) and time_column in item:
                    ts_str = str(item[time_column])
                    try:
                        # Try to parse ISO format timestamp
                        if 'T' in ts_str:
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        else:
                            ts = datetime.fromisoformat(ts_str)
                        timestamps.append(ts)
                    except ValueError:
                        continue
            
            if len(timestamps) < 2:
                return None
            
            # Calculate time differences
            time_diffs = []
            for i in range(1, len(timestamps)):
                diff = timestamps[i] - timestamps[i-1]
                time_diffs.append(diff.total_seconds())
            
            if not time_diffs:
                return None
            
            # Get median time difference
            time_diffs.sort()
            median_seconds = time_diffs[len(time_diffs) // 2]
            
            # Convert to human-readable format
            if median_seconds < 60:
                return f"{int(median_seconds)}s"
            elif median_seconds < 3600:
                return f"{int(median_seconds / 60)}m"
            elif median_seconds < 86400:
                return f"{int(median_seconds / 3600)}h"
            else:
                return f"{int(median_seconds / 86400)}d"
                
        except Exception as e:
            self.logger.warning(f"Could not calculate sample rate in fallback mode: {str(e)}")
            return None
    
    def calculate_statistics(self, data: Any) -> Dict[str, Any]:
        """
        Calculate basic statistics for a data series
        
        Args:
            data: Data series to analyze (pandas Series if available, otherwise list/array)
            
        Returns:
            Dict containing statistical measures
        """
        try:
            # Handle case where pandas is not available
            if not PANDAS_AVAILABLE:
                return self._calculate_statistics_fallback(data)
            
            # Handle pandas Series
            if hasattr(data, 'empty') and data.empty:
                return {}
            
            # Remove non-numeric values
            numeric_data = pd.to_numeric(data, errors='coerce').dropna()
            
            if numeric_data.empty:
                return {}
            
            stats = {
                "count": len(numeric_data),
                "mean": self.sanitize_numeric_value(numeric_data.mean()),
                "median": self.sanitize_numeric_value(numeric_data.median()),
                "std": self.sanitize_numeric_value(numeric_data.std()),
                "min": self.sanitize_numeric_value(numeric_data.min()),
                "max": self.sanitize_numeric_value(numeric_data.max()),
                "quartiles": {
                    "q25": self.sanitize_numeric_value(numeric_data.quantile(0.25)),
                    "q50": self.sanitize_numeric_value(numeric_data.quantile(0.50)),
                    "q75": self.sanitize_numeric_value(numeric_data.quantile(0.75))
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {str(e)}")
            return {}
    
    def format_dashboard_error(
        self,
        error_message: str,
        error_code: str = "DASHBOARD_ERROR",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format error response for dashboard endpoints
        
        Args:
            error_message: Human-readable error message
            error_code: Error code for programmatic handling
            details: Additional error details
            
        Returns:
            Formatted error response
        """
        error_response = {
            "error": True,
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": None
        }
        
        if details:
            error_response["details"] = details
        
        return error_response
    
    def create_cache_key(
        self,
        organization_id: str,
        endpoint: str,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Create consistent cache key for dashboard data
        
        Args:
            organization_id: Organization identifier
            endpoint: Dashboard endpoint name
            parameters: Request parameters
            
        Returns:
            Cache key string
        """
        try:
            # Sort parameters for consistent key generation
            sorted_params = sorted(parameters.items())
            param_str = "_".join([f"{k}:{v}" for k, v in sorted_params])
            
            cache_key = f"dashboard:{organization_id}:{endpoint}:{param_str}"
            
            # Limit key length
            if len(cache_key) > 250:
                import hashlib
                param_hash = hashlib.md5(param_str.encode()).hexdigest()
                cache_key = f"dashboard:{organization_id}:{endpoint}:{param_hash}"
            
            return cache_key
            
        except Exception as e:
            self.logger.warning(f"Error creating cache key: {str(e)}")
            # Fallback to simple key
            return f"dashboard:{organization_id}:{endpoint}:{hash(str(parameters))}"
    
    def _format_time_series_fallback(
        self,
        data: Any,
        time_column: str = 'timestamp',
        value_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fallback time series formatting when pandas is not available
        
        Args:
            data: Raw data (dict, list, or other structure)
            time_column: Name of timestamp column
            value_columns: Columns to include in output
            
        Returns:
            Formatted data for chart rendering
        """
        try:
            # Handle different data formats
            if isinstance(data, list):
                # Assume list of dictionaries
                if not data:
                    return self._empty_time_series_result()
                
                timestamps = []
                series_data = {}
                
                for item in data:
                    if isinstance(item, dict):
                        # Extract timestamp
                        if time_column in item:
                            timestamps.append(str(item[time_column]))
                        
                        # Extract values
                        for key, value in item.items():
                            if key != time_column:
                                if key not in series_data:
                                    series_data[key] = []
                                series_data[key].append(self.sanitize_numeric_value(value))
                
                # Format series
                series = []
                for name, values in series_data.items():
                    if value_columns is None or name in value_columns:
                        series.append({
                            "name": name,
                            "data": values,
                            "type": "line"
                        })
                
                return {
                    "series": series,
                    "timestamps": timestamps,
                    "metadata": {
                        "total_points": len(data),
                        "time_range": {
                            "start": timestamps[0] if timestamps else None,
                            "end": timestamps[-1] if timestamps else None
                        },
                        "columns": list(series_data.keys()),
                        "fallback_mode": True
                    }
                }
            
            elif isinstance(data, dict):
                # Handle dict format
                return {
                    "series": [],
                    "timestamps": [],
                    "metadata": {
                        "total_points": 0,
                        "time_range": None,
                        "columns": [],
                        "fallback_mode": True,
                        "error": "Dict format not supported in fallback mode"
                    }
                }
            
            else:
                return self._empty_time_series_result()
                
        except Exception as e:
            self.logger.error(f"Error in fallback time series formatting: {str(e)}")
            return self._empty_time_series_result()
    
    def _empty_time_series_result(self) -> Dict[str, Any]:
        """Return empty time series result"""
        return {
            "series": [],
            "timestamps": [],
            "metadata": {
                "total_points": 0,
                "time_range": None,
                "columns": [],
                "fallback_mode": True
            }
        }
    
    def _calculate_statistics_fallback(self, data: Any) -> Dict[str, Any]:
        """
        Fallback statistics calculation when pandas is not available
        
        Args:
            data: Data to analyze (list, tuple, or iterable)
            
        Returns:
            Dict containing statistical measures
        """
        try:
            # Convert to list and filter numeric values
            if hasattr(data, '__iter__') and not isinstance(data, (str, dict)):
                numeric_values = []
                for item in data:
                    try:
                        num_val = float(item)
                        if not (math.isnan(num_val) or math.isinf(num_val)):
                            numeric_values.append(num_val)
                    except (ValueError, TypeError):
                        continue
            else:
                return {}
            
            if not numeric_values:
                return {}
            
            # Calculate basic statistics
            count = len(numeric_values)
            sorted_values = sorted(numeric_values)
            
            mean = sum(numeric_values) / count
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            
            # Median
            mid = count // 2
            if count % 2 == 0:
                median = (sorted_values[mid - 1] + sorted_values[mid]) / 2
            else:
                median = sorted_values[mid]
            
            # Standard deviation
            variance = sum((x - mean) ** 2 for x in numeric_values) / count
            std = math.sqrt(variance)
            
            # Quartiles
            q1_idx = count // 4
            q3_idx = 3 * count // 4
            q25 = sorted_values[q1_idx] if q1_idx < count else min_val
            q75 = sorted_values[q3_idx] if q3_idx < count else max_val
            
            stats = {
                "count": count,
                "mean": self.sanitize_numeric_value(mean),
                "median": self.sanitize_numeric_value(median),
                "std": self.sanitize_numeric_value(std),
                "min": self.sanitize_numeric_value(min_val),
                "max": self.sanitize_numeric_value(max_val),
                "quartiles": {
                    "q25": self.sanitize_numeric_value(q25),
                    "q50": self.sanitize_numeric_value(median),
                    "q75": self.sanitize_numeric_value(q75)
                },
                "fallback_mode": True
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error in fallback statistics calculation: {str(e)}")
            return {}