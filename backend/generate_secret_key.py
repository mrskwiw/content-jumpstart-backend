"""
Generate a secure SECRET_KEY for JWT authentication.

Run this script to generate a new secret key, then copy it to your .env file.
"""
import secrets

if __name__ == "__main__":
    secret_key = secrets.token_urlsafe(32)
    print("\n" + "=" * 60)
    print("🔐 Generated SECRET_KEY:")
    print("=" * 60)
    print(f"\n{secret_key}\n")
    print("=" * 60)
    print("Copy this value to your .env file:")
    print(f"SECRET_KEY={secret_key}")
    print("=" * 60 + "\n")
