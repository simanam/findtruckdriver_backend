# Email OTP Setup Guide

## Why Email OTP Instead of Phone?

✅ **Free** - No SMS costs (Supabase includes email for free)
✅ **Unlimited** - No per-message charges
✅ **Passwordless** - Better UX than passwords
✅ **Secure** - 6-digit codes with expiry

❌ Phone SMS OTP costs money per message (Twilio, etc.)

---

## How It Works

1. **User enters email** → `POST /api/v1/auth/email/otp/request`
2. **Supabase sends 6-digit code** to their email
3. **User enters code** → `POST /api/v1/auth/email/otp/verify`
4. **User is authenticated** - No password needed!

---

## Supabase Configuration

### 1. Enable Email OTP

Go to your Supabase Dashboard:
1. Navigate to **Authentication** → **Providers**
2. Find **Email** provider
3. Enable **"Email OTP"**
4. Configure email templates (optional)

### 2. Email Templates

Supabase lets you customize the OTP email:

**Default template looks like:**
```
Your verification code is: 123456

This code expires in 10 minutes.
```

**To customize:**
1. Go to **Authentication** → **Email Templates**
2. Edit the **"Magic Link"** template
3. Add your branding, logo, etc.

### 3. SMTP Configuration (Optional)

By default, Supabase uses their own SMTP server.

**For custom domain emails:**
1. Go to **Project Settings** → **Auth**
2. Configure **SMTP Settings**
3. Add your own SMTP server (SendGrid, Mailgun, etc.)

---

## API Usage

### Request OTP Code

```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver@example.com"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Verification code sent to driver@example.com",
  "email": "driver@example.com"
}
```

### Verify OTP Code

```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/verify \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver@example.com",
    "code": "123456"
  }'
```

**Response:**
```json
{
  "user": {
    "id": "uuid-here",
    "email": "driver@example.com",
    "phone": null,
    "created_at": "2024-01-08T12:00:00Z"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "refresh-token-here",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "driver": null  // or driver profile if exists
}
```

---

## Frontend Integration (React Native)

### Login Screen

```tsx
import { useState } from 'react';

export function EmailLogin() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [loading, setLoading] = useState(false);

  const requestCode = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/email/otp/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      if (response.ok) {
        setStep('code');
        // Show success message
        Alert.alert('Check your email!', 'We sent you a 6-digit code');
      }
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/email/otp/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code })
      });

      const data = await response.json();

      if (response.ok) {
        // Save tokens
        await AsyncStorage.setItem('access_token', data.tokens.access_token);
        await AsyncStorage.setItem('refresh_token', data.tokens.refresh_token);

        // Navigate based on driver profile
        if (data.driver) {
          navigation.navigate('Home');
        } else {
          navigation.navigate('Onboarding');
        }
      } else {
        Alert.alert('Invalid code', 'Please try again');
      }
    } finally {
      setLoading(false);
    }
  };

  if (step === 'email') {
    return (
      <View>
        <Text>Enter your email</Text>
        <TextInput
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          placeholder="driver@example.com"
        />
        <Button
          title="Send Code"
          onPress={requestCode}
          disabled={loading || !email}
        />
      </View>
    );
  }

  return (
    <View>
      <Text>Enter the 6-digit code sent to</Text>
      <Text style={{ fontWeight: 'bold' }}>{email}</Text>

      <TextInput
        value={code}
        onChangeText={setCode}
        keyboardType="number-pad"
        maxLength={6}
        placeholder="123456"
        autoFocus
      />

      <Button
        title="Verify & Login"
        onPress={verifyCode}
        disabled={loading || code.length !== 6}
      />

      <Button
        title="Change Email"
        onPress={() => setStep('email')}
      />
    </View>
  );
}
```

---

## Security Considerations

### OTP Expiry
- Default: **10 minutes**
- Configurable in Supabase Dashboard → Auth Settings

### Rate Limiting
- Supabase has built-in rate limiting
- Prevents spam/abuse
- Configure in Supabase Dashboard

### Account Creation
- First-time users auto-created with `should_create_user: true`
- Email verification happens via OTP (no separate confirmation email needed)

---

## Comparison: Email OTP vs Phone SMS

| Feature | Email OTP | Phone SMS |
|---------|-----------|-----------|
| **Cost** | ✅ Free | ❌ ~$0.01-0.05 per SMS |
| **Speed** | ✅ Instant | ✅ Instant |
| **Delivery** | ✅ 99%+ | ⚠️ 95%+ (carrier issues) |
| **User Experience** | ✅ Good | ✅ Good |
| **Setup** | ✅ Easy | ⚠️ Requires Twilio/etc |
| **Spam Risk** | ⚠️ Lower (email filters) | ✅ Higher delivery |
| **International** | ✅ Works everywhere | ⚠️ Costs vary by country |

### Recommendation
**Use Email OTP** for most users. Optionally support phone as backup.

---

## Migration from Phone to Email

If you already have phone-based users:

1. **Support Both** - Keep phone OTP working
2. **Prompt Email** - Ask existing users to add email
3. **Make Email Primary** - Use email for new signups
4. **Deprecate Phone** - Eventually phase out SMS

---

## Troubleshooting

### "Email not received"

1. **Check spam folder** - Most common issue
2. **Verify email address** - Typos are common
3. **Check Supabase logs** - Auth → Logs shows sent emails
4. **SMTP issues** - If using custom SMTP, check credentials

### "Invalid code"

1. **Code expired** - Default 10 min expiry
2. **Wrong code** - User typo
3. **Already used** - Codes are single-use

### "Too many requests"

1. **Rate limited** - Wait a few minutes
2. **Adjust limits** - Supabase Dashboard → Auth Settings

---

## Advanced: Custom Email Provider

If you want to use your own SMTP:

```bash
# In Supabase Dashboard → Project Settings → Auth

SMTP Host: smtp.sendgrid.net
SMTP Port: 587
SMTP User: apikey
SMTP Password: your-sendgrid-api-key
Sender Email: noreply@findatruckdriver.com
Sender Name: Find a Truck Driver
```

Popular providers:
- **SendGrid** - 100 emails/day free
- **Mailgun** - 5000 emails/month free
- **AWS SES** - Very cheap ($0.10 per 1000 emails)
- **Postmark** - Good deliverability

---

## Testing

### Development Testing

Use a test email (your own Gmail/etc):

```bash
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com"}'
```

Check your inbox for the 6-digit code.

### Production Testing

1. Test with real email addresses
2. Monitor Supabase Auth logs
3. Check email deliverability
4. Test on multiple email providers (Gmail, Outlook, Yahoo)

---

## Summary

✅ **Email OTP is now your primary authentication method**
✅ **No SMS costs** - Save money
✅ **Passwordless** - Better UX
✅ **Already implemented** - Ready to use!

**Endpoints:**
- `POST /api/v1/auth/email/otp/request` - Send code
- `POST /api/v1/auth/email/otp/verify` - Verify code

Start using it in your frontend today! 🚀
