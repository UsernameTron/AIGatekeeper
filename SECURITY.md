# Security Configuration Guide

## Overview

The AI Gatekeeper system requires proper configuration of secrets and environment variables to ensure security. This guide explains how to configure the system securely.

## Required Secrets

### All Environments

1. **OPENAI_API_KEY** (required)
   - OpenAI API key for AI models
   - Format: `sk-...` (starts with 'sk-')
   - Minimum length: 20 characters
   - Example: `export OPENAI_API_KEY="sk-proj-abc123..."`

2. **JWT_SECRET_KEY** (required)
   - Secret key for JWT token signing
   - Minimum length: 32 characters
   - Use a cryptographically secure random string
   - Example: `export JWT_SECRET_KEY="$(openssl rand -hex 32)"`

3. **SECRET_KEY** (required)
   - Flask session secret key
   - Minimum length: 32 characters
   - Should be different from JWT_SECRET_KEY
   - Example: `export SECRET_KEY="$(openssl rand -hex 32)"`

### Production Environment

4. **DATABASE_URL** (required for production)
   - PostgreSQL connection string
   - Format: `postgresql://user:password@host:port/database`
   - Example: `export DATABASE_URL="postgresql://user:pass@localhost:5432/ai_gatekeeper"`

5. **API Keys** (at least one required)
   - Format: `API_KEY_<NAME>=<key>:<role>`
   - Minimum key length: 16 characters
   - Allowed roles: `admin`, `operator`, `viewer`, `api_user`
   - Example: `export API_KEY_ADMIN="$(openssl rand -hex 24):admin"`

## Generating Secure Secrets

### Using OpenSSL (Recommended)

```bash
# Generate a 32-character hex secret (64 bytes)
openssl rand -hex 32

# Generate a 24-character hex secret (48 bytes)
openssl rand -hex 24

# Generate a base64 secret
openssl rand -base64 32
```

### Using Python

```python
import secrets

# Generate a secure random string
secret = secrets.token_hex(32)  # 64 characters
print(f"Generated secret: {secret}")
```

## Configuration Examples

### Development Environment

```bash
# .env.development
export ENVIRONMENT=development
export OPENAI_API_KEY="sk-your-openai-key-here"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
export SECRET_KEY="$(openssl rand -hex 32)"
export API_KEY_DEV="dev-test-key-$(openssl rand -hex 16):admin"
export FLASK_DEBUG=true
```

### Production Environment

```bash
# .env.production
export ENVIRONMENT=production
export OPENAI_API_KEY="sk-your-production-openai-key"
export JWT_SECRET_KEY="your-production-jwt-secret-32chars-min"
export SECRET_KEY="your-production-flask-secret-32chars-min"
export DATABASE_URL="postgresql://user:pass@db-host:5432/ai_gatekeeper_prod"
export API_KEY_PROD_ADMIN="$(openssl rand -hex 32):admin"
export API_KEY_PROD_API="$(openssl rand -hex 32):api_user"
export FLASK_DEBUG=false
```

## Validating Configuration

### Run Secrets Validator

Before starting the application, validate your configuration:

```bash
cd Unified-AI-Platform
python scripts/validate_secrets.py
```

The validator checks for:
- ✅ All required secrets are set
- ✅ Secrets meet minimum length requirements
- ✅ Secrets match expected format patterns
- ✅ No dangerous default values are used
- ✅ API keys are properly formatted
- ⚠️  Warns about potentially weak secrets

### Example Output

```
🔍 Validating secrets for environment: production
============================================================

✅ All secrets validated successfully!
============================================================
```

## Security Best Practices

### DO ✅

1. **Generate unique, random secrets** for each environment
2. **Use different secrets** for development, staging, and production
3. **Rotate secrets** regularly (every 90 days recommended)
4. **Store secrets** in environment variables, not in code
5. **Use secret management tools** (AWS Secrets Manager, HashiCorp Vault, etc.)
6. **Validate secrets** before deployment using `validate_secrets.py`
7. **Monitor for secret exposure** in logs and error messages

### DON'T ❌

1. **Never commit secrets** to version control
2. **Never use default values** from examples/documentation
3. **Never share secrets** across environments
4. **Never log secrets** in application logs
5. **Never use weak secrets** like "password", "secret", "123"
6. **Never skip validation** before deployment

## API Key Management

### Creating API Keys

```bash
# Admin key (full access)
export API_KEY_ADMIN="$(openssl rand -hex 24):admin"

# Operator key (read/write)
export API_KEY_OPERATOR="$(openssl rand -hex 24):operator"

# Viewer key (read-only)
export API_KEY_VIEWER="$(openssl rand -hex 24):viewer"

# API user key (read/write for API operations)
export API_KEY_API="$(openssl rand -hex 24):api_user"
```

### Using API Keys

Include the API key in the Authorization header:

```bash
curl -H "Authorization: Bearer <your-api-key>" \
  http://localhost:5000/api/support/evaluate
```

### JWT Tokens vs API Keys

- **JWT Tokens**: For user authentication, expire after 24 hours (configurable)
- **API Keys**: For service-to-service communication, no expiration

## Rotating Secrets

### When to Rotate

- Every 90 days (recommended)
- After a security incident
- When an employee leaves
- If a secret is compromised

### Rotation Process

1. Generate new secrets
2. Update environment variables in deployment
3. Restart application
4. Verify new secrets work
5. Revoke old secrets
6. Update documentation

## Troubleshooting

### Application Won't Start

**Error**: `ValueError: JWT_SECRET_KEY environment variable must be set`

**Solution**: Set the JWT_SECRET_KEY environment variable:
```bash
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

**Error**: `JWT_SECRET_KEY must be at least 32 characters`

**Solution**: Generate a longer secret:
```bash
export JWT_SECRET_KEY="$(openssl rand -hex 32)"  # 64 characters
```

**Error**: `No API keys configured`

**Solution**: Set at least one API key:
```bash
export API_KEY_ADMIN="$(openssl rand -hex 24):admin"
```

### Validation Failures

Run the validator to see specific errors:
```bash
python scripts/validate_secrets.py
```

Fix any errors reported by the validator before starting the application.

## Emergency Procedures

### Secret Compromised

If a secret is compromised:

1. **Immediately rotate the secret**
2. **Revoke all active tokens** using the compromised secret
3. **Check logs** for unauthorized access
4. **Notify security team**
5. **Update documentation**

### Lock Out

If you're locked out due to configuration issues:

1. Check environment variables: `env | grep -E '(JWT|API_KEY|SECRET)'`
2. Validate configuration: `python scripts/validate_secrets.py`
3. Generate new secrets if needed
4. Restart application with correct configuration

## Additional Resources

- [OWASP Secret Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [JWT Security Best Practices](https://tools.ietf.org/html/rfc8725)
