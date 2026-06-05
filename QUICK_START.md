# ⚡ Quick Start Reference

## 🚀 First Time Setup (10 minutes)

```bash
# 1. Install dependencies
npm install

# 2. Generate encryption key
ENCRYPTION_KEY=$(openssl rand -hex 32)
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"

# 3. Generate WhatsApp verify token
VERIFY_TOKEN=$(openssl rand -hex 16)
echo "VERIFY_TOKEN=$VERIFY_TOKEN"

# 4. Copy environment template
cp .env.example .env.local

# 5. Edit .env.local with:
#    - ANTHROPIC_API_KEY (from console.anthropic.com)
#    - DATABASE_URL (from Supabase)
#    - WHATSAPP_API_KEY (from Meta)
#    - ENCRYPTION_KEY (generated above)
#    - WHATSAPP_VERIFY_TOKEN (generated above)

# 6. Run locally
npm run dev
# Open http://localhost:3000
```

---

## 📋 Environment Variables Needed

| Variable | Get From | Format |
|----------|----------|--------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | `sk-ant-...` |
| `DATABASE_URL` | Supabase project | `postgresql://...` |
| `SUPABASE_URL` | Supabase project | `https://xxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase project | API key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase project | Secret key ⚠️ |
| `WHATSAPP_API_KEY` | Meta Business Platform | API key |
| `WHATSAPP_PHONE_ID` | Meta Business Platform | Numeric ID |
| `WHATSAPP_VERIFY_TOKEN` | Generate: `openssl rand -hex 16` | Random string |
| `ENCRYPTION_KEY` | Generate: `openssl rand -hex 32` | 64 hex chars |
| `KV_URL` | Vercel Storage | Redis URL |
| `KV_REST_API_URL` | Vercel Storage | API URL |
| `KV_REST_API_TOKEN` | Vercel Storage | Access token |
| `BLOB_READ_WRITE_TOKEN` | Vercel Storage | Token |
| `CALCULATOR_ENDPOINT` | Your app | `https://your-app.vercel.app/api/calculate` |
| `LOG_LEVEL` | Choose | `debug`, `info`, `warn`, `error` |
| `SENTRY_DSN` | Sentry (optional) | Full DSN |

---

## 🗄️ Database Setup

### Step 1: Create Supabase Project
```
Go to: https://supabase.com/dashboard
Create new project
```

### Step 2: Run Schema Migration
Copy entire contents of:
```
supabase/migrations/001_initial_schema.sql
```

Paste into Supabase SQL editor and run.

### Step 3: Get Connection String
```
Settings → Database → Connection String → URI
```

Copy to `.env.local` as `DATABASE_URL`

---

## ✅ Local Testing

### Test Orchestrator
```typescript
import { orchestrateWorkflow } from '@/lib/orchestrator';
import * as fs from 'fs';

const imageBuffer = fs.readFileSync('./test-image.jpg');
const result = await orchestrateWorkflow(
  'tenant_123',
  '2026-06',
  [imageBuffer],
  './test-bill.pdf'
);

console.log(result.data?.bill.total_bill); // e.g., $77.70
```

### Test Individual Agents
```typescript
// Image OCR
import { imageOCRAgent } from '@/lib/agents/image-ocr';
const ocr = await imageOCRAgent({ image_data: buffer, image_format: 'jpg' });

// PDF Extraction
import { pdfExtractionAgent } from '@/lib/agents/pdf-extraction';
const pdf = await pdfExtractionAgent({ pdf_path: './bill.pdf' });

// Validation
import { validationAgent } from '@/lib/agents/validation';
const valid = await validationAgent({ readings: ocr.reading });
```

---

## 🚀 Deploy to Vercel

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Set environment variables
vercel env add ANTHROPIC_API_KEY
vercel env add DATABASE_URL
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
vercel env add SUPABASE_SERVICE_ROLE_KEY
vercel env add WHATSAPP_API_KEY
vercel env add WHATSAPP_PHONE_ID
vercel env add WHATSAPP_VERIFY_TOKEN
vercel env add ENCRYPTION_KEY
vercel env add KV_URL
vercel env add KV_REST_API_URL
vercel env add KV_REST_API_TOKEN
vercel env add BLOB_READ_WRITE_TOKEN
vercel env add CALCULATOR_ENDPOINT
# ... add others from ENV_CHECKLIST.md

# 3. Deploy
vercel deploy --prod

# 4. Get your URL
# https://your-project.vercel.app
```

---

## 🔧 Configure WhatsApp Webhook

1. Go to Meta Business Platform → WhatsApp → API Setup
2. Set Callback URL: `https://your-project.vercel.app/api/webhook/whatsapp`
3. Set Verify Token: Your `WHATSAPP_VERIFY_TOKEN` value
4. Subscribe to: `messages`

---

## 🧪 Quick Tests

### Test 1: Health Check
```bash
curl http://localhost:3000/api/health
```

### Test 2: Mock Bill Calculation
```bash
curl -X POST http://localhost:3000/api/calculate-bill \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test_123",
    "billing_period": "2026-06",
    "image_data": "base64_encoded_image"
  }'
```

### Test 3: WhatsApp Webhook Verification
```bash
curl "http://localhost:3000/api/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test_challenge"
```

---

## 🔍 Debugging

### View Logs (Local)
```bash
npm run dev
# Logs appear in console
```

### View Logs (Production)
```bash
vercel logs
```

### Database Queries
```bash
# Open Supabase Dashboard
# Go to SQL Editor

# View audit logs
SELECT * FROM audit_logs 
ORDER BY created_at DESC 
LIMIT 10;

# View bills
SELECT * FROM bills 
WHERE tenant_id = 'your_tenant_id'
ORDER BY created_at DESC;

# View errors
SELECT workflow_id, error_message, created_at
FROM audit_logs
WHERE status = 'failure'
ORDER BY created_at DESC;
```

---

## 📊 File Structure Quick Reference

```
demo/
├── api/                    ← API endpoints
│   ├── webhook/whatsapp.ts (WhatsApp receiver)
│   └── calculate-bill.ts   (Example endpoint)
│
├── lib/                    ← Core logic
│   ├── orchestrator.ts     ⭐ MAIN COORDINATOR
│   ├── logger.ts           (Logging)
│   ├── encryption.ts       (Security)
│   └── agents/
│       ├── image-ocr.ts    (Claude Vision)
│       ├── pdf-extraction.ts (PDF + redaction)
│       ├── validation.ts   (Reconciliation)
│       └── formatter.ts    (Response formatting)
│
├── types/index.ts          ← TypeScript types
│
├── supabase/
│   └── migrations/001_initial_schema.sql (DB schema)
│
└── Documentation
    ├── README.md           (Start here)
    ├── IMPLEMENTATION_GUIDE.md (Detailed)
    ├── ENV_CHECKLIST.md    (All env vars)
    ├── PROJECT_SUMMARY.md  (What's built)
    └── QUICK_START.md      (This file)
```

---

## 🎯 Common Tasks

### Add New Tenant
```sql
INSERT INTO tenants (name, whatsapp_phone, email)
VALUES ('John Tenant', '+6581234567', 'john@example.com');
```

### Query Tenant Bills
```sql
SELECT * FROM bills
WHERE tenant_id = (SELECT id FROM tenants WHERE whatsapp_phone = '+6581234567')
ORDER BY created_at DESC;
```

### Check OCR Quality
```sql
SELECT action, stage, output_data->'confidence_score' as confidence
FROM audit_logs
WHERE action = 'image_extraction'
ORDER BY created_at DESC
LIMIT 5;
```

### Find Discrepancies
```sql
SELECT * FROM discrepancies
WHERE status = 'pending'
ORDER BY created_at DESC;
```

---

## ⚠️ Common Errors & Fixes

| Error | Solution |
|-------|----------|
| "ENCRYPTION_KEY not set" | `openssl rand -hex 32` and add to `.env.local` |
| "Database connection failed" | Check DATABASE_URL format and Supabase is running |
| "OCR confidence too low" | Provide clearer image, ensure meter display visible |
| "WhatsApp webhook not receiving" | Check webhook URL in Meta Platform matches Vercel URL |
| "Claude API error" | Verify ANTHROPIC_API_KEY is correct and not expired |

---

## 📞 Support Quick Links

- **Anthropic Docs:** https://docs.anthropic.com
- **Supabase Docs:** https://supabase.com/docs
- **Vercel Docs:** https://vercel.com/docs
- **WhatsApp Docs:** https://developers.facebook.com/docs/whatsapp
- **Next.js Docs:** https://nextjs.org/docs

---

## ✨ You're Ready!

Everything is set up. Next steps:

1. ✅ Run locally: `npm run dev`
2. ✅ Set up Supabase database
3. ✅ Fill in `.env.local` with API keys
4. ✅ Test orchestrator with sample image
5. ✅ Deploy to Vercel: `vercel deploy --prod`
6. ✅ Configure WhatsApp webhook
7. ✅ Go live! 🚀

---

**Questions?** Check:
- README.md (overview)
- IMPLEMENTATION_GUIDE.md (detailed)
- ENV_CHECKLIST.md (all variables)
