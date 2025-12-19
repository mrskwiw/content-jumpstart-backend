# Login Credentials

## Issue Resolved ✅

**Problem:** Login was failing with "Incorrect email or password" because there were no users in the database.

**Solution:** Created default users using the seed script.

## Default Login Credentials

You can now log in with either of these accounts:

### Account 1 (Primary)
```
Email:    mrskwiw@gmail.com
Password: Random!1Pass
```

### Account 2 (Secondary)
```
Email:    michele.vanhy@gmail.com
Password: Random!1Pass
```

## How to Log In

1. **Open browser:** http://localhost:8000
2. **Enter credentials:**
   - Email: `mrskwiw@gmail.com`
   - Password: `Random!1Pass`
3. **Click "Sign in"**
4. **You should be redirected to:** `/dashboard`

## What Was Wrong

The error message that was flashing too quickly to read was:

```
"Incorrect email or password"
```

This happened because:
1. The database was empty (no users)
2. Backend returned 401 Unauthorized
3. Frontend showed error briefly, then form reset

The error **should** have stayed visible, but it was disappearing. This might be a React state issue or the form was being reset too quickly.

## Users Created

```bash
# Verify users in database
docker exec content-jumpstart-api python -c "
from backend.database import SessionLocal
from backend.models import User
db = SessionLocal()
users = db.query(User).all()
print(f'Total users: {len(users)}')
for u in users:
    print(f'  - {u.email} (Active: {u.is_active})')
db.close()
"

# Output:
# Total users: 2
#   - mrskwiw@gmail.com (Active: True)
#   - michele.vanhy@gmail.com (Active: True)
```

## Create Additional Users

### Option 1: Use the Seed Script

Edit `backend/seed_users.py`:
```python
if __name__ == "__main__":
    user_emails = [
        "mrskwiw@gmail.com",
        "michele.vanhy@gmail.com",
        "newuser@example.com"  # Add new email here
    ]
    seed_users(user_emails, "Random!1Pass")  # Change password if needed
```

Then run:
```bash
docker exec content-jumpstart-api python backend/seed_users.py
```

### Option 2: Use the API Directly

```bash
# Register new user via API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123",
    "full_name": "New User"
  }'
```

### Option 3: Use Python Script

```python
# Create user programmatically
from backend.database import SessionLocal
from backend.models import User
from backend.utils.auth import get_password_hash
import uuid

db = SessionLocal()
user = User(
    id=f"user-{uuid.uuid4().hex[:12]}",
    email="newuser@example.com",
    hashed_password=get_password_hash("SecurePassword123"),
    full_name="New User",
    is_active=True
)
db.add(user)
db.commit()
db.close()
```

## Change Password

To change a user's password:

```python
from backend.database import SessionLocal
from backend.models import User
from backend.utils.auth import get_password_hash

db = SessionLocal()
user = db.query(User).filter(User.email == "mrskwiw@gmail.com").first()
if user:
    user.hashed_password = get_password_hash("NewPassword123")
    db.commit()
    print(f"Password updated for {user.email}")
db.close()
```

## Production Deployment

**IMPORTANT:** Before deploying to production:

1. **Change default password:**
   ```bash
   # Update seed_users.py with secure password
   seed_users(user_emails, "YOUR_SECURE_PASSWORD_HERE")
   ```

2. **Use environment variable:**
   ```python
   import os
   default_password = os.getenv("DEFAULT_USER_PASSWORD", "Random!1Pass")
   seed_users(user_emails, default_password)
   ```

3. **Set in Render:**
   ```
   Environment Variable:
   DEFAULT_USER_PASSWORD=<secure-random-password>
   ```

4. **Run seed on first deploy:**
   - Add to Dockerfile or startup script
   - Or run manually after first deployment

## Troubleshooting Login

### Error: "Incorrect email or password"
```bash
# Check if user exists
docker exec content-jumpstart-api python -c "
from backend.database import SessionLocal
from backend.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == 'mrskwiw@gmail.com').first()
print(f'User exists: {user is not None}')
if user:
    print(f'Active: {user.is_active}')
db.close()
"
```

### Error: "Inactive user"
```bash
# Activate user
docker exec content-jumpstart-api python -c "
from backend.database import SessionLocal
from backend.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == 'mrskwiw@gmail.com').first()
if user:
    user.is_active = True
    db.commit()
    print('User activated')
db.close()
"
```

### Error: Database connection failed
```bash
# Check database is running
docker ps | findstr content-jumpstart-db

# Check database connectivity
docker exec content-jumpstart-db psql -U postgres -d content_jumpstart -c "SELECT COUNT(*) FROM users;"
```

### Error: JWT token errors
```bash
# Check SECRET_KEY is set
docker exec content-jumpstart-api env | grep SECRET_KEY

# If missing, restart with .env
docker-compose down
docker-compose up -d api
```

## Next Steps

1. ✅ **Log in** at http://localhost:8000
2. **Test the dashboard** - Create a client, project, etc.
3. **Test content generation** - Upload brief, generate posts
4. **Review deliverables** - Check quality, export

## Security Notes

**Current Setup (Development):**
- Password: `Random!1Pass` (shared across all users)
- No email verification
- No password reset
- No rate limiting on login

**For Production:**
- Change default password
- Add email verification
- Implement password reset flow
- Add login rate limiting
- Use strong, unique passwords
- Enable 2FA if needed

## API Authentication Endpoints

```
POST /api/auth/login       - Login with email/password
POST /api/auth/register    - Create new user
POST /api/auth/refresh     - Refresh access token
```

Full API docs: http://localhost:8000/docs

---

**You can now log in!** Use `mrskwiw@gmail.com` / `Random!1Pass`
