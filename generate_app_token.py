import requests
import base64

# Your eBay credentials
# You provided: SBX-814323b9fb72-5316-4a47-91a6-2e2a (this is your Client Secret/Cert ID)
# You need to also provide your App ID (Client ID)

print("=== Generate eBay Application Token ===")
print()
print("You provided your Cert ID: SBX-814323b9fb72-5316-4a47-91a6-2e2a")
print("This looks like a SANDBOX Cert ID (starts with SBX-)")
print()
print("To generate a token, I also need your App ID (Client ID)")
print("Both should be available at: https://developer.ebay.com/my/keys")
print()

# For now, let's try with placeholder - user needs to provide App ID
app_id = input("Enter your eBay App ID (Client ID): ").strip()
cert_id = "SBX-814323b9fb72-5316-4a47-91a6-2e2a"  # User provided this

if not app_id:
    print("App ID is required. Please check https://developer.ebay.com/my/keys")
    exit(1)

print(f"Using App ID: {app_id}")
print(f"Using Cert ID: {cert_id}")
print()

# Determine environment based on Cert ID
if cert_id.startswith("SBX-"):
    oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    print("Using SANDBOX environment (based on SBX- prefix)")
else:
    oauth_url = "https://api.ebay.com/identity/v1/oauth2/token"
    print("Using PRODUCTION environment")

# Generate OAuth token using client credentials flow
credentials = f"{app_id}:{cert_id}"
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
    print("Requesting OAuth token...")
    response = requests.post(oauth_url, headers=headers, data=data, timeout=15)

    print(f"Response Status: {response.status_code}")

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 'unknown')
        token_type = token_data.get('token_type', 'Bearer')

        print("SUCCESS! Generated Application Token:")
        print("=" * 60)
        print(f"Token: {access_token}")
        print(f"Type: {token_type}")
        print(f"Expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")
        print("=" * 60)

        # Verify it's an Application Token by checking the structure
        if access_token and 'p^3' in access_token:
            print("✓ This is an Application Token (p^3) - CORRECT for Browse API")
        elif access_token and 'p^1' in access_token:
            print("⚠ This is a User Token (p^1) - may not work for Browse API")
        else:
            print("? Token type unknown from structure")

        print()
        print("NEXT STEPS:")
        print("1. Copy this token")
        print("2. Set it as EBAY_OAUTH_TOKEN in your .env file")
        print("3. Test with your liquidation app")

    else:
        print(f"FAILED: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 401:
            print()
            print("ERROR: Invalid credentials")
            print("- Check your App ID and Cert ID at https://developer.ebay.com/my/keys")
            print("- Make sure they're from the same keyset")
        elif response.status_code == 400:
            print()
            print("ERROR: Bad request")
            print("- Check the scope is correct")
            print("- Verify your app has Browse API permissions")

except Exception as e:
    print(f"Request failed: {e}")
    print()
    print("TROUBLESHOOTING:")
    print("1. Check your internet connection")
    print("2. Verify credentials are correct")
    print("3. Try again in a few minutes")
