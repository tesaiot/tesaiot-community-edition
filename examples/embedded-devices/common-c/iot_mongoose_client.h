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
 * Shared Mongoose-based client for HTTPS and MQTTS.
 *
 * Header-only overview so tutorial readers can map each structure back to the
 * prose in the README: focus on readability and MISRA-C 2004 style where
 * practical.  Every field includes a short inline hint about how the platform
 * uses it.
 */

#ifndef IOT_MONGOOSE_CLIENT_H
#define IOT_MONGOOSE_CLIENT_H

#include <stddef.h>
#include <stdint.h>

/* Return codes */
enum {
  IOT_OK = 0,
  IOT_ERR_ARG = 1,
  IOT_ERR_CONNECT = 2,
  IOT_ERR_TIMEOUT = 3,
  IOT_ERR_TLS = 4,
  IOT_ERR_PROTO = 5,
  IOT_ERR_HTTP = 6,
  IOT_ERR_MQTT = 7
};

typedef enum {
  COMM_MODE_HTTPS = 1,
  COMM_MODE_MQTTS = 2
} comm_mode_t;

typedef struct {
  const char * host;          /* e.g., "localhost" */
  uint16_t     port;          /* e.g., 443, 8883, 9444, 8884 */
  const char * ca_chain;      /* Path to CA chain, optional */
  const char * client_cert;   /* Path to client certificate (PEM), optional */
  const char * client_key;    /* Path to client private key (PEM), optional */
  const char * sni_name;      /* Server name for SNI/verification (optional) */
  uint32_t     connect_timeout_ms; /* e.g., 10000 */
  uint32_t     total_timeout_ms;   /* e.g., 30000 */
  uint8_t      verify_peer;   /* 1 to verify peer (default), 0 to skip */
  uint8_t      reserved8;     /* reserved for alignment */
} iot_tls_conf_t;

typedef struct {
  const char * url;           /* Full URL: https://host:port/path */
  const char * api_key;       /* Optional: Bearer or X-API-KEY value */
  const char * body;          /* Request body (JSON) */
  size_t       body_len;      /* Length of body */
  uint32_t     timeout_ms;    /* Request timeout (<= total_timeout_ms) */
} iot_http_req_t;

typedef struct {
  const char * host;          /* MQTT host */
  uint16_t     port;          /* MQTT TLS port */
  const char * client_id;     /* Client ID */
  const char * username;      /* Optional */
  const char * password;      /* Optional */
  const char * topic;         /* Publish topic */
  const char * payload;       /* Publish payload */
  size_t       payload_len;   /* Payload length */
  uint8_t      qos;           /* 0,1,2 (we use 1 by default) */
  uint8_t      retain;        /* 0/1 */
  uint16_t     keepalive_sec; /* Keepalive interval */
  uint32_t     timeout_ms;    /* Overall op timeout */
} iot_mqtt_req_t;

/* HTTPS POST. Returns 0 on success (2xx), else non-zero */
int iot_https_post(const iot_http_req_t * req, const iot_tls_conf_t * tls);

/* MQTT publish with TLS. Returns 0 on success (PUBACK/accepted) */
int iot_mqtts_publish(const iot_mqtt_req_t * req, const iot_tls_conf_t * tls);

#endif /* IOT_MONGOOSE_CLIENT_H */
