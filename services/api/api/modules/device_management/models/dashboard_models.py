# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class WidgetType(Enum):
    """Dashboard widget types"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    METRIC_CARD = "metric_card"
    TABLE = "table"
    MAP = "map"
    ALERT_LIST = "alert_list"
    DEVICE_STATUS = "device_status"
    TIMELINE = "timeline"
    SCATTER_PLOT = "scatter_plot"
    HISTOGRAM = "histogram"
    TREEMAP = "treemap"


class DashboardType(Enum):
    """Pre-built dashboard types"""
    DEVICE_HEALTH = "device_health"
    PERFORMANCE = "performance"
    SECURITY = "security"
    EDGE_COMPUTING = "edge_computing"
    CUSTOM = "custom"
    FLEET_OVERVIEW = "fleet_overview"
    MAINTENANCE = "maintenance"
    ANALYTICS = "analytics"


class RefreshInterval(Enum):
    """Dashboard refresh intervals"""
    REAL_TIME = 5  # seconds
    FAST = 15
    NORMAL = 30
    SLOW = 60
    VERY_SLOW = 300
    MANUAL = 0


class TimeRange(Enum):
    """Time range presets"""
    LAST_5_MIN = "5m"
    LAST_15_MIN = "15m"
    LAST_30_MIN = "30m"
    LAST_1_HOUR = "1h"
    LAST_3_HOURS = "3h"
    LAST_6_HOURS = "6h"
    LAST_12_HOURS = "12h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    CUSTOM = "custom"


class AggregationFunction(Enum):
    """Metric aggregation functions"""
    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"
    STD_DEV = "stddev"
    RATE = "rate"
    DELTA = "delta"


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class MetricQuery:
    """Query definition for metrics"""
    metric_name: str
    device_filter: Optional[Dict[str, Any]] = None
    aggregation: AggregationFunction = AggregationFunction.AVG
    group_by: Optional[List[str]] = None
    time_range: TimeRange = TimeRange.LAST_1_HOUR
    custom_time_range: Optional[Dict[str, datetime]] = None
    interval: Optional[str] = None  # e.g., "1m", "5m", "1h"
    filters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "metric_name": self.metric_name,
            "device_filter": self.device_filter,
            "aggregation": self.aggregation.value,
            "group_by": self.group_by,
            "time_range": self.time_range.value,
            "custom_time_range": self.custom_time_range,
            "interval": self.interval,
            "filters": self.filters
        }


@dataclass
class WidgetConfig:
    """Configuration for a dashboard widget"""
    widget_id: str
    widget_type: WidgetType
    title: str
    queries: List[MetricQuery]
    position: Dict[str, int]  # {"x": 0, "y": 0, "w": 4, "h": 3}
    options: Dict[str, Any] = field(default_factory=dict)
    thresholds: Optional[List[Dict[str, Any]]] = None
    alert_rules: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "queries": [q.to_dict() for q in self.queries],
            "position": self.position,
            "options": self.options,
            "thresholds": self.thresholds,
            "alert_rules": self.alert_rules
        }


@dataclass
class DashboardLayout:
    """Dashboard layout configuration"""
    columns: int = 12
    row_height: int = 80
    margin: Dict[str, int] = field(default_factory=lambda: {"x": 10, "y": 10})
    container_padding: Dict[str, int] = field(default_factory=lambda: {"x": 10, "y": 10})
    responsive: bool = True
    breakpoints: Dict[str, int] = field(default_factory=lambda: {"lg": 1200, "md": 996, "sm": 768})


@dataclass
class Dashboard:
    """Dashboard configuration model"""
    dashboard_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    dashboard_type: DashboardType = DashboardType.CUSTOM
    widgets: List[WidgetConfig] = field(default_factory=list)
    layout: DashboardLayout = field(default_factory=DashboardLayout)
    refresh_interval: RefreshInterval = RefreshInterval.NORMAL
    time_range: TimeRange = TimeRange.LAST_1_HOUR
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_public: bool = False
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "dashboard_id": self.dashboard_id,
            "org_id": self.org_id,
            "name": self.name,
            "description": self.description,
            "dashboard_type": self.dashboard_type.value,
            "widgets": [w.to_dict() for w in self.widgets],
            "layout": {
                "columns": self.layout.columns,
                "row_height": self.layout.row_height,
                "margin": self.layout.margin,
                "container_padding": self.layout.container_padding,
                "responsive": self.layout.responsive,
                "breakpoints": self.layout.breakpoints
            },
            "refresh_interval": self.refresh_interval.value,
            "time_range": self.time_range.value,
            "variables": self.variables,
            "tags": self.tags,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "is_public": self.is_public,
            "is_default": self.is_default
        }
    
    def add_widget(self, widget: WidgetConfig) -> None:
        """Add a widget to the dashboard"""
        self.widgets.append(widget)
        self.updated_at = datetime.utcnow()
    
    def remove_widget(self, widget_id: str) -> None:
        """Remove a widget from the dashboard"""
        self.widgets = [w for w in self.widgets if w.widget_id != widget_id]
        self.updated_at = datetime.utcnow()
    
    def update_widget(self, widget_id: str, updated_widget: WidgetConfig) -> None:
        """Update a widget configuration"""
        for i, widget in enumerate(self.widgets):
            if widget.widget_id == widget_id:
                self.widgets[i] = updated_widget
                self.updated_at = datetime.utcnow()
                break


@dataclass
class MetricAggregation:
    """Aggregated metric data"""
    metric_name: str
    aggregation_type: AggregationFunction
    value: Union[float, int, None]
    timestamp: datetime
    device_count: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "metric_name": self.metric_name,
            "aggregation_type": self.aggregation_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "device_count": self.device_count,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class AlertVisualization:
    """Alert visualization configuration"""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    device_id: Optional[str] = None
    metric_name: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "device_id": self.device_id,
            "metric_name": self.metric_name,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_active": self.is_active,
            "tags": self.tags
        }


@dataclass
class DashboardTemplate:
    """Pre-built dashboard template"""
    template_id: str
    name: str
    description: str
    dashboard_type: DashboardType
    widgets: List[WidgetConfig]
    layout: DashboardLayout
    default_time_range: TimeRange
    default_refresh_interval: RefreshInterval
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dashboard(self, dashboard_id: str, org_id: str, name: Optional[str] = None) -> Dashboard:
        """Create a dashboard instance from template"""
        return Dashboard(
            dashboard_id=dashboard_id,
            org_id=org_id,
            name=name or self.name,
            description=self.description,
            dashboard_type=self.dashboard_type,
            widgets=self.widgets.copy(),
            layout=self.layout,
            refresh_interval=self.default_refresh_interval,
            time_range=self.default_time_range,
            variables=self.variables.copy(),
            tags=self.tags.copy()
        )


@dataclass
class DashboardExport:
    """Dashboard export configuration"""
    format: str  # "grafana", "json", "yaml"
    include_data: bool = False
    time_range: Optional[TimeRange] = None
    custom_time_range: Optional[Dict[str, datetime]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "format": self.format,
            "include_data": self.include_data,
            "time_range": self.time_range.value if self.time_range else None,
            "custom_time_range": self.custom_time_range
        }