# User Management Guide

The User Management system allows you to create additional admin users and manage authentication for the HomeIOT web dashboard.

---

## Default Admin User

Every HomeIOT installation starts with a master admin user:

| Field | Value |
|-------|-------|
| **Username** | `Admin` |
| **Password** | `123` |

⚠️ **CRITICAL:** Change this password immediately after first login.

---

## Managing Users

Navigate to **Admin → Users** to manage admin accounts.

### User List

View all admin users with:
- Username
- Created date
- Last login (if available)

### Creating a New User

1. Navigate to **Admin → Users**
2. Click **Create User**
3. Enter **Username** (any string)
4. Enter **Password** (minimum 8 characters)
5. Click **Create**

**Requirements:**
- Username must be unique
- Password must be at least 8 characters
- Passwords are hashed with BCrypt (cannot be retrieved, only reset)

### Changing a Password

**Method 1: User Self-Service**
1. Logged in as user
2. Navigate to **Admin → Users**
3. Click on own username
4. Click **Change Password**
5. Enter current password
6. Enter new password (8+ chars)
7. Click **Update**

**Method 2: Admin Reset**
1. Logged in as admin
2. Navigate to **Admin → Users**
3. Click target user
4. Click **Reset Password**
5. Generate new temporary password
6. Share with user (they should change on first login)

### Deleting a User

1. Navigate to **Admin → Users**
2. Click target user
3. Click **Delete User**
4. Confirm deletion

**Note:** Deleted user can no longer access the system. Cannot be undone.

---

## Authentication Flow

### Login

1. Open `http://localhost:5228`
2. Enter **Username** and **Password**
3. Click **Login**

Behind the scenes:
- Credentials sent to server as POST request
- Server validates username and password
- If valid, generates JWT token (24-hour expiration)
- Token returned to browser and stored

### Session Management

- **Token expiration:** 24 hours
- **When token expires:** You must log in again
- **Session timeout:** No automatic logout (token-based only)

### JWT Token

After login, your session uses a JWT (JSON Web Token):
- Stored in browser (automatically handled)
- Sent with every API request
- Contains your user info and expiration time
- Used to authorize admin operations

### Logout

Click **Logout** in web UI:
- Clears browser token
- You're redirected to login screen

---

## Security Considerations

### Password Policy

- **Minimum length:** 8 characters
- **Complexity:** No special requirements (but recommended: mix of upper/lower/numbers/symbols)
- **Hashing:** BCrypt (industry standard, very secure)
- **Storage:** Never stored in plain text

### Best Practices

✅ **DO:**
- Use strong passwords (12+ characters with mixed case + numbers + symbols)
- Change default admin password immediately
- Create separate user for each team member
- Delete unused accounts
- Periodically change passwords

❌ **DON'T:**
- Share passwords between users
- Use simple passwords like `password123`
- Leave default credentials in production
- Store passwords in plain text files

### Audit

Currently, the system tracks:
- User creation date
- Last login timestamp
- Password change attempts (via logs)

For production, consider implementing:
- User login audit log
- IP address tracking
- Suspicious activity alerts

---

## Multi-User Setup

For a team working together:

1. **Create user per team member**
   ```
   Alice - alice123secure
   Bob - bob456secure
   Charlie - charlie789secure
   ```

2. **Each person logs in with their credentials**
   - Each gets their own token
   - All see the same system (shared database)

3. **Currently no role-based access control (RBAC)**
   - All authenticated users have full admin access
   - Future enhancement: Implement read-only roles, module-only access, etc.

---

## Account Recovery

If you forget your password:

### As Admin

1. Create a new temporary user
2. Use that account to log in
3. Delete your old account if needed

Or (if multiple admins exist):

1. Ask another admin to delete your account
2. They create new account for you
3. Log in with new temporary password
4. Change password on first login

### If All Admins Are Locked Out

The only recovery is database-level:

1. Stop API server
2. Edit SQLite database directly (manual BCrypt hash reset)
3. Or delete `data/homeiot.db` to reset to defaults (Admin / 123)

---

## Next Steps

- [📖 Monitor device activity](features-devices.md)
- [📖 View dashboard metrics](features-dashboard.md)
