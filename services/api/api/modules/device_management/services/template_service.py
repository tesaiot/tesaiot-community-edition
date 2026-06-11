# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid
from jsonschema import validate, ValidationError as JsonSchemaValidationError, Draft7Validator
import copy

from ..models.template_models import (
    DeviceTemplate, TemplateVersion, TemplateInstance,
    TemplateStatus, TemplateCategory, ValidationRule,
    INDUSTRY_STANDARD_TEMPLATES
)
from ..models.device_models import Device
from ..models.device_dtos import DeviceCreateDTO
from ..repositories.template_repository import TemplateRepository
from ..interfaces.device_interfaces import IDeviceService
from ....core.exceptions import ValidationError, ResourceNotFoundError, ConflictError

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing device templates"""
    
    def __init__(self, template_repository: TemplateRepository, device_service: Optional[IDeviceService] = None):
        self.repository = template_repository
        self.device_service = device_service
        
    async def initialize(self):
        """Initialize the template service"""
        await self.repository.initialize_indexes()
        logger.info("Template service initialized")
    
    # Template CRUD operations
    async def create_template(
        self,
        template_data: Dict[str, Any],
        org_id: str,
        user_id: Optional[str] = None
    ) -> DeviceTemplate:
        """Create a new device template"""
        try:
            # Generate template ID if not provided
            if "template_id" not in template_data:
                template_data["template_id"] = f"tpl_{uuid.uuid4().hex[:12]}"
            
            # Set organization and user
            template_data["org_id"] = org_id
            template_data["created_by"] = user_id
            template_data["updated_by"] = user_id
            
            # Validate template data
            await self._validate_template_data(template_data)
            
            # Create template object
            template = DeviceTemplate.from_dict(template_data)
            
            # Validate against parent template if specified
            if template.parent_template_id:
                await self._validate_inheritance(template)
            
            # Validate composed templates if specified
            if template.composed_template_ids:
                await self._validate_composition(template)
            
            # Create template
            created_template = await self.repository.create_template(template)
            
            # Create initial version
            await self._create_template_version(created_template, ["Initial version"], user_id)
            
            logger.info(f"Template created: {created_template.template_id} for org {org_id}")
            return created_template
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise
    
    async def get_template(self, template_id: str, org_id: str) -> DeviceTemplate:
        """Get a template by ID"""
        template = await self.repository.get_template(template_id, org_id)
        if not template:
            raise ResourceNotFoundError(f"Template not found: {template_id}")
        return template
    
    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any],
        org_id: str,
        user_id: Optional[str] = None
    ) -> DeviceTemplate:
        """Update an existing template"""
        try:
            # Get existing template
            template = await self.get_template(template_id, org_id)
            
            # Check if template is active
            if template.status != TemplateStatus.ACTIVE and template.status != TemplateStatus.DRAFT:
                raise ValidationError(f"Cannot update template in {template.status.value} status")
            
            # Track changes for versioning
            changes = []
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(template, key) and getattr(template, key) != value:
                    changes.append(f"Updated {key}")
                    setattr(template, key, value)
            
            # Update metadata
            template.updated_at = datetime.utcnow()
            template.updated_by = user_id
            
            # Validate updated template
            await self._validate_template_data(template.to_dict())
            
            # Save changes
            updated_template = await self.repository.update_template(template)
            
            # Create new version if significant changes
            if changes:
                # Increment version
                version_parts = template.version.split(".")
                version_parts[2] = str(int(version_parts[2]) + 1)  # Increment patch version
                template.version = ".".join(version_parts)
                
                await self._create_template_version(updated_template, changes, user_id)
            
            logger.info(f"Template updated: {template_id}")
            return updated_template
            
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            raise
    
    async def delete_template(self, template_id: str, org_id: str) -> bool:
        """Delete (archive) a template"""
        try:
            # Check if template has active instances
            instances = await self.repository.get_template_instances(template_id, org_id)
            if instances:
                raise ConflictError(f"Cannot delete template with {len(instances)} active instances")
            
            # Check if template has child templates
            children = await self.repository.get_child_templates(template_id, org_id)
            if children:
                raise ConflictError(f"Cannot delete template with {len(children)} child templates")
            
            # Archive the template
            result = await self.repository.delete_template(template_id, org_id)
            
            if result:
                logger.info(f"Template archived: {template_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            raise
    
    async def list_templates(
        self,
        org_id: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[DeviceTemplate], int]:
        """List templates with pagination"""
        skip = (page - 1) * page_size
        return await self.repository.list_templates(
            org_id=org_id,
            filters=filters,
            skip=skip,
            limit=page_size
        )
    
    # Template instantiation
    async def instantiate_template(
        self,
        template_id: str,
        device_data: Dict[str, Any],
        org_id: str,
        user_id: Optional[str] = None
    ) -> Device:
        """Create a device from a template"""
        try:
            # Get template
            template = await self.get_template(template_id, org_id)
            
            # Check template status
            if template.status != TemplateStatus.ACTIVE:
                raise ValidationError(f"Template is not active: {template.status.value}")
            
            # Merge template defaults with provided data
            merged_data = self._merge_template_data(template, device_data)
            
            # Validate against template schema
            await self._validate_against_template(merged_data, template)
            
            # Create device using device service
            if not self.device_service:
                raise ValidationError("Device service not available")
            
            # Create device DTO
            device_dto = DeviceCreateDTO(
                name=merged_data["name"],
                device_type=template.device_type,
                protocol=merged_data.get("protocol", template.default_protocol or template.supported_protocols[0]),
                metadata=merged_data.get("metadata", {}),
                tags=merged_data.get("tags", []),
                mac_address=merged_data.get("mac_address"),
                ip_address=merged_data.get("ip_address"),
                firmware_version=merged_data.get("firmware_version"),
                hardware_version=merged_data.get("hardware_version"),
                serial_number=merged_data.get("serial_number"),
                location=merged_data.get("location")
            )
            
            # Register device
            device_dict = await self.device_service.register_device(
                device_data=device_dto.to_dict(),
                org_id=org_id,
                user={"user_id": user_id} if user_id else None
            )
            
            # Create template instance record
            instance = TemplateInstance(
                instance_id=f"tpl_inst_{uuid.uuid4().hex[:12]}",
                device_id=device_dict["device_id"],
                template_id=template_id,
                template_version=template.version,
                org_id=org_id,
                config_overrides=device_data.get("config", {}),
                metadata_overrides=device_data.get("metadata", {}),
                instantiated_by=user_id
            )
            
            await self.repository.create_instance(instance)
            
            logger.info(f"Device {device_dict['device_id']} created from template {template_id}")
            return Device.from_dict(device_dict)
            
        except Exception as e:
            logger.error(f"Error instantiating template: {e}")
            raise
    
    # Template validation
    async def validate_template_data(self, template_id: str, data: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Validate data against a template"""
        try:
            template = await self.get_template(template_id, org_id)
            await self._validate_against_template(data, template)
            
            return {
                "valid": True,
                "errors": []
            }
            
        except ValidationError as e:
            return {
                "valid": False,
                "errors": [str(e)]
            }
        except JsonSchemaValidationError as e:
            return {
                "valid": False,
                "errors": [f"Schema validation error: {e.message}"]
            }
    
    # Template inheritance and composition
    async def inherit_template(
        self,
        parent_template_id: str,
        child_template_data: Dict[str, Any],
        org_id: str,
        user_id: Optional[str] = None
    ) -> DeviceTemplate:
        """Create a new template that inherits from a parent"""
        try:
            # Get parent template
            parent = await self.get_template(parent_template_id, org_id)
            
            # Check if parent allows inheritance
            if not parent.allow_inheritance:
                raise ValidationError(f"Template {parent_template_id} does not allow inheritance")
            
            # Merge parent data with child data
            merged_data = self._inherit_template_data(parent, child_template_data)
            merged_data["parent_template_id"] = parent_template_id
            
            # Create new template
            return await self.create_template(merged_data, org_id, user_id)
            
        except Exception as e:
            logger.error(f"Error inheriting template: {e}")
            raise
    
    async def compose_templates(
        self,
        template_ids: List[str],
        composite_data: Dict[str, Any],
        org_id: str,
        user_id: Optional[str] = None
    ) -> DeviceTemplate:
        """Create a new template by composing multiple templates"""
        try:
            # Get all templates
            templates = []
            for tid in template_ids:
                template = await self.get_template(tid, org_id)
                templates.append(template)
            
            # Merge template data
            merged_data = self._compose_template_data(templates, composite_data)
            merged_data["composed_template_ids"] = template_ids
            
            # Create new template
            return await self.create_template(merged_data, org_id, user_id)
            
        except Exception as e:
            logger.error(f"Error composing templates: {e}")
            raise
    
    # Template versioning
    async def get_template_versions(self, template_id: str, org_id: str) -> List[TemplateVersion]:
        """Get all versions of a template"""
        return await self.repository.get_template_versions(template_id, org_id)
    
    async def get_template_version(
        self,
        template_id: str,
        version_number: str,
        org_id: str
    ) -> Optional[TemplateVersion]:
        """Get a specific version of a template"""
        return await self.repository.get_template_version(template_id, version_number, org_id)
    
    async def revert_to_version(
        self,
        template_id: str,
        version_number: str,
        org_id: str,
        user_id: Optional[str] = None
    ) -> DeviceTemplate:
        """Revert a template to a previous version"""
        try:
            # Get the version
            version = await self.get_template_version(template_id, version_number, org_id)
            if not version:
                raise ResourceNotFoundError(f"Version {version_number} not found for template {template_id}")
            
            # Get current template
            current = await self.get_template(template_id, org_id)
            
            # Update template with version data
            updates = version.template_snapshot
            updates.pop("template_id", None)  # Don't update ID
            updates.pop("org_id", None)  # Don't update org
            
            # Update template
            return await self.update_template(template_id, updates, org_id, user_id)
            
        except Exception as e:
            logger.error(f"Error reverting template to version: {e}")
            raise
    
    # Industry standard templates
    async def create_industry_standard_template(
        self,
        standard_type: str,
        org_id: str,
        user_id: Optional[str] = None,
        customizations: Optional[Dict[str, Any]] = None
    ) -> DeviceTemplate:
        """Create a template from industry standards"""
        try:
            if standard_type not in INDUSTRY_STANDARD_TEMPLATES:
                raise ValidationError(f"Unknown standard template type: {standard_type}")
            
            # Get standard template data
            template_data = copy.deepcopy(INDUSTRY_STANDARD_TEMPLATES[standard_type])
            
            # Apply customizations
            if customizations:
                template_data.update(customizations)
            
            # Create template
            return await self.create_template(template_data, org_id, user_id)
            
        except Exception as e:
            logger.error(f"Error creating industry standard template: {e}")
            raise
    
    async def list_industry_standards(self) -> List[Dict[str, Any]]:
        """List available industry standard templates"""
        standards = []
        for key, value in INDUSTRY_STANDARD_TEMPLATES.items():
            standards.append({
                "key": key,
                "name": value["name"],
                "description": value["description"],
                "category": value["category"].value,
                "device_type": value["device_type"].value,
                "standards_compliance": value.get("standards_compliance", [])
            })
        return standards
    
    # Template statistics
    async def get_template_statistics(self, org_id: str) -> Dict[str, Any]:
        """Get template usage statistics"""
        return await self.repository.get_template_statistics(org_id)
    
    # Helper methods
    async def _validate_template_data(self, template_data: Dict[str, Any]) -> None:
        """Validate template data"""
        # Required fields
        required_fields = ["name", "description", "category", "device_type"]
        for field in required_fields:
            if field not in template_data:
                raise ValidationError(f"Required field missing: {field}")
        
        # Validate enums
        try:
            TemplateCategory(template_data["category"])
        except ValueError:
            raise ValidationError(f"Invalid category: {template_data['category']}")
        
        # Validate JSON schema if provided
        if "validation_schema" in template_data and template_data["validation_schema"]:
            try:
                Draft7Validator.check_schema(template_data["validation_schema"])
            except JsonSchemaValidationError as e:
                raise ValidationError(f"Invalid JSON schema: {e.message}")
    
    async def _validate_against_template(self, data: Dict[str, Any], template: DeviceTemplate) -> None:
        """Validate data against template schema and rules"""
        # Validate against JSON schema
        if template.validation_schema:
            try:
                validate(instance=data, schema=template.validation_schema)
            except JsonSchemaValidationError as e:
                raise ValidationError(f"Schema validation failed: {e.message}")
        
        # Validate against custom rules
        for rule in template.validation_rules:
            await self._validate_rule(data, rule)
    
    async def _validate_rule(self, data: Dict[str, Any], rule: ValidationRule) -> None:
        """Validate a single rule"""
        # Get value from data using field path
        value = self._get_nested_value(data, rule.field_path)
        
        if rule.rule_type == "required" and value is None:
            error_msg = rule.error_message or f"Field {rule.field_path} is required"
            raise ValidationError(error_msg)
        
        if value is not None:
            if rule.rule_type == "type":
                if not isinstance(value, rule.value):
                    error_msg = rule.error_message or f"Field {rule.field_path} must be of type {rule.value}"
                    raise ValidationError(error_msg)
            
            elif rule.rule_type == "range":
                if "min" in rule.value and value < rule.value["min"]:
                    error_msg = rule.error_message or f"Field {rule.field_path} must be >= {rule.value['min']}"
                    raise ValidationError(error_msg)
                if "max" in rule.value and value > rule.value["max"]:
                    error_msg = rule.error_message or f"Field {rule.field_path} must be <= {rule.value['max']}"
                    raise ValidationError(error_msg)
            
            elif rule.rule_type == "enum":
                if value not in rule.value:
                    error_msg = rule.error_message or f"Field {rule.field_path} must be one of {rule.value}"
                    raise ValidationError(error_msg)
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation path"""
        parts = path.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value
    
    def _merge_template_data(self, template: DeviceTemplate, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge template defaults with device data"""
        merged = {
            "name": device_data.get("name", f"{template.name}_instance"),
            "device_type": template.device_type.value,
            "protocol": device_data.get("protocol", template.default_protocol.value if template.default_protocol else template.supported_protocols[0].value),
            "metadata": {},
            "tags": template.default_tags.copy()
        }
        
        # Merge metadata
        if template.metadata_template and template.metadata_template.defaults:
            merged["metadata"] = copy.deepcopy(template.metadata_template.defaults)
        
        if "metadata" in device_data:
            merged["metadata"].update(device_data["metadata"])
        
        # Merge config
        if template.default_config:
            merged["config"] = copy.deepcopy(template.default_config)
            if "config" in device_data:
                merged["config"].update(device_data["config"])
        
        # Add other device data
        for key, value in device_data.items():
            if key not in ["metadata", "config", "tags"]:
                merged[key] = value
        
        # Merge tags
        if "tags" in device_data:
            merged["tags"].extend(device_data["tags"])
            merged["tags"] = list(set(merged["tags"]))  # Remove duplicates
        
        return merged
    
    def _inherit_template_data(self, parent: DeviceTemplate, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge parent template data with child overrides"""
        # Start with parent data
        merged = parent.to_dict()
        
        # Update with child data
        for key, value in child_data.items():
            if key in ["template_id", "org_id", "created_at", "created_by"]:
                continue  # Skip these fields
            
            if key == "validation_rules" and value:
                # Append child rules to parent rules
                parent_rules = merged.get("validation_rules", [])
                merged["validation_rules"] = parent_rules + value
            elif key == "default_tags" and value:
                # Merge tags
                parent_tags = merged.get("default_tags", [])
                merged["default_tags"] = list(set(parent_tags + value))
            else:
                merged[key] = value
        
        return merged
    
    def _compose_template_data(self, templates: List[DeviceTemplate], composite_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compose multiple templates into one"""
        merged = composite_data.copy()
        
        # Merge each template
        for template in templates:
            template_dict = template.to_dict()
            
            # Merge configs
            if "default_config" not in merged:
                merged["default_config"] = {}
            merged["default_config"].update(template_dict.get("default_config", {}))
            
            # Merge metadata schemas
            if "metadata_template" not in merged:
                merged["metadata_template"] = {"schema": {}, "defaults": {}}
            
            # Merge validation rules
            if "validation_rules" not in merged:
                merged["validation_rules"] = []
            merged["validation_rules"].extend(template_dict.get("validation_rules", []))
            
            # Merge tags
            if "default_tags" not in merged:
                merged["default_tags"] = []
            merged["default_tags"].extend(template_dict.get("default_tags", []))
        
        # Remove duplicates from lists
        if "default_tags" in merged:
            merged["default_tags"] = list(set(merged["default_tags"]))
        
        return merged
    
    async def _validate_inheritance(self, template: DeviceTemplate) -> None:
        """Validate template inheritance"""
        parent = await self.repository.get_template(template.parent_template_id, template.org_id)
        if not parent:
            raise ValidationError(f"Parent template not found: {template.parent_template_id}")
        
        if not parent.allow_inheritance:
            raise ValidationError(f"Parent template does not allow inheritance")
    
    async def _validate_composition(self, template: DeviceTemplate) -> None:
        """Validate template composition"""
        for template_id in template.composed_template_ids:
            composed = await self.repository.get_template(template_id, template.org_id)
            if not composed:
                raise ValidationError(f"Composed template not found: {template_id}")
    
    async def _create_template_version(
        self,
        template: DeviceTemplate,
        changes: List[str],
        user_id: Optional[str] = None
    ) -> TemplateVersion:
        """Create a new template version"""
        version = TemplateVersion(
            version_id=f"tpl_ver_{uuid.uuid4().hex[:12]}",
            template_id=template.template_id,
            org_id=template.org_id,
            version_number=template.version,
            changes=changes,
            template_snapshot=template.to_dict(),
            created_by=user_id
        )
        
        return await self.repository.create_version(version)