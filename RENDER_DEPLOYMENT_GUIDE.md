# Render Deployment Guide - Separated Frontend & Backend

## Overview

This guide sets up LotGenius as two separate Render services:

- **Backend Service**: Python FastAPI at https://lot-genius.onrender.com
- **Frontend Service**: Next.js app at your-new-frontend-url.onrender.com

## Current Status

✅ **Backend**: Already deployed and responding to health checks
⚠️ **Pipeline Issue**: 500 error in `/v1/pipeline/upload` - needs investigation
🔄 **Frontend**: Ready for separate deployment

---

## Backend Service Configuration

### Environment Variables (Already Set)

```
# CORS Configuration
CORS_ORIGINS=https://your-frontend-url.onrender.com

# Optional API Integration
KEEPA_API_KEY=your_keepa_key_here

# Scraper Settings (Keep Disabled for Production)
ENABLE_EBAY_SCRAPER=false
ENABLE_FB_SCRAPER=false
ENABLE_GOOGLE_SEARCH_ENRICHMENT=false
SCRAPER_TOS_ACK=false

# eBay Production Credentials (Already Configured)
EBAY_DEV_ID=f040206a-ea80-4c49-93a4-6abdf2fe24bd
EBAY_APP_ID=HussienJ-LotGeniu-PRD-9a1c34eb9-b1930135
EBAY_CERT_ID=PRD-a1c34eb9469f-0e05-4a27-98c6-58e8
```

### Action Required

1. **Update CORS_ORIGINS**: Add your new frontend URL when deployed
2. **Redeploy Backend**: After updating CORS to pick up changes
3. **Debug Pipeline**: Investigate 500 error in pipeline endpoint

---

## Frontend Service Setup (New)

### Render Service Configuration

```yaml
Service Type: Web Service
Environment: Node 18+
Root Directory: frontend
Build Command: npm ci && npm run build
Start Command: npm run start -- -p $PORT
```

### Environment Variables for Frontend

```
# Backend Integration
NEXT_PUBLIC_BACKEND_URL=https://lot-genius.onrender.com
NEXT_PUBLIC_USE_MOCK=0

# Optional API Key (if backend requires it)
NEXT_PUBLIC_API_KEY=your_api_key_if_needed
```

### Deployment Steps

1. **Create New Render Service**:
   - Connect to your GitHub repository
   - Set root directory to `frontend`
   - Configure build/start commands above

2. **Set Environment Variables**:
   - Add all NEXT*PUBLIC* variables listed above
   - Set NEXT_PUBLIC_BACKEND_URL to your backend URL

3. **Deploy & Test**:
   - Deploy the frontend service
   - Note the new frontend URL (e.g., `your-app-frontend.onrender.com`)

4. **Update Backend CORS**:
   - Add frontend URL to backend's CORS_ORIGINS
   - Redeploy backend to apply CORS changes

---

## Validation Testing

### API Health Check (Backend)

```bash
cd lot-genius
python scripts/live_api_check.py
```

**Expected Results**:

- ✅ `GET /healthz` → 200
- ✅ `GET /ebay/health` → 200
- ⚠️ `POST /v1/pipeline/upload` → Currently 500 (needs fix)

### Frontend E2E Testing

#### API-Only Testing (Backend Direct)

```bash
cd frontend
npx playwright test -c playwright.live.config.ts
```

#### UI Testing (Frontend)

```bash
cd frontend
set PLAYWRIGHT_BASE_URL=https://your-frontend-url.onrender.com
npx playwright test -c playwright.live.config.ts
```

---

## Current Issues & Next Steps

### 🔴 Critical: Backend Pipeline Error

- **Issue**: `/v1/pipeline/upload` returning 500 after 111 seconds
- **Impact**: Core functionality broken
- **Action**: Debug backend error logs, check missing dependencies or configuration

### 🟡 Performance Optimization

To achieve <30s response times:

```json
{
  "sims": 1000,
  "roi_target": 1.5,
  "risk_threshold": 0.75
}
```

### 🟢 Architecture Benefits

- **Separation**: Frontend and backend can scale independently
- **Security**: API keys isolated in backend environment
- **Reliability**: Frontend failures don't affect API availability
- **Development**: Teams can work on frontend/backend separately

---

## Expected User Experience

### Backend Root (/)

- Returns 404 - API only, no web interface
- All functionality available via `/v1/*` endpoints

### Frontend UI

- Shows "Direct Backend Mode" toggle
- With NEXT_PUBLIC_BACKEND_URL set, calls backend directly
- Provides file upload → analysis results workflow

### Integration Flow

1. User uploads CSV via frontend UI
2. Frontend POSTs to `backend/v1/pipeline/upload/stream`
3. Backend processes with SSE progress updates
4. Frontend displays results and recommendations

---

## Troubleshooting

### Common Issues

**CORS Errors**:

- Verify CORS_ORIGINS includes exact frontend URL
- Redeploy backend after CORS changes
- Check browser console for specific errors

**API Connection Failures**:

- Verify NEXT_PUBLIC_BACKEND_URL is correct
- Test backend health endpoints directly
- Check network connectivity and firewall rules

**500 Errors**:

- Check Render backend logs for Python tracebacks
- Verify all required environment variables are set
- Test with minimal payload first

### Debug Commands

```bash
# Test backend directly
curl https://lot-genius.onrender.com/healthz

# Test with minimal data
curl -X POST https://lot-genius.onrender.com/v1/pipeline/upload \
  -F "items_csv=@test_single_item.csv" \
  -F "opt_json_inline={\"roi_target\":1.25}"
```

---

## Production Readiness Checklist

### Backend ✅ Mostly Ready

- [x] CORS properly configured
- [x] eBay production credentials integrated
- [x] Health endpoints responding
- [ ] **BLOCKER**: Fix pipeline 500 error
- [x] Error handling and input validation
- [x] Rate limiting and security headers

### Frontend 🔄 Ready for Deployment

- [x] Build configuration verified
- [x] Environment variables defined
- [x] Playwright tests available
- [ ] Deploy to Render
- [ ] Integration testing with backend

### Integration 🔄 Pending Backend Fix

- [ ] End-to-end CSV upload workflow
- [ ] Real-time progress updates (SSE)
- [ ] Error handling and user feedback
- [ ] Performance under load

**Next Action**: Debug and fix the backend pipeline 500 error, then proceed with frontend deployment.
