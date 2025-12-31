"""
Secret Rotation Mechanism

Provides secure secret rotation for JWT tokens and API keys without downtime.

Features:
- Multiple active secrets (primary + secondary)
- Graceful secret rotation
- Zero-downtime deployments
- Automatic cleanup of old secrets

Usage:
    # In config.py
    SECRET_KEYS = SecretManager.get_active_keys()

    # In auth.py
    for key in SECRET_KEYS:
        try:
            payload = jwt.decode(token, key, algorithms=["HS256"])
            break
        except jwt.InvalidSignatureError:
            continue
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import secrets


@dataclass
class Secret:
    """Represents a cryptographic secret"""
    id: str  # Unique identifier (hash of secret)
    value: str  # The actual secret
    created_at: str  # ISO timestamp
    expires_at: Optional[str] = None  # Optional expiry
    status: str = "active"  # active, deprecated, revoked

    def is_expired(self) -> bool:
        """Check if secret is expired"""
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.now()

    def is_active(self) -> bool:
        """Check if secret is currently usable"""
        return self.status == "active" and not self.is_expired()


class SecretManager:
    """
    Manages secret rotation with zero downtime

    Rotation Strategy:
    1. Generate new secret (becomes primary)
    2. Keep old secret active for grace period (becomes secondary)
    3. After grace period, deprecate old secret
    4. After deprecation period, revoke old secret

    Timeline:
    - Day 0: Generate new secret
    - Day 0-7: Both secrets valid (grace period)
    - Day 7-14: Old secret deprecated (warnings logged)
    - Day 14+: Old secret revoked (rejected)
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize secret manager

        Args:
            config_path: Path to secrets config file (default: .secrets.json)
        """
        self.config_path = config_path or Path(".secrets.json")
        self.secrets: Dict[str, Secret] = {}
        self.load_secrets()

    def load_secrets(self):
        """Load secrets from config file"""
        if not self.config_path.exists():
            # Initialize with environment variable secret
            env_secret = os.getenv("SECRET_KEY")
            if env_secret:
                self.add_secret(env_secret, auto_save=False)
            self.save_secrets()
            return

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            for secret_data in data.get("secrets", []):
                secret = Secret(**secret_data)
                self.secrets[secret.id] = secret

        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load secrets: {e}")

    def save_secrets(self):
        """Save secrets to config file"""
        data = {
            "secrets": [asdict(secret) for secret in self.secrets.values()],
            "last_updated": datetime.now().isoformat(),
        }

        # Write atomically (write to temp file, then rename)
        temp_path = self.config_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)

        temp_path.replace(self.config_path)

    def generate_secret(self, length: int = 32) -> str:
        """Generate cryptographically secure random secret"""
        return secrets.token_urlsafe(length)

    def hash_secret(self, secret: str) -> str:
        """Generate unique ID for secret"""
        return hashlib.sha256(secret.encode()).hexdigest()[:16]

    def add_secret(
        self,
        secret: str,
        expires_in_days: Optional[int] = None,
        auto_save: bool = True
    ) -> Secret:
        """
        Add new secret to store

        Args:
            secret: The secret value
            expires_in_days: Optional expiry period (default: no expiry)
            auto_save: Save to disk immediately

        Returns:
            Secret object
        """
        secret_id = self.hash_secret(secret)

        # Check if already exists
        if secret_id in self.secrets:
            return self.secrets[secret_id]

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        new_secret = Secret(
            id=secret_id,
            value=secret,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            status="active",
        )

        self.secrets[secret_id] = new_secret

        if auto_save:
            self.save_secrets()

        return new_secret

    def rotate_secret(
        self,
        grace_period_days: int = 7,
        deprecation_period_days: int = 7
    ) -> Secret:
        """
        Rotate secrets with zero downtime

        Process:
        1. Generate new secret (becomes primary)
        2. Set current primary to expire after grace period
        3. Save both secrets

        Args:
            grace_period_days: Days to keep old secret active
            deprecation_period_days: Days to deprecate before revoking

        Returns:
            New primary secret
        """
        # Generate new secret
        new_secret_value = self.generate_secret()
        new_secret = self.add_secret(new_secret_value, auto_save=False)

        # Deprecate old secrets after grace period
        total_days = grace_period_days + deprecation_period_days
        for secret in self.secrets.values():
            if secret.id != new_secret.id and secret.is_active():
                # Set to expire after grace + deprecation period
                secret.expires_at = (
                    datetime.now() + timedelta(days=total_days)
                ).isoformat()

                # Mark as deprecated after grace period
                if grace_period_days == 0:
                    secret.status = "deprecated"

        self.save_secrets()

        print(f"✅ Secret rotated successfully")
        print(f"   New secret ID: {new_secret.id}")
        print(f"   Grace period: {grace_period_days} days")
        print(f"   Old secrets will expire on: {secret.expires_at if secret.expires_at else 'never'}")

        return new_secret

    def get_active_secrets(self) -> List[str]:
        """
        Get all active secret values

        Returns:
            List of active secrets (primary first)
        """
        active = [
            secret for secret in self.secrets.values()
            if secret.is_active()
        ]

        # Sort by created_at (newest first)
        active.sort(key=lambda s: s.created_at, reverse=True)

        return [s.value for s in active]

    def get_primary_secret(self) -> Optional[str]:
        """Get most recent active secret (primary)"""
        active = self.get_active_secrets()
        return active[0] if active else None

    def revoke_secret(self, secret_id: str):
        """Revoke a specific secret immediately"""
        if secret_id in self.secrets:
            self.secrets[secret_id].status = "revoked"
            self.save_secrets()

    def cleanup_expired(self):
        """Remove expired and revoked secrets"""
        before_count = len(self.secrets)

        # Keep only active and deprecated (not expired) secrets
        self.secrets = {
            sid: secret for sid, secret in self.secrets.items()
            if secret.status in ["active", "deprecated"] and not secret.is_expired()
        }

        removed = before_count - len(self.secrets)

        if removed > 0:
            self.save_secrets()
            print(f"🗑️  Cleaned up {removed} expired/revoked secrets")

    def get_status(self) -> Dict:
        """Get status of all secrets"""
        return {
            "total": len(self.secrets),
            "active": len([s for s in self.secrets.values() if s.is_active()]),
            "deprecated": len([s for s in self.secrets.values() if s.status == "deprecated"]),
            "revoked": len([s for s in self.secrets.values() if s.status == "revoked"]),
            "expired": len([s for s in self.secrets.values() if s.is_expired()]),
            "secrets": [
                {
                    "id": s.id,
                    "status": s.status,
                    "created_at": s.created_at,
                    "expires_at": s.expires_at,
                    "is_active": s.is_active(),
                }
                for s in sorted(
                    self.secrets.values(),
                    key=lambda x: x.created_at,
                    reverse=True
                )
            ]
        }


# Convenience functions

def rotate_jwt_secret():
    """Rotate JWT signing secret"""
    manager = SecretManager()
    new_secret = manager.rotate_secret(
        grace_period_days=7,  # 1 week to deploy new secret
        deprecation_period_days=7,  # 1 week warning period
    )

    print("\n⚠️  IMPORTANT: Update your deployment with new SECRET_KEY:")
    print(f"   SECRET_KEY={new_secret.value}")
    print("\n📋 Deployment steps:")
    print("   1. Update environment variable in Render/Docker")
    print("   2. Deploy new version")
    print("   3. Wait 7 days for all tokens to refresh")
    print("   4. Old secret will auto-expire")


def rotate_api_key():
    """Rotate Anthropic API key"""
    print("\n🔐 API Key Rotation Procedure:")
    print("\n1. Generate new key at https://console.anthropic.com/")
    print("2. Add new key to environment variables")
    print("3. Update ANTHROPIC_API_KEY in .env")
    print("4. Deploy new version")
    print("5. Revoke old key in Anthropic console after 24 hours")
    print("\n⚠️  No grace period for API keys - immediate switch")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python secret_rotation.py rotate-jwt")
        print("  python secret_rotation.py rotate-api")
        print("  python secret_rotation.py status")
        print("  python secret_rotation.py cleanup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "rotate-jwt":
        rotate_jwt_secret()
    elif command == "rotate-api":
        rotate_api_key()
    elif command == "status":
        manager = SecretManager()
        import json
        print(json.dumps(manager.get_status(), indent=2))
    elif command == "cleanup":
        manager = SecretManager()
        manager.cleanup_expired()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
