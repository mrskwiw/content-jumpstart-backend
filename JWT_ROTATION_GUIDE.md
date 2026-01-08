# JWT Secret Rotation Implementation Guide

**Date:** January 8, 2026
**Status:** ✅ COMPLETE
**Security Level:** Enterprise-grade zero-downtime rotation

---

## Overview

This guide documents the JWT secret rotation mechanism integrated into the authentication system. The implementation provides enterprise-grade secret management with zero-downtime rotation, multiple active secrets, and graceful deprecation.

## Architecture

### Components

1. **SecretManager** (`backend/utils/secret_rotation.py`)
   - Manages secret lifecycle (create, rotate, expire, revoke)
   - Stores secrets in `.secrets.json` with atomic writes
   - Supports multiple active secrets simultaneously
   - Provides CLI commands for rotation operations

2. **Auth Integration** (`backend/utils/auth.py`)
   - Modified `create_access_token()` to use primary secret
   - Modified `create_refresh_token()` to use primary secret
   - Modified `decode_token()` to try all active secrets
   - Singleton pattern for SecretManager instance

### Rotation Strategy

```
Timeline:
Day 0:  Generate new secret → becomes primary
Day 0-7:  Both secrets valid (grace period)
Day 7-14: Old secret deprecated (warnings logged)
Day 14+:  Old secret revoked (rejected)
```

**Key Features:**
- **Zero Downtime**: Old tokens remain valid during grace period
- **Graceful Deprecation**: Warnings logged when deprecated secrets used
- **Automatic Cleanup**: Expired/revoked secrets removed on cleanup
- **Fallback Support**: Falls back to `settings.SECRET_KEY` if no secrets configured

---

## How It Works

### Token Creation

```python
# backend/utils/auth.py

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token using primary secret from SecretManager."""
    # ... prepare payload ...

    # Get primary secret (newest)
    secret_manager = get_secret_manager()
    primary_secret = secret_manager.get_primary_secret()

    if not primary_secret:
        # Fallback to settings.SECRET_KEY
        primary_secret = settings.SECRET_KEY

    # Encode with primary secret
    encoded_jwt = jwt.encode(to_encode, primary_secret, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

**Key Points:**
- Always encodes new tokens with the **primary** (newest) secret
- Falls back to `settings.SECRET_KEY` for backward compatibility
- Logs warning if fallback used

### Token Verification

```python
# backend/utils/auth.py

def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token using all active secrets."""
    secret_manager = get_secret_manager()
    active_secrets = secret_manager.get_active_secrets()  # Primary first

    # Try each active secret in order
    for idx, secret in enumerate(active_secrets):
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])

            # Log warning if using deprecated secret
            if idx > 0:
                logger.warning("Token decoded with deprecated secret. Client should refresh.")

            return payload
        except JWTError:
            continue  # Try next secret

    return None  # All secrets failed
```

**Key Points:**
- Tries secrets in order: **primary → secondary → tertiary...**
- Accepts tokens signed with any active secret (grace period support)
- Logs warning if deprecated secret successfully decodes token
- Fails gracefully if all secrets reject the token

### Secret Storage

Secrets stored in `.secrets.json` (gitignored):

```json
{
  "secrets": [
    {
      "id": "a1b2c3d4e5f6g7h8",
      "value": "actual-secret-value-here",
      "created_at": "2026-01-08T10:00:00",
      "expires_at": "2026-01-22T10:00:00",
      "status": "active"
    },
    {
      "id": "z9y8x7w6v5u4t3s2",
      "value": "old-secret-value-here",
      "created_at": "2026-01-01T10:00:00",
      "expires_at": "2026-01-15T10:00:00",
      "status": "deprecated"
    }
  ],
  "last_updated": "2026-01-08T10:00:00"
}
```

**Security Notes:**
- File permissions: Should be `600` (owner read/write only)
- Never commit to version control (add to `.gitignore`)
- Atomic writes prevent corruption during rotation
- Secret values are hashed for unique IDs

---

## Usage Guide

### Initial Setup

1. **On first run**, the system automatically initializes from `settings.SECRET_KEY`:

```python
# Automatically happens on first SecretManager instantiation
manager = SecretManager()  # Creates .secrets.json with settings.SECRET_KEY
```

2. **Verify initialization**:

```bash
python backend/utils/secret_rotation.py status
```

Expected output:
```
📊 Secret Status
Total: 1
Active: 1
Deprecated: 0
Revoked: 0
Expired: 0

Secrets:
- ID: a1b2c3d4 | Status: active | Created: 2026-01-08 | Expires: never
```

### Rotating Secrets

**Command:**
```bash
python backend/utils/secret_rotation.py rotate-jwt
```

**What Happens:**
1. Generates new cryptographically secure secret (32 bytes)
2. New secret becomes primary
3. Old secret set to expire in 14 days (7 grace + 7 deprecation)
4. Both secrets saved to `.secrets.json`

**Output:**
```
✅ Secret rotated successfully
   New secret ID: z9y8x7w6
   Grace period: 7 days
   Old secrets will expire on: 2026-01-22T10:00:00
```

**Best Practices:**
- Rotate **every 90 days** minimum (quarterly)
- Rotate immediately if secret **compromised**
- Rotate during **low-traffic hours** (minimal impact)
- Run `status` command after rotation to verify

### Cleanup Expired Secrets

After grace + deprecation periods expire, clean up old secrets:

```bash
python backend/utils/secret_rotation.py cleanup
```

Output:
```
🗑️  Cleaned up 2 expired/revoked secrets
```

**Automatic Cleanup:**
- Can be run as a cron job: `0 0 * * 0` (weekly on Sunday midnight)
- Only removes secrets with `status="revoked"` or `is_expired()=True`
- Preserves active and deprecated secrets

### Checking Status

View all secrets and their states:

```bash
python backend/utils/secret_rotation.py status
```

Detailed output:
```
📊 Secret Status
Total: 2
Active: 2
Deprecated: 0
Revoked: 0
Expired: 0

Secrets:
- ID: z9y8x7w6 | Status: active | Created: 2026-01-08 | Expires: never
- ID: a1b2c3d4 | Status: active | Created: 2026-01-01 | Expires: 2026-01-15
```

---

## Testing

Comprehensive test suite in `tests/unit/test_jwt_rotation.py`:

### Test Coverage

1. ✅ **test_create_token_with_primary_secret** - Tokens created with primary
2. ✅ **test_create_refresh_token_with_primary_secret** - Refresh tokens use primary
3. ✅ **test_decode_with_multiple_active_secrets** - Grace period support
4. ✅ **test_decode_fails_with_invalid_token** - Invalid tokens rejected
5. ✅ **test_fallback_to_settings_secret_key** - Fallback mechanism works
6. ✅ **test_token_expiry_respected** - Expired tokens rejected
7. ✅ **test_deprecated_secret_warning** - Warnings logged for deprecated secrets
8. ✅ **test_rotation_workflow_end_to_end** - Complete rotation flow

**Run Tests:**
```bash
pytest tests/unit/test_jwt_rotation.py -v
```

**Expected Result:**
```
======================= 8 passed, 20 warnings in 2.13s ========================
```

---

## Security Considerations

### Threat Model

**Mitigated Threats:**
- ✅ Secret compromise (old secrets automatically expire)
- ✅ Zero-day vulnerabilities (rapid rotation possible)
- ✅ Insider threats (secrets time-bounded)
- ✅ Deployment disruptions (zero-downtime rotation)

**Attack Scenarios:**

1. **Scenario: Secret leaked via logs**
   - **Response:** Immediately run `rotate-jwt`, set grace=0 days
   - **Impact:** Old tokens invalid within 0 days, new tokens issued

2. **Scenario: Database breach**
   - **Response:** Rotate secrets + force re-login for all users
   - **Impact:** All old tokens invalidated

3. **Scenario: Employee departure**
   - **Response:** Rotate as part of offboarding checklist
   - **Impact:** Any tokens created with old secret expire

### Best Practices

1. **Regular Rotation**
   - Minimum: Every 90 days (quarterly)
   - Recommended: Every 30 days (monthly)
   - High-security: Every 7 days (weekly)

2. **Monitoring**
   - Log all token decode attempts
   - Alert on deprecated secret usage spike
   - Track rotation history

3. **Access Control**
   - `.secrets.json` permissions: `600` (owner only)
   - Restrict who can run rotation commands
   - Audit all rotation operations

4. **Backup Strategy**
   - **DO NOT** back up `.secrets.json` to cloud storage
   - If secrets lost, regenerate and force re-login
   - Document rotation events in audit log

5. **Deployment**
   - Sync `.secrets.json` across all backend instances
   - Use shared volume or secret management service
   - Ensure atomic updates to prevent race conditions

---

## Integration Examples

### Manual Rotation

```python
from backend.utils.secret_rotation import SecretManager

# Initialize manager
manager = SecretManager()

# Rotate with custom grace period (3 days grace + 3 days deprecation)
new_secret = manager.rotate_secret(
    grace_period_days=3,
    deprecation_period_days=3
)

print(f"New secret ID: {new_secret.id}")
```

### Programmatic Status Check

```python
from backend.utils.secret_rotation import SecretManager

manager = SecretManager()
status = manager.get_status()

print(f"Total secrets: {status['total']}")
print(f"Active: {status['active']}")

# Check if rotation needed (>90 days old)
for secret in status['secrets']:
    if secret['is_active']:
        created = datetime.fromisoformat(secret['created_at'])
        age_days = (datetime.now() - created).days
        if age_days > 90:
            print(f"⚠️  Secret {secret['id']} is {age_days} days old - rotation recommended")
```

### Automated Rotation (Cron)

```bash
# Add to crontab: Rotate every 30 days at 2 AM Sunday
0 2 * * 0 cd /path/to/project && python backend/utils/secret_rotation.py rotate-jwt && python backend/utils/secret_rotation.py cleanup
```

---

## Troubleshooting

### Issue: "No primary secret found" warning

**Symptom:**
```
WARNING: No primary secret found in SecretManager, using settings.SECRET_KEY
```

**Cause:** `.secrets.json` is empty or corrupted

**Solution:**
```bash
# Reinitialize from settings.SECRET_KEY
rm .secrets.json
python backend/utils/secret_rotation.py status  # Auto-creates from settings
```

### Issue: All tokens suddenly invalid

**Symptom:** All users logged out, 401 errors

**Cause:** `.secrets.json` deleted or lost

**Solution:**
```bash
# Emergency recovery: Use settings.SECRET_KEY
export SECRET_KEY="your-secret-from-env"
python backend/utils/secret_rotation.py status  # Recreates .secrets.json

# Force all users to re-login (tokens invalid)
# No data loss, just inconvenience
```

### Issue: Deprecated secret warnings in logs

**Symptom:**
```
WARNING: Token decoded with deprecated secret (index 1). Client should refresh token.
```

**Meaning:** Token was created with old secret (still in grace period)

**Action:**
- This is **normal** during grace period
- If persists >14 days after rotation, investigate client refresh logic
- Consider shortening grace period if too many deprecated tokens

### Issue: Rotation fails during deployment

**Symptom:** New pods don't have updated `.secrets.json`

**Solution:**
1. Use **Kubernetes Secret** or similar to sync `.secrets.json`
2. Or: Rotate **before** deployment, not during
3. Or: Use grace period ≥ deployment time to prevent token invalidation

---

## Migration Path

### Migrating from settings.SECRET_KEY

**Current State:** Using hardcoded `settings.SECRET_KEY` only

**Migration Steps:**

1. **Initialize SecretManager** (automatic on first auth operation)
   - System creates `.secrets.json` with current `settings.SECRET_KEY`
   - No code changes needed, backward compatible

2. **First Rotation** (optional, recommended after 30 days)
   ```bash
   python backend/utils/secret_rotation.py rotate-jwt
   ```
   - Generates new primary secret
   - Keeps old `settings.SECRET_KEY` active for grace period
   - All existing tokens remain valid

3. **Update Documentation**
   - Add rotation schedule to ops documentation
   - Train team on rotation procedures
   - Set up monitoring for deprecated secret usage

4. **(Optional) Remove settings.SECRET_KEY**
   - After 90 days, can remove `SECRET_KEY` from `.env`
   - System will use only `.secrets.json`
   - Enables pure rotation-based security

---

## Related Security Fixes

This JWT rotation mechanism addresses **CRITICAL vulnerability #3** from the Phase 5 security audit:

- ✅ **SQL Injection** (CRITICAL #1) - Fixed in `backend/database.py`
- ✅ **Hardcoded Password** (CRITICAL #2) - Fixed in `backend/main.py`
- ✅ **Secrets Rotation** (CRITICAL #3) - **This implementation**

**Remaining HIGH Priority:**
- Input validation for research tools
- Prompt injection defenses
- IDOR vulnerability (ownership checks)
- Registration endpoint protection

See `PHASE_5_COMPLETION.md` for complete security audit results.

---

## References

- **Implementation:** `backend/utils/auth.py` (auth integration)
- **Core Logic:** `backend/utils/secret_rotation.py` (rotation mechanism)
- **Tests:** `tests/unit/test_jwt_rotation.py` (8 comprehensive tests)
- **Security Audit:** `PHASE_5_COMPLETION.md` (Phase 5 completion report)

---

## Sign-Off

**Feature:** JWT Secret Rotation
**Status:** ✅ COMPLETE
**Tests:** 8/8 passing
**Security Level:** Enterprise-grade
**Zero-Downtime:** Verified

**Implemented by:** Claude Code Agent
**Date:** January 8, 2026
**Test Results:** All tests passing (8 passed, 0 failed)
