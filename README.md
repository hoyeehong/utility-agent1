# Utility Bill Calculator - Agentic Workflow

Automated tenant utility bill calculation using AI agents, WhatsApp integration, and Vercel serverless functions.

## 🌟 Features

- **WhatsApp Integration** - Tenants send meter images via WhatsApp
- **AI-Powered OCR** - Claude Vision extracts meter readings from images
- **PDF Processing** - Secure extraction of SP bill data with PII redaction
- **Smart Reconciliation** - Automatically reconciles discrepancies between sources
- **Serverless Deployment** - 100% cloud-based on Vercel (no servers to manage)
- **Audit Logging** - Complete audit trail in Supabase for compliance
- **Security** - PII encryption, data redaction, PDPA compliant

## 🏗️ Architecture

```
WhatsApp → Vercel Functions → Claude API → Calculator → Supabase → WhatsApp Response
```

**All components are serverless and fully automated.**

## 📋 Quick Links

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Complete setup guide
- **[ENV_CHECKLIST.md](ENV_CHECKLIST.md)** - Environment variables reference
- **[supabase/migrations/001_initial_schema.sql](supabase/migrations/001_initial_schema.sql)** - Database schema

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
npm install
```

### 2. Setup Environment
```bash
cp .env.example .env.local
# Edit .env.local with your API keys (see ENV_CHECKLIST.md)
```

### 3. Setup Database
```bash
# Create Supabase project, then paste schema from:
# supabase/migrations/001_initial_schema.sql
```

### 4. Run Locally
```bash
npm run dev
# http://localhost:3000
```

### 5. Deploy to Vercel
```bash
npm install -g vercel
vercel deploy --prod
```

## 📚 Project Structure

```
├── api/                          # API endpoints
│   ├── webhook/whatsapp.ts      # WhatsApp webhook receiver
│   └── calculate-bill.ts        # Bill calculation endpoint
│
├── lib/                          # Core logic
│   ├── orchestrator.ts          # ⭐ Main workflow coordinator
│   ├── logger.ts                # Logging utility
│   ├── encryption.ts            # PII encryption/redaction
│   │
│   └── agents/                  # AI agents
│       ├── image-ocr.ts         # Extract meter from images
│       ├── pdf-extraction.ts    # Extract meter from PDFs
│       ├── validation.ts        # Validate & reconcile data
│       └── formatter.ts         # Format responses
│
├── types/                        # TypeScript types
│   └── index.ts
│
├── supabase/                     # Database
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── .env.example                  # Environment template
├── ENV_CHECKLIST.md              # Environment variables guide
└── IMPLEMENTATION_GUIDE.md       # Complete setup guide
```

## 🔧 Core Components

### Orchestrator (`lib/orchestrator.ts`)
The heart of the system. Coordinates all agents in sequence:

1. **Input Validation** - Verify images/PDF provided
2. **Image Extraction** - Run Claude Vision OCR
3. **PDF Extraction** - Extract meter data with PII redaction
4. **Data Validation** - Validate & reconcile readings
5. **Calculate** - Call your calculator API
6. **Format & Log** - Prepare response & audit trail

### Agents

| Agent | Purpose |
|-------|---------|
| **Image OCR** | Extracts meter readings from WhatsApp images using Claude Vision |
| **PDF Extraction** | Extracts meter data from SP bill PDFs with PII redaction |
| **Validation** | Validates readings and reconciles discrepancies |
| **Formatter** | Formats results for WhatsApp and audit logging |

### Integrations

| Service | Purpose |
|---------|---------|
| **Claude API** | Image OCR and PDF processing |
| **WhatsApp Business API** | Send/receive messages |
| **Supabase** | PostgreSQL database for audit logs |
| **Vercel** | Serverless function hosting |
| **Your Calculator** | Existing bill calculation API |

## 🔐 Security Features

- **PII Redaction** - Automatically redacts sensitive data from PDFs
- **AES-256 Encryption** - Encrypts sensitive fields before storage
- **Audit Logging** - Tracks all operations for compliance
- **Row Level Security** - Database enforces access control
- **PDPA Compliant** - Designed for Singapore data protection

## 📊 Data Flow

```
TENANT SENDS IMAGE/PDF
        ↓
   Webhook Receives
        ↓
  ┌────────────────────┐
  │ Orchestrator Start │
  └─────────┬──────────┘
        ↓
   Extract Images (Claude Vision)
        ↓
   Extract PDF (Claude with redaction)
        ↓
   Validate & Reconcile
        ↓
   Call Calculator API
        ↓
   Format Response
        ↓
   ┌──────────────────────────┐
   │ Store Audit Log          │
   │ Send WhatsApp Message    │
   │ Return Success Response  │
   └──────────────────────────┘
```

## 💰 Estimated Costs (Monthly)

| Component | Usage | Cost |
|-----------|-------|------|
| Claude API | 100 bills × ~1,800 tokens | $5 |
| Vercel Functions | Included in free tier | $0 |
| Vercel Blob | 100 PDFs × 2MB | $10 |
| Vercel KV | Caching + state | $7.50 |
| Supabase | ~500k records | $25 |
| WhatsApp | 100 messages | $10 |
| **TOTAL** | | **~$60/month** |

## 🧪 Testing

```bash
# Run all tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

## 📈 Monitoring

- **Logs:** `vercel logs`
- **Errors:** Set up Sentry (see ENV_CHECKLIST.md)
- **Database:** Query Supabase audit_logs table
- **Performance:** Monitor Vercel Analytics dashboard

## 🚨 Troubleshooting

See **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md#troubleshooting)** for detailed troubleshooting.

### Common Issues

**WhatsApp webhook not receiving:** Check webhook URL in Meta Business Platform

**OCR returns low confidence:** Provide clearer image, ensure meter display is visible

**Database connection failed:** Verify DATABASE_URL format and Supabase project is active

## 📚 Documentation

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Complete implementation guide
- **[ENV_CHECKLIST.md](ENV_CHECKLIST.md)** - All environment variables
- **[Deployment Architecture](../files/deployment-architecture.md)** - System design
- **[Workflow Architecture](../files/agentic-workflow-architecture.md)** - Workflow design

## 🤝 Support

For questions or issues:
1. Check troubleshooting section in IMPLEMENTATION_GUIDE.md
2. Review environment variables in ENV_CHECKLIST.md
3. Check logs: `vercel logs` (production) or console (development)
4. Query audit logs in Supabase for debugging

## 📄 License

This project is private. Do not distribute without permission.

## ✅ Next Steps

- [ ] Copy `.env.example` to `.env.local`
- [ ] Generate encryption key: `openssl rand -hex 32`
- [ ] Set up Supabase project
- [ ] Add all API keys to `.env.local`
- [ ] Run `npm install && npm run dev`
- [ ] Test with sample images
- [ ] Deploy to Vercel: `vercel deploy --prod`
- [ ] Configure WhatsApp webhook
- [ ] Go live!

---

**Last Updated:** 2026-06-04
**Status:** Ready for implementation ✓
