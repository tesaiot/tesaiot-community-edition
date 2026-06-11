/*
 * SPDX-License-Identifier: Apache-2.0
 * TESAIoT Community Edition — MongoDB initialization
 * Origin: TESAIoT Secure IoT Platform. Contributors: TESAIoT Platform contributors.
 *
 * Single-organization distribution. Creates the application database, the
 * application user, the in-scope collections, and one default organization.
 *
 * Credentials: this script MUST read the SAME variables the API uses to connect
 * (see services/api/api/core/db_config.py), otherwise a fresh `make install`
 * creates a user the API cannot authenticate as. The API connects with:
 *   MONGODB_USER      (default: iot_user)
 *   MONGODB_PASSWORD  (REQUIRED — no fallback; set via the .env file)
 *   authSource=admin  (so the app user is created in the `admin` database)
 *
 * Set these via the .env file (NEVER ship real secrets in source):
 *   MONGODB_USER          (default: iot_user)
 *   MONGODB_PASSWORD      (REQUIRED — fail fast if unset)
 *   MONGO_INITDB_DATABASE (default: tesa_iot)
 *
 * The root user (mongoadmin) is created by the mongo image itself from
 * MONGO_INITDB_ROOT_USERNAME / MONGO_INITDB_ROOT_PASSWORD, so it is NOT
 * recreated here.
 */

const APP_DB = (typeof process !== 'undefined' && process.env && process.env.MONGO_INITDB_DATABASE) || 'tesa_iot';
const APP_USER = (typeof process !== 'undefined' && process.env && process.env.MONGODB_USER) || 'iot_user';
const APP_PASSWORD = (typeof process !== 'undefined' && process.env && process.env.MONGODB_PASSWORD) || '';
const DEFAULT_ORG_ID = (typeof process !== 'undefined' && process.env && process.env.DEFAULT_ORG_ID) || 'default';

// Fail CLOSED: never create an app user with an empty/placeholder password.
// An empty password here would make the API's authenticated connection fail on
// every fresh install (the original 'CHANGEME' bug), or — worse — create a
// weakly-credentialed user. Require the same secret the API requires.
if (!APP_PASSWORD) {
  throw new Error(
    'MONGODB_PASSWORD is not set. init-mongo.js refuses to create the ' +
    'application user (' + APP_USER + ') without the password the API uses ' +
    'to authenticate. Set MONGODB_PASSWORD in your .env file and re-run.'
  );
}

// Create application user scoped to the app database
db = db.getSiblingDB('admin');
try {
  db.createUser({
    user: APP_USER,
    pwd: APP_PASSWORD,
    roles: [
      { role: 'readWrite', db: APP_DB },
      { role: 'dbAdmin', db: APP_DB }
    ]
  });
  print('Application user (' + APP_USER + ') created successfully');
} catch (e) {
  print('Application user creation failed or already exists: ' + e.message);
}

// Switch to the application database
db = db.getSiblingDB(APP_DB);

// Create in-scope collections (firmware / ota_updates are excluded in CE)
db.createCollection('users');
db.createCollection('devices');
db.createCollection('organizations');
db.createCollection('certificates');
db.createCollection('mqtt_permissions');
db.createCollection('audit_logs');

// Indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.devices.createIndex({ device_id: 1 }, { unique: true });
db.devices.createIndex({ certificate_serial: 1 });
db.organizations.createIndex({ name: 1 }, { unique: true });
db.organizations.createIndex({ organization_id: 1 }, { unique: true });

// Create the single default organization
try {
  const defaultOrg = {
    _id: DEFAULT_ORG_ID,
    organization_id: DEFAULT_ORG_ID,
    name: 'Default Organization',
    display_name: 'Default Organization',
    description: 'Single default organization for the self-host distribution',
    plan: 'community',
    status: 'active',
    contact_email: 'admin@localhost',
    created_at: new Date(),
    updated_at: new Date(),
    created_by: 'system_initialization',
    type: 'default',
    settings: {
      max_devices: 999999,
      max_users: 999999,
      features: {
        telemetry: true,
        alerts: true,
        reports: true,
        api_access: true
      }
    },
    metadata: {
      is_default_org: true,
      full_platform_access: true
    }
  };

  db.organizations.insertOne(defaultOrg);
  print('Default organization (' + DEFAULT_ORG_ID + ') created successfully');
} catch (e) {
  print('Default organization creation failed or already exists: ' + e.message);
}

print('MongoDB initialization completed');
