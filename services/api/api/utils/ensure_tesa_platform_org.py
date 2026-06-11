# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Ensure TESA Platform Organization Exists
"""
import logging
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.append('/media/psf/BDH/TESA_IoT_Platform/lastest_portable_TESA_IoT_Platform/production-repo/src/python')

from api.core.database import get_db

logger = logging.getLogger(__name__)

def ensure_tesa_platform_organization():
    """Ensure tesa-platform organization exists in MongoDB"""
    try:
        db = get_db()
        if db is None:
            print("ERROR: Could not connect to database")
            return False
            
        # Check if tesa-platform organization exists
        platform_org = db.organizations.find_one({'_id': 'tesa-platform'})
        
        if platform_org:
            print(f"✅ TESA Platform organization already exists: {platform_org.get('name', 'TESA Platform')}")
            return True
        
        # Create the tesa-platform organization
        platform_org_doc = {
            '_id': 'tesa-platform',
            'organization_id': 'tesa-platform',
            'name': 'TESA Platform Infrastructure',
            'display_name': 'TESA Platform Infrastructure',
            'description': 'Thai Embedded Systems Association Platform Infrastructure Organization',
            'plan': 'platform',
            'status': 'active',
            'contact_email': 'platform@tesa.iot',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system_initialization',
            'type': 'platform',
            'settings': {
                'max_devices': 999999,
                'max_users': 999999,
                'features': {
                    'telemetry': True,
                    'alerts': True,
                    'reports': True,
                    'api_access': True,
                    'advanced_analytics': True,
                    'multi_tenant': True,
                    'white_label': True,
                    'custom_integrations': True
                }
            },
            'metadata': {
                'is_platform_org': True,
                'infrastructure_only': False,
                'full_platform_access': True
            }
        }
        
        # Insert the organization
        result = db.organizations.insert_one(platform_org_doc)
        
        if result.inserted_id:
            print(f"✅ Created TESA Platform organization: {platform_org_doc['name']}")
            print(f"   Organization ID: {platform_org_doc['organization_id']}")
            print(f"   Plan: {platform_org_doc['plan']}")
            print(f"   Status: {platform_org_doc['status']}")
            return True
        else:
            print("❌ Failed to create TESA Platform organization")
            return False
            
    except Exception as e:
        print(f"❌ Error ensuring TESA Platform organization: {e}")
        return False

if __name__ == "__main__":
    print("=== Ensuring TESA Platform Organization ===")
    success = ensure_tesa_platform_organization()
    
    if success:
        print("✅ TESA Platform organization is ready")
        sys.exit(0)
    else:
        print("❌ Failed to ensure TESA Platform organization")
        sys.exit(1)