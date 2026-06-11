# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Advanced Query Models for Device Management
Purpose: Support complex queries with AND/OR conditions, field-specific filters, and pagination
Date: January 27, 2025
Part of TESA IoT Platform Device Management Module
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime
from enum import Enum

from ..models.device_models import DeviceStatus, DeviceType, ConnectionProtocol


# Maximum length allowed for any user-supplied string that is compiled into a
# MongoDB $regex. Capping the length bounds regex-engine work and mitigates
# ReDoS (regular-expression denial of service).
MAX_REGEX_INPUT_LENGTH = 128

# Whitelist of device document field names that may be referenced by a
# client-supplied filter, text-search, or sort. Any field name outside this set
# is rejected (fail-closed) to prevent NoSQL field/operator injection.
ALLOWED_QUERY_FIELDS = frozenset({
    "device_id", "name", "device_type", "status", "protocol",
    "mac_address", "ip_address", "firmware_version", "hardware_version",
    "serial_number", "location", "metadata", "tags", "created_at",
    "updated_at", "last_seen", "certificate_id", "group_ids", "org_id",
})


def _safe_regex_literal(value: Any) -> str:
    """Return a length-capped, regex-escaped literal for safe use in $regex.

    Rejects non-string values and values longer than MAX_REGEX_INPUT_LENGTH so
    that attacker-controlled input cannot inject regex metacharacters (NoSQL
    injection) or pathological patterns (ReDoS).
    """
    if not isinstance(value, str):
        raise ValueError("Regex search value must be a string")
    if len(value) > MAX_REGEX_INPUT_LENGTH:
        raise ValueError(
            f"Search value exceeds maximum length of {MAX_REGEX_INPUT_LENGTH}"
        )
    return re.escape(value)


def _validate_field_name(field_name: Any) -> str:
    """Validate a field name against the allowed-fields whitelist (fail-closed)."""
    if not isinstance(field_name, str) or field_name not in ALLOWED_QUERY_FIELDS:
        raise ValueError(f"Invalid query field: {field_name}")
    return field_name


class QueryOperator(Enum):
    """Query operators for field comparisons"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    REGEX = "regex"


class LogicalOperator(Enum):
    """Logical operators for combining conditions"""
    AND = "and"
    OR = "or"
    NOT = "not"


class SortOrder(Enum):
    """Sort order enumeration"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class FieldFilter:
    """Field-specific filter condition"""
    field: str
    operator: QueryOperator
    value: Any
    case_sensitive: bool = True
    
    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert to MongoDB query format.

        Hardened against NoSQL injection: the field name is validated against
        the allowed-fields whitelist, scalar operators reject dict-typed values
        (so an attacker cannot smuggle in `$where`/`$gt`/etc.), and any value
        used in a $regex is regex-escaped and length-capped to prevent regex
        injection and ReDoS.
        """
        field_name = _validate_field_name(self.field)
        options = "i" if not self.case_sensitive else ""

        # Operators that compare against a scalar value must NOT accept a dict,
        # otherwise a payload like {"$gt": ""} could inject Mongo operators.
        scalar_ops = {
            QueryOperator.EQUALS, QueryOperator.NOT_EQUALS,
            QueryOperator.GREATER_THAN, QueryOperator.GREATER_THAN_OR_EQUAL,
            QueryOperator.LESS_THAN, QueryOperator.LESS_THAN_OR_EQUAL,
        }
        if self.operator in scalar_ops and isinstance(self.value, dict):
            raise ValueError(
                f"Operator {self.operator.value} does not accept object values"
            )

        if self.operator == QueryOperator.EQUALS:
            return {field_name: self.value}
        elif self.operator == QueryOperator.NOT_EQUALS:
            return {field_name: {"$ne": self.value}}
        elif self.operator == QueryOperator.GREATER_THAN:
            return {field_name: {"$gt": self.value}}
        elif self.operator == QueryOperator.GREATER_THAN_OR_EQUAL:
            return {field_name: {"$gte": self.value}}
        elif self.operator == QueryOperator.LESS_THAN:
            return {field_name: {"$lt": self.value}}
        elif self.operator == QueryOperator.LESS_THAN_OR_EQUAL:
            return {field_name: {"$lte": self.value}}
        elif self.operator == QueryOperator.IN:
            if not isinstance(self.value, list):
                raise ValueError("IN operator requires a list value")
            return {field_name: {"$in": self.value}}
        elif self.operator == QueryOperator.NOT_IN:
            if not isinstance(self.value, list):
                raise ValueError("NOT_IN operator requires a list value")
            return {field_name: {"$nin": self.value}}
        elif self.operator == QueryOperator.CONTAINS:
            literal = _safe_regex_literal(self.value)
            return {field_name: {"$regex": f".*{literal}.*", "$options": options}}
        elif self.operator == QueryOperator.STARTS_WITH:
            literal = _safe_regex_literal(self.value)
            return {field_name: {"$regex": f"^{literal}", "$options": options}}
        elif self.operator == QueryOperator.ENDS_WITH:
            literal = _safe_regex_literal(self.value)
            return {field_name: {"$regex": f"{literal}$", "$options": options}}
        elif self.operator == QueryOperator.EXISTS:
            return {field_name: {"$exists": bool(self.value)}}
        elif self.operator == QueryOperator.NOT_EXISTS:
            return {field_name: {"$exists": not bool(self.value)}}
        elif self.operator == QueryOperator.REGEX:
            # Raw, attacker-controlled regex is not permitted (ReDoS / injection
            # risk). Treat the value as a length-capped literal prefix match.
            literal = _safe_regex_literal(self.value)
            return {field_name: {"$regex": f"^{literal}", "$options": options}}
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")


@dataclass
class DateRangeFilter:
    """Date range filter for temporal queries"""
    field: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_start: bool = True
    include_end: bool = True
    
    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert to MongoDB query format"""
        query = {}
        
        if self.start_date:
            op = "$gte" if self.include_start else "$gt"
            query[op] = self.start_date
            
        if self.end_date:
            op = "$lte" if self.include_end else "$lt"
            query[op] = self.end_date
            
        return {self.field: query} if query else {}


@dataclass
class LocationFilter:
    """Location-based filter for geographic queries"""
    latitude: float
    longitude: float
    radius_km: float
    field: str = "location"
    
    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert to MongoDB geospatial query"""
        return {
            self.field: {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [self.longitude, self.latitude]
                    },
                    "$maxDistance": self.radius_km * 1000  # Convert to meters
                }
            }
        }


@dataclass
class QueryCondition:
    """Complex query condition with logical operators"""
    operator: LogicalOperator
    conditions: List[Union['QueryCondition', FieldFilter, DateRangeFilter, LocationFilter]]
    
    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert to MongoDB query format"""
        if self.operator == LogicalOperator.AND:
            sub_queries = []
            for condition in self.conditions:
                sub_query = condition.to_mongo_query()
                if sub_query:
                    sub_queries.append(sub_query)
            return {"$and": sub_queries} if len(sub_queries) > 1 else (sub_queries[0] if sub_queries else {})
            
        elif self.operator == LogicalOperator.OR:
            sub_queries = []
            for condition in self.conditions:
                sub_query = condition.to_mongo_query()
                if sub_query:
                    sub_queries.append(sub_query)
            return {"$or": sub_queries} if sub_queries else {}
            
        elif self.operator == LogicalOperator.NOT:
            if not self.conditions:
                return {}
            sub_query = self.conditions[0].to_mongo_query()
            return {"$not": sub_query} if sub_query else {}
            
        else:
            raise ValueError(f"Unsupported logical operator: {self.operator}")


@dataclass
class SortOption:
    """Sort option for query results"""
    field: str
    order: SortOrder = SortOrder.ASC
    null_handling: Literal["first", "last"] = "last"


@dataclass
class PaginationOptions:
    """Pagination options with cursor support"""
    page_size: int = 20
    cursor: Optional[str] = None  # Base64 encoded cursor
    page: Optional[int] = None  # Traditional page number (fallback)
    
    def validate(self):
        """Validate pagination options"""
        if self.page_size < 1:
            raise ValueError("Page size must be at least 1")
        if self.page_size > 1000:
            raise ValueError("Page size cannot exceed 1000")
        if self.cursor and self.page:
            raise ValueError("Cannot use both cursor and page pagination")


@dataclass
class QueryOptions:
    """Additional query options"""
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    include_count: bool = True
    timeout_ms: Optional[int] = None
    explain: bool = False  # Include query execution plan
    
    def get_projection(self) -> Optional[Dict[str, int]]:
        """Get MongoDB projection from field options"""
        if self.include_fields:
            return {field: 1 for field in self.include_fields}
        elif self.exclude_fields:
            return {field: 0 for field in self.exclude_fields}
        return None


@dataclass
class DeviceQuery:
    """Advanced device query model"""
    # Basic filters
    org_id: str
    conditions: Optional[QueryCondition] = None
    
    # Specific field filters (shortcuts)
    device_types: Optional[List[DeviceType]] = None
    statuses: Optional[List[DeviceStatus]] = None
    protocols: Optional[List[ConnectionProtocol]] = None
    tags: Optional[List[str]] = None
    group_ids: Optional[List[str]] = None
    
    # Date filters
    created_date_range: Optional[DateRangeFilter] = None
    updated_date_range: Optional[DateRangeFilter] = None
    last_seen_date_range: Optional[DateRangeFilter] = None
    
    # Location filter
    location_filter: Optional[LocationFilter] = None
    
    # Text search
    text_search: Optional[str] = None
    text_search_fields: List[str] = field(default_factory=lambda: ["name", "serial_number", "mac_address"])
    
    # Sorting
    sort_options: List[SortOption] = field(default_factory=lambda: [SortOption("created_at", SortOrder.DESC)])
    
    # Pagination
    pagination: PaginationOptions = field(default_factory=PaginationOptions)
    
    # Query options
    options: QueryOptions = field(default_factory=QueryOptions)
    
    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert to MongoDB query"""
        query = {"org_id": self.org_id}
        
        # Add conditions if present
        conditions = []
        
        if self.conditions:
            conditions.append(self.conditions.to_mongo_query())
        
        # Add shortcut filters
        if self.device_types:
            query["device_type"] = {"$in": [dt.value for dt in self.device_types]}
            
        if self.statuses:
            query["status"] = {"$in": [s.value for s in self.statuses]}
            
        if self.protocols:
            query["protocol"] = {"$in": [p.value for p in self.protocols]}
            
        if self.tags:
            query["tags"] = {"$in": self.tags}
            
        if self.group_ids:
            query["group_ids"] = {"$in": self.group_ids}
        
        # Add date range filters
        if self.created_date_range:
            date_query = self.created_date_range.to_mongo_query()
            if date_query:
                query.update(date_query)
                
        if self.updated_date_range:
            date_query = self.updated_date_range.to_mongo_query()
            if date_query:
                query.update(date_query)
                
        if self.last_seen_date_range:
            date_query = self.last_seen_date_range.to_mongo_query()
            if date_query:
                query.update(date_query)
        
        # Add location filter
        if self.location_filter:
            location_query = self.location_filter.to_mongo_query()
            if location_query:
                query.update(location_query)
        
        # Add text search. The search term is regex-escaped and length-capped
        # (ReDoS / regex-injection mitigation) and each target field name is
        # validated against the allowed-fields whitelist (NoSQL field injection
        # mitigation).
        if self.text_search:
            literal = _safe_regex_literal(self.text_search)
            search_conditions = []
            for search_field in self.text_search_fields:
                _validate_field_name(search_field)
                search_conditions.append({
                    search_field: {"$regex": literal, "$options": "i"}
                })
            if search_conditions:
                if "$or" in query:
                    # Merge with existing OR conditions
                    query["$and"] = [{"$or": query.pop("$or")}, {"$or": search_conditions}]
                else:
                    query["$or"] = search_conditions
        
        # Merge all conditions
        if conditions:
            if len(conditions) == 1:
                query.update(conditions[0])
            else:
                query["$and"] = conditions
        
        return query
    
    def get_sort_spec(self) -> List[tuple]:
        """Get MongoDB sort specification"""
        sort_spec = []
        for sort_option in self.sort_options:
            direction = 1 if sort_option.order == SortOrder.ASC else -1
            sort_spec.append((sort_option.field, direction))
        return sort_spec
    
    def validate(self):
        """Validate query parameters (fail-closed field-name validation)."""
        self.pagination.validate()

        # Validate text-search target field names against the whitelist.
        if self.text_search:
            if len(self.text_search) > MAX_REGEX_INPUT_LENGTH:
                raise ValueError(
                    f"text_search exceeds maximum length of "
                    f"{MAX_REGEX_INPUT_LENGTH}"
                )
            for search_field in self.text_search_fields:
                if search_field not in ALLOWED_QUERY_FIELDS:
                    raise ValueError(f"Invalid text search field: {search_field}")

        # Validate sort field names against the whitelist.
        for sort_option in self.sort_options:
            if sort_option.field not in ALLOWED_QUERY_FIELDS:
                raise ValueError(f"Invalid sort field: {sort_option.field}")


@dataclass
class QueryResult:
    """Query result with metadata"""
    items: List[Dict[str, Any]]
    total_count: Optional[int] = None
    next_cursor: Optional[str] = None
    has_more: bool = False
    execution_time_ms: Optional[float] = None
    query_plan: Optional[Dict[str, Any]] = None  # For explain mode
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            "items": self.items,
            "has_more": self.has_more
        }
        
        if self.total_count is not None:
            result["total_count"] = self.total_count
            
        if self.next_cursor:
            result["next_cursor"] = self.next_cursor
            
        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms
            
        if self.query_plan:
            result["query_plan"] = self.query_plan
            
        return result


@dataclass
class AggregationQuery:
    """Aggregation query for device statistics"""
    org_id: str
    group_by: List[str]
    metrics: List[str] = field(default_factory=lambda: ["count"])
    filters: Optional[DeviceQuery] = None
    having: Optional[Dict[str, Any]] = None  # Post-aggregation filters
    
    def to_mongo_pipeline(self) -> List[Dict[str, Any]]:
        """Convert to MongoDB aggregation pipeline"""
        pipeline = []
        
        # Match stage from filters
        if self.filters:
            match_query = self.filters.to_mongo_query()
            if match_query:
                pipeline.append({"$match": match_query})
        else:
            pipeline.append({"$match": {"org_id": self.org_id}})
        
        # Group stage
        group_spec = {"_id": {}}
        for field in self.group_by:
            group_spec["_id"][field] = f"${field}"
        
        # Add metrics
        for metric in self.metrics:
            if metric == "count":
                group_spec["count"] = {"$sum": 1}
            elif metric.startswith("avg_"):
                field = metric[4:]
                group_spec[metric] = {"$avg": f"${field}"}
            elif metric.startswith("sum_"):
                field = metric[4:]
                group_spec[metric] = {"$sum": f"${field}"}
            elif metric.startswith("min_"):
                field = metric[4:]
                group_spec[metric] = {"$min": f"${field}"}
            elif metric.startswith("max_"):
                field = metric[4:]
                group_spec[metric] = {"$max": f"${field}"}
        
        pipeline.append({"$group": group_spec})
        
        # Having stage (post-aggregation filter)
        if self.having:
            pipeline.append({"$match": self.having})
        
        # Sort by count descending by default
        pipeline.append({"$sort": {"count": -1}})

        return pipeline


# Alias for backwards compatibility
QueryPagination = PaginationOptions