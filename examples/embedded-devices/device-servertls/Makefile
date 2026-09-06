# TESA IoT — Unified device client (Server‑TLS) using Mongoose (HTTPS/MQTTS)

.PHONY: all clean help deps servertls run run-https run-mqtts prepare legacy-c

OS := $(shell uname -s)
UNAME_M := $(shell uname -m)
ARCH ?= $(UNAME_M)
TLS_BACKEND ?= openssl # openssl | mbedtls | wolfssl
TLS_BACKEND := $(strip $(TLS_BACKEND))

COMMON_DIR := $(CURDIR)/../common-c
# mg_fetch.mk defines 'deps' and is included before 'all' is declared, so
# without this a bare `make` selects 'deps' — which only prints how to
# install a TLS library and builds nothing.
.DEFAULT_GOAL := all
include $(COMMON_DIR)/mg_fetch.mk

TARGET ?= device_client
SRC := \
  main.c \
  data_schema.c \
  $(COMMON_DIR)/iot_mongoose_client.c \
  $(COMMON_DIR)/mongoose.c

OBJ := $(SRC:.c=.o)

CC ?= cc
CXX ?= c++
CFLAGS ?= -std=c99 -Wall -Wextra -Wconversion -Wsign-conversion -Wmissing-prototypes -Werror=implicit-function-declaration -O2
CFLAGS += -I$(COMMON_DIR)
LDFLAGS ?=

# TLS backend selection
ifeq ($(TLS_BACKEND),openssl)
  CFLAGS += -DMG_ENABLE_OPENSSL=1 -DMG_TLS=MG_TLS_OPENSSL
  ifeq ($(OS),Darwin)
    OPENSSL_PREFIX ?= $(shell brew --prefix openssl@3 2>/dev/null)
    ifneq ($(OPENSSL_PREFIX),)
      CFLAGS += -I$(OPENSSL_PREFIX)/include
      LDFLAGS += -L$(OPENSSL_PREFIX)/lib
    endif
  endif
  LDLIBS += -lssl -lcrypto
else ifeq ($(TLS_BACKEND),mbedtls)
  CFLAGS += -DMG_ENABLE_MBEDTLS=1 -DMG_TLS=MG_TLS_MBED
  LDLIBS += -lmbedtls -lmbedx509 -lmbedcrypto
else ifeq ($(TLS_BACKEND),wolfssl)
  CFLAGS += -DMG_ENABLE_WOLFSSL=1 -DMG_TLS=MG_TLS_WOLFSSL
  LDLIBS += -lwolfssl
else
  $(error Unknown TLS_BACKEND '$(TLS_BACKEND)')
endif

# Platform specifics
ifeq ($(OS),Linux)
  CFLAGS += -D_POSIX_C_SOURCE=200809L -D_GNU_SOURCE
  LDLIBS += -lpthread -ldl
endif
ifeq ($(OS),Darwin)
  LDLIBS += -lpthread
endif

all: $(TARGET)

$(TARGET): deps $(OBJ)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJ) $(LDLIBS)

%.o: %.c config.h data_schema.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)

# Build (Server‑TLS implied by this example)
servertls: all

# Run helpers (set CERTS_DIR to your prepared credentials directory)
RUN_STLS_BASE ?= https://localhost
RUN_MQTT_HOST ?= localhost
RUN_MQTT_PORT ?= 8884

run: run-https

run-https: all
	COMM_MODE=HTTPS API_BASE_URL=$(RUN_STLS_BASE) CERTS_DIR=$(CURDIR)/certs_credentials ./$(TARGET)

run-mqtts: all
	COMM_MODE=MQTTS MQTT_HOST=$(RUN_MQTT_HOST) MQTT_PORT=$(RUN_MQTT_PORT) CERTS_DIR=$(CURDIR)/certs_credentials ./$(TARGET)

# Backward-compat target name
.PHONY: device_https
device_https: $(TARGET)

# Prepare credentials from tutorial/download into local example folder
SCRIPT        := ./scripts/sync_credentials.sh
LOCAL_DL      := $(CURDIR)/download
DOWNLOAD_ROOT ?= $(CURDIR)/../../device-to-platform/download
DEVICE02_DIR  ?= $(if $(wildcard $(LOCAL_DL)/device02),$(LOCAL_DL)/device02,$(DOWNLOAD_ROOT)/device02)

prepare:
	@echo "[prepare] DEVICE02_DIR=$(DEVICE02_DIR)"
	$(SCRIPT) --device-dir "$(DEVICE02_DIR)" --dest-dir "$(CURDIR)/certs_credentials"

# Legacy helpers (optional): build old ./c clients
legacy-c:
	$(MAKE) -C c all

help:
	@echo "Targets:"
	@echo "  all            Build $(TARGET) (TLS_BACKEND=$(TLS_BACKEND))"
	@echo "  run-https      Run HTTPS mode (COMM_MODE=HTTPS)"
	@echo "  run-mqtts      Run MQTTS mode (COMM_MODE=MQTTS)"
	@echo "  prepare        Sync credentials into ./certs_credentials"
	@echo "Variables: TLS_BACKEND=openssl|mbedtls|wolfssl, ARCH=linux|darwin|rpi|rtos"
	@echo "  deps           Print platform-specific dependencies"

deps:
	@echo "[deps] Detected OS=$(OS) ARCH=$(ARCH) TLS_BACKEND=$(TLS_BACKEND)"
	@if [ "$(OS)" = "Linux" ]; then \
	  if echo "$(ARCH)" | grep -qiE 'arm|aarch64'; then \
	    echo "# Embedded Linux / Raspberry Pi (Debian/Ubuntu)"; \
	  else \
	    echo "# Linux (Debian/Ubuntu)"; \
	  fi; \
	  if [ "$(TLS_BACKEND)" = "openssl" ]; then \
	    echo "sudo apt-get update && sudo apt-get install -y build-essential pkg-config libssl-dev"; \
	  elif [ "$(TLS_BACKEND)" = "mbedtls" ]; then \
	    echo "sudo apt-get update && sudo apt-get install -y build-essential pkg-config libmbedtls-dev"; \
	  else \
	    echo "sudo apt-get update && sudo apt-get install -y build-essential pkg-config libwolfssl-dev"; \
	  fi; \
	fi
	@if [ "$(OS)" = "Darwin" ]; then \
	  echo "# macOS (Homebrew)"; \
	  echo "brew install openssl@3"; \
	  echo "# If not found automatically, export CPPFLAGS/LDFLAGS:"; \
	  echo "#   export CPPFLAGS=\`brew --prefix openssl@3\`/include"; \
	  echo "#   export LDFLAGS=\"-L\`brew --prefix openssl@3\`/lib\""; \
	fi
