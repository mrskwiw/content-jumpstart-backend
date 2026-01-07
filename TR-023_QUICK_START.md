# TR-023: Registration Protection - Quick Start Guide

**For Operators and Administrators**

---

## What Changed?

**New users are now INACTIVE by default** and require admin activation before they can login.

---

## Admin Workflow

### Step 1: Check for Pending Users

```bash
GET /api/admin/users/inactive
Authorization: Bearer <your_admin_token>
```

**In Swagger UI:** Navigate to "Admin - User Management" → "List Inactive Users" → Execute

**Response:**
```json
[
  {
    "id": "user-abc123",
    "email": "newuser@example.com",
    "full_name": "New User",
    "is_active": false,
    "is_superuser": false,
    "created_at": "2026-01-07T10:00:00Z"
  }
]
```

---

### Step 2: Activate Legitimate User

```bash
POST /api/admin/users/{user_id}/activate
Authorization: Bearer <your_admin_token>
```

**In Swagger UI:**
1. Navigate to "Admin - User Management" → "Activate User"
2. Enter the `user_id` from Step 1
3. Click "Execute"

**Response:**
```json
{
  "id": "user-abc123",
  "email": "newuser@example.com",
  "full_name": "New User",
  "is_active": true,  ← NOW ACTIVE
  "is_superuser": false,
  "created_at": "2026-01-07T10:00:00Z",
  "updated_at": "2026-01-07T10:05:00Z"
}
```

---

### Step 3: User Can Now Login

The user can now authenticate using their credentials:

```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "their_password"
}
```

---

## Common Admin Operations

### View All Users
```
GET /api/admin/users
Authorization: Bearer <admin_token>
```

### Deactivate User (Suspend Account)
```
POST /api/admin/users/{user_id}/deactivate
Authorization: Bearer <admin_token>
```

**Note:** Cannot deactivate yourself.

### Promote User to Admin
```
POST /api/admin/users/{user_id}/promote
Authorization: Bearer <admin_token>
```

**Warning:** Admins have full access. Use with caution.

### Demote User from Admin
```
POST /api/admin/users/{user_id}/demote
Authorization: Bearer <admin_token>
```

**Note:** Cannot demote yourself.

---

## User Registration Flow

### New User Perspective

1. **User registers** at `/api/auth/register`
   - Provides email, password, full name
   - Receives tokens immediately

2. **User attempts login** - FAILS
   - Error: "Inactive user"
   - Must wait for admin activation

3. **Admin activates account** (you!)
   - Admin reviews pending users
   - Admin activates legitimate user

4. **User can now login** - SUCCESS
   - Full access to application

---

## Security Features

### Rate Limiting
- **3 registrations per hour per IP**
- Prevents spam and bot attacks

### Password Requirements
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit

### Logging
- All registration attempts logged
- Failed attempts logged
- Admin operations logged

**View logs:**
```bash
# Registration attempts
grep "Registration attempt" logs/backend.log

# Admin activations
grep "activated by admin" logs/backend.log
```

---

## Configuration Options

### Option A: Self-Registration + Admin Activation (DEFAULT)

**Current mode** - Users can register, but must be activated by admin.

**Best for:** Internal tools with trusted user base

---

### Option B: Admin-Only Registration

**Enable by:** Uncommenting lines 141-160 in `backend/routers/auth.py`

**Effect:** Only admins can create users (no self-registration)

**Best for:** High-security internal tools

---

### Option C: Email Domain Restriction

**Enable by:** Uncommenting lines 90-98 in `backend/schemas/auth.py`

**Effect:** Only specific email domains can register (e.g., @company.com)

**Best for:** Company-specific tools

---

## Troubleshooting

### Problem: User cannot login after registration

**Solution:** This is expected. Activate the user:
```
POST /api/admin/users/{user_id}/activate
```

---

### Problem: Cannot see pending users

**Cause:** You don't have admin privileges

**Solution:** Ask another admin to promote you:
```
POST /api/admin/users/{your_user_id}/promote
```

---

### Problem: Rate limit error (429)

**Cause:** Too many registrations in 1 hour

**Solution:** Wait 1 hour, or contact system administrator to adjust rate limits

---

## API Documentation

**Full documentation available at:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for the **"Admin - User Management"** section.

---

## Security Reminders

1. **Review inactive users regularly** - Don't let legitimate users wait
2. **Deactivate suspicious accounts immediately** - Better safe than sorry
3. **Be careful with admin promotions** - Admins have full access
4. **Don't demote yourself** - You'll lose admin access
5. **Monitor logs for suspicious activity** - Check `logs/backend.log`

---

## Quick Reference Commands

### Using cURL

```bash
# Login as admin
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"YourPassword"}' \
  | jq -r '.access_token'

# List inactive users
curl http://localhost:8000/api/admin/users/inactive \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Activate user
curl -X POST http://localhost:8000/api/admin/users/USER_ID_HERE/activate \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Using Swagger UI

1. Navigate to http://localhost:8000/docs
2. Click "Authorize" button (top right)
3. Enter your access token: `Bearer YOUR_TOKEN_HERE`
4. Click "Authorize"
5. Now you can execute admin operations

---

## Support

For technical issues or questions, refer to:
- **Full Documentation:** `TR-023_REGISTRATION_PROTECTION.md`
- **Backend Logs:** `logs/backend.log`
- **API Documentation:** http://localhost:8000/docs
