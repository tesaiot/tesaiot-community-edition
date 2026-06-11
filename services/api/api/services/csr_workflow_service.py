# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - CSR Workflow Status Service
Version: v2026.01
Build: 2026-01-09
Module: Device Logs Improvement Feature

This service provides CSR workflow status tracking functionality for:
- Real-time workflow step tracking
- Error diagnosis with actionable suggestions
- Workflow duration metrics
- Multi-device workflow monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..core.database import get_db
from ..models.csr_workflow_status import (
    CSRWorkflowStatusModel,
    CSRWorkflowStatusResponse,
    CSRWorkflowListResponse,
    WorkflowStep,
    StepStatus,
    WorkflowStatus,
    WORKFLOW_STEP_ORDER,
    generate_csr_correlation_id,
    get_error_suggestion
)
from .enhanced_device_log_service import log_csr_event
from ..models.device_log_enhanced import LogLevel

logger = logging.getLogger(__name__)


class CSRWorkflowService:
    """Service for managing CSR workflow status"""

    COLLECTION_NAME = "csr_workflow_status"

    @staticmethod
    def _get_collection():
        """Get the MongoDB collection"""
        db = get_db()
        if db is None:
            raise Exception("Database connection not available")
        return db[CSRWorkflowService.COLLECTION_NAME]

    @staticmethod
    async def create_workflow(
        device_id: str,
        organization_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new CSR workflow for a device.

        Args:
            device_id: Device identifier
            organization_id: Organization ID
            correlation_id: Optional correlation ID (auto-generated if not provided)

        Returns:
            Created workflow document
        """
        try:
            collection = CSRWorkflowService._get_collection()

            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = generate_csr_correlation_id(device_id)

            # Check if workflow already exists for this device
            existing = collection.find_one({"device_id": device_id})
            if existing:
                # If there's an active workflow, update it instead
                if existing.get("workflow_status") == WorkflowStatus.ACTIVE.value:
                    logger.warning(f"Active workflow already exists for device {device_id}")
                    return existing

                # Delete old completed/failed workflow
                collection.delete_one({"device_id": device_id})

            # Create new workflow
            workflow = CSRWorkflowStatusModel(
                device_id=device_id,
                organization_id=organization_id,
                correlation_id=correlation_id,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            doc = workflow.to_mongo_dict()
            result = collection.insert_one(doc)
            doc['_id'] = str(result.inserted_id)

            # Log the workflow creation
            await log_csr_event(
                device_id=device_id,
                event_type="csr_workflow_created",
                message="CSR workflow initiated",
                level=LogLevel.INFO,
                correlation_id=correlation_id,
                details={"workflow_id": str(result.inserted_id)}
            )

            logger.info(f"Created CSR workflow for device {device_id} with correlation_id {correlation_id}")
            return doc

        except Exception as e:
            logger.error(f"Error creating CSR workflow: {e}")
            raise

    @staticmethod
    async def update_step(
        device_id: str,
        step: WorkflowStep,
        status: StepStatus,
        details: Optional[str] = None
    ) -> bool:
        """
        Update a workflow step status.

        Args:
            device_id: Device identifier
            step: Workflow step to update
            status: New status for the step
            details: Optional details about the status change

        Returns:
            True if updated successfully
        """
        try:
            collection = CSRWorkflowService._get_collection()

            # Get current workflow
            workflow = collection.find_one({"device_id": device_id})
            if not workflow:
                logger.warning(f"No workflow found for device {device_id}")
                return False

            now = datetime.utcnow()

            # Calculate duration from previous step
            duration_ms = None
            step_index = WORKFLOW_STEP_ORDER.index(step)
            if step_index > 0:
                prev_step = WORKFLOW_STEP_ORDER[step_index - 1]
                prev_step_data = workflow.get("steps", {}).get(prev_step.value, {})
                prev_timestamp = prev_step_data.get("timestamp")
                if prev_timestamp:
                    if isinstance(prev_timestamp, str):
                        prev_timestamp = datetime.fromisoformat(prev_timestamp.replace('Z', '+00:00'))
                    duration_ms = int((now - prev_timestamp).total_seconds() * 1000)

            # Build update
            update = {
                "$set": {
                    f"steps.{step.value}.status": status.value,
                    f"steps.{step.value}.timestamp": now,
                    f"steps.{step.value}.details": details,
                    "current_step": step.value,
                    "updated_at": now
                }
            }

            if duration_ms is not None:
                update["$set"][f"steps.{step.value}.duration_ms"] = duration_ms

            # Update workflow status based on step status
            if status == StepStatus.FAILED:
                update["$set"]["workflow_status"] = WorkflowStatus.FAILED.value
            elif step == WorkflowStep.DEVICE_ACKNOWLEDGED and status == StepStatus.COMPLETED:
                update["$set"]["workflow_status"] = WorkflowStatus.COMPLETED.value
                update["$set"]["completed_at"] = now

            result = collection.update_one(
                {"device_id": device_id},
                update
            )

            # Log the step update
            correlation_id = workflow.get("correlation_id")
            log_level = LogLevel.ERROR if status == StepStatus.FAILED else LogLevel.INFO
            await log_csr_event(
                device_id=device_id,
                event_type=f"csr_step_{step.value}_{status.value}",
                message=f"CSR workflow step '{step.value}' changed to '{status.value}'",
                level=log_level,
                correlation_id=correlation_id,
                details={
                    "step": step.value,
                    "status": status.value,
                    "details": details,
                    "duration_ms": duration_ms
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating workflow step: {e}")
            raise

    @staticmethod
    async def get_status(device_id: str) -> Optional[CSRWorkflowStatusResponse]:
        """
        Get workflow status for a device.

        Args:
            device_id: Device identifier

        Returns:
            Workflow status or None if not found
        """
        try:
            collection = CSRWorkflowService._get_collection()

            workflow = collection.find_one({"device_id": device_id})
            if not workflow:
                return None

            # Convert ObjectId to string
            workflow['_id'] = str(workflow['_id'])

            # Convert timestamps
            for field in ['started_at', 'completed_at', 'updated_at']:
                if field in workflow and isinstance(workflow[field], datetime):
                    workflow[field] = workflow[field].isoformat()

            for step_data in workflow.get('steps', {}).values():
                if 'timestamp' in step_data and isinstance(step_data['timestamp'], datetime):
                    step_data['timestamp'] = step_data['timestamp'].isoformat()

            # Calculate progress
            completed_steps = sum(
                1 for step in workflow.get('steps', {}).values()
                if step.get('status') == StepStatus.COMPLETED.value
            )
            progress_percentage = int((completed_steps / len(WORKFLOW_STEP_ORDER)) * 100)

            # Calculate total duration
            total_duration_ms = None
            if workflow.get('completed_at'):
                started = datetime.fromisoformat(workflow['started_at'].replace('Z', '+00:00'))
                completed = datetime.fromisoformat(workflow['completed_at'].replace('Z', '+00:00'))
                total_duration_ms = int((completed - started).total_seconds() * 1000)

            return CSRWorkflowStatusResponse(
                device_id=workflow['device_id'],
                correlation_id=workflow['correlation_id'],
                workflow_status=workflow['workflow_status'],
                current_step=workflow.get('current_step'),
                steps=workflow.get('steps', {}),
                started_at=workflow['started_at'],
                completed_at=workflow.get('completed_at'),
                error=workflow.get('error'),
                progress_percentage=progress_percentage,
                total_duration_ms=total_duration_ms
            )

        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            raise

    @staticmethod
    async def complete_workflow(device_id: str) -> bool:
        """
        Mark a workflow as completed.

        Args:
            device_id: Device identifier

        Returns:
            True if completed successfully
        """
        try:
            collection = CSRWorkflowService._get_collection()

            now = datetime.utcnow()

            result = collection.update_one(
                {"device_id": device_id},
                {
                    "$set": {
                        "workflow_status": WorkflowStatus.COMPLETED.value,
                        "completed_at": now,
                        "updated_at": now
                    }
                }
            )

            if result.modified_count > 0:
                # Get correlation ID for logging
                workflow = collection.find_one({"device_id": device_id})
                correlation_id = workflow.get("correlation_id") if workflow else None

                await log_csr_event(
                    device_id=device_id,
                    event_type="csr_workflow_completed",
                    message="CSR workflow completed successfully",
                    level=LogLevel.INFO,
                    correlation_id=correlation_id
                )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error completing workflow: {e}")
            raise

    @staticmethod
    async def fail_workflow(
        device_id: str,
        error_code: str,
        error_message: str,
        failed_step: Optional[str] = None
    ) -> bool:
        """
        Mark a workflow as failed with error details.

        Args:
            device_id: Device identifier
            error_code: Error code (e.g., 'TLS_CERT_REQUIRED')
            error_message: Error message
            failed_step: Step where failure occurred

        Returns:
            True if updated successfully
        """
        try:
            collection = CSRWorkflowService._get_collection()

            # Get error suggestion
            suggestion_info = get_error_suggestion(error_code)
            suggestion = suggestion_info.get("suggestion") if suggestion_info else None

            now = datetime.utcnow()

            error = {
                "step": failed_step,
                "code": error_code,
                "message": error_message,
                "suggestion": suggestion,
                "timestamp": now.isoformat()
            }

            result = collection.update_one(
                {"device_id": device_id},
                {
                    "$set": {
                        "workflow_status": WorkflowStatus.FAILED.value,
                        "error": error,
                        "updated_at": now
                    }
                }
            )

            if result.modified_count > 0:
                # Get correlation ID for logging
                workflow = collection.find_one({"device_id": device_id})
                correlation_id = workflow.get("correlation_id") if workflow else None

                await log_csr_event(
                    device_id=device_id,
                    event_type="csr_workflow_failed",
                    message=f"CSR workflow failed: {error_message}",
                    level=LogLevel.ERROR,
                    correlation_id=correlation_id,
                    error=error
                )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error failing workflow: {e}")
            raise

    @staticmethod
    async def get_active_workflows(
        organization_id: Optional[str] = None,
        limit: int = 100
    ) -> CSRWorkflowListResponse:
        """
        Get all active workflows.

        Args:
            organization_id: Optional filter by organization
            limit: Maximum number of workflows to return

        Returns:
            List of active workflows
        """
        try:
            collection = CSRWorkflowService._get_collection()

            query: Dict[str, Any] = {}
            if organization_id:
                query["organization_id"] = organization_id

            # Get counts by status
            pipeline = [
                {"$match": query} if query else {"$match": {}},
                {
                    "$group": {
                        "_id": "$workflow_status",
                        "count": {"$sum": 1}
                    }
                }
            ]

            status_counts = {item["_id"]: item["count"] for item in collection.aggregate(pipeline)}

            # Get active workflows
            query["workflow_status"] = WorkflowStatus.ACTIVE.value
            cursor = collection.find(query).sort("started_at", -1).limit(limit)

            workflows = []
            for workflow in cursor:
                workflow['_id'] = str(workflow['_id'])

                # Convert timestamps
                for field in ['started_at', 'completed_at', 'updated_at']:
                    if field in workflow and isinstance(workflow[field], datetime):
                        workflow[field] = workflow[field].isoformat()

                for step_data in workflow.get('steps', {}).values():
                    if 'timestamp' in step_data and isinstance(step_data['timestamp'], datetime):
                        step_data['timestamp'] = step_data['timestamp'].isoformat()

                # Calculate progress
                completed_steps = sum(
                    1 for step in workflow.get('steps', {}).values()
                    if step.get('status') == StepStatus.COMPLETED.value
                )
                progress_percentage = int((completed_steps / len(WORKFLOW_STEP_ORDER)) * 100)

                workflows.append(CSRWorkflowStatusResponse(
                    device_id=workflow['device_id'],
                    correlation_id=workflow['correlation_id'],
                    workflow_status=workflow['workflow_status'],
                    current_step=workflow.get('current_step'),
                    steps=workflow.get('steps', {}),
                    started_at=workflow['started_at'],
                    completed_at=workflow.get('completed_at'),
                    error=workflow.get('error'),
                    progress_percentage=progress_percentage
                ))

            return CSRWorkflowListResponse(
                workflows=workflows,
                total=len(workflows),
                active_count=status_counts.get(WorkflowStatus.ACTIVE.value, 0),
                completed_count=status_counts.get(WorkflowStatus.COMPLETED.value, 0),
                failed_count=status_counts.get(WorkflowStatus.FAILED.value, 0)
            )

        except Exception as e:
            logger.error(f"Error getting active workflows: {e}")
            raise

    @staticmethod
    async def delete_workflow(device_id: str) -> bool:
        """
        Delete a workflow for a device.

        Args:
            device_id: Device identifier

        Returns:
            True if deleted successfully
        """
        try:
            collection = CSRWorkflowService._get_collection()

            result = collection.delete_one({"device_id": device_id})
            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"Error deleting workflow: {e}")
            raise

    @staticmethod
    async def cleanup_old_workflows(days: int = 90) -> int:
        """
        Cleanup old completed/failed workflows.

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted workflows
        """
        try:
            collection = CSRWorkflowService._get_collection()

            cutoff = datetime.utcnow() - timedelta(days=days)

            result = collection.delete_many({
                "workflow_status": {"$in": [
                    WorkflowStatus.COMPLETED.value,
                    WorkflowStatus.FAILED.value,
                    WorkflowStatus.EXPIRED.value,
                    WorkflowStatus.CANCELLED.value
                ]},
                "updated_at": {"$lt": cutoff}
            })

            logger.info(f"Cleaned up {result.deleted_count} old CSR workflows")
            return result.deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up workflows: {e}")
            raise

    @staticmethod
    def validate_step_transition(current_step: str, next_step: str) -> bool:
        """
        Validate if a step transition is allowed.

        Args:
            current_step: Current step name
            next_step: Next step name

        Returns:
            True if transition is valid
        """
        try:
            current_idx = WORKFLOW_STEP_ORDER.index(WorkflowStep(current_step))
            next_idx = WORKFLOW_STEP_ORDER.index(WorkflowStep(next_step))
            # Allow same step (status change) or next step only
            return next_idx == current_idx or next_idx == current_idx + 1
        except (ValueError, IndexError):
            return False


# Create service instance
csr_workflow_service = CSRWorkflowService()
