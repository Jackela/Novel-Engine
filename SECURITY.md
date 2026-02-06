# Security Policy

## Reporting a Vulnerability

Please report security issues via GitHub Security Advisories:

- Go to the repository's **Security** tab → **Advisories** → **New draft security advisory**.

If you cannot use GitHub Security Advisories, open a GitHub issue with **no sensitive details** and request a private contact channel.

## Supported Versions

This project is under active development. Security fixes are applied to the default branch.

---

## API Key Storage Security

### Encryption at Rest

All API keys stored via the Brain Settings API are encrypted at rest using Fernet symmetric encryption (AES-128-CBC with HMAC).

**Required Configuration:**

```bash
BRAIN_SETTINGS_ENCRYPTION_KEY=<your-fernet-key>
```

**Generate a secure key:**

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

**Key Rotation:**

To rotate your encryption key:

1. Set the new `BRAIN_SETTINGS_ENCRYPTION_KEY`
2. Re-enter your API keys via the `/api/brain/settings/api-keys` endpoint
3. Old encrypted values will be inaccessible and can be safely discarded

### Security Guarantees

- ✅ API keys are never stored in plaintext
- ✅ API keys are never logged (only masked representations: `sk-1234•••••••xyz`)
- ✅ API responses only show masked keys (first 8 and last 4 characters)
- ✅ Encryption is required for API key storage (503 error if key not set)
- ✅ Invalid encryption keys are rejected with a clear error message

### Configuration Checklist

- [ ] `BRAIN_SETTINGS_ENCRYPTION_KEY` is set in production environment
- [ ] The encryption key is stored securely (e.g., AWS Secrets Manager, HashiCorp Vault)
- [ ] The encryption key is unique per deployment/environment
- [ ] API keys are never committed to version control
- [ ] `.env` file is in `.gitignore`

### Testing Security

Run the security tests to verify encryption behavior:

```bash
pytest tests/unit/api/routers/test_brain_settings_security.py -v
```

Tests verify:
- Encrypted storage of API keys
- Masked output in responses
- No raw keys in logs
- Graceful failure when encryption key is not set
- Round-trip encryption/decryption
