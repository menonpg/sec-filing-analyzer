# Deployment Guide

## Quick Start: Railway Deployment

Railway doesn't natively run docker-compose. Instead, we deploy each service separately. Here's the fastest path:

### Option A: Use Dify Cloud + Our Tools (Fastest)

**Time: 10 minutes**

1. Sign up at [dify.ai](https://dify.ai) (200 free GPT-4 calls)
2. Create a new app → Agent type
3. Add our custom tools via API
4. Connect to your data

**Pros:** No infrastructure, instant start
**Cons:** Limited free tier, less control

---

### Option B: Railway Multi-Service Deploy (Recommended)

**Time: 30-45 minutes**

#### Step 1: Create Railway Project

```bash
# Login to Railway
railway login

# Create new project
railway init
```

#### Step 2: Add PostgreSQL

1. In Railway dashboard → New Service → Database → PostgreSQL
2. Railway auto-creates `DATABASE_URL` and `PG*` variables

#### Step 3: Add Redis (or use Upstash)

**Option: Railway Redis**
1. New Service → Database → Redis
2. Note the connection details

**Option: Upstash (free tier)**
1. Go to [upstash.com](https://upstash.com)
2. Create Redis database
3. Copy host, port, password

#### Step 4: Deploy Dify API

1. New Service → Docker Image
2. Image: `langgenius/dify-api:latest`
3. Add environment variables:

```
MODE=api
LOG_LEVEL=INFO
SECRET_KEY=<generate with: openssl rand -base64 42>
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}
DB_USERNAME=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}
DB_DATABASE=${{Postgres.PGDATABASE}}
REDIS_HOST=<your-redis-host>
REDIS_PORT=6379
REDIS_PASSWORD=<your-redis-password>
REDIS_USE_SSL=true
VECTOR_STORE=qdrant
QDRANT_URL=<your-qdrant-cloud-url>
QDRANT_API_KEY=<your-qdrant-api-key>
AZURE_OPENAI_API_KEY=<your-azure-key>
AZURE_OPENAI_API_BASE=<your-azure-endpoint>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=/app/api/storage
```

4. Set port: 5001

#### Step 5: Deploy Dify Worker

1. New Service → Docker Image
2. Image: `langgenius/dify-api:latest`
3. Same environment variables as API, but:
```
MODE=worker
```
4. No port needed (background worker)

#### Step 6: Deploy Dify Web

1. New Service → Docker Image
2. Image: `langgenius/dify-web:latest`
3. Environment variables:
```
CONSOLE_API_URL=https://<your-api-service>.railway.app
APP_API_URL=https://<your-api-service>.railway.app
```
4. Set port: 3000
5. Generate domain

#### Step 7: Update API URLs

Go back to API service and add:
```
CONSOLE_WEB_URL=https://<your-web-service>.railway.app
SERVICE_API_URL=https://<your-api-service>.railway.app
APP_WEB_URL=https://<your-web-service>.railway.app
```

#### Step 8: Access Dify

1. Open your web service URL
2. Create admin account on first visit
3. Start building!

---

### Option C: Local Docker Compose (Development)

**Time: 15 minutes**

```bash
cd sec-filing-analyzer

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Start all services
docker-compose up -d

# Access Dify at http://localhost:3000
```

---

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | App secret (generate random) | `openssl rand -base64 42` |
| `DB_HOST` | PostgreSQL host | `containers-us-west-123.railway.app` |
| `DB_PASSWORD` | PostgreSQL password | `xxx` |
| `REDIS_HOST` | Redis host | `helpful-koala-12345.upstash.io` |
| `REDIS_PASSWORD` | Redis password | `xxx` |
| `QDRANT_URL` | Qdrant Cloud URL | `https://xxx.qdrant.io:6333` |
| `QDRANT_API_KEY` | Qdrant API key | `xxx` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key | `xxx` |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI endpoint | `https://xxx.openai.azure.com/` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `REDIS_USE_SSL` | Use TLS for Redis | `true` for Upstash |
| `STORAGE_TYPE` | File storage type | `local` |

---

## Connecting Our Custom Tools

Once Dify is running, add our SEC tools:

### Via Dify UI (Easiest)

1. Go to Dify → Tools → Custom
2. For each tool, create an OpenAPI spec or HTTP endpoint
3. Point to our FastAPI service (deploy separately or as Lambda)

### Deploy Tools as Separate Service

```bash
# From sec-filing-analyzer repo
cd tools-api

# Deploy to Railway
railway up
```

Then connect via Dify's external tool feature.

---

## Estimated Costs

| Service | Provider | Cost |
|---------|----------|------|
| Dify (API + Worker + Web) | Railway | ~$10-15/month |
| PostgreSQL | Railway | ~$5/month |
| Redis | Upstash | Free tier (10K/day) |
| Vector DB | Qdrant Cloud | Free tier (1GB) |
| LLM | Azure OpenAI | Pay per token |

**Total infrastructure: ~$15-20/month**

---

## Troubleshooting

### "Connection refused" to database
- Check `DB_HOST` is the external Railway hostname, not `localhost`
- Ensure PostgreSQL service is running

### "Redis connection failed"
- For Upstash: Set `REDIS_USE_SSL=true`
- Check password is correct

### Dify shows blank page
- Check browser console for API errors
- Verify `CONSOLE_API_URL` points to API service

### Vector search not working
- Verify Qdrant credentials
- Check collection exists: `curl $QDRANT_URL/collections`

---

## Next Steps After Deploy

1. **Create Dify account** — First visit to web UI
2. **Add Azure OpenAI model** — Settings → Model Providers
3. **Create Agent app** — Use ReAct pattern for SEC analysis
4. **Add custom tools** — Company search, filing fetch
5. **Test with "What is BCRED?"** — Verify end-to-end
