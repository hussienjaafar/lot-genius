"""
eBay Marketplace Account Deletion - COMPREHENSIVE DEBUG VERSION
This will capture everything eBay sends and try all possible variations
"""

import hashlib
import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

# Create router for eBay compliance endpoints
router = APIRouter(prefix="/ebay", tags=["eBay Compliance Debug"])

# eBay verification token
EBAY_VERIFICATION_TOKEN = os.getenv(
    "EBAY_VERIFICATION_TOKEN", "your-verification-token-here"
)

logger = logging.getLogger(__name__)


@router.get("/debug-marketplace-account-deletion")
@router.post("/debug-marketplace-account-deletion")
async def ebay_verification_debug_comprehensive(request: Request):
    """
    eBay Marketplace Account Deletion - ULTRA DEBUG VERSION
    Captures everything eBay sends and tries all possible hash combinations
    """
    
    # === CAPTURE EVERYTHING ===
    method = request.method
    url = str(request.url)
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    logger.info(f"🔍 === eBay REQUEST DEBUG ===")
    logger.info(f"Method: {method}")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Query Params: {query_params}")
    
    # Get request body for POST requests
    body_str = ""
    form_data = {}
    json_data = {}
    
    if method == "POST":
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode('utf-8') if body_bytes else ""
            logger.info(f"Body: {body_str}")
            
            # Reset request for form/json parsing
            request._body = body_bytes
            
            if "application/json" in headers.get("content-type", "").lower():
                try:
                    import json
                    json_data = json.loads(body_str) if body_str else {}
                    logger.info(f"JSON Data: {json_data}")
                except:
                    logger.info("Failed to parse JSON")
            else:
                try:
                    # Parse form data manually
                    if body_str:
                        for pair in body_str.split('&'):
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                form_data[key] = value
                    logger.info(f"Form Data: {form_data}")
                except:
                    logger.info("Failed to parse form data")
        except Exception as e:
            logger.info(f"Error reading POST body: {e}")
    
    # === FIND CHALLENGE CODE FROM ALL SOURCES ===
    challenge_code = None
    challenge_sources = [
        ("query_challenge_code", query_params.get("challenge_code")),
        ("query_challengeCode", query_params.get("challengeCode")), 
        ("query_challenge", query_params.get("challenge")),
        ("query_code", query_params.get("code")),
        ("form_challenge_code", form_data.get("challenge_code")),
        ("form_challengeCode", form_data.get("challengeCode")),
        ("json_challenge_code", json_data.get("challenge_code") if isinstance(json_data, dict) else None),
        ("json_challengeCode", json_data.get("challengeCode") if isinstance(json_data, dict) else None),
    ]
    
    logger.info(f"🔍 Searching for challenge code in:")
    for source_name, value in challenge_sources:
        logger.info(f"  - {source_name}: {value}")
        if value and not challenge_code:
            challenge_code = str(value)
            logger.info(f"✅ Found challenge_code from {source_name}: {challenge_code}")
    
    if not challenge_code:
        logger.error("❌ NO CHALLENGE CODE FOUND IN ANY SOURCE!")
        return {
            "error": "No challenge code found", 
            "sources_checked": [s[0] for s in challenge_sources],
            "debug_request": {
                "method": method,
                "url": url,
                "query_params": query_params,
                "form_data": form_data,
                "json_data": json_data,
                "body": body_str
            }
        }
    
    # === GET VERIFICATION TOKEN ===
    verification_token = (
        headers.get("x-ebay-verification-token") or 
        headers.get("X-EBAY-VERIFICATION-TOKEN") or
        headers.get("x-ebay-verification-token".upper()) or
        EBAY_VERIFICATION_TOKEN
    )
    
    logger.info(f"🔑 Verification token sources:")
    logger.info(f"  - Header x-ebay-verification-token: {headers.get('x-ebay-verification-token')}")
    logger.info(f"  - Header X-EBAY-VERIFICATION-TOKEN: {headers.get('X-EBAY-VERIFICATION-TOKEN')}")
    logger.info(f"  - Environment EBAY_VERIFICATION_TOKEN: {EBAY_VERIFICATION_TOKEN}")
    logger.info(f"  - Using: {verification_token}")
    
    # === TRY ALL URL FORMAT VARIATIONS ===
    base_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
    
    url_variations = [
        ("base_url", base_url),
        ("base_url_with_slash", base_url.rstrip('/') + '/'),
        ("base_url_no_slash", base_url.rstrip('/')),
        ("full_url_as_sent", str(request.url)),
        ("url_without_query", f"{request.url.scheme}://{request.url.netloc}{request.url.path}"),
        ("url_configured_endpoint", f"{request.url.scheme}://{request.url.netloc}/ebay/marketplace-account-deletion"),
    ]
    
    logger.info(f"🌐 Testing URL variations:")
    hash_results = {}
    
    for url_name, endpoint_url in url_variations:
        # Create hash: challenge_code + verification_token + endpoint_url
        hash_obj = hashlib.sha256()
        hash_obj.update(challenge_code.encode('utf-8'))
        hash_obj.update(verification_token.encode('utf-8'))
        hash_obj.update(endpoint_url.encode('utf-8'))
        hash_result = hash_obj.hexdigest()
        
        hash_results[url_name] = {
            "url": endpoint_url,
            "hash": hash_result
        }
        
        logger.info(f"  {url_name}:")
        logger.info(f"    URL: {endpoint_url}")  
        logger.info(f"    Hash: {hash_result}")
    
    # Use the most likely correct hash (base_url without slash)
    primary_hash = hash_results["base_url_no_slash"]["hash"]
    
    logger.info(f"🎯 PRIMARY RESPONSE:")
    logger.info(f"Challenge Response: {primary_hash}")
    
    # Return the response eBay expects
    response = {
        "challengeResponse": primary_hash
    }
    
    # Add debug info for our reference (eBay will ignore this)
    if "debug" in query_params:
        response["debug_info"] = {
            "method": method,
            "challenge_code_found": challenge_code,
            "verification_token_used": verification_token,
            "all_hash_variations": hash_results,
            "headers_received": headers,
            "query_params": query_params,
            "form_data": form_data,
            "json_data": json_data
        }
    
    return response


# Simple connectivity test endpoint
@router.get("/test")
async def simple_test():
    """Simple test to verify eBay can reach our server"""
    logger.info("🧪 Simple test endpoint called")
    return {"status": "reachable", "message": "eBay can reach this endpoint"}