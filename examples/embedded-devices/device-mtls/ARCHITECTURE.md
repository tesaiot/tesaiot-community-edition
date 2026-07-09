# Device Mutual TLS Architecture (C)

## Overview

C-based MQTT client with Mutual TLS (mTLS) - both client and server authenticate using X.509 certificates.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      C Application                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │     main.c      │───▶│  mqtt_mtls.c    │                     │
│  │  (Entry Point)  │    │  (Paho MQTT C)  │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                              │
│           ▼                      ▼                              │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ cert_manager.c  │───▶│  tls_mtls.c     │                     │
│  │ (Load Certs)    │    │  (OpenSSL mTLS) │                     │
│  └─────────────────┘    └─────────┬───────┘                     │
│                                   │                             │
└───────────────────────────────────┼─────────────────────────────┘
                                    │
           Mutual TLS               │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        │                        ▼
┌──────────────────┐                │          ┌──────────────────┐
│ Client Cert      │                │          │ Server Cert      │
│ device.crt       │◀───────────────┼─────────▶│ (EMQX)           │
│ device.key       │                │          └──────────────────┘
└──────────────────┘                │
                                    ▼
                         ┌──────────────────────┐
                         │   TESAIoT Platform   │
                         │  ┌────────────────┐  │
                         │  │  Vault PKI     │  │
                         │  │  (Signs Certs) │  │
                         │  └────────────────┘  │
                         └──────────────────────┘
```

## Mutual TLS Handshake

```
Device                                         EMQX Broker
  │                                                  │
  │══════════ Phase 1: Server Authentication ═══════ │
  │                                                  │
  │──────────── ClientHello ───────────────────────▶ │
  │                                                  │
  │◀─────────── ServerHello + Server Certificate ─── │
  │                                                  │
  │  ┌─────────────────┐                             │
  │  │ Verify server   │                             │
  │  │ cert against CA │                             │
  │  └─────────────────┘                             │
  │                                                  │
  │══════════ Phase 2: Client Authentication ═══════ │
  │                                                  │
  │◀─────────── CertificateRequest ───────────────── │
  │                                                  │
  │──────────── Client Certificate ────────────────▶ │
  │──────────── CertificateVerify ─────────────────▶ │
  │                                                  │
  │              ┌─────────────────┐                 │
  │              │ Validate client │                 │
  │              │ cert with Vault │                 │
  │              └─────────────────┘                 │
  │                                                  │
  │══════════ Phase 3: Secure Channel ══════════════ │
  │                                                  │
  │──────────── Finished ──────────────────────────▶ │
  │◀─────────── Finished ─────────────────────────── │
  │                                                  │
  │══════════════ mTLS Established ═════════════════ │
  │                                                  │
```

## Certificate Chain

```
┌─────────────────────────────────────────────────┐
│              TESAIoT PKI Hierarchy              │
├─────────────────────────────────────────────────┤
│                                                 │
│    ┌───────────────────┐                        │
│    │     Root CA       │  (Offline, 10-20 yrs)  │
│    └─────────┬─────────┘                        │
│              │ Signs                            │
│              ▼                                  │
│    ┌───────────────────┐                        │
│    │  Intermediate CA  │  (Vault, 5-10 yrs)     │
│    └─────────┬─────────┘                        │
│              │ Signs                            │
│              ▼                                  │
│    ┌───────────────────┐                        │
│    │ Device Certificate│  (90-day rotation)     │
│    └───────────────────┘                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Certificate Files

| File | Format | Purpose |
|------|--------|---------|
| `ca.crt` | PEM | Root/Intermediate CA |
| `device.crt` | PEM | Device X.509 certificate |
| `device.key` | PEM | Private key (RSA/ECDSA) |

## Key Components

| Component | Description | File |
|-----------|-------------|------|
| Main Entry | Application orchestrator | `main.c` |
| MQTT Handler | Connection with mTLS | `mqtt_mtls.c` |
| Certificate Manager | Load and validate certs | `cert_manager.c` |
| TLS Config | OpenSSL mTLS setup | `tls_mtls.c` |

## OpenSSL Setup

```c
SSL_CTX *ctx = SSL_CTX_new(TLS_client_method());

// CA for server verification
SSL_CTX_load_verify_locations(ctx, "ca.crt", NULL);

// Client certificate and key
SSL_CTX_use_certificate_file(ctx, "device.crt", SSL_FILETYPE_PEM);
SSL_CTX_use_PrivateKey_file(ctx, "device.key", SSL_FILETYPE_PEM);

// Require mutual auth
SSL_CTX_set_verify(ctx, SSL_VERIFY_PEER, NULL);
```

## NCSA Compliance

| Level | Requirement | Implementation |
|-------|-------------|----------------|
| Level 2 | Mutual authentication | X.509 client certs |
| Level 2 | Key protection | File perms, encryption |
| Level 3 | Cert management | 90-day rotation |
| Level 3 | Audit trail | Cert serial in logs |
