#!/usr/bin/env python3
"""
Quick test script to verify Supabase connection
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

url = os.getenv("SUPABASE_URL")

# Try new format first, fall back to legacy
publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
anon_key = os.getenv("SUPABASE_ANON_KEY")
secret_key = os.getenv("SUPABASE_SECRET_KEY")
service_key = os.getenv("SUPABASE_SERVICE_KEY")

public_key = publishable_key or anon_key
private_key = secret_key or service_key

print(f"URL: {url}")
print(f"\nPublic key found: {bool(public_key)}")
if public_key:
    print(f"  Type: {'New (sb_publishable_)' if publishable_key else 'Legacy (anon)'}")
    print(f"  Prefix: {public_key[:20]}...")
    print(f"  Length: {len(public_key)}")

print(f"\nPrivate key found: {bool(private_key)}")
if private_key:
    print(f"  Type: {'New (sb_secret_)' if secret_key else 'Legacy (service_key)'}")
    print(f"  Prefix: {private_key[:20]}...")
    print(f"  Length: {len(private_key)}")

key = private_key  # Use private key for testing (bypasses RLS)
print()

try:
    print("Creating Supabase client...")
    client = create_client(url, key)
    print("✅ Client created successfully")
    print()

    print("Testing query to 'drivers' table...")
    response = client.from_("drivers").select("id").limit(1).execute()
    print(f"✅ Query successful! Found {len(response.data)} records")

except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    print()
    print("Troubleshooting:")
    print("1. Check that your SUPABASE_URL is correct")
    print("2. Verify your keys are complete (no truncation)")
    print("3. Ensure the keys are from: Supabase Dashboard → Project Settings → API")
    print("4. The keys should be LONG (200+ characters for JWT, varies for new format)")
    print("5. Check if keys in .env have quotes or extra spaces")
    print("\nNote: If your keys are very short (< 100 chars), they're likely truncated or invalid")
