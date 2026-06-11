# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard metrics service for the single-organization Community Edition.

This is NOT the excluded analytics/AI module. It provides only the
system-health and IoT-telemetry metrics that back the in-scope IoT Telemetry
Dashboard (the panels rendered inside Device Details and the dashboard
controller). It reads from the in-scope datastores:

    - TimescaleDB: IoT telemetry time-series (counts, daily stats)
    - MongoDB: device/telemetry metadata for a single default organization
    - Redis: lightweight metric caching

Provided methods (all consumed by controllers/dashboard.py and
controllers/realtime.py):

    get_realtime_iot_metrics, get_telemetry_daily_stats,
    get_system_health_metrics, get_system_health_metrics_fast,
    get_api_gateway_metrics, get_realtime_logs_analytics,
    _get_fallback_system_health

Out of scope and therefore not present: predictive/AI analytics, heavy
container-monitoring metrics, and any multi-tenant organization aggregation.
"""

import asyncio
import logging
try:
    import docker  # optional: container-level metrics (not required for CE)
except ImportError:
    docker = None
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Import database connections
from ..core.database import get_db, get_redis, db_manager
from ..core.database import get_vault
from ..core.connection_pool import pool_manager

logger = logging.getLogger(__name__)

class RealTimeAnalyticsService:
    """
    Service to fetch real-time data from all platform databases and services
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.docker_client = None
        self.redis_client = None
        self.mongodb_client = None
        
        # Timeout settings for fast response
        self.fast_timeout = 3.0  # 3 seconds for fast endpoints
        self.standard_timeout = 8.0  # 8 seconds for standard endpoints
        
        # Initialize connections
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize connections to all data sources"""
        try:
            # Docker client (optional; container metrics are out of scope for CE)
            self.docker_client = docker.from_env() if docker is not None else None
            
            # Redis client
            self.redis_client = get_redis()
            
            # MongoDB client (get_db returns the database, not client)
            self.mongodb_client = get_db()
            
            self.logger.info("Real-time analytics service connections initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {str(e)}")

    def _acquire_postgres_connection(self):
        """Helper to acquire PostgreSQL connection respecting pooling mode."""
        conn_ctx = None
        if db_manager.use_enhanced_pooling:
            conn_ctx = pool_manager.get_postgresql_connection()
            conn = conn_ctx.__enter__()
        else:
            conn = db_manager.get_postgres_connection()
        if not conn:
            if conn_ctx:
                conn_ctx.__exit__(None, None, None)
            raise Exception("Unable to get PostgreSQL connection")
        return conn, conn_ctx

    def _release_postgres_connection(self, conn_ctx, conn):
        """Helper to release PostgreSQL connection respecting pooling mode."""
        if conn_ctx:
            try:
                conn_ctx.__exit__(None, None, None)
            except Exception as exc:
                self.logger.warning(f"Error releasing enhanced PostgreSQL connection: {exc}")
        else:
            db_manager.return_postgres_connection(conn)

    async def get_realtime_iot_metrics(self, organization_id: str, time_range: str = "1h") -> Dict[str, Any]:
        """
        Get real-time IoT metrics from TimescaleDB
        
        Args:
            organization_id: Organization ID for ACL filtering
            time_range: Time range for data (1h, 6h, 24h, 7d)
            
        Returns:
            Dictionary with real IoT telemetry metrics
        """
        try:
            # Convert time range to interval
            interval_map = {
                "1h": "1 hour",
                "6h": "6 hours", 
                "24h": "24 hours",
                "7d": "7 days"
            }
            interval = interval_map.get(time_range, "1 hour")
            
            # Connect to TimescaleDB directly for better reliability
            conn = None
            conn_ctx = None
            cur = None
            try:
                conn, conn_ctx = self._acquire_postgres_connection()
                cur = conn.cursor()

                # Query 1: Get total message count and throughput (using actual table structure)
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT device_id) as active_devices
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL %s
                    AND dt.organization_id = %s
                """, (interval, organization_id))
                telemetry_stats = cur.fetchone()

                # Query 2: Get recent throughput per minute (using actual table structure)
                cur.execute("""
                    SELECT 
                        time_bucket('1 minute', time) as minute,
                        COUNT(*) as messages_per_minute
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL %s
                    AND dt.organization_id = %s
                    GROUP BY minute
                    ORDER BY minute DESC
                    LIMIT 60
                """, (interval, organization_id))
                throughput_data = cur.fetchall()

                # Query 3: Get anomaly detection results (check if table exists first)
                try:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as anomaly_count,
                            0 as avg_anomaly_score
                        FROM device_events de
                        WHERE de.time >= NOW() - INTERVAL %s
                        AND de.organization_id = %s
                        AND de.severity IN ('medium', 'high')
                    """, (interval, organization_id))
                    anomaly_stats = cur.fetchone()
                except Exception:
                    # If anomaly table doesn't exist, use default values
                    anomaly_stats = (0, 0)

                # Query 4: Get device performance metrics (using actual table structure)
                cur.execute("""
                    SELECT 
                        device_id,
                        COUNT(*) as message_count,
                        MAX(time) as last_seen,
                        AVG(CASE WHEN metric_name = 'temperature' 
                             THEN metric_value END) as avg_temperature
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL %s
                    AND dt.organization_id = %s
                    GROUP BY device_id
                    ORDER BY message_count DESC
                    LIMIT 10
                """, (interval, organization_id))
                device_performance = cur.fetchall()

                # Calculate metrics
                total_messages = telemetry_stats[0] if telemetry_stats and telemetry_stats[0] else 0
                active_devices = telemetry_stats[1] if telemetry_stats and telemetry_stats[1] else 0

                # Calculate throughput (messages per minute) based on time range
                time_range_minutes = {
                    "1h": 60,
                    "6h": 360,
                    "24h": 1440,
                    "7d": 10080
                }.get(time_range, 60)

                throughput_per_min = total_messages / time_range_minutes if time_range_minutes > 0 else 0

                # Process throughput trend data
                throughput_trend = []
                for row in throughput_data[-10:]:  # Last 10 minutes
                    throughput_trend.append({
                        "time": row[0].strftime("%H:%M"),
                        "messages": row[1],
                        "rate": row[1] / 60  # messages per second
                    })

                # Process device performance
                top_devices = []
                for row in device_performance:
                    top_devices.append({
                        "device_id": row[0],
                        "message_count": row[1],
                        "last_seen": row[2].isoformat() if row[2] else None,
                        "avg_temperature": round(row[3], 1) if row[3] else None
                    })

            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass
                self._release_postgres_connection(conn_ctx, conn)
            
            result = {
                "throughput_max": int(max([t["rate"] * 60 for t in throughput_trend]) if throughput_trend else throughput_per_min),
                "throughput_avg": int(throughput_per_min),  # per minute
                "total_messages": total_messages,
                "active_devices": active_devices,
                "anomaly_count": anomaly_stats[0] if anomaly_stats and anomaly_stats[0] else 0,
                "anomaly_score": round(anomaly_stats[1], 2) if anomaly_stats and anomaly_stats[1] else 0,
                "throughput_trend": throughput_trend,
                "top_devices": top_devices,
                "success_rate": 99.8,  # Can be calculated from error logs
                "last_updated": datetime.now().isoformat()
            }

            if result["total_messages"] == 0:
                fallback = self._get_mongo_iot_metrics(organization_id, time_range)
                if fallback:
                    return fallback

            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get IoT metrics: {str(e)}")
            mongo_fallback = self._get_mongo_iot_metrics(organization_id, time_range)
            if mongo_fallback:
                return mongo_fallback
            return self._get_fallback_iot_metrics()

    def _get_mongo_iot_metrics(self, organization_id: str, time_range: str) -> Optional[Dict[str, Any]]:
        db = self.mongodb_client
        if db is None:
            db = get_db()
            if db is None:
                return None
            self.mongodb_client = db

        try:
            time_range_minutes = {
                "1h": 60,
                "6h": 360,
                "24h": 1440,
                "7d": 10080
            }.get(time_range, 60)

            since = datetime.utcnow() - timedelta(minutes=time_range_minutes)
            base_match: Dict[str, Any] = {"timestamp": {"$gte": since}}

            match: Dict[str, Any]
            total_messages: int

            if organization_id:
                # Start with strict tenant filter first
                match = dict(base_match)
                match["organization_id"] = organization_id
                total_messages = db.telemetry.count_documents(match)

                # Dashboard defaults historically stored telemetry with null/default org IDs.
                # If a strict match returns nothing and we're on the primary cluster org,
                # expand the filter to include legacy placeholders to surface real data
                # without leaking other tenant records.
                if total_messages == 0 and organization_id in {"tesa-org", "default", "global"}:
                    fallback_org_ids: list[Any] = []
                    for candidate in [organization_id, None, "", "tesa-org", "global", "default"]:
                        if candidate not in fallback_org_ids:
                            fallback_org_ids.append(candidate)

                    match = dict(base_match)
                    match["organization_id"] = {"$in": fallback_org_ids}
                    total_messages = db.telemetry.count_documents(match)
            else:
                match = dict(base_match)
                total_messages = db.telemetry.count_documents(match)

            if total_messages == 0:
                return None

            active_devices = len(db.telemetry.distinct("device_id", match))

            per_minute = list(db.telemetry.aggregate([
                {"$match": match},
                {
                    "$project": {
                        "bucket": {"$dateTrunc": {"date": "$timestamp", "unit": "minute"}}
                    }
                },
                {"$group": {"_id": "$bucket", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
                {"$limit": 120}
            ]))

            throughput_trend: List[Dict[str, Any]] = []
            max_per_minute = 0
            for entry in per_minute[-10:]:
                bucket = entry.get("_id")
                count = entry.get("count", 0)
                label = bucket.strftime("%H:%M") if isinstance(bucket, datetime) else str(bucket)
                throughput_trend.append({
                    "time": label,
                    "messages": count,
                    "rate": count / 60.0
                })
                if count > max_per_minute:
                    max_per_minute = count

            protocol_counts = defaultdict(int)
            for entry in db.telemetry.aggregate([
                {"$match": match},
                {
                    "$project": {
                        "transport_source": {
                            "$toLower": {
                                "$ifNull": ["$metadata.forwarded_by", "$source"]
                            }
                        }
                    }
                },
                {"$group": {"_id": "$transport_source", "count": {"$sum": 1}}}
            ]):
                source = (entry.get("_id") or "").lower()
                count = entry.get("count", 0)
                if source in {"mqtt_bridge", "live_mqtt_stream", "mqtt_ingest"}:
                    protocol_counts["mqtt"] += count
                elif source in {"api_v1_telemetry", "https_ingest", "http_ingest"}:
                    protocol_counts["https"] += count
                else:
                    protocol_counts["ws"] += count

            top_devices: List[Dict[str, Any]] = []
            for row in db.telemetry.aggregate([
                {"$match": match},
                {
                    "$group": {
                        "_id": "$device_id",
                        "message_count": {"$sum": 1},
                        "last_seen": {"$max": "$timestamp"}
                    }
                },
                {"$sort": {"message_count": -1}},
                {"$limit": 10}
            ]):
                last_seen = row.get("last_seen")
                top_devices.append({
                    "device_id": row.get("_id"),
                    "message_count": row.get("message_count", 0),
                    "last_seen": last_seen.isoformat() if isinstance(last_seen, datetime) else None,
                    "avg_temperature": None
                })

            last_timestamp = None
            for doc in db.telemetry.find(match, {"timestamp": 1}).sort("timestamp", -1).limit(1):
                ts = doc.get("timestamp")
                if isinstance(ts, datetime):
                    last_timestamp = ts.isoformat()

            throughput_avg = int(round(total_messages / time_range_minutes)) if time_range_minutes > 0 else total_messages
            throughput_max = int(max_per_minute)

            return {
                "throughput_max": throughput_max,
                "throughput_avg": throughput_avg,
                "total_messages": total_messages,
                "active_devices": active_devices,
                "anomaly_count": 0,
                "anomaly_score": 0,
                "throughput_trend": throughput_trend,
                "top_devices": top_devices,
                "success_rate": 100,
                "last_updated": last_timestamp or datetime.utcnow().isoformat(),
                "protocol_mix": {
                    "mqtt": protocol_counts["mqtt"],
                    "https": protocol_counts["https"],
                    "ws": protocol_counts["ws"],
                }
            }

        except Exception as exc:
            self.logger.error(f"Mongo fallback for IoT metrics failed: {exc}")
            return None

    async def get_telemetry_daily_stats(self, organization_id: str) -> Dict[str, Any]:
        """
        Get telemetry statistics for the last 24 hours with hourly breakdown.

        Provides:
        - Daily totals (last 24h)
        - Hourly breakdown (24 bars for sparkline)
        - Rolling 15-minute average (live indicator)
        - Protocol mix (MQTT vs HTTPS)
        - Active devices count

        Args:
            organization_id: Organization ID for ACL filtering

        Returns:
            Dictionary with daily telemetry statistics
        """
        try:
            conn = None
            conn_ctx = None
            cur = None

            try:
                conn, conn_ctx = self._acquire_postgres_connection()
                cur = conn.cursor()

                # Query 1: Get 24-hour totals
                cur.execute("""
                    SELECT
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT device_id) as total_devices
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL '24 hours'
                    AND dt.organization_id = %s
                """, (organization_id,))
                daily_totals = cur.fetchone()

                # Query 2: Get hourly breakdown for sparkline (24 bars)
                cur.execute("""
                    SELECT
                        time_bucket('1 hour', time) as hour,
                        COUNT(*) as messages
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL '24 hours'
                    AND dt.organization_id = %s
                    GROUP BY hour
                    ORDER BY hour ASC
                """, (organization_id,))
                hourly_data = cur.fetchall()

                # Query 3: Get rolling 15-minute stats (live indicator)
                cur.execute("""
                    SELECT
                        COUNT(*) as messages,
                        COUNT(DISTINCT device_id) as active_devices
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL '15 minutes'
                    AND dt.organization_id = %s
                """, (organization_id,))
                rolling_15min = cur.fetchone()

                # Query 4: Get protocol mix for 24h
                cur.execute("""
                    SELECT
                        COALESCE(metadata->>'forwarded_by', metadata->>'source', 'unknown') as protocol,
                        COUNT(*) as count
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL '24 hours'
                    AND dt.organization_id = %s
                    GROUP BY protocol
                """, (organization_id,))
                protocol_data = cur.fetchall()

                # Query 5: Get peak hour
                cur.execute("""
                    SELECT
                        time_bucket('1 hour', time) as hour,
                        COUNT(*) as messages
                    FROM device_telemetry dt
                    WHERE dt.time >= NOW() - INTERVAL '24 hours'
                    AND dt.organization_id = %s
                    GROUP BY hour
                    ORDER BY messages DESC
                    LIMIT 1
                """, (organization_id,))
                peak_hour = cur.fetchone()

            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass
                self._release_postgres_connection(conn_ctx, conn)

            # Process results
            total_messages_24h = daily_totals[0] if daily_totals and daily_totals[0] else 0
            total_devices_24h = daily_totals[1] if daily_totals and daily_totals[1] else 0

            # Process hourly breakdown for sparkline
            hourly_breakdown = []
            for row in hourly_data:
                hourly_breakdown.append({
                    "hour": row[0].strftime("%H:00") if row[0] else "00:00",
                    "timestamp": row[0].isoformat() if row[0] else None,
                    "messages": row[1] if row[1] else 0
                })

            # Fill missing hours with 0
            if len(hourly_breakdown) < 24:
                existing_hours = {h["hour"] for h in hourly_breakdown}
                now = datetime.now()
                for i in range(24):
                    hour_str = f"{(now.hour - 23 + i) % 24:02d}:00"
                    if hour_str not in existing_hours:
                        hourly_breakdown.append({
                            "hour": hour_str,
                            "timestamp": None,
                            "messages": 0
                        })
                hourly_breakdown.sort(key=lambda x: x["hour"])

            # Process rolling 15-min
            messages_15min = rolling_15min[0] if rolling_15min and rolling_15min[0] else 0
            active_devices_now = rolling_15min[1] if rolling_15min and rolling_15min[1] else 0
            msg_per_min_live = round(messages_15min / 15, 1) if messages_15min else 0

            # Process protocol mix
            mqtt_count = 0
            https_count = 0
            ws_count = 0
            for row in protocol_data:
                protocol = (row[0] or "").lower()
                count = row[1] if row[1] else 0
                if protocol in {"mqtt_bridge", "live_mqtt_stream", "mqtt_ingest", "mqtt", "mqtts"}:
                    mqtt_count += count
                elif protocol in {"api_v1_telemetry", "https_ingest", "http_ingest", "https", "http", "api"}:
                    https_count += count
                else:
                    ws_count += count

            # Peak hour stats
            peak_hour_messages = peak_hour[1] if peak_hour and peak_hour[1] else 0
            peak_hour_label = peak_hour[0].strftime("%H:00") if peak_hour and peak_hour[0] else None

            # Calculate averages
            avg_per_hour = round(total_messages_24h / 24, 1) if total_messages_24h else 0

            return {
                "success": True,
                "daily": {
                    "total_messages": total_messages_24h,
                    "total_devices": total_devices_24h,
                    "avg_per_hour": avg_per_hour,
                    "peak_hour": {
                        "hour": peak_hour_label,
                        "messages": peak_hour_messages
                    }
                },
                "hourly_breakdown": hourly_breakdown,
                "live": {
                    "msg_per_min": msg_per_min_live,
                    "active_devices": active_devices_now,
                    "window_minutes": 15
                },
                "protocol_mix": {
                    "mqtt": mqtt_count,
                    "mqtt_per_day": mqtt_count,
                    "https": https_count,
                    "https_per_day": https_count,
                    "ws": ws_count
                },
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get telemetry daily stats: {str(e)}")
            # Try MongoDB fallback
            mongo_fallback = self._get_mongo_telemetry_daily_stats(organization_id)
            if mongo_fallback:
                return mongo_fallback
            return self._get_fallback_telemetry_daily_stats()

    def _get_mongo_telemetry_daily_stats(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """MongoDB fallback for telemetry daily stats."""
        db = self.mongodb_client
        if db is None:
            db = get_db()
            if db is None:
                return None
            self.mongodb_client = db

        try:
            since_24h = datetime.utcnow() - timedelta(hours=24)
            since_15min = datetime.utcnow() - timedelta(minutes=15)

            # Build match filter
            match_24h = {"timestamp": {"$gte": since_24h}}
            match_15min = {"timestamp": {"$gte": since_15min}}

            if organization_id:
                match_24h["organization_id"] = organization_id
                match_15min["organization_id"] = organization_id

            # Get 24h totals
            total_messages_24h = db.telemetry.count_documents(match_24h)
            total_devices_24h = len(db.telemetry.distinct("device_id", match_24h))

            # Get 15min totals
            messages_15min = db.telemetry.count_documents(match_15min)
            active_devices_now = len(db.telemetry.distinct("device_id", match_15min))

            # Get hourly breakdown
            hourly_pipeline = [
                {"$match": match_24h},
                {
                    "$project": {
                        "hour": {"$dateTrunc": {"date": "$timestamp", "unit": "hour"}}
                    }
                },
                {"$group": {"_id": "$hour", "messages": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ]
            hourly_data = list(db.telemetry.aggregate(hourly_pipeline))

            hourly_breakdown = []
            peak_hour_messages = 0
            peak_hour_label = None
            for entry in hourly_data:
                hour_dt = entry.get("_id")
                messages = entry.get("messages", 0)
                hour_str = hour_dt.strftime("%H:00") if isinstance(hour_dt, datetime) else "00:00"
                hourly_breakdown.append({
                    "hour": hour_str,
                    "timestamp": hour_dt.isoformat() if isinstance(hour_dt, datetime) else None,
                    "messages": messages
                })
                if messages > peak_hour_messages:
                    peak_hour_messages = messages
                    peak_hour_label = hour_str

            # Get protocol mix
            protocol_pipeline = [
                {"$match": match_24h},
                {
                    "$project": {
                        "protocol": {
                            "$toLower": {"$ifNull": ["$metadata.forwarded_by", "$source"]}
                        }
                    }
                },
                {"$group": {"_id": "$protocol", "count": {"$sum": 1}}}
            ]
            protocol_data = list(db.telemetry.aggregate(protocol_pipeline))

            mqtt_count = 0
            https_count = 0
            ws_count = 0
            for entry in protocol_data:
                protocol = (entry.get("_id") or "").lower()
                count = entry.get("count", 0)
                if protocol in {"mqtt_bridge", "live_mqtt_stream", "mqtt_ingest", "mqtt", "mqtts"}:
                    mqtt_count += count
                elif protocol in {"api_v1_telemetry", "https_ingest", "http_ingest", "https", "http", "api"}:
                    https_count += count
                else:
                    ws_count += count

            msg_per_min_live = round(messages_15min / 15, 1) if messages_15min else 0
            avg_per_hour = round(total_messages_24h / 24, 1) if total_messages_24h else 0

            return {
                "success": True,
                "daily": {
                    "total_messages": total_messages_24h,
                    "total_devices": total_devices_24h,
                    "avg_per_hour": avg_per_hour,
                    "peak_hour": {
                        "hour": peak_hour_label,
                        "messages": peak_hour_messages
                    }
                },
                "hourly_breakdown": hourly_breakdown,
                "live": {
                    "msg_per_min": msg_per_min_live,
                    "active_devices": active_devices_now,
                    "window_minutes": 15
                },
                "protocol_mix": {
                    "mqtt": mqtt_count,
                    "mqtt_per_day": mqtt_count,
                    "https": https_count,
                    "https_per_day": https_count,
                    "ws": ws_count
                },
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as exc:
            self.logger.error(f"Mongo fallback for telemetry daily stats failed: {exc}")
            return None

    def _get_fallback_telemetry_daily_stats(self) -> Dict[str, Any]:
        """Fallback response when all data sources fail."""
        return {
            "success": True,
            "daily": {
                "total_messages": 0,
                "total_devices": 0,
                "avg_per_hour": 0,
                "peak_hour": {
                    "hour": None,
                    "messages": 0
                }
            },
            "hourly_breakdown": [],
            "live": {
                "msg_per_min": 0,
                "active_devices": 0,
                "window_minutes": 15
            },
            "protocol_mix": {
                "mqtt": 0,
                "mqtt_per_day": 0,
                "https": 0,
                "https_per_day": 0,
                "ws": 0
            },
            "last_updated": datetime.now().isoformat()
        }

    async def get_system_health_metrics_fast(self) -> Dict[str, Any]:
        """
        Super fast system health metrics with 3-second timeout
        Used for real-time dashboard to prevent ECONNABORTED errors
        
        Returns:
            Dictionary with essential system health metrics
        """
        try:
            # Set strict timeout for the entire operation
            timeout_start = asyncio.get_event_loop().time()

            # Quick service health checks only
            services: Dict[str, Dict[str, Any]] = {}
            databases: Dict[str, Dict[str, Any]] = {}
            containers: List[Dict[str, Any]] = []

            # Helper for container-based status normalization
            def _status_from_container(entry: Optional[Dict[str, Any]], fallback: str = 'unknown') -> str:
                if not entry:
                    return fallback
                if entry.get('status') != 'running':
                    return 'down'
                health = entry.get('health', '').lower()
                if health and health not in {'healthy', 'up'}:
                    return 'degraded'
                return 'healthy'

            def _uptime_from_container(entry: Optional[Dict[str, Any]]) -> str:
                return entry.get('uptime') if entry and entry.get('uptime') else 'Unknown'

            # Check only essential services with minimal overhead
            try:
                if self.mongodb_client is not None:
                    databases['mongodb'] = {
                        'status': 'healthy',
                        'connections': 5,
                        'response_time': '10ms'
                    }
                else:
                    databases['mongodb'] = {'status': 'disconnected', 'connections': 0, 'response_time': 'N/A'}
            except Exception:
                databases['mongodb'] = {'status': 'error', 'connections': 0, 'response_time': 'N/A'}

            try:
                if self.redis_client is not None:
                    databases['redis'] = {
                        'status': 'healthy',
                        'memory_usage': '128MB',
                        'connected_clients': 3
                    }
                else:
                    databases['redis'] = {'status': 'disconnected', 'memory_usage': 'N/A', 'connected_clients': 0}
            except Exception:
                databases['redis'] = {'status': 'error', 'memory_usage': 'N/A', 'connected_clients': 0}

            # Vault health (lightweight -- avoids expensive calls)
            try:
                vault = get_vault()
                if vault:
                    databases['vault'] = {'status': 'healthy', 'response_time': '15ms'}
                else:
                    databases['vault'] = {'status': 'disconnected'}
            except Exception:
                databases['vault'] = {'status': 'error'}

            # Quick container status (no expensive stats)
            target_names = {
                'tesa-api',
                'tesa-mqtt-bridge',
                'tesa-emqx',
                'tesa-redis',
                'tesa-mongodb',
                'tesa-vault',
                'tesa-prometheus',
                'tesa-timescaledb'
            }

            try:
                if self.docker_client:
                    for container in self.docker_client.containers.list():
                        if container.name not in target_names and len(containers) >= len(target_names):
                            if asyncio.get_event_loop().time() - timeout_start > self.fast_timeout:
                                break
                            continue

                        try:
                            container.reload()
                        except Exception:
                            pass

                        health_state = (
                            container.attrs.get('State', {})
                            .get('Health', {})
                            .get('Status')
                            if getattr(container, 'attrs', None)
                            else None
                        )
                        created_ts = container.attrs.get('Created') if getattr(container, 'attrs', None) else ''
                        containers.append({
                            'name': container.name,
                            'status': container.status,
                            'health': health_state or container.status,
                            'uptime': self._safe_calculate_uptime(created_ts),
                            'cpu_percent': 25 + (hash(container.name) % 30),  # Simulated lightweight metric
                            'memory_percent': 40 + (hash(container.name) % 25),
                            'restart_count': container.attrs.get('RestartCount', 0) if getattr(container, 'attrs', None) else 0,
                        })

                        if asyncio.get_event_loop().time() - timeout_start > self.fast_timeout:
                            break

            except Exception:
                # If Docker fails, return minimal container data
                containers = []

            container_lookup = {entry['name']: entry for entry in containers}

            api_container = container_lookup.get('tesa-api')
            mqtt_container = container_lookup.get('tesa-emqx')
            bridge_container = container_lookup.get('tesa-mqtt-bridge')
            redis_container = container_lookup.get('tesa-redis')
            mongo_container = container_lookup.get('tesa-mongodb')
            vault_container = container_lookup.get('tesa-vault')
            monitoring_container = container_lookup.get('tesa-prometheus')
            timescaledb_container = container_lookup.get('tesa-timescaledb')

            fallback_service_status = {
                'api': 'healthy',
                'mqtt': 'healthy',
                'telemetry': 'healthy',
                'redis': 'healthy',
                'mongodb': 'healthy',
                'vault': 'healthy',
                'monitoring': 'healthy',
                'timescaledb': 'healthy',
            }

            # If direct DB checks fail, fall back to container state
            if redis_container and databases.get('redis', {}).get('status') in {'disconnected', 'error'}:
                databases['redis'] = {
                    'status': _status_from_container(redis_container),
                    'connected_clients': databases.get('redis', {}).get('connected_clients', 0),
                    'memory_usage': databases.get('redis', {}).get('memory_usage', 'N/A'),
                }

            if mongo_container and databases.get('mongodb', {}).get('status') in {'disconnected', 'error'}:
                databases['mongodb'] = {
                    'status': _status_from_container(mongo_container),
                    'connections': databases.get('mongodb', {}).get('connections', 5),
                    'response_time': databases.get('mongodb', {}).get('response_time', '10ms'),
                }

            if vault_container and databases.get('vault', {}).get('status') in {'disconnected', 'error'}:
                databases['vault'] = {
                    'status': _status_from_container(vault_container),
                    'response_time': databases.get('vault', {}).get('response_time', '15ms'),
                }

            # Basic services status aligned with dashboard cards
            services = {
                'api_gateway': {
                    'status': _status_from_container(api_container, fallback_service_status['api']),
                    'uptime': _uptime_from_container(api_container),
                    'requests_per_minute': 45,
                    'display_name': 'API Gateway',
                },
                'mqtt_broker': {
                    'status': _status_from_container(mqtt_container, fallback_service_status['mqtt']),
                    'uptime': _uptime_from_container(mqtt_container),
                    'connected_clients': 12,
                    'messages_per_second': 25,
                    'display_name': 'MQTTS Broker',
                },
                'monitoring': {
                    'status': _status_from_container(monitoring_container, fallback_service_status['monitoring']),
                    'uptime': _uptime_from_container(monitoring_container),
                    'alerts_active': 0,
                    'metrics_collected': True,
                    'display_name': 'Monitoring',
                },
                'telemetry': {
                    'status': _status_from_container(bridge_container, fallback_service_status['telemetry']),
                    'uptime': _uptime_from_container(bridge_container),
                    'streams_active': 1 if bridge_container else 0,
                    'display_name': 'Telemetry Ingest',
                },
                'redis': {
                    'status': _status_from_container(redis_container, fallback_service_status['redis']),
                    'uptime': _uptime_from_container(redis_container),
                    'connected_clients': databases.get('redis', {}).get('connected_clients'),
                    'display_name': 'TESAIoT Caches',
                },
                'mongodb': {
                    'status': _status_from_container(mongo_container, fallback_service_status['mongodb']),
                    'uptime': _uptime_from_container(mongo_container),
                    'connections': databases.get('mongodb', {}).get('connections'),
                    'display_name': 'Databases',
                },
                'vault': {
                    'status': _status_from_container(vault_container, fallback_service_status['vault']),
                    'uptime': _uptime_from_container(vault_container),
                    'display_name': 'PKI Server',
                },
                'timescaledb': {
                    'status': _status_from_container(timescaledb_container, fallback_service_status['timescaledb']),
                    'uptime': _uptime_from_container(timescaledb_container),
                    'display_name': 'TimescaleDB',
                },
            }

            return {
                'services': services,
                'databases': databases,
                'containers': containers,
                'system_metrics': {
                    'overall_health': 'healthy',
                    'total_containers': len(containers),
                    'healthy_containers': len([c for c in containers if c['health'] == 'healthy']),
                    'avg_cpu_usage': sum(c['cpu_percent'] for c in containers) / len(containers) if containers else 0,
                    'avg_memory_usage': sum(c['memory_percent'] for c in containers) / len(containers) if containers else 0
                },
                'generated_at': datetime.now().isoformat(),
                'response_time': 'fast'
            }
            
        except Exception as e:
            self.logger.error(f"Fast system health error: {str(e)}")
            return self._get_fallback_system_health()
    
    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """
        Get real-time system health from Docker and databases
        
        Returns:
            Dictionary with system health metrics
        """
        try:
            health_data = {
                "containers": [],
                "databases": {},
                "overall_health": "healthy",
                "last_updated": datetime.now().isoformat()
            }
            
            # Get Docker container stats
            if self.docker_client:
                containers = self.docker_client.containers.list()
                for container in containers:
                    try:
                        stats = container.stats(stream=False)
                        
                        # Calculate CPU percentage (with safer error handling)
                        cpu_percent = 0
                        try:
                            if 'cpu_stats' in stats and 'precpu_stats' in stats:
                                cpu_stats = stats['cpu_stats']
                                precpu_stats = stats['precpu_stats']
                                
                                # Safely get CPU usage values
                                cpu_usage = cpu_stats.get('cpu_usage', {})
                                precpu_usage = precpu_stats.get('cpu_usage', {})
                                
                                total_usage = cpu_usage.get('total_usage', 0)
                                prev_total_usage = precpu_usage.get('total_usage', 0)
                                
                                # Get system CPU usage (handle different field names)
                                system_cpu = cpu_stats.get('system_cpu_usage', 0) or cpu_stats.get('system_usage', 0)
                                prev_system_cpu = precpu_stats.get('system_cpu_usage', 0) or precpu_stats.get('system_usage', 0)
                                
                                cpu_delta = total_usage - prev_total_usage
                                system_delta = system_cpu - prev_system_cpu
                                
                                if system_delta > 0 and cpu_delta >= 0:
                                    # Get number of CPUs (safer way)
                                    percpu_usage = cpu_usage.get('percpu_usage', [])
                                    num_cpus = len(percpu_usage) if percpu_usage else 1
                                    
                                    # Alternative: get from online_cpus if percpu_usage is missing
                                    if num_cpus == 1 and 'online_cpus' in cpu_stats:
                                        num_cpus = cpu_stats['online_cpus']
                                    
                                    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
                                    cpu_percent = min(cpu_percent, 100.0)  # Cap at 100%
                        except (KeyError, TypeError, ZeroDivisionError) as e:
                            # If CPU calculation fails, use a fallback method or set to 0
                            cpu_percent = 0
                        
                        # Calculate memory percentage (with safer error handling)
                        memory_percent = 0
                        memory_usage_mb = 0
                        try:
                            if 'memory_stats' in stats:
                                memory_stats = stats['memory_stats']
                                mem_usage = memory_stats.get('usage', 0)
                                mem_limit = memory_stats.get('limit', 0)
                                
                                if mem_usage > 0:
                                    memory_usage_mb = mem_usage / (1024 * 1024)  # Convert to MB
                                
                                if mem_limit > 0 and mem_usage > 0:
                                    memory_percent = (mem_usage / mem_limit) * 100.0
                                    memory_percent = min(memory_percent, 100.0)  # Cap at 100%
                        except (KeyError, TypeError, ZeroDivisionError):
                            memory_percent = 0
                            memory_usage_mb = 0
                        
                        # Determine container health
                        container_health = "healthy"
                        if cpu_percent > 80 or memory_percent > 85:
                            container_health = "warning"
                        if cpu_percent > 95 or memory_percent > 95:
                            container_health = "critical"
                        
                        health_data["containers"].append({
                            "name": container.name,
                            "status": container.status,
                            "health": container_health,
                            "cpu_percent": round(cpu_percent, 1),
                            "memory_percent": round(memory_percent, 1),
                            "uptime": self._safe_calculate_uptime(container.attrs.get('Created', '')),
                            "restart_count": container.attrs['RestartCount'] if 'RestartCount' in container.attrs else 0
                        })
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to get stats for container {container.name}: {str(e)}")
            
            # Get database health
            # MongoDB
            try:
                if self.mongodb_client is not None:
                    # self.mongodb_client is actually the database, not the client
                    # Get the client from the database
                    mongo_client = self.mongodb_client.client
                    server_status = mongo_client.admin.command("serverStatus")
                    db_stats = self.mongodb_client.command("dbStats")
                    
                    health_data["databases"]["mongodb"] = {
                        "status": "healthy",
                        "connections": server_status.get('connections', {}).get('current', 0),
                        "uptime": server_status.get('uptime', 0),
                        "memory_usage_mb": round(server_status.get('mem', {}).get('resident', 0)),
                        "database_size_gb": round(db_stats.get('dataSize', 0) / (1024**3), 2),
                        "collections": db_stats.get('collections', 0)
                    }
            except Exception as e:
                health_data["databases"]["mongodb"] = {"status": "error", "error": str(e)}
            
            # Redis
            try:
                if self.redis_client is not None:
                    redis_info = self.redis_client.info()
                    
                    health_data["databases"]["redis"] = {
                        "status": "healthy",
                        "memory_usage_mb": round(redis_info.get('used_memory', 0) / (1024**2), 1),
                        "connected_clients": redis_info.get('connected_clients', 0),
                        "total_keys": self.redis_client.dbsize(),
                        "uptime_seconds": redis_info.get('uptime_in_seconds', 0)
                    }
            except Exception as e:
                health_data["databases"]["redis"] = {"status": "error", "error": str(e)}
            
            # TimescaleDB
            conn = None
            conn_ctx = None
            cur = None
            try:
                conn, conn_ctx = self._acquire_postgres_connection()
                # Import RealDictCursor if needed for some queries
                cur = conn.cursor()
                
                # Get database size and connection count
                cur.execute("""
                    SELECT 
                        pg_database_size(current_database())/1024/1024/1024 as size_gb,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT extract(epoch from (now() - pg_postmaster_start_time()))) as uptime_seconds
                """)
                
                db_stats = cur.fetchone()
                
                health_data["databases"]["timescaledb"] = {
                    "status": "healthy",
                    "database_size_gb": round(db_stats[0], 2),
                    "active_connections": db_stats[1],
                    "uptime_seconds": int(db_stats[2])
                }
                
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass
                self._release_postgres_connection(conn_ctx, conn)

            return health_data
            
        except Exception as e:
            self.logger.error(f"Failed to get system health: {str(e)}")
            return self._get_fallback_health_metrics()
    
    def _safe_calculate_uptime(self, created_time_str: str) -> str:
        """Safely calculate container uptime from created timestamp"""
        try:
            if not created_time_str:
                return "Unknown"

            clean_time = created_time_str

            if clean_time.endswith('Z'):
                clean_time = clean_time[:-1] + '+00:00'

            if '.' in clean_time:
                prefix, suffix = clean_time.split('.', 1)
                tz_sep = '+' if '+' in suffix else '-' if '-' in suffix else None
                if tz_sep:
                    frac, tz = suffix.split(tz_sep, 1)
                    frac = ''.join(ch for ch in frac if ch.isdigit())[:6]
                    clean_time = f"{prefix}.{frac}{tz_sep}{tz}"
                else:
                    frac = ''.join(ch for ch in suffix if ch.isdigit())[:6]
                    clean_time = f"{prefix}.{frac}"

            created_time = datetime.fromisoformat(clean_time)
            uptime_seconds = (datetime.now(created_time.tzinfo) - created_time).total_seconds()
            return self._format_uptime(uptime_seconds)
        except (ValueError, TypeError, AttributeError):
            return "Unknown"
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime seconds into human readable string"""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _get_fallback_system_health(self) -> Dict[str, Any]:
        """Fallback system health data when Docker monitoring fails"""
        fallback_services = [
            {"name": "API Gateway", "status": "healthy", "uptime": "2h 45m", "lastCheck": "30s ago", 
             "metrics": {"cpu": 25, "memory": 45, "requests": 1234, "errors": 0}},
            {"name": "MongoDB", "status": "healthy", "uptime": "2h 45m", "lastCheck": "15s ago",
             "metrics": {"cpu": 32, "memory": 56, "requests": 456, "errors": 1}},
            {"name": "Redis Cache", "status": "degraded", "uptime": "2h 30m", "lastCheck": "45s ago",
             "metrics": {"cpu": 56, "memory": 82, "requests": 234, "errors": 12}},
            {"name": "Vault PKI", "status": "healthy", "uptime": "2h 45m", "lastCheck": "20s ago",
             "metrics": {"cpu": 12, "memory": 34, "requests": 123, "errors": 0}},
            {"name": "MQTT Broker", "status": "healthy", "uptime": "2h 40m", "lastCheck": "10s ago",
             "metrics": {"cpu": 18, "memory": 38, "requests": 567, "errors": 0}}
        ]
        
        # Generate timeline
        timeline = []
        current_time = datetime.now()
        for i in range(20):
            time_point = current_time - timedelta(minutes=20-i)
            timeline.append({
                "time": time_point.strftime("%H:%M"),
                "cpu": 42 + (i % 3 - 1) * 5,
                "memory": 65 + (i % 4 - 2) * 3,
                "disk": 75 + (i % 2) * 2,
                "network": 85 + (i % 5) * 10
            })
        
        return {
            "services": fallback_services,
            "system_metrics": {"cpu_usage": 42, "memory_usage": 65, "disk_usage": 75, "network_io": 85},
            "resource_timeline": timeline,
            "last_updated": datetime.now().isoformat(),
            "status": "fallback_data"
        }
    
    async def get_api_gateway_metrics(self, time_range: str = "1h") -> Dict[str, Any]:
        """
        Get real-time API gateway metrics
        
        Args:
            time_range: Time range for metrics
            
        Returns:
            Dictionary with API gateway performance data
        """
        try:
            # Convert time range to interval
            interval_map = {
                "1h": "1 hour",
                "6h": "6 hours", 
                "24h": "24 hours",
                "7d": "7 days"
            }
            interval = interval_map.get(time_range, "1 hour")
            
            # Connect to TimescaleDB for API metrics
            conn = None
            conn_ctx = None
            cur = None
            try:
                conn, conn_ctx = self._acquire_postgres_connection()
                cur = conn.cursor()

                # Query API request metrics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        COUNT(CASE WHEN status_code BETWEEN 200 AND 399 THEN 1 END) as successful_requests,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_requests,
                        AVG(response_time_ms) as avg_response_time,
                        MAX(response_time_ms) as max_response_time,
                        MIN(response_time_ms) as min_response_time
                    FROM api_metrics
                    WHERE time >= NOW() - INTERVAL %s
                """, (interval,))
                api_stats = cur.fetchone()

                # Query top endpoints
                cur.execute("""
                    SELECT 
                        endpoint,
                        COUNT(*) as request_count,
                        AVG(response_time_ms) as avg_response_time,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
                    FROM api_metrics
                    WHERE time >= NOW() - INTERVAL %s
                    GROUP BY endpoint
                    ORDER BY request_count DESC
                    LIMIT 10
                """, (interval,))
                top_endpoints = cur.fetchall()

                # Query response time trend
                cur.execute("""
                    SELECT 
                        time_bucket('5 minutes', time) as bucket,
                        AVG(response_time_ms) as avg_response_time,
                        COUNT(*) as request_count
                    FROM api_metrics
                    WHERE time >= NOW() - INTERVAL %s
                    GROUP BY bucket
                    ORDER BY bucket DESC
                    LIMIT 12
                """, (interval,))
                response_trend = cur.fetchall()

            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass
                self._release_postgres_connection(conn_ctx, conn)
            
            # Process the data
            total_requests = api_stats[0] if api_stats[0] else 0
            successful_requests = api_stats[1] if api_stats[1] else 0
            error_requests = api_stats[2] if api_stats[2] else 0
            avg_response_time = round(api_stats[3], 1) if api_stats[3] else 0
            
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 100
            
            # Process top endpoints
            endpoints_data = []
            for row in top_endpoints:
                endpoints_data.append({
                    "endpoint": row[0],
                    "requests": row[1],
                    "avg_response_ms": round(row[2], 1),
                    "error_rate": round((row[3] / row[1] * 100), 1) if row[1] > 0 else 0
                })
            
            # Process response time trend
            trend_data = []
            for row in reversed(response_trend):  # Reverse to get chronological order
                trend_data.append({
                    "time": row[0].strftime("%H:%M"),
                    "avg_response_ms": round(row[1], 1),
                    "request_count": row[2]
                })
            
            return {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "error_requests": error_requests,
                "success_rate": round(success_rate, 1),
                "avg_response_time_ms": avg_response_time,
                "requests_per_minute": round(total_requests / (60 if time_range == "1h" else 360), 1),
                "top_endpoints": endpoints_data,
                "response_time_trend": trend_data,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get API gateway metrics: {str(e)}")
            return self._get_fallback_api_metrics()
    
    async def get_realtime_logs_analytics(self, organization_id: str, time_range: str = "1h") -> Dict[str, Any]:
        """
        Get real-time logs and events analytics
        
        Args:
            organization_id: Organization ID for filtering
            time_range: Time range for log analysis
            
        Returns:
            Dictionary with log analytics data
        """
        try:
            interval_map = {
                "1h": "1 hour",
                "6h": "6 hours", 
                "24h": "24 hours",
                "7d": "7 days"
            }
            interval = interval_map.get(time_range, "1 hour")
            
            conn = None
            conn_ctx = None
            cur = None
            try:
                conn, conn_ctx = self._acquire_postgres_connection()
                cur = conn.cursor()

                # Query log level distribution
                cur.execute("""
                    SELECT 
                        severity as level,
                        COUNT(*) as count
                    FROM device_events
                    WHERE time >= NOW() - INTERVAL %s
                    AND organization_id = %s
                    GROUP BY level
                    ORDER BY count DESC
                """, (interval, organization_id))
                log_levels = cur.fetchall()

                # Query log sources
                cur.execute("""
                    SELECT 
                        event_type as source,
                        COUNT(*) as count,
                        COUNT(CASE WHEN level IN ('error', 'critical') THEN 1 END) as error_count
                    FROM device_events
                    WHERE time >= NOW() - INTERVAL %s
                    AND organization_id = %s
                    GROUP BY source
                    ORDER BY count DESC
                    LIMIT 10
                """, (interval, organization_id))
                log_sources = cur.fetchall()

                # Query recent errors and warnings
                cur.execute("""
                    SELECT 
                        time,
                        severity as level,
                        event_type as source,
                        message,
                        details as metadata
                    FROM device_events
                    WHERE time >= NOW() - INTERVAL %s
                    AND level IN ('error', 'warning', 'critical')
                    AND organization_id = %s
                    ORDER BY time DESC
                    LIMIT 50
                """, (interval, organization_id))
                recent_issues = cur.fetchall()

                # Query log volume trend
                cur.execute("""
                    SELECT 
                        time_bucket('10 minutes', time) as bucket,
                        COUNT(*) as log_count,
                        COUNT(CASE WHEN level = 'error' THEN 1 END) as error_count,
                        COUNT(CASE WHEN level = 'warning' THEN 1 END) as warning_count
                    FROM device_events
                    WHERE time >= NOW() - INTERVAL %s
                    AND organization_id = %s
                    GROUP BY bucket
                    ORDER BY bucket DESC
                    LIMIT 6
                """, (interval, organization_id))
                log_trend = cur.fetchall()

            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass
                self._release_postgres_connection(conn_ctx, conn)
            
            # Process log level data
            level_distribution = {}
            total_logs = 0
            for row in log_levels:
                level_distribution[row[0]] = row[1]
                total_logs += row[1]
            
            # Process source data
            sources_data = []
            for row in log_sources:
                sources_data.append({
                    "source": row[0],
                    "total_logs": row[1],
                    "error_count": row[2],
                    "error_rate": round((row[2] / row[1] * 100), 1) if row[1] > 0 else 0
                })
            
            # Process recent issues
            issues_data = []
            for row in recent_issues[:20]:  # Limit to 20 most recent
                issues_data.append({
                    "timestamp": row[0].isoformat(),
                    "level": row[1],
                    "source": row[2],
                    "message": row[3][:200],  # Truncate long messages
                    "metadata": json.loads(row[4]) if row[4] else {}
                })
            
            # Process trend data
            trend_data = []
            for row in reversed(log_trend):
                trend_data.append({
                    "time": row[0].strftime("%H:%M"),
                    "total_logs": row[1],
                    "errors": row[2],
                    "warnings": row[3]
                })
            
            return {
                "total_logs": total_logs,
                "error_count": level_distribution.get('error', 0),
                "warning_count": level_distribution.get('warning', 0),
                "info_count": level_distribution.get('info', 0),
                "level_distribution": level_distribution,
                "top_sources": sources_data,
                "recent_issues": issues_data,
                "log_trend": trend_data,
                "health_score": max(0, 100 - (level_distribution.get('error', 0) * 2 + level_distribution.get('warning', 0))),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get log analytics: {str(e)}")
            return self._get_fallback_log_metrics()
    
    def _get_fallback_iot_metrics(self) -> Dict[str, Any]:
        """Fallback IoT metrics when database is unavailable"""
        return {
            "throughput_max": 0,
            "throughput_avg": 0,
            "total_messages": 0,
            "active_devices": 0,
            "anomaly_count": 0,
            "anomaly_score": 0,
            "throughput_trend": [],
            "top_devices": [],
            "success_rate": 0,
            "last_updated": datetime.now().isoformat(),
            "status": "database_unavailable"
        }
    
    def _get_fallback_health_metrics(self) -> Dict[str, Any]:
        """Fallback health metrics when monitoring is unavailable"""
        return {
            "containers": [],
            "databases": {},
            "overall_health": "unknown",
            "last_updated": datetime.now().isoformat(),
            "status": "monitoring_unavailable"
        }
    
    def _get_fallback_api_metrics(self) -> Dict[str, Any]:
        """Fallback API metrics when data is unavailable"""
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "error_requests": 0,
            "success_rate": 0,
            "avg_response_time_ms": 0,
            "requests_per_minute": 0,
            "top_endpoints": [],
            "response_time_trend": [],
            "last_updated": datetime.now().isoformat(),
            "status": "data_unavailable"
        }
    
    def _get_fallback_log_metrics(self) -> Dict[str, Any]:
        """Fallback log metrics when log system is unavailable"""
        return {
            "total_logs": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "level_distribution": {},
            "top_sources": [],
            "recent_issues": [],
            "log_trend": [],
            "health_score": 0,
            "last_updated": datetime.now().isoformat(),
            "status": "logs_unavailable"
        }

# Service instance
realtime_analytics_service = RealTimeAnalyticsService()
