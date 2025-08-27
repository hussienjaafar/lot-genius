import sys
import os
import requests
sys.path.insert(0, 'backend')

# Test eBay OAuth token directly
oauth_token = 'v^1.1#i^1#f^0#p^1#r^0#I^3#t^H4sIAAAAAAAA/+VYe2wURRjv9UUqRSAQoATMuUII4O7t7u29NvTIlV7bE/riamlLkcztzrbb3u0eO7O0R4wpJRYTFRGUYPynGl8R/gBJBR8QHwlGUlMUI/ggEP8wSEDRBAiJoLPbUq6VQKGX2MT9ZzMz3/fN9/2+18ywXfkFS3oqeq5OcUzK7u1iu7IdDm4yW5Cft/TBnOy5eVlsGoGjt2tBV253zrllCCTiSXE1REldQ9DZmYhrSLQniynT0EQdIBWJGkhAJGJJjIYqV4k8w4pJQ8e6pMcpZ6S0mAKSILAQAq+PB4IsCWRWuymzTi+meFYBQPB5gNstCzGWLCNkwoiGMNCwtcx7aNZP8746nhV5n8j6GYEXmihnPTSQqmuEhGGpoK2taPMaaareWVOAEDQwEUIFI6GyaHUoUhquqlvmSpMVHIIhigE20cjRCl2GznoQN+Gdt0E2tRg1JQkiRLmCgzuMFCqGbipzH+rbSMfcMQ4Aye2XAISQlzMCZZluJAC+sx7WjCrTik0qQg2rOHU3RAkasTYo4aFRFRERKXVav1oTxFVFhUYxFS4JNYZqaqhghYmQCrXH6FU6LoeaatLRkgba5+cEN++OBWjJAziv4HUPbTQobQjmUTut0DVZtUBDziodl0CiNRyNDZeGDSGq1qqNkIItjdLp+GEM2SbLqYNeNHGrZvkVJggQTnt4dw8Mc2NsqDETw2EJoxdsiEhWJZOqTI1etGNxKHw6UTHVinFSdLk6OjqYDjejGy0unmU5V0PlqqjUChOAsmitXLfp1bsz0KptigQJJ1JFnEoSXTpJrBIFtBYqKHiEAO8dwn2kWsHRs/+aSLPZNTIjMpUhAagIitsryxznZUnNyUSGBIeC1GXpAWMgRSeA0Q5xMg4kSEskzswENFRZdHsU3u1XIC17AwotBBSFjnlkL80pEJICGYtJAf//KVHGGupRKBkQZybWMxXnVZHaytWRZKu3HpdsqKoNVCTaANTDbWb9Gr2pTFXKy7SyKOzQ+epw8Viz4bbGr4gTb+I6sn9GALByPWMgVOgIQ3lc5kUlPQlr9LgqpSaWg92GXAMMnCoxU2QchfE4+Y3L1FAyGclQxc6YA++tWNyf3RnsVP9Nl7qtVcgK3IlllcWPiACQVBmrD1m5zkh6wqUDcgixptfbWjtHE96OyBUzU0yLCREmmsjkHDhmJpUUc4a0NHnsLIMNkxgxdhZyx5BNCd/XRnZnZgiaaksrRve0Z+d4QImZ8faxs8gQxMcVoiq5akyoACWWDpqsyoN3BMa2m0EbJcaASDcNcj1iqq0jc53eDjVyAMGGHo9Do54bd+lNJEwMYnE40WpwBmqRCnBut+PqxLKL83m8bt4r8P5x2SbZ55/1E62DZLpz3sNNyDXyWSaYZX9ct+MY2+04mu1wsKUszS1lF+fnPJ6bU0ghUnsYBDQ5pncyKlAYUvY0gE0DMu0wlQSqkT0j69vz26ONX688tOvIpg2bmeVHswrSXod617Fzht+HCnK4yWmPRey8Wyt53NTZU3gP6+d95PTvY/1N7CO3VnO5Wbkz5/s/bq897d3s737hrKdyHfvK9GQfO2WYyOHIyyKhnBVdub90vvxHOLfss9lomve5vr4P/nS9s+DKnmvlx3d/OPf8j5VTX3XOOban7+K+5p1Fy/9q7umZcWLRe1eKlrx/etrqwydbdxRt/Knu58uHm1PvdvT3HFvs+ar3tcvfgS+uV/26/cKuT87unHN97bmFlWdObdnS8WLzkRsv73tE9P7efeCgfPL18iwAtrVc2OQX297cHXry7bWfHz+wtPmZSe2Ve7dtLeQfPX7m2o0TDz9dcfFUQfeG/oH+k4XCuf7C/IN7867O+zLvN+6N8C/fdxZ9tGbHU13LFzbO/eHS3z3zDzU0BhSKez5snNo/8MATIVbo7QpsfUlteGjNQP7kt74ZKHp2x8y2RZcOfar49lHTB336D4XBldq3EwAA'

print('=== DIRECT eBay Browse API TEST ===')
print('Testing OAuth token with eBay Browse API...')
print()

# Direct API test
url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
headers = {
    'Authorization': f'Bearer {oauth_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
}

params = {
    'q': 'Apple AirPods Pro',
    'limit': 5
}

try:
    print('Making direct API call to eBay...')
    response = requests.get(url, params=params, headers=headers, timeout=15)

    print(f'Response Status: {response.status_code}')
    print(f'Response Headers: {dict(response.headers)}')

    if response.status_code == 200:
        data = response.json()
        items = data.get('itemSummaries', [])

        if items:
            print(f'SUCCESS: Found {len(items)} current eBay listings')
            print()
            for i, item in enumerate(items[:3], 1):
                title = item.get('title', 'No title')
                price_info = item.get('price', {})
                price = price_info.get('value', 0)
                currency = price_info.get('currency', 'USD')

                print(f'{i}. {currency} {price} - {title}')

                # Check if this is a good match for liquidation
                if 'airpods' in title.lower() and 'pro' in title.lower():
                    print(f'   *** GOOD MATCH for liquidation pricing ***')
                print()

            print('TOKEN WORKS! Your eBay OAuth integration is successful.')
            print('You can now get real eBay pricing data for liquidation analysis.')

        else:
            print('API call successful but no items found')
            print('Response data:', data)
    else:
        print(f'API Error: {response.status_code}')
        print('Response text:', response.text)

        if response.status_code == 403:
            print('Token may need additional permissions or scopes')
        elif response.status_code == 401:
            print('Token may be expired or invalid')

except Exception as e:
    print(f'Request failed: {e}')

print()
print('=== NEXT STEPS ===')
print('If this worked:')
print('1. Set EBAY_OAUTH_TOKEN in your .env file')
print('2. Your app will now get real eBay pricing data!')
print('3. Test with your liquidation manifest')
print()
print('If this failed:')
print('1. Check token scopes in eBay Developer account')
print('2. Ensure token has "Buy API" permissions')
print('3. Token might be expired (they typically last 2 hours)')
