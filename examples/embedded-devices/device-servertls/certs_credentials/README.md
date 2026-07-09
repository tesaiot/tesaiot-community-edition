# Certificate Credentials

This directory should contain your certificate bundle downloaded from TESAIoT Admin UI.

## How to Get Certificates

1. Log in to [TESAIoT Admin UI](https://admin.tesaiot.com)
2. Navigate to **Devices** > Select your device
3. Click **Download Credentials Bundle**
4. Extract the bundle into this directory

## Required Files

For mTLS authentication:
- `ca-chain.pem` - CA certificate chain
- `client.pem` - Client certificate
- `client.key` - Private key (keep secret!)
- `endpoints.json` - Broker endpoints

## Security Warning

**NEVER commit certificates or private keys to version control!**

These files are already in .gitignore.
