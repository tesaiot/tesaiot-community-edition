/*
 * Copyright (c) 2025 TESAIoT Platform (TESA)
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
 * TESA IoT Platform — Server-TLS HTTPS device example (classic layout)
 *
 * Mirrors the mTLS tutorial but highlights where API keys and one-way TLS are
 * used.  Treat this file as a ready-made checklist when porting to another
 * device.
 */

#ifndef TESA_HTTPS_STLS_CONFIG_H
#define TESA_HTTPS_STLS_CONFIG_H

#include <stdint.h>

/* Default device identity (Device02) */
#ifndef DEVICE_ID_SERVERTLS
#define DEVICE_ID_SERVERTLS         "e919a2f9-ad08-40be-a539-bef6b3b678a4"
#endif

/* Force Server‑TLS for this example */
#ifndef USE_MTLS
#define USE_MTLS                    (0U)
#endif

/* Endpoint default for Server‑TLS (can be overridden via API_BASE_URL env). */
#define DEFAULT_API_BASE_URL        "https://localhost"

/* MQTT defaults (Server‑TLS): CE exposes the serverTLS listener on localhost:8884. */
#define DEFAULT_MQTT_HOST           "localhost"
#define DEFAULT_MQTT_PORT           (8884U)

/* Unified credentials directory for this example */
#define PATH_CERTS_DIR              "certs_credentials/"
#define PATH_CA_CHAIN               PATH_CERTS_DIR "ca-chain.pem"
#define PATH_CLIENT_CERT            PATH_CERTS_DIR "client_cert.pem" /* unused */
#define PATH_CLIENT_KEY             PATH_CERTS_DIR "client_key.pem"  /* unused */
#define PATH_API_KEY                PATH_CERTS_DIR "api_key.txt"
#define PATH_ENDPOINTS_JSON         PATH_CERTS_DIR "endpoints.json"
#define SYSTEM_CA_BUNDLE_PATH       "/etc/ssl/certs/ca-certificates.crt"
#define PATH_DEVICE_ID              PATH_CERTS_DIR "device_id.txt"
#define PATH_SCHEMA_PROFILE_TXT     PATH_CERTS_DIR "schema_profile.txt"

/* Basename constants */
#define FILE_CA_CHAIN               "ca-chain.pem"
#define FILE_CLIENT_CERT            "client_cert.pem"
#define FILE_CLIENT_KEY             "client_key.pem"
#define FILE_API_KEY                "api_key.txt"
#define FILE_ENDPOINTS_JSON         "endpoints.json"
#define FILE_DEVICE_ID              "device_id.txt"
#define FILE_SCHEMA_PROFILE         "schema_profile.txt"

/* Timing and limits */
#define HTTP_CONNECT_TIMEOUT_SEC    (10L)
#define HTTP_TOTAL_TIMEOUT_SEC      (30L)
#define HTTP_RETRY_COUNT            (3U)
#define MAX_URL_SIZE                (512U)
#define MAX_HDR_SIZE                (256U)
#define MAX_API_KEY_SIZE            (256U)
#define MAX_JSON_SIZE               (2048U)
#define MAX_FILE_SIZE               (4096U)

/* MQTT sizing */
#define MAX_TOPIC_SIZE              (256U)

/* Communication mode selection via env COMM_MODE=HTTPS|MQTTS (default: HTTPS for examples) */
#define COMM_MODE_DEFAULT           (1U) /* 1=HTTPS, 2=MQTTS */

#ifndef ENABLE_DEBUG_LOG
#define ENABLE_DEBUG_LOG            (0U)
#endif

#if ENABLE_DEBUG_LOG
#include <stdio.h>
#define DBG_PRINTF(...) do { (void)printf(__VA_ARGS__); } while (0)
#else
#define DBG_PRINTF(...) do { } while (0)
#endif

/* Schema profile constants (optional) */
#define SCHEMA_PROFILE_DEVICE01     (1U)
#define SCHEMA_PROFILE_DEVICE02     (2U)
#ifndef SCHEMA_PROFILE
#define SCHEMA_PROFILE              SCHEMA_PROFILE_DEVICE02
#endif

#endif /* TESA_HTTPS_STLS_CONFIG_H */
