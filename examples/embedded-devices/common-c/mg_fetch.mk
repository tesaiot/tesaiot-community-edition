# Helper to fetch Mongoose single-file library when missing

COMMON_DIR ?= $(dir $(lastword $(MAKEFILE_LIST)))
MONGOOSE_VERSION ?= 7.19
MONGOOSE_BASE ?= https://raw.githubusercontent.com/cesanta/mongoose/$(MONGOOSE_VERSION)
MONGOOSE_C := $(COMMON_DIR)/mongoose.c
MONGOOSE_H := $(COMMON_DIR)/mongoose.h

.PHONY: deps
deps: $(MONGOOSE_C) $(MONGOOSE_H)

$(MONGOOSE_C):
	@echo "Downloading mongoose.c (v$(MONGOOSE_VERSION)) ..."
	@curl -fsSL "$(MONGOOSE_BASE)/mongoose.c" -o "$@"

$(MONGOOSE_H):
	@echo "Downloading mongoose.h (v$(MONGOOSE_VERSION)) ..."
	@curl -fsSL "$(MONGOOSE_BASE)/mongoose.h" -o "$@"

