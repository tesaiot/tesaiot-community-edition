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
 * Minimal flexible data schema → JSON (MISRA-C 2004 style)
 *
 * Tutorial focus: demonstrate how to turn a lightweight sensor schema into a
 * JSON payload without relying on heavy external libraries.  The helpers keep
 * direct control over formatting so developers can trace every byte that goes
 * on the wire.
 */

#include "data_schema.h"

#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <stdlib.h>

#define JSON_SAFE_APPEND(rc) do { if ((rc) < 0) { return -1; } pos += (size_t)(rc); if (pos >= out_size) { return -1; } } while (0)

/* Default payload skeleton so first run succeeds even without schema file */
static schema_field_t default_fields[] = {
    { "temperature", SCHEMA_F64, { .f64 = 25.0 } },
    { "status",      SCHEMA_STR, { .str = "ok" } },
    { "motion",      SCHEMA_BOOL,{ .b   = 0U } }
};

void schema_init(schema_document_t * doc, schema_field_t * fields, size_t field_count)
{
    if ((doc == NULL) || (fields == NULL)) {
        return;
    }
    doc->timestamp_ms = 0U;
    doc->fields = (field_count > 0U) ? fields : default_fields;
    doc->field_count = (field_count > 0U) ? field_count : (sizeof(default_fields) / sizeof(default_fields[0]));
}

void schema_update_timestamp(schema_document_t * doc, uint64_t ts_ms)
{
    if (doc != NULL) {
        doc->timestamp_ms = ts_ms;
    }
}

/*
 * append_quoted — write a JSON string with escaping into `out`.
 * We stay explicit instead of using printf-format specifiers so readers learn
 * how control characters and quotes are handled.
 */
static int append_quoted(char * out, size_t out_size, size_t * pos, const char * s)
{
    if ((out == NULL) || (pos == NULL)) {
        return -1;
    }
    size_t p = *pos; int rc = snprintf(&out[p], (out_size > p) ? (out_size - p) : 0U, "\"");
    if (rc < 0) { return -1; } p += (size_t)rc; if (p >= out_size) { return -1; }
    for (size_t i = 0U; (s != NULL) && (s[i] != '\0'); ++i) {
        const char c = s[i];
        if ((c == '"') || (c == '\\')) {
            rc = snprintf(&out[p], (out_size > p) ? (out_size - p) : 0U, "\\%c", (int)c);
        } else if ((unsigned char)c < 0x20U) {
            rc = snprintf(&out[p], (out_size > p) ? (out_size - p) : 0U, "\\u%04x", (unsigned int)c);
        } else {
            rc = snprintf(&out[p], (out_size > p) ? (out_size - p) : 0U, "%c", (int)c);
        }
        if (rc < 0) {
            return -1;
        }
        p += (size_t)rc; if (p >= out_size) { return -1; }
    }
    rc = snprintf(&out[p], (out_size > p) ? (out_size - p) : 0U, "\"");
    if (rc < 0) {
        return -1;
    }
    p += (size_t)rc; if (p >= out_size) { return -1; }
    *pos = p;
    return 0;
}

/*
 * schema_to_json — serialise fields into a single JSON object.
 * Out buffer is preallocated by caller; we return -1 if anything would exceed
 * the limit so callers learn to size their buffers conservatively.
 */
int schema_to_json(const schema_document_t * doc, char * out, size_t out_size)
{
    size_t pos = 0U; int rc;
    if ((doc == NULL) || (out == NULL) || (out_size < 8U)) {
        return -1;
    }
    rc = snprintf(&out[pos], out_size, "{"); JSON_SAFE_APPEND(rc);
    for (size_t i = 0U; i < doc->field_count; ++i) {
        const schema_field_t * f = &doc->fields[i];
        if (i > 0U) { rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U, ","); JSON_SAFE_APPEND(rc); }
        (void)append_quoted(out, out_size, &pos, f->name);
        rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U, ":"); JSON_SAFE_APPEND(rc);
        switch (f->type) {
            case SCHEMA_F64:
                rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U, "%g", f->value.f64);
                break;
            case SCHEMA_I32:
                rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U, "%ld", (long)f->value.i32);
                break;
            case SCHEMA_BOOL:
                rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U, "%s", (f->value.b!=0U)?"true":"false");
                break;
            case SCHEMA_STR:
                (void)append_quoted(out, out_size, &pos, f->value.str);
                rc = 0;
                break;
            case SCHEMA_OBJ3:
                rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U,
                              "{\"x\":%g,\"y\":%g,\"z\":%g}",
                              f->value.obj3.x, f->value.obj3.y, f->value.obj3.z);
                break;
            default:
                rc = -1;
                break;
        }
        JSON_SAFE_APPEND(rc);
    }
    rc = snprintf(&out[pos], (out_size > pos)?(out_size - pos):0U, "}"); JSON_SAFE_APPEND(rc);
    return 0;
}

/* Small monotonic clock helper used by the tutorials for timestamps. */
uint64_t schema_get_monotonic_ms(void)
{
    struct timeval tv;
    if (gettimeofday(&tv, NULL) != 0) {
        return 0U;
    }
    return ((uint64_t)tv.tv_sec * 1000ULL) + ((uint64_t)tv.tv_usec / 1000ULL);
}
