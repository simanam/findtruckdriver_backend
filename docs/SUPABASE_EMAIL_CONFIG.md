# Supabase Email OTP Configuration

## What You See vs What You Need

### ❌ What You're Looking For (Doesn't Exist)
- A separate "Email OTP" toggle

### ✅ What Actually Works
- Email OTP is **automatically enabled** when you enable the **Email provider**
- The settings you see control **how** email OTP works

---

## Step-by-Step Setup

### 1. Enable Email Provider

In your Supabase Dashboard:

1. Go to **Authentication** → **Providers**
2. Find **Email** in the list
3. Click to expand
4. **Enable** the toggle at the top

✅ This automatically enables email OTP!

### 2. Configure Email OTP Settings

You should see these settings (as shown in your screenshot):

#### **Email OTP Expiration**
- Default: `3600` seconds (1 hour)
- This is how long the code remains valid
- ✅ Keep default or adjust as needed

#### **Email OTP Length**
- Default: `8` digits
- This is the length of the code sent to users
- ✅ Our backend now supports 6-8 digit codes
- You can change this to `6` if you prefer shorter codes

#### **Other Settings You Can Ignore**
- ❌ **Secure email change** - Only for password-based accounts
- ❌ **Secure password change** - We're passwordless, so this doesn't apply
- ❌ **Minimum password length** - Not used for OTP
- ❌ **Password Requirements** - Not used for OTP

### 3. Test Email Templates (Optional)

1. Go to **Authentication** → **Email Templates**
2. Find **"Confirm signup"** or **"Magic Link"**
3. You'll see the email template with `{{ .Token }}` or `{{ .Code }}`
4. Customize if desired

---

## How Supabase Email OTP Works

### 🚨 CRITICAL: Force OTP Code (Not Magic Link)

When calling `db.auth.sign_in_with_otp()`, you **must** specify `"channel": "email"` to get an OTP code:

```python
# ✅ Correct - Sends OTP code (8 digits)
db.auth.sign_in_with_otp({
    "email": "user@example.com",
    "options": {
        "should_create_user": True,
        "channel": "email",  # ← REQUIRED for OTP code!
    }
})

# ❌ Wrong - Sends magic link (clickable URL)
db.auth.sign_in_with_otp({
    "email": "user@example.com",
    "options": {
        "should_create_user": True
        # Missing "channel": "email"
    }
})
```

### The Flow

1. **Backend calls** `sign_in_with_otp()` with `"channel": "email"`
2. **Supabase generates** an 8-digit code (based on your settings)
3. **Supabase sends email** with the code
4. **User enters code** in your app
5. **Backend calls** `db.auth.verify_otp({ email, token, type: "email" })`
6. **Supabase validates** and returns JWT tokens

---

## Important: The Code is Called "Token" in the API

In Supabase's API, the OTP code is referred to as a "token":

```python
# ✅ Correct
db.auth.verify_otp({
    "email": "user@example.com",
    "token": "12345678",  # The 8-digit code
    "type": "email"
})

# ❌ Wrong
db.auth.verify_otp({
    "email": "user@example.com",
    "code": "12345678",  # This won't work
    "type": "email"
})
```

**Our backend handles this correctly** - we accept "code" from the user and send it as "token" to Supabase.

---

## Testing

### 1. Start Your Backend

```bash
cd finddriverbackend
./run_dev.sh
```

### 2. Request OTP

```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "YOUR_EMAIL@gmail.com"}'
```

### 3. Check Your Email

Look for an email from Supabase with an **8-digit code** (or 6-digit if you changed the setting).

### 4. Verify Code

```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/verify \
  -H "Content-Type: application/json" \
  -d '{
    "email": "YOUR_EMAIL@gmail.com",
    "code": "12345678"
  }'
```

You should get back:
```json
{
  "user": { ... },
  "tokens": {
    "access_token": "...",
    "refresh_token": "..."
  },
  "driver": null
}
```

---

## Troubleshooting

### "Email not received"

1. **Check spam folder** - Supabase emails often land there
2. **Wait a minute** - Sometimes delayed
3. **Check Supabase logs**:
   - Go to **Authentication** → **Logs**
   - Look for email send events
4. **Verify email provider is enabled**

### "Invalid token" error

1. **Code expired** - Default 1 hour, request new code
2. **Wrong code** - Check typos
3. **Code already used** - Codes are single-use

### "Code is 6 digits but mine is 8"

Your Supabase settings show **Email OTP Length: 8**, so you'll get 8-digit codes.

To change to 6 digits:
1. Dashboard → Auth → Providers → Email
2. Change **Email OTP Length** to `6`
3. Save

---

## Email Template Customization

### Default Template

The email Supabase sends looks like:

```
Confirm your signup

Enter this code: 12345678

This code expires in 1 hour.
```

### Customize It

1. Go to **Authentication** → **Email Templates**
2. Find **"Confirm signup"** template
3. Edit the HTML/text
4. Use variables:
   - `{{ .Token }}` - The OTP code
   - `{{ .Email }}` - User's email
   - `{{ .SiteURL }}` - Your app URL

Example custom template:
```html
<h1>Welcome to Find a Truck Driver!</h1>

<p>Your verification code is:</p>
<h2 style="font-size: 32px; letter-spacing: 8px;">{{ .Token }}</h2>

<p>This code expires in 1 hour.</p>

<p>If you didn't request this, please ignore this email.</p>
```

---

## Cost Comparison

| Method | Cost |
|--------|------|
| **Email OTP** | ✅ **FREE** (included with Supabase) |
| **Phone SMS** | ❌ ~$0.01-0.05 per SMS (via Twilio) |
| **Magic Link** | ✅ FREE (also email) |

**Email OTP is the best choice for cost-effectiveness!**

---

## Summary

✅ **Email provider is already enabled** (based on your screenshot)
✅ **Email OTP Length is 8 digits** (you can change to 6 if desired)
✅ **Our backend supports 6-8 digit codes** (flexible)
✅ **No additional configuration needed** - Just test it!

### Quick Test

1. Use your own email
2. Send OTP request via API
3. Check email for 8-digit code
4. Verify code via API
5. Done! 🎉

### Update Frontend

Make sure your React Native input accepts 8 digits:

```tsx
<TextInput
  value={code}
  onChangeText={setCode}
  keyboardType="number-pad"
  maxLength={8}  // Changed from 6 to 8
  placeholder="Enter 8-digit code"
/>
```

---

## Need Help?

If email OTP isn't working:

1. Check **Authentication** → **Providers** → **Email** is enabled
2. Check **Authentication** → **Logs** for send events
3. Try with your own email first (not a test email)
4. Check spam folder

**The system is ready to use right now!** No additional setup needed beyond enabling the Email provider.
