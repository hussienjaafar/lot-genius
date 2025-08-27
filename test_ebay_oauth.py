import sys
import os
sys.path.insert(0, 'backend')

# Set your eBay OAuth token
os.environ['EBAY_OAUTH_TOKEN'] = 'v^1.1#i^1#I^3#r^0#f^0#p^1#t^H4sIAAAAAAAA/+VYbWwURRi+67WQWsAYvlSMXlb5IWT3Zj97t3KH1y962s+7ctJSwb3d2Xbbvd1lZ5b2UGNtCDEG0GDiBz8IJCooMRqIEUwkSggSNWIVI4EYI/4BjKZotBGicfdayrUSQHqJTdw/m5l5553ned73nZldMDCjfMmm+k0js/0zS3YOgIESv5+uAOUzypbOCZTcWeYDBQb+nQP3DZQOBs4uQ1JWt8QkRJZpIBjsz+oGEvOdUcKxDdGUkIZEQ8pCJGJZTMUbG0SGAqJlm9iUTZ0IJmqiBMuH1TCnVMqZTESQIoLba1z22WZGCQFIPB+WeRVIApDpsDuOkAMTBsKSgaMEAxieBGGSqWxjgMgKIsdSDBPpIIJpaCPNNFwTChCxPFwxP9cuwHptqBJC0MauEyKWiNelmuOJmtqmtmWhAl+xMR1SWMIOmtiqNhUYTEu6A6+9DMpbiylHliFCRCg2usJEp2L8MpibgJ+XWgjzMqeoCpfhXE1luihS1pl2VsLXxuH1aAqp5k1FaGAN566nqKtGpgfKeKzV5LpI1AS9V6sj6ZqqQTtK1FbF2+MtLUSs3kFIg8ZDZIOJV0BDc8hU1SqyMkxzLMNmIqTMS7TACezYQqPexmSetFK1aSiaJxoKNpm4Crqo4WRtmAJtXKNmo9mOq9hDVGjHjGvIdnhBHY2ig7sNL64w6woRzDevH4Hx2RjbWsbBcNzD5IG8RFFCsixNISYP5nNxLH36UZToxtgSQ6G+vj6qj6VMuyvEAECHVjU2pORumJUI19ar9VF77foTSC1PRYbuTKSJOGe5WPrdXHUBGF1EjOO5CCOM6T4RVmxy7z86CjiHJlZEsSqEgxzN8QDSAgSMxHDFqJDYWJKGPBwwI+XIrGT3QmzpkgxJ2c0zJwttTRFZXmXYsApJRYioJBdRVTLDKwJJqxACCDMZORL+PxXKjaZ6Cso2xEXJ9aLleVOitTGZsLqFNK5a19Qaqc/2SNCs7XHSj5gddZq6os6oS8E+k2mujd5oNVyVfLXuRhO3uesXQwCv1osnQr2JMFSmRC8lmxZsMXVNzk2vALO20iLZOFfl5Nx2Cuq6+5oS1bhlJYqzYxcvgP9us7g53sU7qf6jU+qqrJCXuNOLlTcfuQ4kS6Pcc8ir9Rwlm9mQKbmXEK97bR71lHhr7v11WrF2CXpsc5SmjF48qTxdCq2XKRsi07HdOzfV7N3D2sxeaLinGrZNXYd2mp5yPWezDpYyOpxuhV2EBNekaXbk0pW8wDKVAExtO5LzB+ra6bYlTW0rLm2c0uU6NPFTP+bLP/Sg/xMw6D9a4veDGkDSS8H9MwIrSwOzCKRhSCHJUDJmP6VJKoW0LsP9krUh1QtzlqTZJXN9J84/n2ofevjAi4c2rHuaWn7UV17wx2Hno+D28X8O5QG6ouAHBLjrykgZfevC2QwPwkwlA1iBYzvAvVdGS+kFpfPaf+zoOFt3ETZsCl04GQu8tR+U/QZmjxv5/WW+0kG/r/OW6tCexUvvuBva7Kk9TziL6radPnjpwvyv1uw/nx7aGNhcgrcsXr3j4K6WoXdfW1Tz7IbP52qJc87Jc00Hnuud84vy86Xu5NwT+/gz3xCPlfXvCM4D6u4v33ivfU5ZvPNI4PuhuLx9wshtRG9my9FnVr1zPLPxI+GPM/P+PPP6ofO5+Z/VPp4MfVrx1OqKLcFk6P0ftl5o6Rzmf//w2301D+4e3nX88KxWGDjdm9j1SnjzkZOvNi5ZGczqycPD1WvSF0dyL1FpZebC1LZjDQ8M7133RX8kmYinnvR9p6/Y3rvddyq1tyr6l36Me+HNrs0fnP4pbn28nB7pjPQ0L/r613tehvve7tkza3D9aEz/Bij+/hYLEgAA'

from lotgenius.datasources.ebay_api import fetch_ebay_sold_comps_api

print('=== TESTING eBay OAuth TOKEN ===')
print('Testing with Apple AirPods Pro...')
print()

try:
    results = fetch_ebay_sold_comps_api(
        query="Apple AirPods Pro 2nd Generation",
        brand="Apple",
        model="AirPods Pro",
        max_results=5,
        days_lookback=60
    )

    if results:
        print(f'✅ SUCCESS: Found {len(results)} eBay comparables')
        print()
        for i, comp in enumerate(results[:3], 1):
            print(f'{i}. ${comp.price:.2f} - {comp.title[:60]}...')
            print(f'   Match Score: {comp.match_score:.2f} | Source: {comp.source}')
            print(f'   URL: {comp.url}')
            print()
    else:
        print('❌ No results found. Possible issues:')
        print('- Token may not have correct permissions')
        print('- Rate limiting')
        print('- Search terms too specific')
        print('- Need to try current listings instead of sold listings')

    # Let's also test the OAuth Browse API for current listings
    print()
    print('=== TESTING CURRENT LISTINGS (OAuth Browse API) ===')

    from lotgenius.datasources.ebay_api import EbayAPIClient
    client = EbayAPIClient(oauth_token=os.environ['EBAY_OAUTH_TOKEN'])

    current_items = client.search_items_oauth(
        query="Apple AirPods Pro",
        max_results=5
    )

    if current_items:
        print(f'✅ Found {len(current_items)} current eBay listings')
        for item in current_items[:3]:
            title = item.get('title', 'No title')
            price = item.get('price', {}).get('value', 0)
            print(f'${price:.2f} - {title[:60]}...')
    else:
        print('❌ No current listings found')

except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()

print()
print('=== NEXT STEPS ===')
print('If this works:')
print('1. Set EBAY_OAUTH_TOKEN in your environment permanently')
print('2. Test with your liquidation manifest')
print('3. Monitor API usage limits')
print()
print('If this fails:')
print('1. Check token permissions in eBay Developer account')
print('2. Verify token is not expired')
print('3. Try with simpler search terms')
