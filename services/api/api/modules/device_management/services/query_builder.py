# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Query Builder Service for Device Management
Purpose: Build and optimize complex queries for device searches
Date: January 27, 2025
Part of TESA IoT Platform Device Management Module
"""

import logging
import base64
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..models.query_models import (
    DeviceQuery, QueryCondition, FieldFilter, DateRangeFilter,
    LocationFilter, QueryOperator, LogicalOperator, SortOption,
    PaginationOptions, QueryOptions, AggregationQuery,
    DeviceStatus, DeviceType, ConnectionProtocol, SortOrder
)
from ...dashboard.utils.metrics_decorator import track_dashboard_method
from ....core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class DeviceQueryBuilder:
    """Service for building and optimizing device queries"""
    
    def __init__(self):
        self.max_query_complexity = 10  # Maximum nested conditions
        self.default_page_size = 20
        self.max_page_size = 1000
        logger.info("DeviceQueryBuilder initialized")
    
    @track_dashboard_method(
        method_name="build_query_from_params",
        module="device_management",
        operation="query_build"
    )
    def build_query_from_params(self, params: Dict[str, Any], org_id: str) -> DeviceQuery:
        """
        Build a DeviceQuery from request parameters
        
        Args:
            params: Request parameters
            org_id: Organization ID
            
        Returns:
            DeviceQuery object
        """
        try:
            # Initialize query with org_id
            query = DeviceQuery(org_id=org_id)
            
            # Parse basic filters
            if "device_types" in params:
                device_types = params["device_types"]
                if isinstance(device_types, str):
                    device_types = [device_types]
                query.device_types = [DeviceType(dt) for dt in device_types]
            
            if "statuses" in params:
                statuses = params["statuses"]
                if isinstance(statuses, str):
                    statuses = [statuses]
                query.statuses = [DeviceStatus(s) for s in statuses]
            
            if "protocols" in params:
                protocols = params["protocols"]
                if isinstance(protocols, str):
                    protocols = [protocols]
                query.protocols = [ConnectionProtocol(p) for p in protocols]
            
            if "tags" in params:
                tags = params["tags"]
                if isinstance(tags, str):
                    tags = [tags]
                query.tags = tags
            
            if "group_ids" in params:
                group_ids = params["group_ids"]
                if isinstance(group_ids, str):
                    group_ids = [group_ids]
                query.group_ids = group_ids
            
            # Parse date range filters
            query.created_date_range = self._parse_date_range(
                params.get("created_after"),
                params.get("created_before"),
                "created_at"
            )
            
            query.updated_date_range = self._parse_date_range(
                params.get("updated_after"),
                params.get("updated_before"),
                "updated_at"
            )
            
            query.last_seen_date_range = self._parse_date_range(
                params.get("last_seen_after"),
                params.get("last_seen_before"),
                "last_seen"
            )
            
            # Parse location filter
            if all(key in params for key in ["latitude", "longitude", "radius_km"]):
                query.location_filter = LocationFilter(
                    latitude=float(params["latitude"]),
                    longitude=float(params["longitude"]),
                    radius_km=float(params["radius_km"])
                )
            
            # Parse text search
            if "search" in params:
                query.text_search = params["search"]
                if "search_fields" in params:
                    query.text_search_fields = params["search_fields"]
            
            # Parse complex conditions
            if "conditions" in params:
                query.conditions = self._parse_conditions(params["conditions"])
            
            # Parse sorting
            if "sort_by" in params:
                sort_fields = params["sort_by"]
                if isinstance(sort_fields, str):
                    sort_fields = [sort_fields]
                
                sort_orders = params.get("sort_order", ["desc"])
                if isinstance(sort_orders, str):
                    sort_orders = [sort_orders]
                
                query.sort_options = []
                for i, field in enumerate(sort_fields):
                    order = SortOrder(sort_orders[i] if i < len(sort_orders) else "desc")
                    query.sort_options.append(SortOption(field, order))
            
            # Parse pagination
            query.pagination = self._parse_pagination(params)
            
            # Parse query options
            query.options = self._parse_query_options(params)
            
            # Validate the query
            query.validate()
            
            return query
            
        except Exception as e:
            logger.error(f"Error building query from params: {str(e)}")
            raise ValidationError(f"Invalid query parameters: {str(e)}")
    
    def _parse_date_range(
        self,
        start: Optional[str],
        end: Optional[str],
        field: str
    ) -> Optional[DateRangeFilter]:
        """Parse date range from string parameters"""
        if not start and not end:
            return None
        
        date_range = DateRangeFilter(field=field)
        
        if start:
            try:
                date_range.start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(f"Invalid date format for {field} start: {start}")
        
        if end:
            try:
                date_range.end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(f"Invalid date format for {field} end: {end}")
        
        return date_range
    
    def _parse_conditions(self, conditions_data: Any) -> QueryCondition:
        """Parse complex query conditions from JSON"""
        if isinstance(conditions_data, str):
            try:
                conditions_data = json.loads(conditions_data)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON in conditions parameter")
        
        return self._build_condition(conditions_data)
    
    def _build_condition(self, data: Dict[str, Any], depth: int = 0) -> QueryCondition:
        """Recursively build query conditions"""
        if depth > self.max_query_complexity:
            raise ValidationError("Query too complex: maximum nesting depth exceeded")
        
        if "operator" not in data:
            raise ValidationError("Missing operator in condition")
        
        operator = LogicalOperator(data["operator"])
        conditions = []
        
        for cond_data in data.get("conditions", []):
            if "operator" in cond_data and cond_data["operator"] in ["and", "or", "not"]:
                # Nested logical condition
                conditions.append(self._build_condition(cond_data, depth + 1))
            elif "field" in cond_data:
                # Field filter
                conditions.append(self._build_field_filter(cond_data))
            else:
                raise ValidationError(f"Invalid condition structure: {cond_data}")
        
        return QueryCondition(operator=operator, conditions=conditions)
    
    def _build_field_filter(self, data: Dict[str, Any]) -> FieldFilter:
        """Build field filter from data"""
        if "field" not in data or "operator" not in data:
            raise ValidationError("Field filter must have 'field' and 'operator'")
        
        operator = QueryOperator(data["operator"])
        
        # Some operators don't require a value
        if operator in [QueryOperator.EXISTS, QueryOperator.NOT_EXISTS]:
            value = data.get("value", True)
        else:
            if "value" not in data:
                raise ValidationError(f"Field filter with operator {operator} requires a value")
            value = data["value"]
        
        return FieldFilter(
            field=data["field"],
            operator=operator,
            value=value,
            case_sensitive=data.get("case_sensitive", True)
        )
    
    def _parse_pagination(self, params: Dict[str, Any]) -> PaginationOptions:
        """Parse pagination options from parameters"""
        page_size = int(params.get("page_size", self.default_page_size))
        
        if "cursor" in params:
            return PaginationOptions(page_size=page_size, cursor=params["cursor"])
        elif "page" in params:
            return PaginationOptions(page_size=page_size, page=int(params["page"]))
        else:
            return PaginationOptions(page_size=page_size)
    
    def _parse_query_options(self, params: Dict[str, Any]) -> QueryOptions:
        """Parse query options from parameters"""
        options = QueryOptions()
        
        if "include_fields" in params:
            fields = params["include_fields"]
            options.include_fields = fields if isinstance(fields, list) else [fields]
        
        if "exclude_fields" in params:
            fields = params["exclude_fields"]
            options.exclude_fields = fields if isinstance(fields, list) else [fields]
        
        options.include_count = params.get("include_count", "true").lower() == "true"
        options.explain = params.get("explain", "false").lower() == "true"
        
        if "timeout_ms" in params:
            options.timeout_ms = int(params["timeout_ms"])
        
        return options
    
    @track_dashboard_method(
        method_name="encode_cursor",
        module="device_management",
        operation="query_cursor"
    )
    def encode_cursor(self, last_item: Dict[str, Any], sort_fields: List[str]) -> str:
        """
        Encode pagination cursor from last item
        
        Args:
            last_item: Last item from current page
            sort_fields: Fields used for sorting
            
        Returns:
            Base64 encoded cursor
        """
        cursor_data = {
            "sort_values": {},
            "id": last_item.get("device_id")
        }
        
        for field in sort_fields:
            value = last_item.get(field)
            if isinstance(value, datetime):
                value = value.isoformat()
            cursor_data["sort_values"][field] = value
        
        cursor_json = json.dumps(cursor_data)
        return base64.b64encode(cursor_json.encode()).decode()
    
    @track_dashboard_method(
        method_name="decode_cursor",
        module="device_management",
        operation="query_cursor"
    )
    def decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """
        Decode pagination cursor
        
        Args:
            cursor: Base64 encoded cursor
            
        Returns:
            Cursor data dictionary
        """
        try:
            cursor_json = base64.b64decode(cursor).decode()
            return json.loads(cursor_json)
        except Exception as e:
            logger.error(f"Error decoding cursor: {str(e)}")
            raise ValidationError("Invalid cursor format")
    
    def apply_cursor_to_query(
        self,
        query: Dict[str, Any],
        cursor_data: Dict[str, Any],
        sort_options: List[SortOption]
    ) -> Dict[str, Any]:
        """
        Apply cursor-based pagination to MongoDB query
        
        Args:
            query: Base MongoDB query
            cursor_data: Decoded cursor data
            sort_options: Sort options from query
            
        Returns:
            Modified query with cursor conditions
        """
        if not cursor_data or "sort_values" not in cursor_data:
            return query
        
        # Build cursor condition based on sort fields
        cursor_conditions = []
        sort_values = cursor_data["sort_values"]
        
        for i, sort_option in enumerate(sort_options):
            field = sort_option.field
            if field not in sort_values:
                continue
            
            value = sort_values[field]
            # Convert ISO string back to datetime if needed
            if field in ["created_at", "updated_at", "last_seen"] and isinstance(value, str):
                value = datetime.fromisoformat(value)
            
            if sort_option.order == SortOrder.DESC:
                # For descending sort, we want items less than the cursor value
                condition = {field: {"$lt": value}}
            else:
                # For ascending sort, we want items greater than the cursor value
                condition = {field: {"$gt": value}}
            
            # Handle tie-breaking with device_id
            if i == len(sort_options) - 1 and "id" in cursor_data:
                tie_breaker = {"device_id": {"$gt": cursor_data["id"]}}
                condition = {"$or": [condition, {"$and": [{field: value}, tie_breaker]}]}
            
            cursor_conditions.append(condition)
        
        if cursor_conditions:
            if "$and" in query:
                query["$and"].extend(cursor_conditions)
            else:
                query["$and"] = [query] + cursor_conditions if query else cursor_conditions
        
        return query
    
    @track_dashboard_method(
        method_name="build_aggregation_query",
        module="device_management",
        operation="query_aggregation"
    )
    def build_aggregation_query(
        self,
        params: Dict[str, Any],
        org_id: str
    ) -> AggregationQuery:
        """
        Build aggregation query from parameters
        
        Args:
            params: Request parameters
            org_id: Organization ID
            
        Returns:
            AggregationQuery object
        """
        # Parse group by fields
        group_by = params.get("group_by", [])
        if isinstance(group_by, str):
            group_by = [group_by]
        
        # Parse metrics
        metrics = params.get("metrics", ["count"])
        if isinstance(metrics, str):
            metrics = [metrics]
        
        # Build base query for filters
        base_query = None
        if any(key in params for key in ["device_types", "statuses", "protocols", "tags"]):
            base_query = self.build_query_from_params(params, org_id)
        
        # Parse having conditions
        having = None
        if "having" in params:
            having = json.loads(params["having"]) if isinstance(params["having"], str) else params["having"]
        
        return AggregationQuery(
            org_id=org_id,
            group_by=group_by,
            metrics=metrics,
            filters=base_query,
            having=having
        )
    
    def optimize_query(self, query: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Optimize MongoDB query and suggest indexes
        
        Args:
            query: MongoDB query
            
        Returns:
            Tuple of (optimized_query, suggested_indexes)
        """
        optimized = query.copy()
        suggested_indexes = []
        
        # Analyze query structure
        if "$or" in query:
            # Suggest indexes for each OR branch
            for branch in query["$or"]:
                if isinstance(branch, dict):
                    for field in branch.keys():
                        if field not in ["$and", "$or", "$not"]:
                            suggested_indexes.append(field)
        
        # Check for commonly queried fields
        common_fields = ["status", "device_type", "protocol", "org_id", "created_at"]
        for field in common_fields:
            if field in query:
                suggested_indexes.append(field)
        
        # Compound index suggestions
        if "org_id" in query and "status" in query:
            suggested_indexes.append("org_id_status_compound")
        
        if "org_id" in query and "device_type" in query:
            suggested_indexes.append("org_id_device_type_compound")
        
        # Remove duplicates
        suggested_indexes = list(set(suggested_indexes))
        
        return optimized, suggested_indexes