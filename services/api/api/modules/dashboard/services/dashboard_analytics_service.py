# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Analytics Service Implementation
Purpose: Analytics service for dashboard metrics and time-series data processing
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 3
"""

import logging
import math
import random
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from flask import g

# Optional dependencies - handle gracefully if not available
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

from ..interfaces import IDashboardAnalyticsService
from ..utils.metrics_decorator import track_dashboard_method, DashboardMetricsCollector

# Optional imports for dependencies
try:
    from ....core.rbac import RBAC
    RBAC_AVAILABLE = True
except ImportError:
    RBAC = None
    RBAC_AVAILABLE = False

try:
    from ....database import get_db
    DB_AVAILABLE = True
except ImportError:
    get_db = None
    DB_AVAILABLE = False

try:
    from ....cache import get_redis
    REDIS_AVAILABLE = True
except ImportError:
    get_redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class DashboardAnalyticsService(IDashboardAnalyticsService):
    """
    Modular implementation of dashboard analytics service.
    Provides time-series analytics, metrics processing, and performance analytics.
    """
    
    def __init__(
        self,
        db_session: Optional[Any] = None,
        cache_service: Optional[Any] = None,
        utilities_service: Optional[Any] = None
    ):
        """
        Initialize dashboard analytics service
        
        Args:
            db_session: Database session
            cache_service: Optional cache service
            utilities_service: Optional utilities service
        """
        self.db_session = db_session
        self.cache = cache_service
        self.utilities = utilities_service
        self.metrics_collector = DashboardMetricsCollector()
        self.logger = logger

    def _validate_security_context(self, organization_id: str, user_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate RBAC security context for analytics access
        
        Args:
            organization_id: Organization identifier
            user_context: Optional user context
            
        Returns:
            Boolean indicating if access is allowed
            
        Raises:
            ValueError: If security validation fails
        """
        try:
            if not RBAC_AVAILABLE:
                self.logger.warning("RBAC not available, allowing access")
                return True
            
            # Get current user context
            current_user = user_context or getattr(g, 'current_user', {})
            if not current_user:
                raise ValueError("No user context available for RBAC validation")
            
            # Check if user has access to organization
            user_org_id = getattr(g, 'organization_id', None)
            if user_org_id != organization_id:
                raise ValueError(f"User does not have access to organization {organization_id}")
            
            # Platform admins should use dedicated endpoints
            if RBAC.is_platform_admin(current_user):
                raise ValueError("Platform admins should use platform-specific analytics endpoints")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Security validation failed: {e}")
            raise ValueError(f"Access denied: {e}")

    def _sanitize_numeric_value(self, value: Union[int, float, str, None], fallback: Union[int, float] = 0) -> Union[int, float]:
        """
        Sanitize numeric values to prevent NaN/Infinity in JSON responses
        
        Args:
            value: Value to sanitize
            fallback: Fallback value if sanitization fails
            
        Returns:
            Sanitized numeric value
        """
        try:
            if value is None:
                return fallback
            
            # Convert to float for processing
            numeric_value = float(value)
            
            # Check for invalid values
            if math.isnan(numeric_value) or math.isinf(numeric_value):
                self.logger.warning(f"Invalid numeric value detected: {value}, using fallback: {fallback}")
                return fallback
            
            # Return as int if it's a whole number, otherwise float
            return int(numeric_value) if numeric_value.is_integer() else numeric_value
            
        except (ValueError, TypeError, AttributeError):
            self.logger.warning(f"Could not convert value to numeric: {value}, using fallback: {fallback}")
            return fallback

    def _sanitize_analytics_data(self, data: Any) -> Any:
        """
        Recursively sanitize analytics data to prevent chart errors
        
        Args:
            data: Data to sanitize (dict, list, or primitive)
            
        Returns:
            Sanitized data structure
        """
        if isinstance(data, dict):
            return {key: self._sanitize_analytics_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_analytics_data(item) for item in data]
        elif isinstance(data, (int, float)):
            return self._sanitize_numeric_value(data)
        else:
            return data

    async def _get_time_range_dates(self, time_range: str) -> Tuple[datetime, datetime]:
        """
        Parse time range string into start and end dates
        
        Args:
            time_range: Time range string (e.g., "24h", "7d", "30d")
            
        Returns:
            Tuple of (start_date, end_date)
        """
        end_date = datetime.utcnow()
        
        if time_range == "24h":
            start_date = end_date - timedelta(hours=24)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            # Default to 24 hours
            start_date = end_date - timedelta(hours=24)
            
        return start_date, end_date

    @track_dashboard_method('dashboard_analytics_service')
    async def get_metrics_analytics(
        self,
        organization_id: str,
        metrics: List[str],
        start_date: datetime,
        end_date: datetime,
        aggregation: str = "hourly"
    ) -> Dict[str, Any]:
        """
        Get metrics analytics for dashboard with time-series data processing
        
        Args:
            organization_id: Organization identifier
            metrics: List of metrics to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            aggregation: Data aggregation level
            
        Returns:
            Dict containing metrics analytics
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If analytics retrieval fails
        """
        try:
            # Validate input
            if not organization_id or not isinstance(organization_id, str):
                raise ValueError("organization_id must be a non-empty string")
            
            if not metrics or not isinstance(metrics, list):
                raise ValueError("metrics must be a non-empty list")
            
            # Validate security context
            self._validate_security_context(organization_id)
            
            # Get database connection
            db = get_db() if DB_AVAILABLE else None
            if db is None:
                self.logger.warning("Database not available, using mock data")
                return await self._get_mock_metrics_analytics(metrics, start_date, end_date, aggregation)
            
            # Build time-series query based on aggregation
            pipeline = []
            
            # Match organization and time range
            match_stage = {
                '$match': {
                    'organization_id': organization_id,
                    'timestamp': {
                        '$gte': start_date,
                        '$lte': end_date
                    }
                }
            }
            pipeline.append(match_stage)
            
            # Group by time interval
            if aggregation == "hourly":
                group_id = {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'},
                    'hour': {'$hour': '$timestamp'}
                }
            elif aggregation == "daily":
                group_id = {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                }
            else:  # Default to hourly
                group_id = {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'},
                    'hour': {'$hour': '$timestamp'}
                }
            
            # Build aggregation fields based on requested metrics
            group_fields = {'_id': group_id}
            for metric in metrics:
                if metric in ['device_count', 'active_devices']:
                    group_fields[metric] = {'$sum': 1}
                elif metric in ['data_points', 'telemetry_count']:
                    group_fields[metric] = {'$sum': '$count'}
                elif metric in ['avg_response_time', 'avg_cpu_usage']:
                    group_fields[metric] = {'$avg': f'${metric}'}
                else:
                    group_fields[metric] = {'$sum': 1}  # Default aggregation
            
            pipeline.append({'$group': group_fields})
            pipeline.append({'$sort': {'_id': 1}})
            
            # Execute aggregation pipeline
            try:
                analytics_results = list(db.telemetry.aggregate(pipeline))
            except Exception as e:
                self.logger.warning(f"Database query failed: {e}, using mock data")
                return await self._get_mock_metrics_analytics(metrics, start_date, end_date, aggregation)
            
            # Process results into time-series format
            time_series_data = []
            for result in analytics_results:
                timestamp_parts = result['_id']
                
                if aggregation == "hourly":
                    timestamp = datetime(
                        timestamp_parts['year'],
                        timestamp_parts['month'],
                        timestamp_parts['day'],
                        timestamp_parts.get('hour', 0)
                    )
                else:  # daily
                    timestamp = datetime(
                        timestamp_parts['year'],
                        timestamp_parts['month'],
                        timestamp_parts['day']
                    )
                
                data_point = {
                    'timestamp': timestamp.isoformat(),
                    'date': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add metric values
                for metric in metrics:
                    value = result.get(metric, 0)
                    data_point[metric] = self._sanitize_numeric_value(value)
                
                time_series_data.append(data_point)
            
            # Calculate summary statistics
            summary_stats = {}
            for metric in metrics:
                values = [point.get(metric, 0) for point in time_series_data]
                if values:
                    summary_stats[metric] = {
                        'total': sum(values),
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
                else:
                    summary_stats[metric] = {
                        'total': 0,
                        'average': 0,
                        'min': 0,
                        'max': 0,
                        'count': 0
                    }
            
            analytics_data = {
                'time_series': time_series_data,
                'summary': summary_stats,
                'metadata': {
                    'organization_id': organization_id,
                    'metrics': metrics,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'aggregation': aggregation,
                    'total_points': len(time_series_data),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            # Sanitize all data
            analytics_data = self._sanitize_analytics_data(analytics_data)
            
            self.logger.info(f"Generated analytics for {len(metrics)} metrics with {len(time_series_data)} data points")
            return analytics_data
            
        except Exception as e:
            self.logger.error(f"Error generating metrics analytics: {e}", exc_info=True)
            # Return fallback mock data on error
            return await self._get_mock_metrics_analytics(metrics, start_date, end_date, aggregation)

    async def _get_mock_metrics_analytics(
        self,
        metrics: List[str],
        start_date: datetime,
        end_date: datetime,
        aggregation: str
    ) -> Dict[str, Any]:
        """
        Generate mock analytics data for fallback scenarios
        
        Args:
            metrics: List of metrics to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            aggregation: Data aggregation level
            
        Returns:
            Dict containing mock analytics data
        """
        time_series_data = []
        current_time = start_date
        
        # Generate time intervals based on aggregation
        if aggregation == "hourly":
            interval = timedelta(hours=1)
        else:  # daily
            interval = timedelta(days=1)
        
        while current_time <= end_date:
            data_point = {
                'timestamp': current_time.isoformat(),
                'date': current_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Generate mock data for each metric
            for metric in metrics:
                if metric == 'device_count':
                    data_point[metric] = random.randint(50, 200)
                elif metric == 'active_devices':
                    data_point[metric] = random.randint(40, 180)
                elif metric == 'data_points':
                    data_point[metric] = random.randint(1000, 5000)
                elif metric == 'avg_response_time':
                    data_point[metric] = round(random.uniform(20, 100), 2)
                elif metric == 'avg_cpu_usage':
                    data_point[metric] = round(random.uniform(30, 80), 2)
                else:
                    data_point[metric] = random.randint(10, 100)
            
            time_series_data.append(data_point)
            current_time += interval
        
        # Calculate summary statistics
        summary_stats = {}
        for metric in metrics:
            values = [point.get(metric, 0) for point in time_series_data]
            summary_stats[metric] = {
                'total': sum(values),
                'average': round(sum(values) / len(values), 2) if values else 0,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'count': len(values)
            }
        
        return {
            'time_series': time_series_data,
            'summary': summary_stats,
            'metadata': {
                'metrics': metrics,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'aggregation': aggregation,
                'total_points': len(time_series_data),
                'generated_at': datetime.utcnow().isoformat(),
                'mock_data': True
            }
        }

    @track_dashboard_method('dashboard_trend_analysis')
    async def get_trend_analysis(
        self,
        organization_id: str,
        metric: str,
        time_window: int = 30,
        trend_type: str = "linear"
    ) -> Dict[str, Any]:
        """
        Analyze trends in dashboard metrics with statistical analysis
        
        Args:
            organization_id: Organization identifier
            metric: Metric to analyze
            time_window: Time window in days
            trend_type: Type of trend analysis
            
        Returns:
            Dict containing trend analysis
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If trend analysis fails
        """
        try:
            # Validate input
            if not organization_id or not isinstance(organization_id, str):
                raise ValueError("organization_id must be a non-empty string")
            
            if not metric or not isinstance(metric, str):
                raise ValueError("metric must be a non-empty string")
            
            # Validate security context
            self._validate_security_context(organization_id)
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_window)
            
            # Get metrics data for trend analysis
            metrics_data = await self.get_metrics_analytics(
                organization_id=organization_id,
                metrics=[metric],
                start_date=start_date,
                end_date=end_date,
                aggregation="daily"
            )
            
            time_series = metrics_data.get('time_series', [])
            if not time_series:
                raise ValueError("No data available for trend analysis")
            
            # Extract values for analysis
            values = [point.get(metric, 0) for point in time_series]
            dates = [point.get('timestamp') for point in time_series]
            
            # Perform trend analysis
            if trend_type == "linear" and len(values) >= 2:
                # Simple linear regression for trend
                n = len(values)
                x = list(range(n))
                
                # Calculate linear trend
                sum_x = sum(x)
                sum_y = sum(values)
                sum_xy = sum(xi * yi for xi, yi in zip(x, values))
                sum_x2 = sum(xi ** 2 for xi in x)
                
                if n * sum_x2 - sum_x ** 2 != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                    intercept = (sum_y - slope * sum_x) / n
                else:
                    slope = 0
                    intercept = sum_y / n if n > 0 else 0
                
                # Generate trend line
                trend_line = [intercept + slope * xi for xi in x]
                
                # Calculate trend direction and strength
                if slope > 0:
                    trend_direction = "increasing"
                elif slope < 0:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
                
                # Calculate R-squared for trend strength
                if len(values) > 1:
                    y_mean = sum(values) / len(values)
                    ss_tot = sum((yi - y_mean) ** 2 for yi in values)
                    ss_res = sum((yi - trend_i) ** 2 for yi, trend_i in zip(values, trend_line))
                    
                    if ss_tot > 0:
                        r_squared = 1 - (ss_res / ss_tot)
                    else:
                        r_squared = 0
                else:
                    r_squared = 0
                
                trend_strength = "strong" if r_squared > 0.7 else "moderate" if r_squared > 0.3 else "weak"
                
            else:
                # Fallback: simple trend based on first and last values
                if len(values) >= 2:
                    slope = (values[-1] - values[0]) / len(values)
                    trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
                    r_squared = 0.5  # Moderate confidence for fallback
                    trend_strength = "moderate"
                    trend_line = values  # Use actual values as trend line
                else:
                    slope = 0
                    trend_direction = "stable"
                    r_squared = 0
                    trend_strength = "weak"
                    trend_line = values
            
            # Calculate additional statistics
            if values:
                volatility = np.std(values) if NUMPY_AVAILABLE else self._calculate_std(values)
                average_value = sum(values) / len(values)
                change_percent = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
            else:
                volatility = 0
                average_value = 0
                change_percent = 0
            
            trend_analysis = {
                'metric': metric,
                'time_window_days': time_window,
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'slope': self._sanitize_numeric_value(slope),
                'r_squared': self._sanitize_numeric_value(r_squared),
                'volatility': self._sanitize_numeric_value(volatility),
                'average_value': self._sanitize_numeric_value(average_value),
                'change_percent': self._sanitize_numeric_value(change_percent),
                'data_points': len(values),
                'trend_line': [self._sanitize_numeric_value(val) for val in trend_line],
                'original_values': [self._sanitize_numeric_value(val) for val in values],
                'timestamps': dates,
                'metadata': {
                    'organization_id': organization_id,
                    'analysis_type': trend_type,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            self.logger.info(f"Generated trend analysis for metric '{metric}': {trend_direction} trend with {trend_strength} strength")
            return trend_analysis
            
        except Exception as e:
            self.logger.error(f"Error in trend analysis: {e}", exc_info=True)
            # Return fallback analysis
            return {
                'metric': metric,
                'time_window_days': time_window,
                'trend_direction': 'stable',
                'trend_strength': 'weak',
                'slope': 0,
                'r_squared': 0,
                'volatility': 0,
                'average_value': 0,
                'change_percent': 0,
                'data_points': 0,
                'trend_line': [],
                'original_values': [],
                'timestamps': [],
                'metadata': {
                    'organization_id': organization_id,
                    'analysis_type': trend_type,
                    'generated_at': datetime.utcnow().isoformat(),
                    'error': 'Fallback analysis due to processing error'
                }
            }

    def _calculate_std(self, values: List[float]) -> float:
        """
        Calculate standard deviation without numpy
        
        Args:
            values: List of numeric values
            
        Returns:
            Standard deviation
        """
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    async def get_dashboard_analytics(
        self,
        organization_id: str,
        time_range: str = "24h",
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard analytics data
        
        Args:
            organization_id: Organization identifier
            time_range: Time range for analytics (24h, 7d, 30d)
            user_context: Optional user context for RBAC
            
        Returns:
            Dict containing comprehensive analytics data
        """
        try:
            # Validate security context
            self._validate_security_context(organization_id, user_context)
            
            # Parse time range
            start_date, end_date = await self._get_time_range_dates(time_range)
            
            # Get core metrics
            core_metrics = ['device_count', 'active_devices', 'data_points', 'avg_response_time']
            metrics_analytics = await self.get_metrics_analytics(
                organization_id=organization_id,
                metrics=core_metrics,
                start_date=start_date,
                end_date=end_date,
                aggregation="hourly"
            )
            
            # Get trend analysis for key metric
            trend_analysis = await self.get_trend_analysis(
                organization_id=organization_id,
                metric='device_count',
                time_window=7 if time_range in ['7d', '30d'] else 1
            )
            
            # Compile comprehensive analytics
            analytics_data = {
                'overview': {
                    'time_range': time_range,
                    'total_data_points': metrics_analytics.get('metadata', {}).get('total_points', 0),
                    'metrics_analyzed': core_metrics
                },
                'metrics': metrics_analytics,
                'trends': trend_analysis,
                'performance': {
                    'avg_response_time': metrics_analytics.get('summary', {}).get('avg_response_time', {}),
                    'data_throughput': metrics_analytics.get('summary', {}).get('data_points', {})
                },
                'metadata': {
                    'organization_id': organization_id,
                    'generated_at': datetime.utcnow().isoformat(),
                    'time_range': time_range,
                    'analysis_period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    }
                }
            }
            
            return self._sanitize_analytics_data(analytics_data)
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard analytics: {e}", exc_info=True)
            raise