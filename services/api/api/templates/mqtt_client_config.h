/*
 * TESAIoT Community Edition
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 */

/*
 * Copyright (c) 2024-2025 Assoc. Prof. Wiroon Sriborrirux, BDH Corporation
 * Licensed under the Apache License, Version 2.0
 * Managed by: Thai Embedded Systems Association (TESA)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/*
 * MQTT Client Configuration Template
 * Generated for device: {device_id}
 * Environment: {environment}
 */

#ifndef MQTT_CLIENT_CONFIG_H
#define MQTT_CLIENT_CONFIG_H

// MQTT Broker Settings
#define MQTT_BROKER_HOST     "localhost"  /* set to your deployment's TESA_MQTT_DOMAIN */
#define MQTT_BROKER_PORT     8883  // MQTTS port
#define MQTT_USE_TLS         1

// Device Credentials
#define DEVICE_ID            "{device_id}"
#define MQTT_CLIENT_ID       "{device_id}"

// MQTT Topics
#define TELEMETRY_TOPIC      "telemetry/{device_id}"
#define COMMAND_TOPIC        "commands/{device_id}"
#define STATUS_TOPIC         "status/{device_id}"

// TLS Configuration
#define USE_MUTUAL_TLS       1
// Certificate paths (update these based on your file system)
#define CA_CERT_PATH         "ca_certificate.pem"
#define CLIENT_CERT_PATH     "certificate.pem"
#define CLIENT_KEY_PATH      "private_key.pem"

// Connection Parameters
#define MQTT_KEEPALIVE       60  // seconds
#define MQTT_QOS            1
#define MQTT_RETAIN         0

// Buffer Sizes
#define MQTT_BUFFER_SIZE    1024
#define MAX_TOPIC_LENGTH    128
#define MAX_PAYLOAD_SIZE    512

#endif // MQTT_CLIENT_CONFIG_H
