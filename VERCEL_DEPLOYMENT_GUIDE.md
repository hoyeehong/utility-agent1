# Vercel Deployment Guide - Python FastAPI + Telegram Bot

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     TELEGRAM BOT (LOCAL/HEROKU)             │
│  - Handles /start command                                    │
│  - Receives images from users                                │
│  - POSTs webhook to Vercel API                               │
│  - Sends formatted responses back to user                    │
└────────────────────────────┬────────────────────────────────┘
                             │ (webhook)
                             ↓
┌─────────────────────────────────────────────────────────────┐
│             VERCEL SERVERLESS FUNCTIONS (PYTHON)            │
│                                                              │
│  ├─ /api/index.py ─────────── Main FastAPI app             │
│  ├─ /api/telegram.py ──────── Webhook handler (POST)       │
│  ├─ /api/calculate.py ─────── Bill calculation API         │
│  │                                                          │
│  └─ Modules (imported by functions):                        │
│     ├─ utility_calculator.py (bill logic)                   │
│     ├─ tariff_rate_manager.py (rate fetching)               │
│     ├─ orchestrator.py (workflow)                           │
│     ├─ agents_*.py (image OCR, PDF extraction, etc)         │
│     └─ telegram_utils.py (send/receive)                     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                   SUPABASE DATABASE                         │
│                                                              │
│  ├─ tariff_rates (electricity, water rates)                 │
│  ├─ meter_readings (audit trail)                            │
│  ├─ bills (calculation history)                             │
│  └─ RLS policies (security)                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Step-by-Step Deployment

### Step 1: Prepare GitHub Repository

```bash
cd /Users/hoyeehong/Desktop/demo

# Verify all files are committed
git status

# If there are changes:
git add .
git commit -m "Add Vercel Python serverless setup"

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Connect Vercel to GitHub

1. Go to https://vercel.com/dashboard
2. Click "Add New..." → "Project"
3. Select "Import Git Repository"
4. Search for `utility-bill-calculator` (your repo)
5. Click "Import"
6. Vercel auto-detects Python configuration

### Step 3: Configure Environment Variables on Vercel

In Vercel Dashboard → Your Project → Settings → Environment Variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
TELEGRAM_BOT_TOKEN=your-telegram-token
TELEGRAM_ADMIN_ID=your-telegram-user-id (optional)
ENCRYPTION_KEY=your-64-char-hex-key
LOG_LEVEL=INFO
```

**Where to get each:**
- `SUPABASE_URL` & `SUPABASE_KEY`: Supabase project settings → API
- `TELEGRAM_BOT_TOKEN`: From BotFather on Telegram
- `ENCRYPTION_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`

### Step 4: Run Supabase Database Schema

1. Go to Supabase Dashboard → Your Project
2. Click "SQL Editor"
3. Click "New Query"
4. Copy entire contents of `supabase/schema.sql`
5. Paste and execute

**Expected output:** 3 tables created + seed data inserted

### Step 5: Get Your Vercel URL

After deployment succeeds:
- Go to Vercel Dashboard → Your Project
- Copy the deployment URL (e.g., `https://utility-calculator-xyz.vercel.app`)
- This is your backend API URL

### Step 6: Update Telegram Bot Webhook

If you're hosting Telegram bot separately, configure it to POST to Vercel:

```bash
VERCEL_URL="https://your-app.vercel.app"
TELEGRAM_BOT_TOKEN="your-bot-token"

# Set webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${VERCEL_URL}/api/telegram\"}"

# Verify webhook
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

## 📚 API Endpoints

### 1. Health Check
```bash
GET https://your-app.vercel.app/health
# Returns: {"status":"ok","version":"2.0.0"}
```

### 2. Telegram Webhook
```bash
POST https://your-app.vercel.app/api/telegram
Body: Telegram webhook payload (automatic)
```

### 3. Calculate Bill (Direct API)
```bash
POST https://your-app.vercel.app/api/calculate
Content-Type: application/json

{
  "electricity_current": 150,
  "electricity_previous": 100,
  "water_current": 8.3,
  "water_previous": 5.0
}

# Response:
{
  "status": "success",
  "data": {
    "bill": {
      "electricity_charge": 16.81,
      "water_charge": 43.21,
      "gst": 5.40,
      "total_bill_with_gst": 65.42
    }
  }
}
```

## 🧪 Testing

### Test 1: Health Check
```bash
curl https://your-app.vercel.app/health
# Expected: 200 OK with {"status":"ok"}
```

### Test 2: Direct Bill Calculation
```bash
curl -X POST https://your-app.vercel.app/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "electricity_current": 150,
    "electricity_previous": 100,
    "water_current": 8.3,
    "water_previous": 5.0
  }'
```

### Test 3: Telegram Integration
1. Send `/start` to your Telegram bot
2. Send meter images
3. Bot POSTs to Vercel → calculation → response sent to Telegram

### Test 4: Supabase Connection
```bash
# From Supabase SQL Editor:
SELECT * FROM tariff_rates;
SELECT * FROM bills ORDER BY created_at DESC LIMIT 5;
```

## 🔍 Monitoring & Debugging

### View Vercel Logs
```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# View logs
vercel logs --project=utility-bill-calculator
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError: No module named..." | Check `requirements.txt` has all dependencies |
| "Supabase connection failed" | Verify `SUPABASE_URL` and `SUPABASE_KEY` in env vars |
| "Telegram webhook not working" | Ensure webhook URL is correctly registered with Telegram |
| "Cold start too slow" | Increase memory allocation in `vercel.json` |
| "Tariff rates empty" | Run `supabase/schema.sql` to seed data |

### Logs to Look For

**Success:**
```
✅ Tariff rate manager initialized
✅ Supabase client created
📱 Telegram webhook received
✅ Bill calculated: $65.42
```

**Errors:**
```
❌ Telegram webhook error
❌ Supabase connection failed
❌ Calculation failed
```

## 📊 Performance

| Metric | Expected |
|--------|----------|
| Bill calculation | <100ms |
| Telegram webhook | <2s (cold start) |
| Rate lookup | <1ms (cached) |
| Health check | <10ms |
| Concurrent users | Unlimited (auto-scales) |

## 💰 Cost Estimate

| Service | Free Tier | Estimated Cost |
|---------|-----------|----------------|
| Vercel | 100GB bandwidth/month | $0 |
| Supabase | 500MB database | $0 |
| Google Cloud Vision | 1000 requests/month | ~$0.50 |
| **Total** | | **~$0.50/month** |

## 🔄 Continuous Deployment

After first deployment, auto-deployment is enabled:

```bash
# Make code changes
git add .
git commit -m "Fix something"
git push origin main

# Vercel auto-deploys (1-2 minutes)
# Check progress in Vercel Dashboard
```

## 📝 Environment Variables Reference

```bash
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-anon-key
TELEGRAM_BOT_TOKEN=123:ABC

# Optional
ENCRYPTION_KEY=0123...abcd (64 hex chars)
TELEGRAM_ADMIN_ID=123456
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
```

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Vercel project created
- [ ] All environment variables set
- [ ] Supabase schema executed
- [ ] Health check passes
- [ ] Telegram webhook registered
- [ ] Test message sent to bot
- [ ] Bill calculated successfully
- [ ] Logs show no errors

## 🎯 Next Steps

1. ✅ Deploy code to Vercel (this guide)
2. ✅ Configure database (Supabase)
3. ✅ Set environment variables
4. ✅ Verify health check
5. ✅ Test Telegram integration
6. 📊 Monitor logs for 24 hours
7. 🚀 Go live!

---

**Status:** Ready to deploy! Follow steps 1-6 above.

**Questions?** Check the troubleshooting section or Vercel CLI logs.
