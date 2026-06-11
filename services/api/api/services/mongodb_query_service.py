# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - MongoDB Query Service for AI
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: MongoDB Query Service
Purpose: Enable AI to perform dynamic MongoDB queries
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from bson import ObjectId
import re
import os

from ..core.rbac import RBAC

logger = logging.getLogger(__name__)

class MongoDBQueryService:
    """Service to handle dynamic MongoDB queries for AI analysis."""
    
    def __init__(self, db, user_context=None):
        self.db = db
        self.user_context = user_context  # Contains user_id, organization_id, role
        self.allowed_collections = ['devices', 'telemetry', 'organizations', 'users', 'certificates']
        
        # Security: Define sensitive fields that should never be returned
        self.sensitive_fields = {
            'users': ['password', 'password_hash', 'api_key', 'secret_key', 'private_key', 'access_token', 'refresh_token'],
            'devices': ['private_key', 'secret', 'api_credentials', 'auth_token'],
            'certificates': ['private_key', 'key_material'],
            'organizations': ['api_key', 'secret_key', 'billing_info', 'payment_details'],
            'telemetry': ['auth_token', 'api_key']
        }
        
        # Security: Define fields that can be queried but not returned
        self.restricted_query_fields = ['password', 'password_hash', 'private_key', 'secret', 'api_key', 'auth_token']
        
        logger.info("MongoDB Query Service initialized with security filters")
    
    def filter_by_organization(self, filter_dict: Dict[str, Any], collection_name: str) -> Dict[str, Any]:
        """
        Add organization filter to query unless platform admin.
        
        Args:
            filter_dict: Base MongoDB query filter
            collection_name: Name of the collection being queried
            
        Returns:
            Filter with organization restrictions applied
        """
        if not self.user_context or RBAC.is_platform_admin(self.user_context):
            return filter_dict
            
        org_id = self.user_context.get('organization_id')
        if not org_id:
            return filter_dict
            
        # Apply org filtering for collections that have organization data
        if collection_name == 'devices':
            filter_dict['organization_id'] = org_id
        elif collection_name == 'users':
            filter_dict['organization_id'] = org_id
        elif collection_name == 'telemetry':
            # For telemetry, filter by devices in the organization
            org_devices = list(self.db.devices.find({'organization_id': org_id}, {'device_id': 1}))
            device_ids = [d['device_id'] for d in org_devices]
            filter_dict['device_id'] = {'$in': device_ids}
        elif collection_name == 'organizations':
            # Non-super admins can only see their own organization
            filter_dict['_id'] = ObjectId(org_id) if ObjectId.is_valid(org_id) else org_id
        elif collection_name == 'certificates':
            # Filter certificates by organization via device ownership
            org_devices = list(self.db.devices.find({'organization_id': org_id}, {'device_id': 1}))
            device_ids = [d['device_id'] for d in org_devices]
            filter_dict['device_id'] = {'$in': device_ids}
            
        return filter_dict
    
    def parse_natural_language_query(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into MongoDB query.
        
        Examples:
        - "devices with temperature > 80" → {"collection": "telemetry", "filter": {"temperature": {"$gt": 80}}}
        - "inactive devices in last 7 days" → {"collection": "devices", "filter": {"last_seen": {"$lt": <7 days ago>}}}
        - "which devices in BDH organization are Gateway?" → {"collection": "devices", "filter": {"organization": "BDH Corporation", "type": {"$regex": "gateway", "$options": "i"}}}
        """
        query_lower = query.lower()
        
        # Determine collection
        collection = self._detect_collection(query_lower)
        
        # Build filter based on patterns
        filter_dict = {}
        
        # Store conditions that might need to be combined
        org_condition = None
        type_condition = None
        
        # Temperature queries
        if "temperature" in query_lower:
            temp_match = re.search(r'temperature\s*[><]=?\s*(\d+)', query_lower)
            if temp_match:
                temp_value = float(temp_match.group(1))
                if ">" in query_lower:
                    filter_dict["temperature"] = {"$gt": temp_value}
                elif "<" in query_lower:
                    filter_dict["temperature"] = {"$lt": temp_value}
        
        # Time-based queries
        if "last" in query_lower and "days" in query_lower:
            days_match = re.search(r'last\s*(\d+)\s*days?', query_lower)
            if days_match:
                days = int(days_match.group(1))
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                if "inactive" in query_lower or "offline" in query_lower:
                    filter_dict["last_seen"] = {"$lt": cutoff_date}
                else:
                    filter_dict["timestamp"] = {"$gte": cutoff_date}
        
        # Status queries
        if "active" in query_lower and "inactive" not in query_lower:
            filter_dict["status"] = "active"
        elif "inactive" in query_lower or "offline" in query_lower:
            filter_dict["status"] = {"$in": ["inactive", "offline"]}
        
        # Certificate queries
        if "certificate" in query_lower:
            if "expired" in query_lower:
                filter_dict["certificate_expires_at"] = {"$lt": datetime.utcnow()}
            elif "expiring" in query_lower:
                # Expiring in next 30 days
                filter_dict["certificate_expires_at"] = {
                    "$lt": datetime.utcnow() + timedelta(days=30),
                    "$gt": datetime.utcnow()
                }
        
        # Algorithm queries
        if "ecc" in query_lower or "rsa" in query_lower:
            if "ecc" in query_lower:
                filter_dict["$or"] = [
                    {"certificate_info.key_algorithm": {"$regex": "ECC", "$options": "i"}},
                    {"metadata.certificate_algorithm": {"$regex": "ECC", "$options": "i"}}
                ]
            elif "rsa" in query_lower:
                filter_dict["$or"] = [
                    {"certificate_info.key_algorithm": {"$regex": "RSA", "$options": "i"}},
                    {"metadata.certificate_algorithm": {"$regex": "RSA", "$options": "i"}}
                ]
        
        # Organization queries
        if any(word in query_lower for word in ["organization", "org ", "bdh", "tesa", "smart factory"]):
            # Try to extract organization name
            org_patterns = [
                r'in\s+(\w+(?:\s+\w+)*?)\s+(?:organization|org)',
                r'(?:organization|org)\s+["\']?([^"\']+)["\']?',
                r'(bdh|tesa|smart\s+factory)',
            ]
            
            org_name = None
            for pattern in org_patterns:
                match = re.search(pattern, query_lower, re.IGNORECASE)
                if match:
                    org_name = match.group(1).strip()
                    break
            
            if org_name:
                # Map common abbreviations to full names
                org_mapping = {
                    'bdh': 'BDH Corporation',
                    'tesa': 'Thai Embedded Systems Association',
                    'smart factory': 'Smart Factory Thailand',
                    'cu': 'Chulalongkorn University',
                    'bangkok hospital': 'Bangkok Hospital Group',
                    'siriraj': 'Siriraj Hospital'
                }
                
                # Check if we have a mapping
                org_full_name = org_mapping.get(org_name.lower(), org_name)
                
                # For exact matches, use the full organization name
                if org_full_name in ['BDH Corporation', 'Thai Embedded Systems Association', 
                                     'Smart Factory Thailand', 'Chulalongkorn University',
                                     'Bangkok Hospital Group', 'Siriraj Hospital',
                                     'National Telemedicine Center', 'AgriTech Solutions Demo']:
                    org_condition = {"organization": org_full_name}
                else:
                    # For partial matches, try regex (though it seems to have issues)
                    org_condition = {"$or": [
                        {"organization": {"$regex": org_name, "$options": "i"}},
                        {"organization_name": {"$regex": org_name, "$options": "i"}}
                    ]}
        
        # Device type queries
        if any(word in query_lower for word in ["gateway", "sensor", "actuator", "controller", "medical", "monitor"]):
            # Handle multiple type variations
            if "gateway" in query_lower:
                # Match both 'gateway' and 'edge_gateway'
                type_condition = {"type": {"$regex": "gateway", "$options": "i"}}
            elif "sensor" in query_lower:
                # Match 'sensor', 'iot_sensor', etc.
                type_condition = {"type": {"$regex": "sensor", "$options": "i"}}
            elif "actuator" in query_lower:
                type_condition = {"type": {"$regex": "actuator", "$options": "i"}}
            elif "controller" in query_lower:
                type_condition = {"type": "controller"}
            elif "medical" in query_lower:
                type_condition = {"type": {"$regex": "medical", "$options": "i"}}
        
        # Combine organization and type conditions if both exist
        if org_condition and type_condition:
            # Both organization and type filters
            filter_dict.update(org_condition)
            filter_dict.update(type_condition)
        elif org_condition:
            filter_dict.update(org_condition)
        elif type_condition:
            filter_dict.update(type_condition)
        
        return {
            "collection": collection,
            "filter": filter_dict,
            "limit": 100  # Default limit
        }
    
    def _detect_collection(self, query_lower: str) -> str:
        """Detect which collection to query based on keywords."""
        # More flexible collection detection
        # Check for explicit collection mentions first
        for collection in self.allowed_collections:
            if collection in query_lower:
                return collection
        
        # Check for device-related keywords (most common queries)
        device_keywords = ["device", "gateway", "sensor", "controller", "actuator", "iot", 
                          "equipment", "hardware", "unit", "node", "endpoint", "thing"]
        if any(word in query_lower for word in device_keywords):
            return "devices"
        
        # Check for telemetry/data keywords
        telemetry_keywords = ["temperature", "humidity", "telemetry", "sensor data", "reading",
                             "measurement", "metric", "data", "value", "signal", "status"]
        if any(word in query_lower for word in telemetry_keywords):
            # If asking about devices with telemetry, still use devices
            if any(word in query_lower for word in ["device", "which", "name", "list"]):
                return "devices"
            return "telemetry"
        
        # Check for certificate keywords
        cert_keywords = ["certificate", "cert", "expir", "algorithm", "ssl", "tls", "pki", "x509"]
        if any(word in query_lower for word in cert_keywords):
            return "devices"  # Certificates are part of device records
        
        # Check for organization keywords
        org_keywords = ["organization", "org", "company", "corporation", "business", "entity", "tenant"]
        if any(word in query_lower for word in org_keywords):
            # If also has device keywords, prioritize devices
            if not any(word in query_lower for word in device_keywords):
                return "organizations"
        
        # Check for user keywords
        user_keywords = ["user", "admin", "operator", "person", "account", "member", "staff"]
        if any(word in query_lower for word in user_keywords):
            return "users"
        
        # Default to devices as it's the most common query
        return "devices"
    
    def execute_query(self, parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the parsed MongoDB query safely."""
        collection_name = parsed_query.get("collection", "devices")
        
        # Security check
        if collection_name not in self.allowed_collections:
            raise ValueError(f"Collection {collection_name} not allowed for queries")
        
        collection = getattr(self.db, collection_name)
        filter_dict = parsed_query.get("filter", {})
        
        # Apply organization filtering using the dedicated method
        filter_dict = self.filter_by_organization(filter_dict, collection_name)
        
        limit = min(parsed_query.get("limit", 100), 1000)  # Max 1000 results
        
        logger.info(f"Executing query on collection '{collection_name}' with filter: {filter_dict}")
        logger.info(f"Database name: {self.db.name}")
        
        try:
            # Execute query
            results = list(collection.find(filter_dict).limit(limit))
            logger.info(f"Query returned {len(results)} results")
            
            # Clean up results (remove sensitive data)
            cleaned_results = []
            for doc in results:
                cleaned_doc = self._clean_document(doc, collection_name)
                cleaned_results.append(cleaned_doc)
            
            return cleaned_results
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def _clean_document(self, doc: Dict[str, Any], collection_name: str = None) -> Dict[str, Any]:
        """Remove sensitive information from documents based on collection."""
        # Convert ObjectId to string
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        
        # Remove sensitive fields based on collection
        if collection_name and collection_name in self.sensitive_fields:
            for field in self.sensitive_fields[collection_name]:
                doc.pop(field, None)
        
        # Also remove common sensitive fields
        common_sensitive = ["private_key", "password", "password_hash", "api_key", "secret", 
                           "access_token", "refresh_token", "auth_token", "credentials"]
        for field in common_sensitive:
            doc.pop(field, None)
        
        # Handle nested ObjectIds and dates
        for key, value in list(doc.items()):
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, datetime):
                doc[key] = value.isoformat()
            elif isinstance(value, dict):
                # Recursively clean nested documents
                doc[key] = self._clean_document(value)
        
        return doc
    
    def _get_all_keys(self, d: Dict[str, Any], parent_key: str = '') -> List[str]:
        """Extract all keys from a nested dictionary."""
        keys = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            keys.append(new_key)
            if isinstance(v, dict) and not k.startswith('$'):
                keys.extend(self._get_all_keys(v, new_key))
        return keys
    
    def execute_openai_generated_query(self, query_description: str) -> Dict[str, Any]:
        """
        Have OpenAI generate a MongoDB query based on natural language description,
        execute it, and then have OpenAI summarize the results.
        """
        try:
            # Security check: Prevent queries for sensitive data
            query_lower = query_description.lower()
            sensitive_keywords = ['password', 'secret', 'private key', 'api key', 'token', 
                                'credentials', 'auth', 'billing', 'payment', 'credit card']
            
            for keyword in sensitive_keywords:
                if keyword in query_lower:
                    return {
                        "query_description": query_description,
                        "generated_filter": {},
                        "total_results": 0,
                        "summary": f"Access denied: Queries for sensitive information ({keyword}) are not allowed for security compliance.",
                        "sample_results": []
                    }
            
            import openai
            openai.api_key = os.environ.get('OPENAI_API_KEY')
            
            if not openai.api_key:
                raise ValueError("OpenAI API key not configured")
            
            # Step 1: Have OpenAI generate the MongoDB query
            system_prompt = """You are a MongoDB query expert for the TESA IoT Platform.
Generate MongoDB queries based on user requests. Be FLEXIBLE with synonyms and variations.

The database has these collections:

1. devices: IoT devices, equipment, hardware, units, nodes, endpoints, things
   - Fields: device_id, name, organization, organization_id, type, status, model, location, metadata, certificate_info, certificate_algorithm, created_at, updated_at
   - Types: 'gateway' (router, hub), 'sensor' (detector, probe), 'controller' (actuator, PLC), 'edge_gateway', 'iot_sensor', 'medical_device'
   - Status: 'active' (online, connected), 'inactive' (offline, disconnected), 'maintenance'
   
2. telemetry: Time-series sensor data, readings, measurements, metrics
   - Fields: device_id, timestamp, temperature, humidity, pressure, voltage, current, data, metadata
   
3. organizations: Company, corporation, business, entity, tenant records
   - Fields: _id, name, type, description, contact, address, parent_organization_id, created_at, updated_at
   
4. users: User accounts, people, staff, operators
   - Fields: _id, email, name, role, organization_id, status, created_at, last_login
   - Roles: 'super_admin', 'organization_admin', 'admin', 'operator', 'viewer', 'user'
   
5. certificates: Certificate management, SSL, TLS, PKI
   - Fields: _id, device_id, serial_number, subject, issuer, valid_from, valid_to, algorithm, status

Organization name variations (use the FULL NAME in filters):
- 'BDH', 'bdh', 'BDH org' → 'BDH Corporation'
- 'TESA', 'tesa' → 'Thai Embedded Systems Association'
- 'Smart Factory', 'factory' → 'Smart Factory Thailand'
- 'Chula', 'CU' → 'Chulalongkorn University'
- 'Bangkok Hospital' → 'Bangkok Hospital Group'
- 'Siriraj' → 'Siriraj Hospital'

BE FLEXIBLE: Understand synonyms and variations. Examples:
- "equipment" = device
- "unit" = device  
- "router" = gateway
- "probe" = sensor
- "inactive" = offline
- "company" = organization

SECURITY RESTRICTIONS:
- NEVER query for passwords, private keys, api keys, secrets, or auth tokens
- NEVER include sensitive fields in the filter
- These fields will be automatically removed from results: password, password_hash, private_key, api_key, secret, auth_token

IMPORTANT: 
- Return a JSON object with TWO fields: "collection" and "filter"
- The "collection" field specifies which collection to query
- The "filter" field contains the MongoDB query filter
- Use EXACT match for standardized values (types, organizations, roles)
- Do NOT include any sensitive fields in the filter

Example response format:
{
  "collection": "devices",
  "filter": {"organization": "BDH Corporation", "type": "gateway"}
}"""

            query_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate a MongoDB query for: {query_description}"}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            query_text = query_response.choices[0].message.content.strip()
            logger.info(f"OpenAI generated query: {query_text}")
            
            # Parse the generated query
            try:
                # Try to parse as JSON first
                import json
                query_obj = json.loads(query_text)
                
                # Check if it has the new format with collection and filter
                if isinstance(query_obj, dict) and "collection" in query_obj and "filter" in query_obj:
                    collection_name = query_obj["collection"]
                    mongo_filter = query_obj["filter"]
                else:
                    # Old format - just the filter
                    mongo_filter = query_obj
                    collection_name = self._detect_collection(query_description.lower())
            except (json.JSONDecodeError, ValueError, TypeError):
                try:
                    # SECURITY: parse strictly as JSON (no Python-literal
                    # evaluation of model-derived text). Normalize single
                    # quotes which JSON does not accept, then json.loads.
                    normalized = query_text.replace("'", '"')
                    parsed = json.loads(normalized)
                    if not isinstance(parsed, dict):
                        raise ValueError("Generated query is not a JSON object")
                    mongo_filter = parsed
                    collection_name = self._detect_collection(query_description.lower())
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Try to extract dictionary from response
                    import re
                    dict_match = re.search(r'\{.*\}', query_text, re.DOTALL)
                    if dict_match:
                        try:
                            query_obj = json.loads(dict_match.group(0))
                            if "collection" in query_obj and "filter" in query_obj:
                                collection_name = query_obj["collection"]
                                mongo_filter = query_obj["filter"]
                            else:
                                mongo_filter = query_obj
                                collection_name = self._detect_collection(query_description.lower())
                        except:
                            mongo_filter = {}
                            collection_name = "devices"
                    else:
                        mongo_filter = {}
                        collection_name = "devices"
            
            # Validate collection name
            if collection_name not in self.allowed_collections:
                logger.warning(f"Invalid collection '{collection_name}' requested, defaulting to 'devices'")
                collection_name = "devices"
            
            # Security: Check if filter contains sensitive fields
            if mongo_filter:
                filter_keys = self._get_all_keys(mongo_filter)
                for key in filter_keys:
                    if any(restricted in key.lower() for restricted in self.restricted_query_fields):
                        return {
                            "query_description": query_description,
                            "generated_filter": mongo_filter,
                            "total_results": 0,
                            "summary": f"Access denied: Querying by sensitive field '{key}' is not allowed for security compliance.",
                            "sample_results": []
                        }
            
            # Step 2: Execute the query
            logger.info(f"Executing query on collection '{collection_name}' with filter: {mongo_filter}")
            results = self.execute_query({
                "collection": collection_name,
                "filter": mongo_filter,
                "limit": 100
            })
            
            # Step 3: Have OpenAI summarize the results
            if results:
                # Limit data sent to OpenAI to avoid token limits
                # Only send essential fields for each result
                limited_results = []
                for r in results[:10]:  # Max 10 results
                    limited_result = {}
                    # Include only key fields based on collection
                    if collection_name == "devices":
                        limited_result = {
                            "name": r.get("name", "Unknown"),
                            "device_id": r.get("device_id", "N/A"),
                            "type": r.get("type", "N/A"),
                            "status": r.get("status", "N/A"),
                            "organization": r.get("organization", "N/A")
                        }
                    elif collection_name == "users":
                        limited_result = {
                            "name": r.get("name", "Unknown"),
                            "email": r.get("email", "N/A"),
                            "role": r.get("role", "N/A"),
                            "organization_id": r.get("organization_id", "N/A")
                        }
                    elif collection_name == "organizations":
                        limited_result = {
                            "name": r.get("name", "Unknown"),
                            "type": r.get("type", "N/A"),
                            "description": r.get("description", "N/A")[:100]  # Limit description length
                        }
                    else:
                        # For other collections, include basic fields
                        limited_result = {k: v for k, v in r.items() if k in ["_id", "name", "status", "type", "timestamp"]}
                    
                    limited_results.append(limited_result)
                
                summary_prompt = f"""Summarize these query results for the user who asked: "{query_description}"
                
Collection queried: {collection_name}
Total results found: {len(results)}
Sample results (showing up to 10):
{json.dumps(limited_results, indent=2)}

Provide a clear, concise summary focusing on what the user asked for."""

                summary_response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an AI assistant helping users understand IoT device data."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                summary = summary_response.choices[0].message.content
            else:
                # When no results, provide a meaningful response based on the query
                no_results_prompt = f"""The user asked: "{query_description}"
                
The query was executed on collection '{collection_name}' with filter: {json.dumps(mongo_filter)}
But returned 0 results.

Please provide a helpful response explaining:
1. What was searched for
2. Why there might be no results
3. Suggestions for what the user could try next

Context about the TESA IoT Platform:
- Collections available: devices, telemetry, organizations, users, certificates
- The system stores IoT device data, sensor readings, user accounts, and certificates
- Data might not exist yet if devices haven't been added or haven't sent telemetry

Be specific and helpful, not generic."""

                summary_response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an AI assistant for the TESA IoT Platform helping users understand their queries."},
                        {"role": "user", "content": no_results_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                summary = summary_response.choices[0].message.content
            
            return {
                "query_description": query_description,
                "generated_filter": mongo_filter,
                "total_results": len(results),
                "summary": summary,
                "sample_results": results[:5] if results else []
            }
            
        except Exception as e:
            logger.error(f"Error in OpenAI query generation: {e}")
            # Fall back to the original parser
            parsed = self.parse_natural_language_query(query_description)
            results = self.execute_query(parsed)
            return self.analyze_query_results(query_description, results)
    
    def analyze_query_results(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze query results and provide summary statistics."""
        analysis = {
            "total_results": len(results),
            "query": query,
            "summary": {}
        }
        
        if not results:
            analysis["summary"]["message"] = "No results found for your query"
            return analysis
        
        # Analyze based on query type
        query_lower = query.lower()
        
        if "temperature" in query_lower and results:
            # Temperature analysis
            if "temperature" in results[0]:
                temps = [r["temperature"] for r in results if "temperature" in r]
                analysis["summary"]["avg_temperature"] = sum(temps) / len(temps)
                analysis["summary"]["max_temperature"] = max(temps)
                analysis["summary"]["min_temperature"] = min(temps)
                analysis["summary"]["devices_count"] = len(set(r.get("device_id") for r in results))
        
        elif "certificate" in query_lower or "algorithm" in query_lower:
            # Certificate analysis
            expired = 0
            expiring_soon = 0
            algorithm_counts = {}
            
            for r in results:
                # Check expiry
                if "certificate_expires_at" in r:
                    exp_date = r["certificate_expires_at"]
                    if isinstance(exp_date, str):
                        exp_date = datetime.fromisoformat(exp_date.replace('Z', '+00:00'))
                    
                    if exp_date < datetime.utcnow():
                        expired += 1
                    elif exp_date < datetime.utcnow() + timedelta(days=30):
                        expiring_soon += 1
                
                # Count algorithms
                algo = None
                if "certificate_info" in r and "key_algorithm" in r["certificate_info"]:
                    algo = r["certificate_info"]["key_algorithm"]
                elif "metadata" in r and "certificate_algorithm" in r["metadata"]:
                    algo = r["metadata"]["certificate_algorithm"]
                elif "certificate_algorithm" in r:
                    algo = r["certificate_algorithm"]
                
                if algo:
                    # Normalize algorithm names
                    algo_normalized = algo.upper().replace("-", " ")
                    if "ECC" in algo_normalized or "P-256" in algo_normalized or "P256" in algo_normalized:
                        algo_normalized = "ECC P-256"
                    elif "RSA" in algo_normalized:
                        if "3072" in algo_normalized:
                            algo_normalized = "RSA 3072"
                        elif "4096" in algo_normalized:
                            algo_normalized = "RSA 4096"
                        else:
                            algo_normalized = "RSA"
                    
                    algorithm_counts[algo_normalized] = algorithm_counts.get(algo_normalized, 0) + 1
            
            analysis["summary"]["expired_certificates"] = expired
            analysis["summary"]["expiring_soon"] = expiring_soon
            analysis["summary"]["total_certificates"] = len(results)
            
            # Add algorithm breakdown if relevant to query
            if any(word in query_lower for word in ["algorithm", "ecc", "rsa", "versus", "vs", "compare"]):
                # Format algorithm counts as a string for React compatibility
                algo_parts = []
                for algo, count in algorithm_counts.items():
                    algo_parts.append(f"{algo}: {count}")
                analysis["summary"]["certificate_algorithms"] = ", ".join(algo_parts)
        
        elif "status" in query_lower or "active" in query_lower or "inactive" in query_lower:
            # Status analysis
            status_counts = {}
            for r in results:
                status = r.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Format status breakdown as a string for React compatibility
            status_parts = []
            for status, count in status_counts.items():
                status_parts.append(f"{count} {status}")
            analysis["summary"]["status_breakdown"] = ", ".join(status_parts)
        
        # Add sample results (first 5)
        analysis["sample_results"] = results[:5]
        
        return analysis


# Example usage in chat service:
"""
# In chat_service.py, add:
from .mongodb_query_service import MongoDBQueryService

class ChatService:
    def __init__(self):
        # ... existing init ...
        self.query_service = MongoDBQueryService(self.db)
    
    async def send_message(self, ...):
        # Check if it's a data query
        if any(keyword in message.lower() for keyword in ['show', 'find', 'list', 'which', 'analyze']):
            try:
                # Parse and execute query
                parsed = self.query_service.parse_natural_language_query(message)
                results = self.query_service.execute_query(parsed)
                analysis = self.query_service.analyze_query_results(message, results)
                
                # Format response
                response_text = f"Found {analysis['total_results']} results:\n\n"
                for key, value in analysis['summary'].items():
                    response_text += f"- {key.replace('_', ' ').title()}: {value}\n"
                
                return {
                    "text": response_text,
                    "data": analysis
                }
            except Exception as e:
                logger.error(f"Query service error: {e}")
"""