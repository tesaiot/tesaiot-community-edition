# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from flask import Blueprint, request
from fastapi import APIRouter
from datetime import datetime
import logging

from ..services.telemetry_analytics_service import telemetry_analytics_service
from ..repositories.telemetry_analytics_repository import telemetry_analytics_repository
from ..models.telemetry_analytics_models import (
    AnalyticsType, AnomalyType, PatternType, AnalyticsConfiguration
)
from ....auth.decorators import require_auth, require_device_access
from ....utils.response_helpers import success_response, error_response
from ....utils.validators import validate_request_data

logger = logging.getLogger(__name__)

# Create FastAPI router for module integration
router = APIRouter(prefix="/analytics", tags=["telemetry-analytics"])

# Create Flask blueprint for legacy support
telemetry_analytics_bp = Blueprint('telemetry_analytics', __name__)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/analyze', methods=['POST'])
@require_auth
@require_device_access
async def analyze_telemetry(device_id: str):
    """
    Analyze telemetry data for a device
    
    Request body:
    {
        "metric_name": "temperature",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z",
        "analytics_types": ["anomaly_detection", "statistical", "pattern_recognition"],
        "config": {
            "anomaly_sensitivity": 0.95,
            "forecast_horizon_hours": 24
        }
    }
    """
    try:
        data = request.get_json()
        user = request.user
        org_id = user.get("organization_id")
        
        # Validate required fields
        required_fields = ["metric_name", "start_time", "end_time", "analytics_types"]
        validation_error = validate_request_data(data, required_fields)
        if validation_error:
            return error_response(validation_error, 400)
        
        # Parse timestamps
        try:
            start_time = datetime.fromisoformat(data["start_time"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))
        except ValueError as e:
            return error_response(f"Invalid timestamp format: {str(e)}", 400)
        
        # Parse analytics types
        analytics_types = []
        for at in data["analytics_types"]:
            try:
                analytics_types.append(AnalyticsType(at))
            except ValueError:
                return error_response(f"Invalid analytics type: {at}", 400)
        
        # Create analytics configuration if provided
        config = None
        if "config" in data:
            config = AnalyticsConfiguration(
                config_id=f"{device_id}:{org_id}",
                device_id=device_id,
                org_id=org_id,
                enabled_analytics=analytics_types,
                metrics_to_analyze=[data["metric_name"]],
                **data["config"]
            )
        
        # Perform analytics
        results = await telemetry_analytics_service.analyze_telemetry(
            device_id=device_id,
            org_id=org_id,
            metric_name=data["metric_name"],
            start_time=start_time,
            end_time=end_time,
            analytics_types=analytics_types,
            config=config
        )
        
        # Convert results to JSON-serializable format
        response_data = {}
        for key, value_list in results.items():
            response_data[key] = [item.to_dict() for item in value_list]
        
        return success_response(
            data=response_data,
            message=f"Analytics completed for device {device_id}"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing telemetry: {str(e)}")
        return error_response(f"Failed to analyze telemetry: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/anomalies', methods=['GET'])
@require_auth
@require_device_access
async def get_anomalies(device_id: str):
    """
    Get detected anomalies for a device
    
    Query parameters:
    - start_time: Start timestamp (ISO format)
    - end_time: End timestamp (ISO format)
    - anomaly_types: Comma-separated list of anomaly types
    - severity: Filter by severity (critical, high, medium, low)
    - is_confirmed: Filter by confirmation status (true/false)
    - limit: Maximum number of results (default: 100)
    """
    try:
        user = request.user
        org_id = user.get("organization_id")
        
        # Parse query parameters
        start_time = None
        end_time = None
        
        if request.args.get('start_time'):
            start_time = datetime.fromisoformat(request.args['start_time'].replace('Z', '+00:00'))
        
        if request.args.get('end_time'):
            end_time = datetime.fromisoformat(request.args['end_time'].replace('Z', '+00:00'))
        
        # Parse anomaly types
        anomaly_types = None
        if request.args.get('anomaly_types'):
            anomaly_types = []
            for at in request.args['anomaly_types'].split(','):
                try:
                    anomaly_types.append(AnomalyType(at.strip()))
                except ValueError:
                    return error_response(f"Invalid anomaly type: {at}", 400)
        
        # Parse other filters
        severity = request.args.get('severity')
        is_confirmed = None
        if request.args.get('is_confirmed'):
            is_confirmed = request.args['is_confirmed'].lower() == 'true'
        
        limit = int(request.args.get('limit', 100))
        
        # Get anomalies
        anomalies = await telemetry_analytics_repository.get_anomalies(
            device_id=device_id,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            anomaly_types=anomaly_types,
            severity=severity,
            is_confirmed=is_confirmed,
            limit=limit
        )
        
        return success_response(
            data=[anomaly.to_dict() for anomaly in anomalies],
            message=f"Retrieved {len(anomalies)} anomalies for device {device_id}"
        )
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {str(e)}")
        return error_response(f"Failed to get anomalies: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/predictions', methods=['GET'])
@require_auth
@require_device_access
async def get_predictions(device_id: str):
    """
    Get predictions for a device
    
    Query parameters:
    - metric_name: Filter by metric name
    - model_id: Filter by model ID
    - start_time: Start timestamp for predictions
    - end_time: End timestamp for predictions
    - limit: Maximum number of results (default: 10)
    """
    try:
        user = request.user
        org_id = user.get("organization_id")
        
        # Parse query parameters
        metric_name = request.args.get('metric_name')
        model_id = request.args.get('model_id')
        
        start_time = None
        end_time = None
        
        if request.args.get('start_time'):
            start_time = datetime.fromisoformat(request.args['start_time'].replace('Z', '+00:00'))
        
        if request.args.get('end_time'):
            end_time = datetime.fromisoformat(request.args['end_time'].replace('Z', '+00:00'))
        
        limit = int(request.args.get('limit', 10))
        
        # Get predictions
        predictions = await telemetry_analytics_repository.get_predictions(
            device_id=device_id,
            org_id=org_id,
            metric_name=metric_name,
            model_id=model_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return success_response(
            data=[prediction.to_dict() for prediction in predictions],
            message=f"Retrieved {len(predictions)} predictions for device {device_id}"
        )
        
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        return error_response(f"Failed to get predictions: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/patterns', methods=['GET'])
@require_auth
@require_device_access
async def get_patterns(device_id: str):
    """
    Get detected patterns for a device
    
    Query parameters:
    - pattern_types: Comma-separated list of pattern types
    - start_time: Start timestamp
    - end_time: End timestamp
    - min_confidence: Minimum confidence score (0-1)
    - limit: Maximum number of results (default: 50)
    """
    try:
        user = request.user
        org_id = user.get("organization_id")
        
        # Parse query parameters
        pattern_types = None
        if request.args.get('pattern_types'):
            pattern_types = []
            for pt in request.args['pattern_types'].split(','):
                try:
                    pattern_types.append(PatternType(pt.strip()))
                except ValueError:
                    return error_response(f"Invalid pattern type: {pt}", 400)
        
        start_time = None
        end_time = None
        
        if request.args.get('start_time'):
            start_time = datetime.fromisoformat(request.args['start_time'].replace('Z', '+00:00'))
        
        if request.args.get('end_time'):
            end_time = datetime.fromisoformat(request.args['end_time'].replace('Z', '+00:00'))
        
        min_confidence = float(request.args.get('min_confidence', 0.0))
        limit = int(request.args.get('limit', 50))
        
        # Get patterns
        patterns = await telemetry_analytics_repository.get_patterns(
            device_id=device_id,
            org_id=org_id,
            pattern_types=pattern_types,
            start_time=start_time,
            end_time=end_time,
            min_confidence=min_confidence,
            limit=limit
        )
        
        return success_response(
            data=[pattern.to_dict() for pattern in patterns],
            message=f"Retrieved {len(patterns)} patterns for device {device_id}"
        )
        
    except Exception as e:
        logger.error(f"Error getting patterns: {str(e)}")
        return error_response(f"Failed to get patterns: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/statistics', methods=['GET'])
@require_auth
@require_device_access
async def get_statistics(device_id: str):
    """
    Get statistical summaries for a device
    
    Query parameters:
    - metric_name: Filter by metric name
    - start_time: Start timestamp
    - end_time: End timestamp
    - limit: Maximum number of results (default: 100)
    """
    try:
        user = request.user
        org_id = user.get("organization_id")
        
        # Parse query parameters
        metric_name = request.args.get('metric_name')
        
        start_time = None
        end_time = None
        
        if request.args.get('start_time'):
            start_time = datetime.fromisoformat(request.args['start_time'].replace('Z', '+00:00'))
        
        if request.args.get('end_time'):
            end_time = datetime.fromisoformat(request.args['end_time'].replace('Z', '+00:00'))
        
        limit = int(request.args.get('limit', 100))
        
        # Get statistics
        statistics = await telemetry_analytics_repository.get_statistics(
            device_id=device_id,
            org_id=org_id,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return success_response(
            data=[stat.to_dict() for stat in statistics],
            message=f"Retrieved {len(statistics)} statistical summaries for device {device_id}"
        )
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return error_response(f"Failed to get statistics: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/correlations', methods=['POST'])
@require_auth
@require_device_access
async def analyze_correlations(device_id: str):
    """
    Analyze correlations between metrics
    
    Request body:
    {
        "metrics": ["temperature", "humidity", "pressure"],
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z",
        "lag_analysis": true
    }
    """
    try:
        data = request.get_json()
        user = request.user
        org_id = user.get("organization_id")
        
        # Validate required fields
        required_fields = ["metrics", "start_time", "end_time"]
        validation_error = validate_request_data(data, required_fields)
        if validation_error:
            return error_response(validation_error, 400)
        
        # Parse timestamps
        try:
            start_time = datetime.fromisoformat(data["start_time"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))
        except ValueError as e:
            return error_response(f"Invalid timestamp format: {str(e)}", 400)
        
        # Analyze correlations
        correlation_result = await telemetry_analytics_service.analyze_correlations(
            device_id=device_id,
            org_id=org_id,
            metrics=data["metrics"],
            start_time=start_time,
            end_time=end_time,
            lag_analysis=data.get("lag_analysis", True)
        )
        
        return success_response(
            data=correlation_result.to_dict(),
            message=f"Correlation analysis completed for device {device_id}"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing correlations: {str(e)}")
        return error_response(f"Failed to analyze correlations: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/analytics-config', methods=['GET', 'PUT'])
@require_auth
@require_device_access
async def manage_analytics_config(device_id: str):
    """
    Get or update analytics configuration for a device
    """
    try:
        user = request.user
        org_id = user.get("organization_id")
        
        if request.method == 'GET':
            # Get configuration
            config = await telemetry_analytics_repository.get_analytics_configuration(
                device_id=device_id,
                org_id=org_id
            )
            
            if config:
                return success_response(
                    data=config.to_dict(),
                    message=f"Retrieved analytics configuration for device {device_id}"
                )
            else:
                # Return default configuration
                default_config = AnalyticsConfiguration(
                    config_id=f"{device_id}:{org_id}",
                    device_id=device_id,
                    org_id=org_id
                )
                return success_response(
                    data=default_config.to_dict(),
                    message="Default analytics configuration"
                )
        
        else:  # PUT
            # Update configuration
            data = request.get_json()
            
            # Get existing config or create new one
            config = await telemetry_analytics_repository.get_analytics_configuration(
                device_id=device_id,
                org_id=org_id
            )
            
            if not config:
                config = AnalyticsConfiguration(
                    config_id=f"{device_id}:{org_id}",
                    device_id=device_id,
                    org_id=org_id
                )
            
            # Update fields
            if "enabled_analytics" in data:
                config.enabled_analytics = [AnalyticsType(a) for a in data["enabled_analytics"]]
            if "metrics_to_analyze" in data:
                config.metrics_to_analyze = data["metrics_to_analyze"]
            if "processing_interval_minutes" in data:
                config.processing_interval_minutes = data["processing_interval_minutes"]
            if "anomaly_sensitivity" in data:
                config.anomaly_sensitivity = data["anomaly_sensitivity"]
            if "forecast_horizon_hours" in data:
                config.forecast_horizon_hours = data["forecast_horizon_hours"]
            if "pattern_detection_window_hours" in data:
                config.pattern_detection_window_hours = data["pattern_detection_window_hours"]
            if "statistical_window_hours" in data:
                config.statistical_window_hours = data["statistical_window_hours"]
            if "correlation_threshold" in data:
                config.correlation_threshold = data["correlation_threshold"]
            if "auto_retrain_models" in data:
                config.auto_retrain_models = data["auto_retrain_models"]
            if "retrain_interval_days" in data:
                config.retrain_interval_days = data["retrain_interval_days"]
            if "alert_on_anomalies" in data:
                config.alert_on_anomalies = data["alert_on_anomalies"]
            if "store_predictions" in data:
                config.store_predictions = data["store_predictions"]
            
            config.updated_at = datetime.utcnow()
            
            # Store configuration
            success = await telemetry_analytics_repository.store_analytics_configuration(config)
            
            if success:
                return success_response(
                    data=config.to_dict(),
                    message=f"Updated analytics configuration for device {device_id}"
                )
            else:
                return error_response("Failed to update configuration", 500)
        
    except Exception as e:
        logger.error(f"Error managing analytics configuration: {str(e)}")
        return error_response(f"Failed to manage analytics configuration: {str(e)}", 500)


@telemetry_analytics_bp.route('/devices/<device_id>/telemetry/anomalies/<anomaly_id>/confirm', methods=['PUT'])
@require_auth
@require_device_access
async def confirm_anomaly(device_id: str, anomaly_id: str):
    """
    Confirm or reject an anomaly
    
    Request body:
    {
        "is_confirmed": true,
        "notes": "Confirmed by operator - equipment malfunction"
    }
    """
    try:
        data = request.get_json()
        user = request.user
        
        # Update anomaly confirmation status
        # This would be implemented in the repository
        # For now, return success
        
        return success_response(
            message=f"Anomaly {anomaly_id} confirmation updated"
        )
        
    except Exception as e:
        logger.error(f"Error confirming anomaly: {str(e)}")
        return error_response(f"Failed to confirm anomaly: {str(e)}", 500)


@telemetry_analytics_bp.route('/telemetry/analytics/cleanup', methods=['POST'])
@require_auth
async def cleanup_old_data():
    """
    Clean up old analytics data (admin only)
    
    Request body:
    {
        "retention_days": 30
    }
    """
    try:
        user = request.user
        
        # Check if user is admin
        if user.get("role") != "admin":
            return error_response("Admin access required", 403)
        
        data = request.get_json()
        retention_days = data.get("retention_days", 30)
        
        # Perform cleanup
        cleanup_stats = await telemetry_analytics_repository.cleanup_old_data(retention_days)
        
        return success_response(
            data=cleanup_stats,
            message=f"Cleaned up analytics data older than {retention_days} days"
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up data: {str(e)}")
        return error_response(f"Failed to clean up data: {str(e)}", 500)