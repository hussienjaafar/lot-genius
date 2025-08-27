import requests
import base64

# Your token
token = 'v^1.1#i^1#f^0#p^1#r^0#I^3#t^H4sIAAAAAAAA/+VYe2wURRjv9UUqRSAQoATMuUII4O7t7u29NvTIlV7bE/riamlLkcztzrbb3u0eO7O0R4wpJRYTFRGUYPynGl8R/gBJBR8QHwlGUlMUI/ggEP8wSEDRBAiJoLPbUq6VQKGX2MT9ZzMz3/fN9/2+18ywXfkFS3oqeq5OcUzK7u1iu7IdDm4yW5Cft/TBnOy5eVlsGoGjt2tBV253zrllCCTiSXE1REldQ9DZmYhrSLQniynT0EQdIBWJGkhAJGJJjIYqV4k8w4pJQ8e6pMcpZ6S0mAKSILAQAq+PB4IsCWRWuymzTi+meFYBQPB5gNstCzGWLCNkwoiGMNCwtcx7aNZP8746nhV5n8j6GYEXmihnPTSQqmuEhGGpoK2taPMaaareWVOAEDQwEUIFI6GyaHUoUhquqlvmSpMVHIIhigE20cjRCl2GznoQN+Gdt0E2tRg1JQkiRLmCgzuMFCqGbipzH+rbSMfcMQ4Aye2XAISQlzMCZZluJAC+sx7WjCrTik0qQg2rOHU3RAkasTYo4aFRFRERKXVav1oTxFVFhUYxFS4JNYZqaqhghYmQCrXH6FU6LoeaatLRkgba5+cEN++OBWjJAziv4HUPbTQobQjmUTut0DVZtUBDziodl0CiNRyNDZeGDSGq1qqNkIItjdLp+GEM2SbLqYNeNHGrZvkVJggQTnt4dw8Mc2NsqDETw2EJoxdsiEhWJZOqTI1etGNxKHw6UTHVinFSdLk6OjqYDjejGy0unmU5V0PlqqjUChOAsmitXLfp1bsz0KptigQJJ1JFnEoSXTpJrBIFtBYqKHiEAO8dwn2kWsHRs/+aSLPZNTIjMpUhAagIitsryxznZUnNyUSGBIeC1GXpAWMgRSeA0Q5xMg4kSEskzswENFRZdHsU3u1XIC17AwotBBSFjnlkL80pEJICGYtJAf//KVHGGupRKBkQZybWMxXnVZHaytWRZKu3HpdsqKoNVCTaANTDbWb9Gr2pTFXKy7SyKOzQ+epw8Viz4bbGr4gTb+I6sn9GALByPWMgVOgIQ3lc5kUlPQlr9LgqpSaWg92GXAMMnCoxU2QchfE4+Y3L1FAyGclQxc6YA++tWNyf3RnsVP9Nl7qtVcgK3IlllcWPiACQVBmrD1m5zkh6wqUDcgixptfbWjtHE96OyBUzU0yLCREmmsjkHDhmJpUUc4a0NHnsLIMNkxgxdhZyx5BNCd/XRnZnZgiaaksrRve0Z+d4QImZ8faxs8gQxMcVoiq5akyoACWWDpqsyoN3BMa2m0EbJcaASDcNcj1iqq0jc53eDjVyAMGGHo9Do54bd+lNJEwMYnE40WpwBmqRCnBut+PqxLKL83m8bt4r8P5x2SbZ55/1E62DZLpz3sNNyDXyWSaYZX9ct+MY2+04mu1wsKUszS1lF+fnPJ6bU0ghUnsYBDQ5pncyKlAYUvY0gE0DMu0wlQSqkT0j69vz26ONX688tOvIpg2bmeVHswrSXod617Fzht+HCnK4yWmPRey8Wyt53NTZU3gP6+d95PTvY/1N7CO3VnO5Wbkz5/s/bq897d3s737hrKdyHfvK9GQfO2WYyOHIyyKhnBVdub90vvxHOLfss9lomve5vr4P/nS9s+DKnmvlx3d/OPf8j5VTX3XOOban7+K+5p1Fy/9q7umZcWLRe1eKlrx/etrqwydbdxRt/Knu58uHm1PvdvT3HFvs+ar3tcvfgS+uV/26/cKuT87unHN97bmFlWdObdnS8WLzkRsv73tE9P7efeCgfPL18iwAtrVc2OQX297cHXry7bWfHz+wtPmZSe2Ve7dtLeQfPX7m2o0TDz9dcfFUQfeG/oH+k4XCuf7C/IN7867O+zLvN+6N8C/fdxZ9tGbHU13LFzbO/eHS3z3zDzU0BhSKez5snNo/8MATIVbo7QpsfUlteGjNQP7kt74ZKHp2x8y2RZcOfar49lHTB336D4XBldq3EwAA'

print("Token format analysis:")
print(f"Length: {len(token)}")
print(f"Starts with: {token[:20]}...")
print(f"Contains special chars: {'#' in token}, {'%' in token}")

# Decode the token to see its structure
try:
    # eBay tokens are typically URL-encoded base64
    import urllib.parse
    decoded_token = urllib.parse.unquote(token)
    print(f"URL decoded: {decoded_token[:50]}...")

    # Try to see if it's compressed (gzip)
    import gzip
    import io

    # Look for gzip header in the base64 part
    parts = decoded_token.split('#')
    for i, part in enumerate(parts):
        print(f"Part {i}: {part}")

except Exception as e:
    print(f"Decode error: {e}")

print()
print("Let's try a simple test with minimal API call:")

headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/json',
    'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
}

# Try the search endpoint first
try:
    response = requests.get(
        'https://api.ebay.com/buy/browse/v1/item_summary/search',
        params={'q': 'test', 'limit': 1},
        headers=headers,
        timeout=10
    )
    print(f"Search API Status: {response.status_code}")
    print(f"Search Response: {response.text[:200]}...")
except Exception as e:
    print(f"Search API Error: {e}")

print()
print("=== POSSIBLE ISSUES ===")
print("1. Token might be a User Token (needs user consent) vs Application Token")
print("2. Token might not have Browse API scope")
print("3. Token might be for sandbox environment")
print("4. Token format might need URL encoding/decoding")
print()
print("=== NEXT STEPS ===")
print("1. Double-check you copied the 'Application Token' not 'User Token'")
print("2. Verify the scope includes 'https://api.ebay.com/oauth/api_scope/buy.item.browse'")
print("3. Check if token was generated for sandbox vs production")
