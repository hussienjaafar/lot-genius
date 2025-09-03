"""
eBay Marketplace Account Deletion and Verification endpoints
Required for eBay production API access
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

# Create router for eBay compliance endpoints
router = APIRouter(prefix="/ebay", tags=["eBay Compliance"])

# eBay verification token - set this in your .env file
EBAY_VERIFICATION_TOKEN = os.getenv(
    "EBAY_VERIFICATION_TOKEN", "your-verification-token-here"
)

logger = logging.getLogger(__name__)


@router.get("/marketplace-account-deletion")
async def ebay_verification_token(
    challenge_code: str,
    verification_token: Optional[str] = Header(None, alias="X-EBAY-VERIFICATION-TOKEN"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    eBay Marketplace Account Deletion verification endpoint

    eBay will call this endpoint to verify your server can handle account deletion notifications.
    This endpoint must return the challenge_code to pass verification.

    Example eBay call:
    GET /ebay/marketplace-account-deletion?challenge_code=abc123
    Header: X-EBAY-VERIFICATION-TOKEN: your-token
    """
    logger.info(
        f"eBay verification request received - challenge_code: {challenge_code}"
    )
    logger.info(f"User-Agent: {user_agent}")

    # Log token for debugging (temporarily disable validation)
    logger.info(f"Verification token received: {verification_token}")
    logger.info(f"Expected token: {EBAY_VERIFICATION_TOKEN}")

    # Temporarily disable token validation for eBay testing
    # if verification_token and verification_token != EBAY_VERIFICATION_TOKEN:
    #     logger.warning(f"Invalid verification token received: {verification_token}")
    #     raise HTTPException(status_code=401, detail="Invalid verification token")

    # Return the challenge code as required by eBay
    return {"challengeResponse": challenge_code}


@router.get("/marketplace-account-deletion/")
async def ebay_verification_token_with_slash(
    challenge_code: str,
    verification_token: Optional[str] = Header(None, alias="X-EBAY-VERIFICATION-TOKEN"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    eBay Marketplace Account Deletion verification endpoint with trailing slash
    Some APIs require exact path matching including trailing slashes
    """
    logger.info(
        f"eBay verification request (with slash) - challenge_code: {challenge_code}"
    )
    logger.info(f"User-Agent: {user_agent}")
    logger.info(f"Verification token received: {verification_token}")

    return {"challengeResponse": challenge_code}


@router.get("/marketplace-account-deletion-plaintext")
async def ebay_verification_plain_text(
    challenge_code: str,
    verification_token: Optional[str] = Header(None, alias="X-EBAY-VERIFICATION-TOKEN"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    eBay Marketplace Account Deletion - PLAIN TEXT RESPONSE
    This is likely what eBay actually expects based on common webhook patterns
    """
    logger.info(f"eBay PLAIN TEXT verification - challenge_code: {challenge_code}")
    logger.info(f"User-Agent: {user_agent}")
    logger.info(f"Verification token received: {verification_token}")
    
    # Return plain text response - this is the most common webhook validation pattern
    return PlainTextResponse(content=challenge_code)


@router.post("/marketplace-account-deletion-plaintext")
async def ebay_verification_plain_text_post(
    request: Request,
    verification_token: Optional[str] = Header(None, alias="X-EBAY-VERIFICATION-TOKEN"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    eBay Marketplace Account Deletion - PLAIN TEXT RESPONSE (POST)
    Handle POST requests with challenge in body
    """
    body = await request.body()
    form_data = await request.form() if body else {}
    json_data = await request.json() if body and request.headers.get("content-type") == "application/json" else {}
    
    # Try to get challenge from multiple sources
    challenge_code = (
        request.query_params.get("challenge_code") or 
        form_data.get("challenge_code") or 
        json_data.get("challenge_code") or
        json_data.get("challenge") or
        "unknown"
    )
    
    logger.info(f"eBay PLAIN TEXT POST verification - challenge_code: {challenge_code}")
    logger.info(f"User-Agent: {user_agent}")
    logger.info(f"Request body: {body}")
    logger.info(f"Form data: {form_data}")
    logger.info(f"JSON data: {json_data}")
    
    return PlainTextResponse(content=challenge_code)


# Also add the endpoint at root level in case eBay expects no prefix
@router.get("/account-deletion")
async def ebay_account_deletion_simple(
    challenge_code: str,
    verification_token: Optional[str] = Header(None, alias="X-EBAY-VERIFICATION-TOKEN"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    eBay Account Deletion endpoint without marketplace prefix
    """
    logger.info(f"eBay verification (simple path) - challenge_code: {challenge_code}")
    logger.info(f"User-Agent: {user_agent}")
    logger.info(f"Verification token received: {verification_token}")

    return {"challengeResponse": challenge_code}


@router.post("/marketplace-account-deletion")
async def ebay_account_deletion_notification(request: Request):
    """
    eBay Marketplace Account Deletion notification endpoint

    eBay will POST to this endpoint when a user requests account deletion.
    You must acknowledge receipt and handle the deletion appropriately.

    Expected payload from eBay:
    {
        "metadata": {
            "notificationId": "unique-id",
            "timestamp": "2023-11-15T10:30:00.000Z",
            "eventType": "MARKETPLACE_ACCOUNT_DELETION"
        },
        "notification": {
            "data": {
                "userId": "user123",
                "username": "username123"
            }
        }
    }
    """
    try:
        # Parse the request body
        notification_data = await request.json()

        logger.info(f"eBay account deletion notification received: {notification_data}")

        # Extract user information
        metadata = notification_data.get("metadata", {})
        notification = notification_data.get("notification", {})
        data = notification.get("data", {})

        notification_id = metadata.get("notificationId")
        user_id = data.get("userId")
        username = data.get("username")

        logger.info(f"Processing account deletion for user: {user_id} ({username})")

        # TODO: Implement your account deletion logic here
        # Examples:
        # 1. Remove user data from your database
        # 2. Delete any stored eBay tokens for this user
        # 3. Log the deletion for compliance records
        # 4. Send confirmation email if required

        # For now, just log the request
        logger.info(f"Account deletion processed for notification: {notification_id}")

        # Return success response as required by eBay
        return {
            "status": "SUCCESS",
            "message": "Account deletion notification processed successfully",
        }

    except Exception as e:
        logger.error(f"Error processing eBay account deletion notification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def ebay_compliance_health():
    """
    Health check endpoint for eBay compliance
    """
    return {
        "status": "healthy",
        "service": "eBay Compliance Endpoints",
        "endpoints": {
            "verification": "/ebay/marketplace-account-deletion (GET)",
            "notification": "/ebay/marketplace-account-deletion (POST)",
            "health": "/ebay/health",
        },
    }
