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
 * TESA IoT Platform — Unified device client (mTLS): HTTPS or MQTTS via Mongoose
 *
 * Tutorial roadmap:
 *  - teach how to load credentials/bundle files from disk safely
 *  - show how schema-driven telemetry becomes JSON
 *  - demonstrate transport selection (HTTPS vs MQTTS) with identical payloads
 *
 * Every helper below begins with a comment spelling out the "why" so readers
 * can connect the C code back to the deployment steps in the README.
 */

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>
#include <strings.h>

#include "config.h"
#include "data_schema.h"
#include "../common-c/iot_mongoose_client.h"

/* read_small_file — load a credential/helper file into caller-provided buffer. */
static int read_small_file(const char * path, char * out, size_t out_size)
{
  FILE * f = NULL;
  size_t n = 0U;
  if ((path == NULL) || (out == NULL) || (out_size < 2U)) {
    return -1;
  }
  f = fopen(path, "rb");
  if (f == NULL) {
    return -1;
  }
  n = fread(out, 1U, out_size - 1U, f);
  fclose(f);
  out[n] = '\0';
  return 0;
}

/* file_exists — we do an explicit fopen so the tutorial works on bare POSIX. */
static int file_exists(const char * path)
{
  FILE * f = NULL;
  if (path == NULL) {
    return 0;
  }
  f = fopen(path, "rb");
  if (f != NULL) {
    fclose(f);
    return 1;
  }
  return 0;
}

/* join_path — cheap path joiner that respects trailing slash in CERTS_DIR. */
static void join_path(char * out, size_t out_sz, const char * dir, const char * name)
{
  size_t d = 0U;
  if ((out == NULL) || (out_sz == 0U) || (name == NULL)) {
    return;
  }
  if ((dir == NULL) || (dir[0] == '\0')) {
    (void)snprintf(out, out_sz, "%s", name);
    return;
  }
  d = strlen(dir);
  if (d > 0U && (dir[d - 1U] == '/' || dir[d - 1U] == '\\')) {
    (void)snprintf(out, out_sz, "%s%s", dir, name);
  } else {
    (void)snprintf(out, out_sz, "%s/%s", dir, name);
  }
}

/* make_iso8601_utc — produce UTC timestamps the admin UI expects. */
static void make_iso8601_utc(char * out, size_t out_size)
{
  time_t now = time(NULL);
  struct tm g;
  (void)gmtime_r(&now, &g);
  (void)strftime(out, out_size, "%Y-%m-%dT%H:%M:%SZ", &g);
}

/* parse_json_string_value — tiny JSON helper to reuse values from endpoints.json. */
static int parse_json_string_value(const char * buf, const char * key, char * out, size_t out_sz)
{
  const char * k = strstr(buf, key);
  const char * q = NULL;
  const char * s = NULL;
  const char * e = NULL;
  size_t n = 0U;
  if ((k == NULL) || (out == NULL) || (out_sz == 0U)) {
    return -1;
  }
  q = strchr(k, '"'); if (q == NULL) return -1;
  q = strchr(q + 1, '"'); if (q == NULL) return -1;
  s = q + 1;
  s = strchr(s, '"'); if (s == NULL) return -1;
  ++s;
  e = strchr(s, '"'); if ((e == NULL) || (e <= s)) return -1;
  n = (size_t)(e - s);
  if (n >= out_sz) {
    n = out_sz - 1U;
  }
  (void)memcpy(out, s, n);
  out[n] = '\0';
  return 0;
}

/* parse_json_int_value — read integer config, mainly used for MQTT port defaults. */
static int parse_json_int_value(const char * buf, const char * key, int * value)
{
  const char * k = strstr(buf, key);
  const char * c = NULL;
  int v = 0;
  if ((k == NULL) || (value == NULL)) {
    return -1;
  }
  c = strchr(k, ':'); if (c == NULL) return -1;
  ++c;
  while (*c == ' ') {
    ++c;
  }
  v = atoi(c);
  *value = v;
  return 0;
}

/* ---------------------------------------------
 * Minimal JSON-Schema (properties) parser
 * Supports: type (integer|number|string|boolean), minimum, maximum, enum[0]
 * Reads from download/data_schema.txt adjacent to CERTS_DIR (../download)
 * --------------------------------------------- */
static double frand01(void) { return (double) rand() / (double) RAND_MAX; }

/*
 * load_schema_fields — read JSON schema and populate fields with sample data.
 * We deliberately keep this small and iterative so developers can adapt it to
 * their own schema rules without diving into a full JSON parser.
 */
static int load_schema_fields(const char * schema_path, schema_field_t * out, size_t max_fields)
{
  FILE * f = fopen(schema_path, "rb"); if (!f) return -1;
  fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
  if (n <= 0 || n > 1*1024*1024) { fclose(f); return -1; }
  char * buf = (char *) malloc((size_t)n + 1U); if (!buf) { fclose(f); return -1; }
  if (fread(buf, 1U, (size_t)n, f) != (size_t)n) {
    fclose(f);
    free(buf);
    return -1;
  }
  fclose(f);
  buf[n]='\0';

  /* move into properties section */
  const char * props = strstr(buf, "\"properties\"");
  if (!props) { free(buf); return -1; }
  const char * p = strchr(props, '{'); if (!p) { free(buf); return -1; }

  size_t count = 0U;
  while (count < max_fields && (p = strchr(p, '"')) != NULL) {
    const char * name_start = p + 1; const char * name_end = strchr(name_start, '"'); if (!name_end) break;
    /* extract property name */
    size_t name_len = (size_t)(name_end - name_start); if (name_len == 0 || name_len > 63) { p = name_end ? name_end+1 : name_start; continue; }
    char name[64]; memcpy(name, name_start, name_len); name[name_len] = '\0';
    /* skip timestamp field: handled by outer JSON */
    if (strcasecmp(name, "timestamp") == 0) { p = name_end + 1; continue; }
    /* find block start */
    const char * block = strchr(name_end, '{'); if (!block) break;
    /* find block end heuristically */
    const char * next_prop = strstr(block, "}\n"); if (!next_prop) next_prop = block + 512; /* safety */

    /* parse type */
    const char * tpos = strstr(block, "\"type\"");
    char type[16] = {0};
    if (tpos) {
      const char * q1 = strchr(tpos, '"'); q1 = q1 ? strchr(q1+1,'"') : NULL; const char * q2 = q1 ? strchr(q1+1,'"') : NULL; if (q1 && q2 && (size_t)(q2-q1-1) < sizeof(type)) { memcpy(type, q1+1, (size_t)(q2-q1-1)); type[q2-q1-1]='\0'; }
    }

    /* parse minimum/maximum if any */
    double vmin = 0.0, vmax = 100.0; int has_min = 0, has_max = 0;
    const char * mnp = strstr(block, "\"minimum\""); if (mnp) { const char * c = strchr(mnp, ':'); if (c){ vmin = atof(c+1); has_min = 1; } }
    const char * mxp = strstr(block, "\"maximum\""); if (mxp) { const char * c = strchr(mxp, ':'); if (c){ vmax = atof(c+1); has_max = 1; } }
    if (!has_min && !has_max) { vmin = 0.0; vmax = 100.0; }

    /* enum: pick first element if string */
    char enum0[32] = {0};
    const char * enp = strstr(block, "\"enum\"");
    if (enp) {
      const char * b = strchr(enp, '['); const char * q = b ? strchr(b, '"') : NULL; const char * qe = q ? strchr(q+1,'"') : NULL;
      if (q && qe && (size_t)(qe-q-1) < sizeof(enum0)) { memcpy(enum0, q+1, (size_t)(qe-q-1)); enum0[qe-q-1] = '\0'; }
    }

    /* map to schema_field_t */
    schema_field_t f; memset(&f, 0, sizeof(f)); f.name = strdup(name);
    if (strcasecmp(type, "integer") == 0) { f.type = SCHEMA_I32; int lo = (int)vmin; int hi = (int)vmax; if (hi <= lo) hi = lo + 100; int val = lo + (rand() % (hi - lo + 1)); f.value.i32 = val; }
    else if (strcasecmp(type, "number") == 0) { f.type = SCHEMA_F64; double r = vmin + frand01() * (vmax - vmin); f.value.f64 = r; }
    else if (strcasecmp(type, "boolean") == 0) { f.type = SCHEMA_BOOL; f.value.b = (rand() % 2) ? 1U : 0U; }
    else if (strcasecmp(type, "string") == 0) { f.type = SCHEMA_STR; const char * sval = enum0[0] ? enum0 : "ok"; f.value.str = strdup(sval); }
    else { /* unsupported: skip */ p = name_end + 1; continue; }

    out[count++] = f;
    p = name_end + 1;
  }
  free(buf);
  return (int) count;
}

/* inspect COMM_MODE env to let users switch transports without recompiling. */
static int is_mode_mqtts(void)
{
  const char * m = getenv("COMM_MODE");
  if (m == NULL) return 0;
  return (strcasecmp(m, "MQTTS") == 0) ? 1 : 0;
}

/*
 * apply_cli_overrides — interpret tutorial flags so readers can experiment
 * without editing config.h.  We only enable safe overrides (duration/interval
 * and connection targets).
 */
static void apply_cli_overrides(int argc, char **argv,
                                int * duration_sec, int * interval_ms,
                                int * force_mqtts,
                                char * host_buf, size_t host_sz,
                                int * port)
{
  int i = 1;
  if (duration_sec == NULL || interval_ms == NULL || force_mqtts == NULL || host_buf == NULL || port == NULL) return;
  while (i < argc) {
    const char * a = argv[i];
    if ((strcmp(a, "--period") == 0) && (i + 1 < argc)) {
      long v = strtol(argv[i+1], NULL, 10); if (v < 0) v = 0; *duration_sec = (int)(v * 60L); i += 2; continue;
    }
    if ((strcmp(a, "--interval") == 0) && (i + 1 < argc)) {
      long v = strtol(argv[i+1], NULL, 10); if (v <= 0) v = 1; *interval_ms = (int)(v * 1000L); i += 2; continue;
    }
    if ((strcmp(a, "--mode") == 0) && (i + 1 < argc)) {
      const char * m = argv[i+1]; *force_mqtts = (strcasecmp(m, "MQTTS") == 0) ? 1 : 0; i += 2; continue;
    }
    if ((strcmp(a, "--host") == 0) && (i + 1 < argc)) {
      (void)snprintf(host_buf, host_sz, "%s", argv[i+1]); i += 2; continue;
    }
    if ((strcmp(a, "--port") == 0) && (i + 1 < argc)) {
      long p = strtol(argv[i+1], NULL, 10); if (p > 0 && p < 65536) *port = (int)p; i += 2; continue;
    }
    /* unknown flag: skip */
    ++i;
  }
}

/*
 * main — glue everything together: load credentials, build telemetry JSON,
 * and send it either over HTTPS or MQTTS depending on COMM_MODE/CLI flags.
 */
int main(int argc, char **argv)
{
  char base_url[MAX_URL_SIZE] = {0};
  char url[MAX_URL_SIZE] = {0};
  char device_id[128] = {0};
  char endpoints_buf[MAX_FILE_SIZE] = {0};
  char json_buf[MAX_JSON_SIZE] = {0};

  const char * certs_dir_env = getenv("CERTS_DIR");
  const char * certs_dir = (certs_dir_env != NULL && certs_dir_env[0] != '\0') ? certs_dir_env : PATH_CERTS_DIR;

  /* Resolve schema path: SCHEMA_PATH env or sibling ../download/data_schema.txt */
  char schema_path[512] = {0};
  const char * schema_env = getenv("SCHEMA_PATH");
  if (schema_env && schema_env[0] != '\0') {
    snprintf(schema_path, sizeof(schema_path), "%s", schema_env);
  } else {
    /* if CERTS_DIR ends with /certs_credentials, replace with /download/data_schema.txt */
    const char * cc = strstr(certs_dir, "/certs_credentials");
    if (cc) {
      size_t len = (size_t)(cc - certs_dir);
      if (len < sizeof(schema_path)) { memcpy(schema_path, certs_dir, len); schema_path[len] = '\0'; }
    } else {
      snprintf(schema_path, sizeof(schema_path), "%s", certs_dir);
    }
    size_t l = strlen(schema_path); if (l + strlen("/download/data_schema.txt") + 1 < sizeof(schema_path)) strcat(schema_path, "/download/data_schema.txt");
  }

  /* Resolve base URL: ENV → endpoints.json → default */
  {
    const char * env_base = getenv("API_BASE_URL");
    if (env_base != NULL && env_base[0] != '\0') {
      (void)snprintf(base_url, sizeof(base_url), "%s", env_base);
    } else {
      char p[512]; join_path(p, sizeof(p), certs_dir, FILE_ENDPOINTS_JSON);
      if (read_small_file(p, endpoints_buf, sizeof(endpoints_buf)) == 0) {
        /* very small parse: look for api_base_url or ingest_base_url */
        if (parse_json_string_value(endpoints_buf, "api_base_url", base_url, sizeof(base_url)) != 0) {
          (void)parse_json_string_value(endpoints_buf, "ingest_base_url", base_url, sizeof(base_url));
        }
      }
      if (base_url[0] == '\0') (void)snprintf(base_url, sizeof(base_url), "%s", DEFAULT_API_BASE_URL);
    }
  }
  if (snprintf(url, sizeof(url), "%s/api/v1/telemetry", base_url) >= (int)sizeof(url)) { (void)fprintf(stderr, "URL too long\n"); return 1; }

  /* Device ID: ENV → certs file → default */
  {
    const char * env_id = getenv("DEVICE_ID");
    if (env_id != NULL && env_id[0] != '\0') { (void)snprintf(device_id, sizeof(device_id), "%s", env_id); }
    else {
      char p[512]; join_path(p, sizeof(p), certs_dir, FILE_DEVICE_ID);
      if (read_small_file(p, device_id, sizeof(device_id)) != 0) (void)snprintf(device_id, sizeof(device_id), "%s", DEVICE_ID_MTLS);
      size_t n = strlen(device_id); while (n>0U && (device_id[n-1]=='\n'||device_id[n-1]=='\r'||device_id[n-1]==' ')) { device_id[n-1] = '\0'; --n; }
    }
  }

  /* Resolve credential files */
  char ca[512], crt[512], key[512];
  join_path(ca,  sizeof(ca),  certs_dir, FILE_CA_CHAIN);
  join_path(crt, sizeof(crt), certs_dir, FILE_CLIENT_CERT);
  join_path(key, sizeof(key), certs_dir, FILE_CLIENT_KEY);
  if (!(file_exists(crt) && file_exists(key))) {
    (void)fprintf(stderr, "mTLS requires client_cert.pem and client_key.pem in %s\n", certs_dir);
    return 1;
  }

  /* Community Edition: EMQX runs a password_based webhook authenticator on every
     listener, so an mTLS client must still send username=device_id and a
     non-empty password (its device API key) to engage the auth chain; the
     webhook then authorises by the client-certificate CN. Load the API key. */
  char api_key[MAX_API_KEY_SIZE] = {0};
  { char kp[512]; join_path(kp, sizeof(kp), certs_dir, FILE_API_KEY);
    if (read_small_file(kp, api_key, sizeof(api_key)) == 0) {
      size_t n = strlen(api_key);
      while (n>0U && (api_key[n-1]=='\n'||api_key[n-1]=='\r'||api_key[n-1]==' ')) { api_key[n-1]='\0'; --n; }
    } }

  /* Loop controls */
  int duration_sec = 0; int interval_ms = 1000;
  {
    const char * env_dur = getenv("SEND_DURATION_SEC");
    const char * env_int = getenv("SEND_INTERVAL_MS");
    duration_sec = (env_dur != NULL) ? atoi(env_dur) : 0;
    interval_ms = (env_int != NULL) ? atoi(env_int) : 1000;
    if (duration_sec < 0) { duration_sec = 0; }
    if (interval_ms <= 0) { interval_ms = 1000; }
  }

  /* MQTT host/port if used; CLI overrides are applied below */
  char mqtt_host[128] = {0};
  int  mqtt_port = (int) DEFAULT_MQTT_PORT;
  {
    const char * eh = getenv("MQTT_HOST");
    const char * ep = getenv("MQTT_PORT");
    if (eh != NULL && eh[0] != '\0') (void)snprintf(mqtt_host, sizeof(mqtt_host), "%s", eh);
    if (ep != NULL && ep[0] != '\0') { int p = atoi(ep); if (p > 0 && p < 65536) mqtt_port = p; }
    if (mqtt_host[0] == '\0') {
      /* Try endpoints.json minimal parse */
      if (endpoints_buf[0] != '\0') {
        (void)parse_json_string_value(endpoints_buf, "mqtt_host", mqtt_host, sizeof(mqtt_host));
        int mp = 0; if (parse_json_int_value(endpoints_buf, "mqtt_mtls_port", &mp) == 0) { if (mp > 0 && mp < 65536) mqtt_port = mp; }
      }
      if (mqtt_host[0] == '\0') (void)snprintf(mqtt_host, sizeof(mqtt_host), "%s", DEFAULT_MQTT_HOST);
    }
  }

  /* CLI overrides: period/interval/mode and host/port */
  {
    int force_mqtts = -1;
    apply_cli_overrides(argc, argv, &duration_sec, &interval_ms, &force_mqtts, mqtt_host, sizeof(mqtt_host), &mqtt_port);
    if (force_mqtts == 1) {
      setenv("COMM_MODE", "MQTTS", 1);
    } else if (force_mqtts == 0) {
      setenv("COMM_MODE", "HTTPS", 1);
    }
  }

  /* Mongoose TLS base conf (we may tweak CA per mode below) */
  iot_tls_conf_t tls; (void)memset(&tls, 0, sizeof(tls));
  tls.client_cert = crt; tls.client_key = key;
  tls.verify_peer = 1U; tls.connect_timeout_ms = (uint32_t)(HTTP_CONNECT_TIMEOUT_SEC * 1000L); tls.total_timeout_ms = (uint32_t)(HTTP_TOTAL_TIMEOUT_SEC * 1000L);

  srand((unsigned int)time(NULL));
  const time_t start = time(NULL);
  do {
    /* Build telemetry JSON body */
    char ts[32]; make_iso8601_utc(ts, sizeof(ts));
    /* Build data fields from schema if available, otherwise use a small default set */
    schema_field_t fields[64]; size_t field_count = 0U;
    int nfields = load_schema_fields(schema_path, fields, 64);
    if (nfields > 0) {
      field_count = (size_t) nfields;
    } else {
      const double temp = 26.0 + ((double)(rand()%50))/10.0; /* 26.0..30.9 */
      const int batt = 90 + (rand()%10);
      fields[field_count++] = (schema_field_t){ "temperature", SCHEMA_F64, { .f64 = temp } };
      fields[field_count++] = (schema_field_t){ "battery",     SCHEMA_I32, { .i32 = batt } };
      fields[field_count++] = (schema_field_t){ "status",      SCHEMA_STR, { .str = (batt>92)?"ok":"warn" } };
    }
    schema_document_t doc; schema_init(&doc, fields, field_count);
    char data_json[MAX_JSON_SIZE]; (void)memset(data_json, 0, sizeof(data_json));
    if (schema_to_json(&doc, data_json, sizeof(data_json)) != 0) { (void)fprintf(stderr, "Failed to build JSON\n"); return 1; }
    if (snprintf(json_buf, sizeof(json_buf), "{\"device_id\":\"%s\",\"timestamp\":\"%s\",\"data\":%s}", device_id, ts, data_json) >= (int)sizeof(json_buf)) { (void)fprintf(stderr, "JSON too long\n"); return 1; }

    if (is_mode_mqtts() != 0) {
      /* Send via MQTTS (mTLS) */
      /* CE: verify the broker with the local Vault-PKI CA chain (not public trust). */
      tls.ca_chain = file_exists(PATH_CA_CHAIN) ? PATH_CA_CHAIN : NULL; tls.sni_name = mqtt_host;
      char topic[MAX_TOPIC_SIZE]; (void)snprintf(topic, sizeof(topic), "device/%s/telemetry", device_id);
      iot_mqtt_req_t mreq; (void)memset(&mreq, 0, sizeof(mreq));
      /* CE requires username=device_id + non-empty password (the device API key)
         to engage the auth webhook, which then authorises by client-cert CN. */
      mreq.host = mqtt_host; mreq.port = (uint16_t)mqtt_port; mreq.client_id = device_id;
      mreq.username = device_id; mreq.password = (api_key[0] != '\0') ? api_key : NULL;
      mreq.topic = topic; mreq.payload = json_buf; mreq.payload_len = strlen(json_buf); mreq.qos = 1U; mreq.retain = 0U; mreq.keepalive_sec = 30U; mreq.timeout_ms = (uint32_t)(HTTP_TOTAL_TIMEOUT_SEC * 1000L);
      const int rc = iot_mqtts_publish(&mreq, &tls);
      if (rc != IOT_OK) { (void)fprintf(stderr, "MQTTS publish failed: %d\n", rc); return 2; }
      (void)printf("OK: published (mTLS MQTTS) to %s:%d %s\n", mqtt_host, mqtt_port, topic);
    } else {
      /* Send via HTTPS (mTLS) */
      /* CE: verify the ingest edge with the local Vault-PKI CA chain. */
      tls.ca_chain = file_exists(PATH_CA_CHAIN) ? PATH_CA_CHAIN : NULL; tls.sni_name = NULL; /* SNI from URL */
      iot_http_req_t hreq; (void)memset(&hreq, 0, sizeof(hreq));
      hreq.url = url; hreq.body = json_buf; hreq.body_len = strlen(json_buf); hreq.api_key = NULL; hreq.timeout_ms = (uint32_t)(HTTP_TOTAL_TIMEOUT_SEC * 1000L);
      const int rc = iot_https_post(&hreq, &tls);
      if (rc != IOT_OK) { (void)fprintf(stderr, "HTTPS mTLS POST failed: %d\n", rc); return 2; }
      (void)printf("OK: sent telemetry (mTLS HTTPS) to %s\n", url);
    }

    if (duration_sec == 0) break;
    {
      struct timespec ts; ts.tv_sec = (time_t)(interval_ms / 1000); ts.tv_nsec = (long)((interval_ms % 1000) * 1000000L);
      (void)nanosleep(&ts, NULL);
    }
  } while ((time(NULL) - start) < duration_sec);
  return 0;
}
