# Deployment Checklist - Railway

## ✅ Pre-Deployment (Completed)

- [x] Cached database solution implemented
- [x] TariffRateManager class created
- [x] UtilityCalculator integrated
- [x] Admin CLI tool created
- [x] Supabase schema prepared
- [x] Railway configuration files created (railway.toml, Procfile)
- [x] Git repository initialized
- [x] All code committed

## 📋 Deployment Steps (To Do)

### Step 1: GitHub Setup (5 minutes)
- [ ] Go to https://github.com/new
- [ ] Create repository: `utility-bill-calculator`
- [ ] Copy repository URL

### Step 2: Push Code to GitHub (2 minutes)
```bash
cd /Users/hoyeehong/Desktop/demo
git remote add origin https://github.com/YOUR_USERNAME/utility-bill-calculator.git
git branch -M main
git push -u origin main
```
- [ ] Verify code appears on GitHub

### Step 3: Create Railway Project (3 minutes)
- [ ] Go to https://railway.app/dashboard
- [ ] Click "New Project"
- [ ] Select "Deploy from GitHub repo"
- [ ] Select your repository
- [ ] Wait for auto-deployment to start

### Step 4: Configure Environment Variables (5 minutes)
In Railway Dashboard → Your Project → Variables tab:

```
SUPABASE_URL = https://your-project.supabase.co
SUPABASE_KEY = your-anon-key
ANTHROPIC_API_KEY = your-anthropic-key
TELEGRAM_BOT_TOKEN = your-telegram-bot-token
TELEGRAM_ADMIN_ID = your-telegram-id (optional)
```

- [ ] Set SUPABASE_URL
- [ ] Set SUPABASE_KEY
- [ ] Set ANTHROPIC_API_KEY
- [ ] Set TELEGRAM_BOT_TOKEN
- [ ] Trigger redeploy (click deploy button)

### Step 5: Run Supabase Migration (2 minutes)
1. Go to Supabase Dashboard → SQL Editor
2. Copy contents of `supabase/schema.sql`
3. Paste and execute

- [ ] tariff_rates table created
- [ ] meter_readings table created
- [ ] bills table created
- [ ] Seed data inserted (3 rates)

### Step 6: Verify Deployment (5 minutes)

```bash
# Get your public URL from Railway Dashboard
curl https://your-app.railway.app/health
# Expected: {"status":"ok","timestamp":"...","version":"2.0.0"}
```

- [ ] Health check passes
- [ ] No connection errors in logs
- [ ] "Tariff rate manager initialized" in logs

## 🧪 Post-Deployment Testing

### Test 1: Check Tariff Manager
- [ ] View logs for "Tariff rate manager initialized"
- [ ] Confirm no Supabase connection errors

### Test 2: Test with Telegram
- [ ] Send `/start` to bot
- [ ] Send meter images
- [ ] Verify bill calculates correctly
- [ ] Check bill includes water breakdown (usage + waterborne + conservation)

### Test 3: Verify Rates
- [ ] Query Supabase: `SELECT * FROM tariff_rates`
- [ ] Confirm 3 rates present (electricity, water_usage, water_waterborne)

### Test 4: Test Admin CLI (Local)
```bash
python cli_admin.py get-rates
python cli_admin.py history electricity
```
- [ ] CLI commands work locally
- [ ] Current rates display correctly

## 📊 Performance Verification

- [ ] Bill calculation: <100ms
- [ ] Health endpoint: <10ms
- [ ] No timeout errors
- [ ] Memory usage stable

## 🔄 Continuous Deployment

After first deployment, auto-deployment is enabled:

```bash
# Make changes
git add .
git commit -m "..."
git push origin main
# Railway auto-deploys within 1-2 minutes
```

- [ ] Auto-deployment configured on Railway

## 📝 Documentation

- [ ] Deployment guide saved (RAILWAY_DEPLOYMENT_GUIDE.md)
- [ ] Tariff setup guide updated (TARIFF_SETUP_GUIDE.txt)
- [ ] README.md updated with deployment info
- [ ] Environment variables documented

## 🎯 Final Status

- [ ] Application deployed to Railway
- [ ] All environment variables configured
- [ ] Database schema created
- [ ] Telegram bot connected and tested
- [ ] Health checks passing
- [ ] Logs clean (no errors)

## 📞 Support Info

**If deployment fails:**
1. Check Railway logs: "Logs" tab in dashboard
2. Verify all env vars set
3. Confirm GitHub repo is public
4. Check requirements.txt has all dependencies
5. Look for Python errors in logs

**Common issues:**
- "Module not found" → Update requirements.txt
- "Supabase connection failed" → Check env vars
- "Health check failed" → Check FastAPI startup in logs

## 🚀 Next Steps After Deployment

1. ✅ Test with real Telegram messages
2. ✅ Verify bills match expected calculations
3. ✅ Monitor logs for 24 hours
4. ✅ Set up quarterly rate update reminders
5. ✅ Add Telegram alerts for new tenants

---

**Estimated Total Time: 20-30 minutes**

**Status: READY TO DEPLOY ✅**
