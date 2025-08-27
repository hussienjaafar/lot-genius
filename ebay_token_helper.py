"""
Helper to get a fresh eBay OAuth token for Browse API access.
"""

import requests
import base64
import json

def get_ebay_application_token(client_id: str, client_secret: str, environment: str = "production"):
    """
    Get an application-level OAuth token for eBay Browse API.

    Args:
        client_id: Your eBay App ID
        client_secret: Your eBay Client Secret
        environment: "production" or "sandbox"

    Returns:
        OAuth token string or None if failed
    """

    # eBay OAuth endpoints
    if environment == "production":
        oauth_url = "https://api.ebay.com/identity/v1/oauth2/token"
    else:
        oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

    # Prepare credentials
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'grant_type': 'client_credentials',
        'scope': 'https://api.ebay.com/oauth/api_scope/buy.item.browse'
    }

    try:
        print(f"Requesting new eBay OAuth token from {environment}...")
        response = requests.post(oauth_url, headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 'unknown')

            print(f"✅ SUCCESS: Got new token")
            print(f"   Token: {access_token[:50]}...")
            print(f"   Expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")

            return access_token
        else:
            print(f"❌ Failed to get token: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error getting token: {e}")
        return None


if __name__ == "__main__":
    print("eBay OAuth Token Helper")
    print("=======================")
    print()
    print("To get a new token, you need your eBay App credentials:")
    print("1. Go to: https://developer.ebay.com/my/keys")
    print("2. Find your Application (Keyset)")
    print("3. Copy your App ID and Client Secret")
    print()

    # For security, don't hardcode credentials
    print("Enter your eBay credentials:")
    client_id = input("App ID (Client ID): ").strip()
    client_secret = input("Client Secret: ").strip()

    if client_id and client_secret:
        # Try production first
        token = get_ebay_application_token(client_id, client_secret, "production")

        if not token:
            print("\nTrying sandbox environment...")
            token = get_ebay_application_token(client_id, client_secret, "sandbox")

        if token:
            print("\n" + "="*60)
            print("SUCCESS! Use this token in your app:")
            print("="*60)
            print(f"EBAY_OAUTH_TOKEN={token}")
            print("="*60)
            print("\nAdd this to your environment variables or .env file")
        else:
            print("\n❌ Could not get a valid token")
            print("Check your credentials and try again")
    else:
        print("❌ App ID and Client Secret are required")
