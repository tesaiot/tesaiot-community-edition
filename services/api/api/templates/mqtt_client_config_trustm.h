/*
 * TESAIoT Community Edition
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 */

/*
 * MQTT Client Configuration for Infineon OPTIGA™ Trust M Devices
 * Generated for device: {device_id}
 * Trust M UID: {trustm_uid}
 * Generated at: {timestamp}
 * Environment: Production
 */

#ifndef MQTT_CLIENT_CONFIG_TRUSTM_H
#define MQTT_CLIENT_CONFIG_TRUSTM_H

/*******************************************************************************
 * MQTT Broker Settings
 ******************************************************************************/
#define MQTT_BROKER_HOST     "localhost"  /* set to your deployment's TESA_MQTT_DOMAIN */
#define MQTT_BROKER_PORT     8883  // MQTTS with mTLS
#define MQTT_USE_TLS         1
#define MQTT_USE_MUTUAL_TLS  1

/*******************************************************************************
 * Device Identification
 ******************************************************************************/
#define DEVICE_ID            "{device_id}"

// IMPORTANT: Use Trust M UID as MQTT Client Identifier
// This MUST match the Trust M UID (OID 0xE0C2) from your hardware
#define MQTT_CLIENT_IDENTIFIER        "{trustm_uid}"
#define MQTT_CLIENT_IDENTIFIER_MAX_LEN 64  // Trust M UID is 54 hex chars

/*******************************************************************************
 * Trust M Certificate Configuration
 ******************************************************************************/
// Phase 1: Initial Connection (Factory Certificate)
// Use Infineon factory certificate from Trust M chip
#define TRUSTM_CERT_OID_FACTORY       0xE0E9  // Infineon factory certificate
#define TRUSTM_KEY_OID_FACTORY        0xE0F0  // Factory private key slot

// Phase 2: After CSR and Protected Update (Platform Certificate)
// TESAIoT platform certificate will be stored here via Protected Update
#define TRUSTM_CERT_OID_PLATFORM      0xE0E1  // Platform certificate slot
#define TRUSTM_KEY_OID_PLATFORM       0xE0F1  // Platform private key slot

// Current active certificate (change after Protected Update completes)
// Initially use factory cert, then switch to platform cert
#define TRUSTM_CERT_OID_ACTIVE        TRUSTM_CERT_OID_FACTORY
#define TRUSTM_KEY_OID_ACTIVE         TRUSTM_KEY_OID_FACTORY

/*******************************************************************************
 * Root CA Certificate Configuration
 ******************************************************************************/
// CA chain includes both:
// 1. Infineon OPTIGA Trust M CA 300 (for factory cert)
// 2. TESAIoT Platform CA (for platform-issued cert after CSR)
#define CA_CHAIN_PATH         "ca-chain.pem"

// Trust M CA certificate storage
#define TRUSTM_CA_OID_INFINEON        0xE0E8  // Infineon Trust M CA 300
#define TRUSTM_CA_OID_PLATFORM        0xE0EF  // TESAIoT Platform CA (optional)

/*******************************************************************************
 * MQTT Topics
 ******************************************************************************/
#define TELEMETRY_TOPIC      "telemetry/{device_id}"
#define COMMAND_TOPIC        "commands/{device_id}"
#define STATUS_TOPIC         "status/{device_id}"
#define CSR_TOPIC            "commands/csr"  // For sending CSR to platform

/*******************************************************************************
 * Connection Parameters
 ******************************************************************************/
#define MQTT_KEEPALIVE       60   // seconds
#define MQTT_QOS             1    // At least once delivery
#define MQTT_RETAIN          0
#define MQTT_CLEAN_SESSION   1

/*******************************************************************************
 * Buffer Sizes
 ******************************************************************************/
#define MQTT_BUFFER_SIZE     2048  // Larger for Trust M operations
#define MAX_TOPIC_LENGTH     128
#define MAX_PAYLOAD_SIZE     1024

/*******************************************************************************
 * Trust M Hardware Integration
 ******************************************************************************/
// These macros should be implemented in your Trust M abstraction layer

// Read certificate from Trust M OID
// Example: trustm_read_cert(TRUSTM_CERT_OID_ACTIVE, cert_buffer, &cert_len)
#define TRUSTM_READ_CERT(oid, buffer, length) \
    trustm_read_data(oid, buffer, length)

// Sign data with Trust M private key
// Example: trustm_sign(TRUSTM_KEY_OID_ACTIVE, hash, hash_len, signature, &sig_len)
#define TRUSTM_SIGN_DATA(oid, hash, hash_len, signature, sig_len) \
    trustm_ecdsa_sign(oid, hash, hash_len, signature, sig_len)

/*******************************************************************************
 * Workflow Instructions
 ******************************************************************************/
/*
 * PHASE 1: Initial Connection with Factory Certificate
 * =====================================================
 * 1. Read factory certificate from Trust M OID 0xE0E9
 * 2. Use factory private key from OID 0xE0F0 for TLS handshake
 * 3. Connect to MQTT broker with client_id = Trust M UID ({trustm_uid})
 * 4. Platform will auto-activate device on first successful connection
 *
 * PHASE 2: Generate and Submit CSR (Optional - for platform certificate)
 * ======================================================================
 * 1. Generate new key pair in Trust M OID 0xE0F1 (if not using factory key)
 * 2. Create CSR with CN=device_id or CN=trustm_uid
 * 3. Publish CSR to topic: commands/csr
 * 4. Platform will sign CSR and prepare Protected Update manifest
 *
 * PHASE 3: Protected Update (Certificate Rotation)
 * ================================================
 * 1. Receive Protected Update manifest via MQTT
 * 2. Verify manifest integrity and version
 * 3. Write platform certificate to Trust M OID 0xE0E1
 * 4. Update TRUSTM_CERT_OID_ACTIVE to 0xE0E1
 * 5. Update TRUSTM_KEY_OID_ACTIVE to 0xE0F1
 * 6. Reconnect with platform certificate
 *
 * Note: You can continue using factory certificate indefinitely if you don't
 * need certificate rotation. Protected Update is optional.
 */

/*******************************************************************************
 * Example Usage
 ******************************************************************************/
/*
 * // Initialize MQTT client
 * mqtt_client_config_t config = {
 *     .broker_host = MQTT_BROKER_HOST,
 *     .broker_port = MQTT_BROKER_PORT,
 *     .client_id = MQTT_CLIENT_IDENTIFIER,  // Trust M UID
 *     .use_tls = MQTT_USE_TLS,
 *     .use_mutual_tls = MQTT_USE_MUTUAL_TLS,
 *     .ca_chain_path = CA_CHAIN_PATH,
 *     .keepalive = MQTT_KEEPALIVE
 * };
 *
 * // Read certificate from Trust M
 * uint8_t cert_buffer[2048];
 * uint16_t cert_len = sizeof(cert_buffer);
 * trustm_read_data(TRUSTM_CERT_OID_ACTIVE, cert_buffer, &cert_len);
 *
 * // Configure TLS callbacks to use Trust M for signing
 * mqtt_tls_set_sign_callback(trustm_sign_callback);
 *
 * // Connect to broker
 * mqtt_connect(&config);
 */

/*******************************************************************************
 * Security Notes
 ******************************************************************************/
/*
 * IMPORTANT SECURITY CONSIDERATIONS:
 *
 * 1. Private keys NEVER leave Trust M chip (OID 0xE0F0, 0xE0F1)
 * 2. Factory certificate is read-only (OID 0xE0E9)
 * 3. Platform certificate slot (OID 0xE0E1) can be updated via Protected Update
 * 4. Always verify Protected Update manifest before applying
 * 5. Trust M UID is immutable hardware identifier
 * 6. Use MQTT_CLIENT_IDENTIFIER = Trust M UID for authentication
 */

#endif // MQTT_CLIENT_CONFIG_TRUSTM_H
