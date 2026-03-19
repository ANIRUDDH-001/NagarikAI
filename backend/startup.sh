#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== NagarikAI Startup Checks ==="

# 1. Environment Variable Verification
REQUIRED_VARS=("SUPABASE_URL" "SUPABASE_KEY" "GROQ_API_KEY" "SARVAM_API_KEY")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Environment variable $var is not set."
        exit 1
    fi
done
echo "✅ All required environment variables are set."

# 2. Supabase Connectivity Test
echo "Testing Supabase connectivity..."
python -c "
import os
from db.supabase_client import supabase
try:
    # Quick select to verify API connection and key
    supabase.table('schemes').select('id').limit(1).execute()
    print('✅ Supabase connected successfully.')
except Exception as e:
    print('❌ Supabase connection failed:', e)
    exit(1)
"

# 3. Groq Connectivity Test
echo "Testing Groq AI connectivity..."
python -c "
import os
from groq import Groq
client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
try:
    client.chat.completions.create(
        model='meta-llama/llama-4-scout-17b-16e-instruct',
        messages=[{'role': 'user', 'content': 'ping'}],
        max_tokens=5
    )
    print('✅ Groq connected successfully.')
except Exception as e:
    print('❌ Groq connection failed:', e)
    exit(1)
"

# 4. Database Volume Integrity Check (Warning only, don't block boot)
echo "Verifying scheme pool size..."
python -c "
import os
from db.supabase_client import supabase
res = supabase.table('schemes').select('id', count='exact').execute()
count = res.count or 0
print(f'-> Found {count} schemes in database.')
if count < 40:
    print('⚠️ WARNING: Scheme count is low (< 40). Production pool may be incomplete!')
else:
    print('✅ Scheme pool size is satisfactory.')
"

# 5. Start Uvicorn
echo "=== Starting Uvicorn Server ==="
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
