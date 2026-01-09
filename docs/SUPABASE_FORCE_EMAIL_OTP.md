# How to Force Email OTP Code (Not Magic Link) in Supabase

## 🚨 The Problem

Supabase sends **magic links** by default when you call `sign_in_with_otp()` with an email. To get an **OTP code** instead, you need to **configure Supabase** properly.

---

## ✅ Solution: Configure Supabase Dashboard

### Step 1: Disable Magic Links (Enable OTP Only)

1. **Go to your Supabase Dashboard**
   - URL: https://supabase.com/dashboard

2. **Navigate to Authentication → URL Configuration**
   - Click on your project
   - Go to **Authentication** in the left sidebar
   - Click **URL Configuration**

3. **Set Site URL to a non-web URL**
   - **Site URL:** Set to something like `myapp://`
   - This prevents magic links from working (forces OTP codes)

### Step 2: Verify Email Provider Settings

1. **Go to Authentication → Providers**

2. **Click on Email**

3. **Verify these settings:**
   - ✅ **Enable Email Provider** - ON
   - ✅ **Confirm email** - OFF (for passwordless OTP)
   - ✅ **Secure email change** - OFF (not needed for OTP)
   - ✅ **Email OTP Length** - 8 (or 6 if you prefer)
   - ✅ **Email OTP Expiration** - 3600 seconds (1 hour)

4. **Save Changes**

### Step 3: Check Email Templates

1. **Go to Authentication → Email Templates**

2. **Select "Confirm signup"**

3. **Verify the template includes:**
   ```html
   {{ .Token }}
   ```
   or
   ```html
   {{ .Code }}
   ```

4. If it shows `{{ .ConfirmationURL }}`, that's a magic link template!

   **Change it to:**
   ```html
   <h2>Your verification code is:</h2>
   <h1 style="font-size: 32px; letter-spacing: 8px;">{{ .Token }}</h1>
   <p>This code expires in 1 hour.</p>
   ```

5. **Save Template**

---

## 🧪 Alternative: Use Supabase REST API Directly

If the Python SDK isn't working, we can call the Supabase REST API directly:

```python
import httpx

async def request_email_otp_direct(email: str, supabase_url: str, supabase_key: str):
    """Request OTP code via direct Supabase REST API call"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{supabase_url}/auth/v1/otp",
            json={
                "email": email,
                "create_user": True,
                "gotrue_meta_security": {},
            },
            headers={
                "apikey": supabase_key,
                "Content-Type": "application/json",
            }
        )

        if response.status_code != 200:
            raise Exception(f"Failed to send OTP: {response.text}")

        return response.json()
```

---

## 📧 What's the Difference?

### Magic Link (Default)
```
Subject: Confirm your signup

Click here to sign in:
https://yourproject.supabase.co/auth/v1/verify?token=...&type=signup

This link expires in 1 hour.
```

### OTP Code (What We Want)
```
Subject: Confirm your signup

Your verification code is: 12345678

This code expires in 1 hour.
```

---

## 🔍 Debugging

### Check What Supabase Sent

1. **Look at the email you received**
   - Is there a clickable link? → Magic link
   - Is there an 8-digit code? → OTP code ✅

2. **Check Supabase Auth Logs**
   - Dashboard → Authentication → Logs
   - Look for "email sent" events
   - Check the template used

### Test with curl

```bash
# Direct API call to Supabase
curl -X POST "https://YOUR_PROJECT.supabase.co/auth/v1/otp" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "create_user": true
  }'
```

Check your email after this call. If you still get a magic link, the issue is in Supabase configuration (not our backend).

---

## 🎯 Quick Fix Checklist

- [ ] Set Site URL to `myapp://` (not http/https)
- [ ] Verify Email Provider is enabled
- [ ] Check Email OTP Length is set (6 or 8)
- [ ] Verify email template uses `{{ .Token }}` not `{{ .ConfirmationURL }}`
- [ ] Save all changes in Supabase Dashboard
- [ ] Test by requesting OTP again

---

## ⚡ Pro Tip: Use Phone OTP Instead

If email OTP continues to send magic links and you can't fix it, consider using **Phone OTP** instead:

```python
# Phone OTP (works reliably)
response = db.auth.sign_in_with_otp({
    "phone": "+1234567890"
})
```

Phone OTP **always** sends a code (never a link), so it's more reliable. The only downside is SMS costs money (~$0.01-0.05 per message).

---

## 📚 Supabase Documentation

- **Email OTP:** https://supabase.com/docs/guides/auth/auth-email-passwordless
- **Phone OTP:** https://supabase.com/docs/guides/auth/phone-login
- **REST API:** https://supabase.com/docs/reference/javascript/auth-signinwithotp

---

## 🆘 Still Getting Magic Links?

If you've followed all steps and still get magic links:

1. **Contact Supabase Support**
   - They might have project-specific settings blocking OTP codes
   - Dashboard → Help → Contact Support

2. **Use Magic Link Verification**
   - Alternative: Parse the token from the magic link URL
   - Extract `access_token` and `refresh_token` from URL
   - Return to user (not ideal for mobile apps)

3. **Switch to Phone OTP**
   - Most reliable option
   - Requires Twilio account setup
   - Costs ~$0.01-0.05 per SMS

---

## Next Steps

1. **Update Supabase Settings** (Site URL, email templates)
2. **Test OTP Request** (check if you get a code)
3. **If still getting links:** Try the direct REST API approach above
4. **If nothing works:** Use Phone OTP or contact Supabase support

Good luck! 🚀
