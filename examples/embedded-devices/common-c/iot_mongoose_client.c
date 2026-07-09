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
 *
 * TESA IoT Platform Tutorial Sample — shared helpers for Mongoose clients.
 */

/*
 * Shared Mongoose-based client implementation
 *
 * This file provides the reusable building blocks for the C examples so that
 * each tutorial focuses on explaining the transport- or security-specific
 * behaviour.  Every exported function tries to answer three questions for the
 * reader: why the step is required, what it does, and how it achieves the
 * result with the Mongoose library.
 */

#include <string.h>
#include <stdio.h>
#include <time.h>
#include <stdlib.h>

#include "iot_mongoose_client.h"
#include "mongoose.h"

/* Internal helpers */
/*
 * Quick utility to check whether a string is either NULL or empty.  We use it
 * to guard optional configuration fields so that the code stays defensive when
 * tutorial readers experiment with trimming parameters.
 */
static int is_null_or_empty(const char * s) { return (s == NULL) || (s[0] == '\0'); }

static char *read_file_alloc(const char *path, size_t *out_len) {
  FILE *f = NULL; char *buf = NULL; long n = 0;
  if (out_len != NULL) *out_len = 0;
  if (is_null_or_empty(path)) return NULL;
  f = fopen(path, "rb"); if (f == NULL) return NULL;
  if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
  n = ftell(f); if (n <= 0) { fclose(f); return NULL; }
  if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); return NULL; }
  buf = (char *) malloc((size_t)n + 1U); if (buf == NULL) { fclose(f); return NULL; }
  if (fread(buf, 1U, (size_t)n, f) != (size_t)n) { free(buf); fclose(f); return NULL; }
  fclose(f); buf[n] = '\0'; if (out_len != NULL) *out_len = (size_t)n; return buf;
}

/* ========================= HTTPS ========================= */

struct http_ctx_s {
  const iot_http_req_t * req;
  const iot_tls_conf_t * tls;
  int done;
  int result;
  int status_code;
};

static void http_ev_handler(struct mg_connection * c, int ev, void * ev_data)
{
  struct http_ctx_s * ctx = (struct http_ctx_s *) c->fn_data;
  (void) ev_data;
  if (ctx == NULL) { return; }

  if (ev == MG_EV_CONNECT) {
    const char * url = ctx->req->url;
    struct mg_str h = mg_url_host(url);
    const char * uri = mg_url_uri(url);
    unsigned long bl = (unsigned long) ctx->req->body_len;

    /* Initialize TLS with provided certs/keys */
    if (ctx->tls != NULL) {
      struct mg_tls_opts topts;
      (void) memset(&topts, 0, sizeof(topts));
      /* Read certificate/key files into memory buffers (Mongoose expects PEM/DER contents) */
      char *ca_mem = NULL, *cert_mem = NULL, *key_mem = NULL; size_t ca_len = 0, cert_len = 0, key_len = 0;
      if (!is_null_or_empty(ctx->tls->ca_chain))   { ca_mem   = read_file_alloc(ctx->tls->ca_chain,   &ca_len); }
      if (!is_null_or_empty(ctx->tls->client_cert)) { cert_mem = read_file_alloc(ctx->tls->client_cert, &cert_len); }
      if (!is_null_or_empty(ctx->tls->client_key))  { key_mem  = read_file_alloc(ctx->tls->client_key,  &key_len); }
      if (ca_mem   != NULL) { topts.ca   = mg_str_n(ca_mem,   ca_len); }
      if (cert_mem != NULL) { topts.cert = mg_str_n(cert_mem, cert_len); }
      if (key_mem  != NULL) { topts.key  = mg_str_n(key_mem,  key_len); }
      topts.name = (!is_null_or_empty(ctx->tls->sni_name)) ? mg_str(ctx->tls->sni_name) : h;
      topts.skip_verification = (ctx->tls->verify_peer == 0U) ? 1 : 0;
      mg_tls_init(c, &topts);
      free(ca_mem); free(cert_mem); free(key_mem);
    }

    /* Build and send HTTP POST */
    if (ctx->req->api_key != NULL) {
      mg_printf(c,
        "POST %s HTTP/1.1\r\n"
        "Host: %.*s\r\n"
        "Content-Type: application/json\r\n"
        "X-API-KEY: %s\r\n"
        "Content-Length: %lu\r\n\r\n",
        uri, (int)h.len, h.buf, ctx->req->api_key, bl);
    } else {
      mg_printf(c,
        "POST %s HTTP/1.1\r\n"
        "Host: %.*s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %lu\r\n\r\n",
        uri, (int)h.len, h.buf, bl);
    }
    mg_send(c, ctx->req->body, ctx->req->body_len);
  } else if (ev == MG_EV_HTTP_MSG) {
    struct mg_http_message * hm = (struct mg_http_message *) ev_data;
    int code = mg_http_status(hm);
    ctx->status_code = code;
    ctx->result = (code >= 200 && code < 300) ? IOT_OK : IOT_ERR_HTTP;
    ctx->done = 1;
    c->is_closing = 1;
  } else if (ev == MG_EV_ERROR) {
    ctx->result = IOT_ERR_PROTO;
    ctx->done = 1;
    c->is_closing = 1;
  }
}

int iot_https_post(const iot_http_req_t * req, const iot_tls_conf_t * tls)
{
  if ((req == NULL) || (req->url == NULL) || (req->body == NULL)) { return IOT_ERR_ARG; }

  struct mg_mgr mgr;
  struct http_ctx_s ctx;
  (void) memset(&ctx, 0, sizeof(ctx));
  ctx.req = req; ctx.tls = tls; ctx.done = 0; ctx.result = IOT_ERR_TIMEOUT; ctx.status_code = 0;

  mg_mgr_init(&mgr);
  if (mg_http_connect(&mgr, req->url, http_ev_handler, &ctx) == NULL) {
    mg_mgr_free(&mgr);
    return IOT_ERR_CONNECT;
  }

  const uint32_t total_ms = (tls != NULL && tls->total_timeout_ms > 0U) ? tls->total_timeout_ms : 30000U;
  const uint64_t start = mg_millis();
  while ((ctx.done == 0) && ((mg_millis() - start) < (uint64_t) total_ms)) {
    mg_mgr_poll(&mgr, 100);
  }
  mg_mgr_free(&mgr);
  return ctx.done ? ctx.result : IOT_ERR_TIMEOUT;
}

/* ========================= MQTT ========================= */

struct mqtt_ctx_s {
  const iot_mqtt_req_t * req;
  const iot_tls_conf_t  * tls;
  uint16_t pub_id;
  int done;
  int result;
  int connack;
};

static void mqtt_ev_handler(struct mg_connection * c, int ev, void * ev_data)
{
  struct mqtt_ctx_s * ctx = (struct mqtt_ctx_s *) c->fn_data;

  if (ev == MG_EV_CONNECT) {
    if (ctx->tls != NULL) {
      struct mg_tls_opts topts; (void) memset(&topts, 0, sizeof(topts));
      char *ca_mem = NULL, *cert_mem = NULL, *key_mem = NULL; size_t ca_len = 0, cert_len = 0, key_len = 0;
      if (!is_null_or_empty(ctx->tls->ca_chain))   { ca_mem   = read_file_alloc(ctx->tls->ca_chain,   &ca_len); }
      if (!is_null_or_empty(ctx->tls->client_cert)){ cert_mem = read_file_alloc(ctx->tls->client_cert, &cert_len); }
      if (!is_null_or_empty(ctx->tls->client_key)) { key_mem  = read_file_alloc(ctx->tls->client_key,  &key_len); }
      if (ca_mem   != NULL) { topts.ca   = mg_str_n(ca_mem,   ca_len); }
      if (cert_mem != NULL) { topts.cert = mg_str_n(cert_mem, cert_len); }
      if (key_mem  != NULL) { topts.key  = mg_str_n(key_mem,  key_len); }
      if (!is_null_or_empty(ctx->tls->sni_name))   { topts.name = mg_str(ctx->tls->sni_name); }
      topts.skip_verification = (ctx->tls->verify_peer == 0U) ? 1 : 0;
      mg_tls_init(c, &topts);
      free(ca_mem); free(cert_mem); free(key_mem);
    }
  } else if (ev == MG_EV_MQTT_OPEN) {
    int * status = (int *) ev_data;
    ctx->connack = (status != NULL) ? *status : -1;
    if (ctx->connack != 0) {
      ctx->result = IOT_ERR_MQTT;
      ctx->done = 1; c->is_closing = 1; return;
    }
    /* Publish now */
    {
      struct mg_mqtt_opts mo; (void) memset(&mo, 0, sizeof(mo));
      mo.client_id = mg_str(ctx->req->client_id != NULL ? ctx->req->client_id : "");
      mo.user      = mg_str(ctx->req->username != NULL ? ctx->req->username : "");
      mo.pass      = mg_str(ctx->req->password != NULL ? ctx->req->password : "");
      mo.topic     = mg_str(ctx->req->topic);
      mo.message   = mg_str(ctx->req->payload);
      mo.qos       = ctx->req->qos;
      mo.retain    = (ctx->req->retain != 0U);
      mo.keepalive = ctx->req->keepalive_sec;
      ctx->pub_id = mg_mqtt_pub(c, &mo);
    }
  } else if (ev == MG_EV_MQTT_CMD) {
    struct mg_mqtt_message * mm = (struct mg_mqtt_message *) ev_data;
    if (mm != NULL && mm->cmd == MQTT_CMD_PUBACK) {
      if (mm->id == ctx->pub_id) {
        ctx->result = IOT_OK; ctx->done = 1; c->is_closing = 1;
      }
    }
  } else if (ev == MG_EV_ERROR) {
    ctx->result = IOT_ERR_PROTO; ctx->done = 1; c->is_closing = 1;
  } else if (ev == MG_EV_CLOSE) {
    if (ctx->done == 0) { ctx->result = IOT_ERR_CONNECT; ctx->done = 1; }
  }
}

int iot_mqtts_publish(const iot_mqtt_req_t * req, const iot_tls_conf_t * tls)
{
  if ((req == NULL) || is_null_or_empty(req->host) || is_null_or_empty(req->topic) || (req->payload == NULL)) {
    return IOT_ERR_ARG;
  }

  /* Build URL like mqtt://host:port */
  char url[320];
  (void) memset(url, 0, sizeof(url));
  (void) snprintf(url, sizeof(url), "mqtt://%s:%u", req->host, (unsigned) req->port);

  struct mg_mgr mgr; mg_mgr_init(&mgr);
  struct mqtt_ctx_s ctx; (void) memset(&ctx, 0, sizeof(ctx));
  ctx.req = req; ctx.tls = tls; ctx.done = 0; ctx.result = IOT_ERR_TIMEOUT; ctx.connack = -1; ctx.pub_id = 0;

  struct mg_mqtt_opts mo; (void) memset(&mo, 0, sizeof(mo));
  /* Login parameters go via mg_mqtt_connect opts; publish content is set in handler to reuse qos/retain */
  mo.client_id = mg_str(req->client_id != NULL ? req->client_id : "");
  mo.user      = mg_str(req->username != NULL ? req->username : "");
  mo.pass      = mg_str(req->password != NULL ? req->password : "");
  mo.keepalive = req->keepalive_sec;
  mo.clean     = true;
  mo.version   = 4; /* MQTT v3.1.1 by default */

  if (mg_mqtt_connect(&mgr, url, &mo, mqtt_ev_handler, &ctx) == NULL) {
    mg_mgr_free(&mgr);
    return IOT_ERR_CONNECT;
  }

  const uint32_t total_ms = (req->timeout_ms > 0U) ? req->timeout_ms : (tls != NULL && tls->total_timeout_ms > 0U ? tls->total_timeout_ms : 30000U);
  const uint64_t start = mg_millis();
  while ((ctx.done == 0) && ((mg_millis() - start) < (uint64_t) total_ms)) {
    mg_mgr_poll(&mgr, 100);
  }
  mg_mgr_free(&mgr);
  return ctx.done ? ctx.result : IOT_ERR_TIMEOUT;
}
