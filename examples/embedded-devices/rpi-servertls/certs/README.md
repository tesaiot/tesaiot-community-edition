# TLS certificates (not committed)

Place the CE private-PKI CA bundle here so the client can verify the broker/edge:

```bash
cp ../../../../config/tls/ca-bundle.pem ca.pem
```

`ca.pem` is git-ignored. Never commit device credentials or private keys.
