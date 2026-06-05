# Telegram Bot Setup + Vercel Backend Integration

## 🤖 Quick Setup (10 minutes)

### Step 1: Create Telegram Bot

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow prompts:
   - **Bot name:** "Utility Bill Calculator" (or your choice)
   - **Bot username:** Something like `utility_bill_bot` (must end with `_bot`)
5. Copy the **token** (looks like `123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh`)
6. Save it for later

**Token format:** `{BOT_ID}:{API_KEY}`

### Step 2: Set Bot Commands

1. Send to BotFather: `/setcommands`
2. Select your bot
3. Send these commands (copy/paste):
```
start - Start using the bot
calculate - Calculate bill from readings
help - Show help message
```

### Step 3: Configure Webhook (Point to Vercel)

Once you have your Vercel URL (from deployment):

```bash
# Set these variables
BOT_TOKEN="your-token-from-botfather"
VERCEL_URL="https://your-app.vercel.app"

# Register webhook with Telegram
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${VERCEL_URL}/api/telegram\",
    \"drop_pending_updates\": true
  }"

# Verify webhook is set
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

**Expected response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://your-app.vercel.app/api/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### Step 4: Test the Bot

1. Open Telegram
2. Search for your bot (e.g., `@utility_bill_bot`)
3. Send `/start`
4. Send meter images or readings
5. Bot should respond with calculations

## 🔄 Workflow

```
User sends image/text to Telegram bot
    ↓
Telegram server receives message
    ↓
Telegram POSTs webhook to: https://your-app.vercel.app/api/telegram
    ↓
Vercel Python function processes:
  - Downloads image from Telegram
  - Extracts meter readings (via OCR or user input)
  - Looks up current tariff rates (from Supabase cache)
  - Calculates bill
  - Stores in Supabase
    ↓
Vercel sends response back to telegram_handler
    ↓
telegram_handler formats message
    ↓
Telegram bot sends message to user
    ↓
User receives formatted bill
```

## 📱 Example Interactions

### Scenario 1: User Sends Meter Image

```
User: [sends photo of electricity meter showing 150 kWh]
Bot: 🔄 Processing your meter readings...

[After 2-3 seconds]

Bot: ⚡ Electricity Charge
Current reading: 150 kWh
Previous reading: 100 kWh
Usage: 50 kWh @ $0.2674/kWh
Charge: $13.37

💧 Water Charges
Current reading: 8.3 m³
Previous reading: 5.0 m³
Usage: 3.3 m³

Water Usage: 3.3 m³ @ $1.43/m³ = $4.72
Waterborne Tax: 3.3 m³ @ $1.09/m³ = $3.60
Water Conservation: 50% × $4.72 = $2.36
Subtotal: $10.68

📊 Summary
Electricity: $13.37
Water: $10.68
Subtotal: $24.05
GST (9%): $2.16
💰 Total Due: $26.21

✅ Bill saved to database
```

### Scenario 2: User Sends Text

```
User: electricity 150 100 water 8.3 5
Bot: [same response as above]
```

## 🛠️ Troubleshooting

### Bot not responding?

1. **Check webhook registration:**
```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```
If `"has_custom_certificate": false` and URL is correct, webhook is registered.

2. **Check Vercel logs:**
```bash
vercel logs --project=utility-bill-calculator
```
Look for "Telegram webhook received" or error messages.

3. **Check Supabase connection:**
```bash
# From Supabase SQL Editor:
SELECT * FROM tariff_rates;
```

4. **Send test message to verify endpoint:**
```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": YOUR_CHAT_ID,
    "text": "Test message"
  }'
```

### Common Errors

| Error | Fix |
|-------|-----|
| "Webhook URL unreachable" | Ensure Vercel deployment succeeded |
| "Bot not responding" | Check webhook registered with `getWebhookInfo` |
| "Tariff rates empty" | Run `supabase/schema.sql` |
| "Image OCR failed" | Ensure Google Cloud Vision credentials set (optional) |
| "Calculation error" | Check Supabase env vars are correct |

## 🔐 Security Notes

- ✅ Bot token stored in Vercel as environment variable (never in code)
- ✅ User IDs not logged (only chat IDs)
- ✅ Meter readings encrypted in Supabase
- ✅ API calls only between Telegram → Vercel → Supabase
- ✅ No public AI model access (private Supabase)

## 📊 Bot Capabilities

✅ Supports multiple users simultaneously
✅ Handles image uploads (any meter display)
✅ Automatic meter reading extraction
✅ Dynamic tariff rate lookups
✅ Multi-tenant support (different chat IDs)
✅ Complete audit trail in Supabase
✅ Error handling & user feedback

## 🚀 Production Checklist

- [ ] Bot token created from BotFather
- [ ] Vercel deployment successful
- [ ] All env vars set in Vercel
- [ ] Supabase schema created
- [ ] Webhook registered with Telegram
- [ ] Health check passes (`/health`)
- [ ] Test message received in bot
- [ ] Bill calculation working
- [ ] Logs show no errors
- [ ] Ready for users!

---

**Time to production: ~30 minutes** ⏱️

Start with Step 1, then follow Vercel deployment guide.
