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
 * TESA IoT Platform — Unified device client (Server-TLS): HTTPS or MQTTS via Mongoose
 *
 * Server-TLS mode shows the same payload flow as the mTLS example but focuses on
 * API key handling and CA validation.  Comments emphasise why each step exists
 * so beginners can match the code with the onboarding instructions.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "config.h"
#include "data_schema.h"
#include "../common-c/iot_mongoose_client.h"

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

static void iso8601(char * out, size_t out_size)
{
  time_t now = time(NULL);
  struct tm g;
  (void)gmtime_r(&now, &g);
  (void)strftime(out, out_size, "%Y-%m-%dT%H:%M:%SZ", &g);
}

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

/* Minimal JSON-Schema parsing helpers (flat properties) */
static double frand01(void) { return (double) rand() / (double) RAND_MAX; }

/*
 * load_schema_fields — identical logic to the mTLS example so we can reuse the
 * documentation notes.  Generates plausible demo values from schema metadata.
 */
static int load_schema_fields(const char * schema_path, schema_field_t * out, size_t max_fields)
{
  FILE * f = fopen(schema_path, "rb"); if (!f) return -1;
  fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
  if (n <= 0 || n > 1024*1024) { fclose(f); return -1; }
  char * buf = (char *) malloc((size_t)n + 1U); if (!buf) { fclose(f); return -1; }
  if (fread(buf, 1U, (size_t)n, f) != (size_t)n) {
    fclose(f);
    free(buf);
    return -1;
  }
  fclose(f);
  buf[n]='\0';
  const char * props = strstr(buf, "\"properties\""); if (!props) { free(buf); return -1; }
  const char * p = strchr(props, '{'); if (!p) { free(buf); return -1; }
  size_t count = 0U;
  while (count < max_fields && (p = strchr(p, '"')) != NULL) {
    const char * ns = p+1; const char * ne = strchr(ns,'"'); if (!ne) break; size_t nl = (size_t)(ne-ns); if (nl==0 || nl>63) { p = ne?ne+1:ns; continue; }
    char name[64]; memcpy(name, ns, nl); name[nl]='\0'; if (strcasecmp(name, "timestamp")==0){ p = ne+1; continue; }
    const char * block = strchr(ne,'{'); if (!block) break;
    /* type */
    char type[16] = {0}; const char * tpos = strstr(block, "\"type\"");
    if (tpos) { const char * q1=strchr(tpos,'"'); q1=q1?strchr(q1+1,'"'):NULL; const char * q2=q1?strchr(q1+1,'"'):NULL; if(q1&&q2 && (size_t)(q2-q1-1)<sizeof(type)){ memcpy(type,q1+1,(size_t)(q2-q1-1)); type[q2-q1-1]='\0'; }}
    /* min/max */
    double vmin=0.0, vmax=100.0; int has_min=0,has_max=0; const char * mnp=strstr(block,"\"minimum\""); if(mnp){ const char * c=strchr(mnp,':'); if(c){ vmin=atof(c+1); has_min=1; }} const char * mxp=strstr(block,"\"maximum\""); if(mxp){ const char * c=strchr(mxp,':'); if(c){ vmax=atof(c+1); has_max=1; }} if(!has_min && !has_max){ vmin=0.0; vmax=100.0; }
    /* enum[0] for string */
    char enum0[32] = {0}; const char * enp=strstr(block,"\"enum\""); if(enp){ const char * b=strchr(enp,'['); const char * q=b?strchr(b,'"'):NULL; const char * qe=q?strchr(q+1,'"'):NULL; if(q&&qe && (size_t)(qe-q-1)<sizeof(enum0)){ memcpy(enum0,q+1,(size_t)(qe-q-1)); enum0[qe-q-1]='\0'; }}
    schema_field_t f; memset(&f,0,sizeof(f)); f.name=strdup(name);
    if (strcasecmp(type,"integer")==0){ f.type=SCHEMA_I32; int lo=(int)vmin; int hi=(int)vmax; if(hi<=lo) hi=lo+100; f.value.i32 = lo + (rand() % (hi-lo+1)); }
    else if (strcasecmp(type,"number")==0){ f.type=SCHEMA_F64; double r=vmin + frand01() * (vmax-vmin); f.value.f64=r; }
    else if (strcasecmp(type,"boolean")==0){ f.type=SCHEMA_BOOL; f.value.b=(rand()%2)?1U:0U; }
    else if (strcasecmp(type,"string")==0){ f.type=SCHEMA_STR; const char * sv= enum0[0]?enum0:"ok"; f.value.str=strdup(sv); }
    else { p = ne+1; continue; }
    out[count++] = f; p = ne+1;
  }
  free(buf); return (int)count;
}

static int is_mode_mqtts(void)
{
  const char * m = getenv("COMM_MODE");
  if (m == NULL) return 0;
  return (strcasecmp(m, "MQTTS") == 0) ? 1 : 0;
}

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
    ++i;
  }
}

/* main — glue code for Server-TLS path: load API key, send telemetry. */
int main(int argc, char **argv)
{
  char base[MAX_URL_SIZE]={0}, url[MAX_URL_SIZE]={0};
  char api_key[MAX_API_KEY_SIZE]={0};
  char dev_id[128]={0};
  char json[MAX_JSON_SIZE]={0};
  char endpoints[MAX_FILE_SIZE]={0};

  const char * certs_dir = getenv("CERTS_DIR");
  if (!certs_dir || !*certs_dir) certs_dir = PATH_CERTS_DIR;

  /* Resolve API base: ENV → endpoints.json → default */
  {
    const char * env_base = getenv("API_BASE_URL");
    if (env_base && *env_base) snprintf(base,sizeof(base),"%s",env_base);
    else {
      char p[512]; join_path(p,sizeof(p),certs_dir,FILE_ENDPOINTS_JSON);
      if (read_small_file(p,endpoints,sizeof(endpoints))==0) {
        if (parse_json_string_value(endpoints, "api_base_url", base, sizeof(base)) != 0) {
          (void)parse_json_string_value(endpoints, "ingest_base_url", base, sizeof(base));
        }
      }
      if (!base[0]) snprintf(base,sizeof(base),"%s",DEFAULT_API_BASE_URL);
    }
  }
  (void)snprintf(url,sizeof(url),"%s/api/v1/telemetry",base);

  /* Load API key and device id */
  {
    char pkey[512]; join_path(pkey,sizeof(pkey),certs_dir,FILE_API_KEY);
    if (read_small_file(pkey,api_key,sizeof(api_key))!=0) { fprintf(stderr,"Missing api_key.txt in %s\n", certs_dir); return 1; }
    for(size_t n=strlen(api_key); n>0 && (api_key[n-1]=='\n'||api_key[n-1]=='\r'||api_key[n-1]==' '); --n){ api_key[n-1]='\0'; }
    const char * env_id = getenv("DEVICE_ID");
    if (env_id && *env_id) snprintf(dev_id,sizeof(dev_id),"%s",env_id);
    else { char pid[512]; join_path(pid,sizeof(pid),certs_dir,FILE_DEVICE_ID); if (read_small_file(pid,dev_id,sizeof(dev_id))!=0) snprintf(dev_id,sizeof(dev_id),"%s",DEVICE_ID_SERVERTLS); for(size_t n=strlen(dev_id); n>0 && (dev_id[n-1]=='\n'||dev_id[n-1]=='\r'||dev_id[n-1]==' '); --n){ dev_id[n-1]='\0'; } }
  }

  /* MQTT creds (serverTLS often uses username/password) */
  char mqtt_user[256] = {0};
  char mqtt_pass[256] = {0};
  {
    char pu[512]; char pp[512];
    join_path(pu,sizeof(pu),certs_dir,"mqtt_username.txt");
    join_path(pp,sizeof(pp),certs_dir,"mqtt_password.txt");
    (void)read_small_file(pu,mqtt_user,sizeof(mqtt_user));
    (void)read_small_file(pp,mqtt_pass,sizeof(mqtt_pass));
    size_t n;
    n = strlen(mqtt_user); while (n>0U && (mqtt_user[n-1]=='\n'||mqtt_user[n-1]=='\r'||mqtt_user[n-1]==' ')) { mqtt_user[n-1]='\0'; --n; }
    n = strlen(mqtt_pass); while (n>0U && (mqtt_pass[n-1]=='\n'||mqtt_pass[n-1]=='\r'||mqtt_pass[n-1]==' ')) { mqtt_pass[n-1]='\0'; --n; }
  }

  /* Loop controls */
  int duration_sec = 0; int interval_ms = 1000;
  { const char *d=getenv("SEND_DURATION_SEC"), *i=getenv("SEND_INTERVAL_MS"); duration_sec = d?atoi(d):0; interval_ms = i?atoi(i):1000; if(duration_sec<0) duration_sec=0; if(interval_ms<=0) interval_ms=1000; }

  /* MQTT host/port if used; endpoints may override, CLI later overrides env/endpoints */
  char mqtt_host[128] = {0};
  int  mqtt_port = (int) DEFAULT_MQTT_PORT;
  {
    const char * eh = getenv("MQTT_HOST");
    const char * ep = getenv("MQTT_PORT");
    if (eh != NULL && eh[0] != '\0') (void)snprintf(mqtt_host, sizeof(mqtt_host), "%s", eh);
    if (ep != NULL && ep[0] != '\0') { int p = atoi(ep); if (p > 0 && p < 65536) mqtt_port = p; }
    if (mqtt_host[0] == '\0') {
      if (endpoints[0] != '\0') {
        (void)parse_json_string_value(endpoints, "mqtt_host", mqtt_host, sizeof(mqtt_host));
        int mp = 0; if (parse_json_int_value(endpoints, "mqtt_tls_port", &mp) == 0) { if (mp > 0 && mp < 65536) mqtt_port = mp; }
      }
      if (mqtt_host[0] == '\0') (void)snprintf(mqtt_host, sizeof(mqtt_host), "%s", DEFAULT_MQTT_HOST);
    }
  }

  /* CLI overrides */
  {
    int force_mqtts = -1;
    apply_cli_overrides(argc, argv, &duration_sec, &interval_ms, &force_mqtts, mqtt_host, sizeof(mqtt_host), &mqtt_port);
    if (force_mqtts == 1) setenv("COMM_MODE", "MQTTS", 1);
    else if (force_mqtts == 0) setenv("COMM_MODE", "HTTPS", 1);
  }

  /* Mongoose TLS conf */
  iot_tls_conf_t tls; (void)memset(&tls, 0, sizeof(tls));
  tls.ca_chain = file_exists(PATH_CA_CHAIN) ? PATH_CA_CHAIN : NULL;
  tls.client_cert = NULL; tls.client_key = NULL; /* serverTLS */
  tls.verify_peer = 1U; tls.connect_timeout_ms = (uint32_t)(HTTP_CONNECT_TIMEOUT_SEC * 1000L); tls.total_timeout_ms = (uint32_t)(HTTP_TOTAL_TIMEOUT_SEC * 1000L);

  srand((unsigned int)time(NULL));
  const time_t start = time(NULL);
  do {
    /* Build JSON data block from schema if available, otherwise fallback */
    char ts[32]; iso8601(ts,sizeof(ts));
    schema_field_t fields[64]; size_t fc=0U;
    char schema_path[512]={0};
    const char * schema_env = getenv("SCHEMA_PATH");
    if (schema_env && schema_env[0] != '\0') snprintf(schema_path,sizeof(schema_path),"%s",schema_env);
    else {
      const char * cc = strstr(certs_dir, "/certs_credentials");
      if (cc){ size_t len=(size_t)(cc-certs_dir); memcpy(schema_path, certs_dir, len); schema_path[len]='\0'; }
      else snprintf(schema_path,sizeof(schema_path),"%s",certs_dir);
      size_t l=strlen(schema_path); if (l + strlen("/download/data_schema.txt") + 1 < sizeof(schema_path)) strcat(schema_path, "/download/data_schema.txt");
    }
    int nfields = load_schema_fields(schema_path, fields, 64);
    if (nfields <= 0){
      const double temp = 29.0 + ((double)(rand()%40))/10.0; const int humidity = 50 + (rand()%20);
      fields[fc++] = (schema_field_t){ "temperature", SCHEMA_F64, { .f64 = temp } };
      fields[fc++] = (schema_field_t){ "humidity",    SCHEMA_I32, { .i32 = humidity } };
    } else {
      fc = (size_t) nfields;
    }
    schema_document_t doc; schema_init(&doc, fields, fc);
    char data_json[MAX_JSON_SIZE]; memset(data_json, 0, sizeof(data_json));
    if (schema_to_json(&doc, data_json, sizeof(data_json)) != 0) { fprintf(stderr, "Failed to build JSON\n"); return 1; }
    if (snprintf(json, sizeof(json), "{\"device_id\":\"%s\",\"timestamp\":\"%s\",\"data\":%s}", dev_id, ts, data_json) >= (int)sizeof(json)) { fprintf(stderr, "JSON too long\n"); return 1; }

    if (is_mode_mqtts() != 0) {
      /* MQTTS (Server‑TLS): username/password + CA verify */
      char topic[MAX_TOPIC_SIZE]; (void)snprintf(topic, sizeof(topic), "device/%s/telemetry", dev_id);
      iot_mqtt_req_t mreq; (void)memset(&mreq, 0, sizeof(mreq));
      mreq.host = mqtt_host; mreq.port = (uint16_t)mqtt_port; mreq.client_id = dev_id;
      mreq.username = (mqtt_user[0] != '\0') ? mqtt_user : dev_id; /* fallback to device_id */
      mreq.password = (mqtt_pass[0] != '\0') ? mqtt_pass : NULL;
      mreq.topic = topic; mreq.payload = json; mreq.payload_len = strlen(json);
      mreq.qos = 1U; mreq.retain = 0U; mreq.keepalive_sec = 30U; mreq.timeout_ms = (uint32_t)(HTTP_TOTAL_TIMEOUT_SEC * 1000L);
      tls.sni_name = mqtt_host;
      const int rc = iot_mqtts_publish(&mreq, &tls);
      if (rc != IOT_OK) { (void)fprintf(stderr, "MQTTS publish failed: %d\n", rc); return 2; }
      (void)printf("OK: published (Server‑TLS MQTTS) to %s:%d %s\n", mqtt_host, mqtt_port, topic);
    } else {
      /* HTTPS (Server‑TLS): X-API-KEY, verified against the CE private-PKI CA.
         The cloud build trusted the public OS CA for tesaiot.com; Community
         Edition's nginx edge is signed by the local Vault/bootstrap CA, so we
         must keep our own ca-chain.pem and leave verify_peer on. SNI is derived
         from the request URL by Mongoose. */
      tls.ca_chain = file_exists(PATH_CA_CHAIN) ? PATH_CA_CHAIN : NULL;
      tls.sni_name = NULL;
      iot_http_req_t hreq; (void)memset(&hreq, 0, sizeof(hreq));
      hreq.url = url; hreq.body = json; hreq.body_len = strlen(json);
      /* For Server‑TLS HTTPS, send only X-API-KEY (omit Bearer) */
      hreq.api_key = api_key; /* include device API key header */
      hreq.timeout_ms = (uint32_t)(HTTP_TOTAL_TIMEOUT_SEC * 1000L);
      const int rc = iot_https_post(&hreq, &tls);
      if (rc != IOT_OK) { (void)fprintf(stderr, "HTTPS POST failed: %d\n", rc); return 2; }
      (void)printf("OK: sent telemetry to %s\n", url);
    }

    if (duration_sec == 0) break;
    usleep((unsigned int)(interval_ms * 1000));
  } while ((time(NULL) - start) < duration_sec);
  return 0;
}
