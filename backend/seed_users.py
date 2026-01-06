"""
Seed initial users into the database.
"""

from typing import List
import uuid
import os
import secrets

from backend.database import SessionLocal
from backend.models import User
from backend.utils.auth import get_password_hash


def seed_users(emails: List[str], password: str) -> None:
    """
    Create users if they do not already exist.
    """
    db = SessionLocal()
    hashed = get_password_hash(password)
    created = 0

    try:
        for email in emails:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"Skipping {email}: already exists")
                continue

            user = User(
                id=f"user-{uuid.uuid4().hex[:12]}",
                email=email,
                hashed_password=hashed,
                full_name=email.split("@")[0],
            )
            db.add(user)
            created += 1

        if created:
            db.commit()
        print(f"Total created: {created}")
    finally:
        db.close()


if __name__ == "__main__":
    user_emails = ["mrskwiw@gmail.com", "michele.vanhy@gmail.com"]

    # SECURITY FIX: Use environment variable for password (TR-018)
    default_password = os.getenv("DEFAULT_USER_PASSWORD")

    if not default_password:
        # Generate secure random password if not provided
        default_password = secrets.token_urlsafe(16)
        print("WARNING: No DEFAULT_USER_PASSWORD set in environment!")
        print(f"Generated random password for new users: {default_password}")
        print("IMPORTANT: Save this password immediately - it won't be shown again!")
        print("Set DEFAULT_USER_PASSWORD in .env to use a custom password")
    else:
        print("Using DEFAULT_USER_PASSWORD from environment")
        print("SECURITY: Password not displayed (using environment variable)")

    seed_users(user_emails, default_password)
