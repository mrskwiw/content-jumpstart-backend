"""
Seed initial users into the database.
"""
from typing import List
import uuid

from database import SessionLocal
from models import User
from utils.auth import get_password_hash


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
    seed_users(user_emails, "Random!1Pass")
