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
 * Minimal flexible data schema → JSON helper.
 * Structured identical to the mTLS example so developers can compare the
 * security modes side-by-side without re-learning the data layer.
 */

#ifndef TESA_DATA_SCHEMA_H
#define TESA_DATA_SCHEMA_H

#include <stddef.h>
#include <stdint.h>

typedef enum { SCHEMA_F64=0, SCHEMA_I32, SCHEMA_BOOL, SCHEMA_STR, SCHEMA_OBJ3 } schema_type_t;
typedef struct { double x; double y; double z; } schema_obj3_t;

typedef struct {
    const char * name;
    schema_type_t type;
    union { double f64; int32_t i32; uint32_t b; const char * str; schema_obj3_t obj3; } value;
} schema_field_t;

typedef struct {
    uint64_t timestamp_ms;
    schema_field_t * fields;
    size_t field_count;
} schema_document_t;

void schema_init(schema_document_t * doc, schema_field_t * fields, size_t field_count);
void schema_update_timestamp(schema_document_t * doc, uint64_t ts_ms);
int schema_to_json(const schema_document_t * doc, char * out, size_t out_size);
uint64_t schema_get_monotonic_ms(void);

#endif /* TESA_DATA_SCHEMA_H */
