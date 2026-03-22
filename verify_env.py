import os
import httpx
import asyncio
from dotenv import load_dotenv

# Load .env file
load_dotenv()

async def verify_supabase():
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url:
        print("❌ SUPABASE_URL not found in .env")
        return

    print(f"Checking Supabase: {url}")
    
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}"
    }
    
    try:
        # Simple health check or REST API check
        async with httpx.AsyncClient() as client:
            # Try to hit the REST API root or a health endpoint
            # Supabase usually has a /auth/v1/health or rest/v1/
            # Let's try to hit the rest endpoint root
            response = await client.get(f"{url}/rest/v1/", headers=headers)
            print(f"Supabase Anon Check: Status {response.status_code}")
            if response.status_code == 200:
                print("✅ Supabase Anon Key works!")
            else:
                print(f"⚠️ Supabase Anon Key returned status {response.status_code}")

            if service_key:
                service_headers = {
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}"
                }
                response_service = await client.get(f"{url}/rest/v1/", headers=service_headers)
                print(f"Supabase Service Check: Status {response_service.status_code}")
                if response_service.status_code == 200:
                    print("✅ Supabase Service Role Key works!")
                else:
                    print(f"⚠️ Supabase Service Role Key returned status {response_service.status_code}")

    except Exception as e:
        print(f"❌ Supabase Error: {e}")

async def verify_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in .env")
        return

    print("Checking Groq API...")
    try:
        import groq
        client = groq.Groq(api_key=api_key)
        # List models is a good non-consumptive test
        models = client.models.list()
        print(f"✅ Groq API works! Found {len(models.data)} models.")
    except Exception as e:
        print(f"❌ Groq Error: {e}")

async def verify_sarvam():
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("❌ SARVAM_API_KEY not found in .env")
        return

    print("Checking Sarvam AI API...")
    headers = {
        "api-subscription-key": api_key
    }
    try:
        async with httpx.AsyncClient() as client:
            # Sarvam doesn't always have a generic list models, but let's try a health check or simple GET that might exist
            # Based on search, base URL is https://api.sarvam.ai/
            # Let's try to hit the base or a likely public endpoint with auth
            # Since we don't have a guaranteed read-only endpoint, we'll try to just check if we get a 200/401/403
            response = await client.get("https://api.sarvam.ai/", headers=headers)
            print(f"Sarvam AI Check: Status {response.status_code}")
            # If it's a base URL, it might be 404 or 403, but if it's 401 it means invalid key
            # Let's check if we can get a better endpoint
            # Actually, without a clear list models endpoint, testing it might be tricky without making a billable call
            if response.status_code in [200, 201]:
                print("✅ Sarvam AI Key works!")
            elif response.status_code == 401:
                print("❌ Sarvam AI Key is Invalid (401)")
            else:
                print(f"ℹ️ Sarvam AI returned {response.status_code}. Key might be valid, but endpoint hit is not intended.")
                print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Sarvam Error: {e}")

async def main():
    print("=== Environment Variable Verification ===")
    await verify_supabase()
    print("\n" + "="*40 + "\n")
    await verify_groq()
    print("\n" + "="*40 + "\n")
    await verify_sarvam()
    print("\n=== End of Verification ===")

if __name__ == "__main__":
    asyncio.run(main())
