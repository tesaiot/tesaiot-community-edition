# =============================================================================
# TESAIoT Community Edition - Makefile
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Thin wrapper over docker compose + ./scripts/*. Run `make help`.
# =============================================================================

SHELL        := /bin/bash
COMPOSE      := docker compose
SCRIPTS      := ./scripts
# Override a single service for logs/restart:  make logs s=api
s            ?=

.DEFAULT_GOAL := help

.PHONY: help install set-domain up down restart logs ps health secrets \
        init-pki init-db init-emqx init-apisix preflight build pull backup restore \
        clean teardown unseal

help: ## Show this help
	@echo "TESAIoT Community Edition - make targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## One-command bootstrap (builds from source). Add PREBUILT=1 to pull pre-built images.
	@$(SCRIPTS)/install.sh $(if $(DOMAIN),--domain=$(DOMAIN),) $(if $(PREBUILT),--prebuilt,)

set-domain: ## Set/change the public domain in one place: make set-domain DOMAIN=iot.acme.com
	@test -n "$(DOMAIN)" || { echo "usage: make set-domain DOMAIN=iot.acme.com"; exit 1; }
	@$(SCRIPTS)/generate-secrets.sh --domain=$(DOMAIN)
	@# `up -d` (NOT `restart`): restart never re-reads .env, so the recreated
	@# env (TESA_PUBLIC_*, EMQX_CERT_*) would not reach the containers.
	@$(COMPOSE) up -d
	@echo "Domain wired and services recreated. If Vault PKI is initialised, re-run: make init-pki  (re-appends the client-CA chain for the regenerated cert)"

preflight: ## Check host prerequisites (docker, ports, disk, .env)
	@$(SCRIPTS)/preflight-check.sh

secrets: ## Generate .env, mongo keyfile, first-run TLS certs
	@$(SCRIPTS)/generate-secrets.sh $(if $(DOMAIN),--domain=$(DOMAIN),)

build: ## Build all service images from source
	@$(COMPOSE) build

pull: ## Pull pre-built images from the registry (api, admin-ui, mqtt-bridge)
	@$(COMPOSE) pull api admin-ui mqtt-bridge

up: ## Start the full stack
	@$(COMPOSE) up -d

down: ## Stop and remove containers (data kept)
	@$(COMPOSE) down

restart: ## Restart all services (or one: make restart s=api)
	@$(COMPOSE) restart $(s)

logs: ## Tail logs for all services (or one: make logs s=api)
	@$(COMPOSE) logs -f --tail=200 $(s)

ps: ## Show container status
	@$(COMPOSE) ps

health: ## Probe all services and print a status table
	@$(SCRIPTS)/healthcheck.sh

smoke: ## End-to-end smoke test (login, device, telemetry, MQTT, gateways)
	@python3 $(SCRIPTS)/smoke-test.py

init-pki: ## Initialise / unseal Vault and build the PKI hierarchy
	@$(SCRIPTS)/init-vault-pki.sh

unseal: ## Manually unseal Vault after a reboot (uses VAULT_UNSEAL_KEY_* from .env)
	@$(SCRIPTS)/unseal-vault.sh

init-db: ## Initialise MongoDB replica set + verify TimescaleDB hypertable
	@$(SCRIPTS)/init-databases.sh

init-emqx: ## Provision EMQX broker auth (internal bridge user)
	@$(SCRIPTS)/init-emqx.sh

init-apisix: ## Sync admin key + verify APISIX routes
	@$(SCRIPTS)/init-apisix-routes.sh

backup: ## Dump databases + secrets to ./backups/
	@$(SCRIPTS)/backup.sh

restore: ## Restore from a backup:  make restore FILE=backups/xxx.tar.gz
	@test -n "$(FILE)" || { echo "usage: make restore FILE=backups/xxx.tar.gz"; exit 1; }
	@$(SCRIPTS)/restore.sh "$(FILE)"

teardown: ## Stop stack (data kept). Add MODE=volumes or MODE=purge
	@$(SCRIPTS)/teardown.sh $(if $(MODE),--$(MODE),)

clean: ## Remove containers, networks AND volumes (DESTROYS DATA)
	@$(SCRIPTS)/teardown.sh --volumes
