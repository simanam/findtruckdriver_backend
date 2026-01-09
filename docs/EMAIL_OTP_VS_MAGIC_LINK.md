# Email OTP vs Magic Link - Important Difference

## 🚨 The Problem

When you call `db.auth.sign_in_with_otp()` with an email, Supabase can send **two different types** of authentication:

1. **Magic Link** - A clickable link (default behavior)
2. **OTP Code** - An 8-digit code (what we want)

If you receive a **link** instead of a **code**, that's a magic link!

---

## ✅ Solution: Force OTP Code

To ensure Supabase sends an **OTP code** (not a magic link), we must specify `"channel": "email"` in the options:

### ❌ Wrong (Sends Magic Link)
```python
db.auth.sign_in_with_otp({
    "email": "user@example.com",
    "options": {
        "should_create_user": True,
        "email_redirect_to": None  # This doesn't force OTP!
    }
})
```

**Result:** Email contains a clickable link like:
```
http://localhost:3000/#access_token=...
```

### ✅ Correct (Sends OTP Code)
```python
db.auth.sign_in_with_otp({
    "email": "user@example.com",
    "options": {
        "should_create_user": True,
        "channel": "email",  # ← This forces OTP code!
    }
})
```

**Result:** Email contains an 8-digit code like:
```
Your verification code is: 12345678
```

---

## 📧 What You'll Receive

### With Magic Link
```
Subject: Confirm your signup

Click this link to sign in:
http://localhost:3000/#access_token=eyJhbGc...&expires_in=3600

This link expires in 1 hour.
```

### With OTP Code (Correct)
```
Subject: Confirm your signup

Your verification code is: 12345678

This code expires in 1 hour.
```

---

## 🔧 Backend Fix Applied

**File:** `app/routers/auth.py`

**Updated code:**
```python
@router.post("/email/otp/request", status_code=status.HTTP_200_OK)
async def request_email_otp(
    request: EmailOTPRequest,
    db: Client = Depends(get_db_client)
):
    response = db.auth.sign_in_with_otp({
        "email": request.email,
        "options": {
            "should_create_user": True,
            "channel": "email",  # ← Fixed: Now sends OTP code
        }
    })
```

---

## 🧪 Test It Now

### 1. Restart Backend (if needed)
```bash
cd finddriverbackend
./run_dev.sh
```

### 2. Request OTP
```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com"}'
```

### 3. Check Your Email
You should now receive an **8-digit code** (not a link!)

### 4. Verify Code
```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com", "code": "12345678"}'
```

---

## 📚 Supabase Documentation

From Supabase docs on `sign_in_with_otp()`:

> **channel** (optional): The channel to use for OTP delivery. Options:
> - `"email"` - Sends OTP code via email
> - `"sms"` - Sends OTP code via SMS
> - If not specified, sends a magic link

**Reference:** https://supabase.com/docs/reference/javascript/auth-signinwithotp

---

## 🎯 Summary

| Parameter | Behavior |
|-----------|----------|
| No `channel` specified | Sends **magic link** (clickable URL) |
| `"channel": "email"` | Sends **OTP code** (8 digits) ✅ |
| `"channel": "sms"` | Sends **OTP code** via SMS (requires phone) |

**Always use `"channel": "email"` for email OTP authentication!**

---

## ⚠️ Common Confusion

**Q: Why did I get a link instead of a code?**
A: The backend was missing `"channel": "email"` in the options. This is now fixed.

**Q: Can I use the magic link to authenticate?**
A: Yes, but it requires a different verification flow. We're using OTP codes for consistency with the mobile app UX.

**Q: What if I still get a link?**
A:
1. Make sure backend code has `"channel": "email"` (now fixed)
2. Restart backend server
3. Clear any cached requests
4. Try again with a fresh request

---

## 🚀 You're All Set!

The backend is now fixed. You should receive **8-digit OTP codes** in your email instead of magic links.

Test it now and you'll see the difference! 🎉
