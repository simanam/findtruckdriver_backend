# Backend Documentation

Welcome to the Find a Truck Driver backend documentation!

---

## 🚀 Quick Start for Frontend Team

**Start here if you're integrating the frontend:**

1. **[QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md)** ⭐
   - All endpoints with request/response examples
   - Copy-paste ready code for React Native
   - Complete authentication flow
   - Working examples for all features

2. **[API_URLS_REFERENCE.md](./API_URLS_REFERENCE.md)** 📋
   - List of all API URLs (copy & paste ready)
   - Most important endpoints highlighted
   - Common mistakes to avoid

3. **[FRONTEND_TROUBLESHOOTING.md](./FRONTEND_TROUBLESHOOTING.md)** 🔧
   - Solutions for 404, 401, CORS errors
   - Network issues on physical devices
   - Debugging tools and tips

---

## 📖 Complete Guides

### Frontend Integration
- **[FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md)** - Full React Native integration guide with complete code examples

### Email Authentication
- **[EMAIL_OTP_SETUP.md](./EMAIL_OTP_SETUP.md)** - How email OTP works, why it's better than phone SMS
- **[SUPABASE_EMAIL_CONFIG.md](./SUPABASE_EMAIL_CONFIG.md)** - Supabase email provider configuration guide

### Database & Configuration
- **[database_schema.sql](./database_schema.sql)** - Complete database schema
- **[SUPABASE_KEYS_EXPLAINED.md](./SUPABASE_KEYS_EXPLAINED.md)** - Understanding Supabase API keys (new vs legacy)

---

## 🎯 I Want To...

### "Start integrating the frontend"
→ Read [QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md)

### "Fix a 404 error"
→ Check [FRONTEND_TROUBLESHOOTING.md](./FRONTEND_TROUBLESHOOTING.md#issue-1-404-not-found)

### "Understand email OTP"
→ Read [EMAIL_OTP_SETUP.md](./EMAIL_OTP_SETUP.md)

### "See all API endpoints"
→ Open [API_URLS_REFERENCE.md](./API_URLS_REFERENCE.md) or http://localhost:8000/docs

### "Configure Supabase email"
→ Follow [SUPABASE_EMAIL_CONFIG.md](./SUPABASE_EMAIL_CONFIG.md)

### "Understand the database"
→ Read [database_schema.sql](./database_schema.sql)

### "Learn about API keys"
→ Read [SUPABASE_KEYS_EXPLAINED.md](./SUPABASE_KEYS_EXPLAINED.md)

---

## 🔑 Essential Info

### Base URL
```
http://localhost:8000
```

### All Endpoints Start With
```
/api/v1/
```

### Example Complete URL
```
http://localhost:8000/api/v1/auth/email/otp/request
```

### Interactive API Docs
```
http://localhost:8000/docs
```

---

## 📱 Frontend Integration Checklist

- [ ] Backend server running (`./run_dev.sh`)
- [ ] Can access http://localhost:8000/health
- [ ] Created `config/api.ts` with correct URLs
- [ ] Implemented email OTP authentication
- [ ] Tested login flow with your own email
- [ ] Implemented driver profile creation
- [ ] Added location permissions
- [ ] Tested check-in feature
- [ ] Tested status updates
- [ ] Tested nearby drivers search

---

## 🆘 Getting Help

1. **Test with Swagger UI:** http://localhost:8000/docs
2. **Check troubleshooting guide:** [FRONTEND_TROUBLESHOOTING.md](./FRONTEND_TROUBLESHOOTING.md)
3. **View backend logs:** `tail -f logs/app.log`
4. **Test with curl:** Examples in [QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md)

---

## 📚 Document Index

### Frontend Integration
| Document | Purpose | Audience |
|----------|---------|----------|
| [QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md) | Quick reference with code examples | Frontend developers |
| [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md) | Complete integration guide | Frontend developers |
| [API_URLS_REFERENCE.md](./API_URLS_REFERENCE.md) | All API endpoints | Frontend developers |
| [FRONTEND_TROUBLESHOOTING.md](./FRONTEND_TROUBLESHOOTING.md) | Common issues & solutions | Frontend developers |

### Backend Configuration
| Document | Purpose | Audience |
|----------|---------|----------|
| [EMAIL_OTP_SETUP.md](./EMAIL_OTP_SETUP.md) | Email authentication guide | Backend/DevOps |
| [SUPABASE_EMAIL_CONFIG.md](./SUPABASE_EMAIL_CONFIG.md) | Supabase email settings | Backend/DevOps |
| [SUPABASE_KEYS_EXPLAINED.md](./SUPABASE_KEYS_EXPLAINED.md) | API key reference | Backend/DevOps |

### Database
| Document | Purpose | Audience |
|----------|---------|----------|
| [database_schema.sql](./database_schema.sql) | Database schema | Backend/Database |

---

## 🎉 Ready to Build!

The backend is fully functional with:
- ✅ 22 API endpoints
- ✅ Email OTP authentication (free, passwordless)
- ✅ Location tracking with privacy fuzzing
- ✅ Map search & clustering
- ✅ Comprehensive documentation

**Start with [QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md) and you'll be up and running in minutes!**
