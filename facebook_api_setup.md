# Meta Graph API Token Setup Guide

## IMPORTANT: Facebook Marketplace Limitations

**Facebook does NOT provide direct API access to Marketplace listings.** Here are the key limitations:

### What Facebook Graph API CAN'T Do:

❌ Search Facebook Marketplace listings
❌ Get sold prices from Marketplace
❌ Access public marketplace data
❌ Scrape marketplace content via API

### What Facebook Graph API CAN Do:

✅ Manage your own business pages
✅ Post to pages you own
✅ Access page insights/analytics
✅ Manage ads and campaigns

## Alternative Approaches for Facebook Marketplace Data

### 1. Third-Party Aggregators (Recommended)

- **Services**: Bright Data, Apify, ScrapingBee
- **Pros**: Legal, reliable, maintained
- **Cons**: Costs money, limited free tiers
- **Best for**: Production use

### 2. Manual Research

- **Process**: Manual price checking on Marketplace
- **Pros**: Free, accurate for specific items
- **Cons**: Time-intensive, not scalable
- **Best for**: High-value items

### 3. Focus on Other Data Sources

- **eBay API**: ✅ Already implemented
- **Amazon (Keepa)**: ✅ Already implemented
- **Other platforms**: Mercari, Poshmark, etc.
- **Best for**: Comprehensive pricing without Facebook

## If You Still Want Meta Graph API Token

### Step 1: Create Facebook App

1. Go to https://developers.facebook.com/
2. Click "Create App"
3. Choose "Business" app type
4. Fill in app details

### Step 2: Get App Credentials

1. Go to App Settings → Basic
2. Copy:
   - **App ID**
   - **App Secret**

### Step 3: Generate Access Token

1. Go to Tools → Graph API Explorer
2. Select your app
3. Generate token with required permissions
4. For business use, you'll need:
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `business_management`

### Step 4: Get Long-Lived Token

```bash
curl -G \
-d "grant_type=fb_exchange_token" \
-d "client_id={app-id}" \
-d "client_secret={app-secret}" \
-d "fb_exchange_token={short-lived-token}" \
https://graph.facebook.com/oauth/access_token
```

## Recommended Implementation Strategy

### Option A: Skip Facebook for Now

Focus on your working data sources:

- ✅ **eBay API** (already implemented)
- ✅ **Keepa/Amazon** (already implemented)
- Add other platforms later

### Option B: Use Third-Party Service

1. Sign up for marketplace data service
2. Get API credentials
3. Implement their API (similar to eBay)

### Option C: Basic Graph API Setup

Even though it won't give marketplace data, here's how to implement it:

```python
# Add to your .env file
FACEBOOK_ACCESS_TOKEN=your_token_here
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret

# Implementation would go in facebook_graph_api.py
import requests

def get_facebook_data(query):
    # This won't work for marketplace, but shows the pattern
    token = os.environ.get('FACEBOOK_ACCESS_TOKEN')
    url = f"https://graph.facebook.com/v18.0/search"
    params = {
        'q': query,
        'type': 'page',  # Can't search marketplace
        'access_token': token
    }
    response = requests.get(url, params=params)
    return response.json()
```

## My Recommendation

**Skip Facebook Marketplace for now.** Your app already has:

- ✅ High-quality eBay sold comps
- ✅ Amazon pricing via Keepa
- ✅ ML-enhanced matching

This gives you excellent pricing data for liquidation decisions. Add Facebook later via a paid service if needed.

Focus on testing your current integration with real liquidation manifests!
