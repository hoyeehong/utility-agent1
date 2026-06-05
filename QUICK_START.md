# ⚡ Quick Start Reference

## 🚀 First Time Setup (10 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate encryption key
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Copy environment template
cp .env.example .env

# 4. Edit .env with:
#    - TELEGRAM_BOT_TOKEN (from BotFather)
#    - SUPABASE_URL (from Supabase project)
#    - SUPABASE_KEY (from Supabase project)
#    - GOOGLE_APPLICATION_CREDENTIALS (optional, for OCR)
#    - ENCRYPTION_KEY (generated above)

# 5. Run locally
python main.py
# Server runs on http://localhost:8000
```

---

## 📋 Environment Variables Needed (Required)

| Variable | Get From | Format |
|----------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | BotFather on Telegram | `123456:ABC-DEF...` |
| `SUPABASE_URL` | Supabase project settings | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase project settings | Anon key |

---

## 🗄️ Database Setup

### Step 1: Create Supabase Project
```
Go to: https://app.supabase.com/projects
Create new project
```

### Step 2: Run Schema Migration
Copy entire contents of:
```
supabase/schema.sql
```

Paste into Supabase SQL editor and run.

### Step 3: Get Connection Details
```
Settings → API → URL and anon key
```

Copy to `.env` as `SUPABASE_URL` and `SUPABASE_KEY`

---

## ✅ Local Testing

### Test Calculator
```python
from utility_calculator import UtilityCalculator

calc = UtilityCalculator()
bill = calc.calculate_bill(
    electricity_usage=150,  # kWh
    water_usage=8.3,        # m³
    previous_data={'electricity': 100, 'water': 5}
)
print(f"Total bill: ${bill['total_bill_with_gst']:.2f}")
```

### Test Tariff Manager
```python
from tariff_rate_manager import TariffRateManager

manager = TariffRateManager()
rates = manager.get_rates()
print(f"Electricity rate: ${rates['electricity_rate']}/kWh")
print(f"Water rate: ${rates['water_rate']}/m³")
```

---

## 🚀 Deploy to Railway

```bash
# 1. Install Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# 2. Login to Railway
railway login

# 3. Create new project
railway init

# 4. Set environment variables
railway variable set TELEGRAM_BOT_TOKEN your-token
railway variable set SUPABASE_URL your-url
railway variable set SUPABASE_KEY your-key

# 5. Deploy
railway deploy

# 6. Get your URL
railway open
```

---

## 🧪 Quick Tests

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

### Test 2: Calculate Bill
```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "electricity_current": 150,
    "electricity_previous": 100,
    "water_current": 8.3,
    "water_previous": 5.0
  }'
```

---

## 🔍 Debugging

### View Logs (Local)
```bash
python main.py
# Logs appear in console
```

### View Logs (Railway)
```bash
railway logs
```

### Database Queries (Supabase)
```bash
# Open Supabase Dashboard → SQL Editor

# View tariff rates
SELECT * FROM tariff_rates ORDER BY updated_at DESC LIMIT 5;

# View meter readings
SELECT * FROM meter_readings ORDER BY created_at DESC LIMIT 10;

# View bills
SELECT * FROM bills ORDER BY created_at DESC LIMIT 10;
```

---

## 📊 File Structure Quick Reference

```
demo/
├── main.py                      ← FastAPI app
├── utility_calculator.py        ⭐ BILL CALCULATION
├── tariff_rate_manager.py       ← Dynamic rates
├── telegram_handler.py          ← Telegram integration
├── agents_image_ocr.py          (Image processing)
├── agents_pdf_extraction.py     (PDF processing)
├── agents_validation.py         (Validation)
├── agents_formatter.py          (Response formatting)
├── cli_admin.py                 (Admin CLI)
├── encryption.py                (Security)
├── logger.py                    (Logging)
├── schemas.py                   (Data models)
├── requirements.txt             (Dependencies)
├── supabase/schema.sql          (DB schema)
├── railway.toml                 (Railway config)
├── Procfile                     (Start command)
├── .env.example                 (Environment template)
└── Documentation
    ├── README.md
    ├── QUICK_START.md (this file)
    ├── PROJECT_SUMMARY.md
    └── DEPLOYMENT_CHECKLIST.md
```

---

## 🎯 Common Tasks

### Add Tariff Rate
```bash
python cli_admin.py add-rate --type electricity --rate 0.2674 --effective-date 2026-06-01
```

### Check Current Rates
```bash
python cli_admin.py get-rates
```

### Calculate Bill
```bash
python -c "
from utility_calculator import UtilityCalculator
calc = UtilityCalculator()
bill = calc.calculate_bill(150, 8.3, {'electricity': 100, 'water': 5})
print(f'Bill: \${bill[\"total_bill_with_gst\"]:.2f}')
"
```

---

## ⚠️ Common Errors & Fixes

| Error | Solution |
|-------|----------|
| "Telegram token not set" | Copy TELEGRAM_BOT_TOKEN to .env from BotFather |
| "Supabase connection failed" | Check SUPABASE_URL and SUPABASE_KEY format |
| "Database schema error" | Run supabase/schema.sql in Supabase SQL editor |
| "Encryption key invalid" | Generate new key: `python -c "import secrets; print(secrets.token_hex(32))"` |
| "Rates table empty" | Run admin CLI: `python cli_admin.py add-rate ...` |

---

## 📞 Support Quick Links

- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Supabase Docs:** https://supabase.com/docs
- **Railway Docs:** https://docs.railway.app
- **Google Cloud Vision:** https://cloud.google.com/vision/docs
- **FastAPI:** https://fastapi.tiangolo.com/

---

## ✨ You're Ready!

Everything is set up. Next steps:

1. ✅ Create Telegram bot via BotFather
2. ✅ Create Supabase project
3. ✅ Fill in `.env` with tokens
4. ✅ Run locally: `python main.py`
5. ✅ Test calculator with sample data
6. ✅ Deploy to Railway
7. ✅ Go live! 🚀

---

**Questions?** Check:
- README.md (overview)
- PROJECT_SUMMARY.md (architecture)
- DEPLOYMENT_CHECKLIST.md (deployment steps)
