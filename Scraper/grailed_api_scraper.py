import json
import os
import random
import time
import requests
from playwright.sync_api import sync_playwright


AUTH_STATE_FILE = "grailed_auth.json"


def login_and_save_cookies():
    print("Opening browser for login")
    print("Please log in to Grailed manually")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("Navigating to Grailed")

        try:
            page.goto("https://www.grailed.com", timeout=30000)
            print("Page loaded")
            page.wait_for_timeout(2000)
        except Exception:
            print("Page took longer to load but continuing")

        print("Click the login button and use EMAIL/PASSWORD")
        print("Complete the login process then press ENTER")

        input("Press ENTER after you have logged in: ")

        print("Saving authentication")
        page.wait_for_timeout(2000)

        current_url = page.url
        print(f"Current URL: {current_url}")

        cookies = page.context.cookies()
        cookie_names = [c['name'] for c in cookies if 'grailed' in c['name'].lower() or 'jwt' in c['name'].lower()]
        print(f"Grailed cookies found: {cookie_names}")

        if not cookie_names:
            print("Warning: No Grailed cookies detected")
            print("Make sure you are logged in before continuing")
            proceed = input("Continue anyway? (y/n): ")
            if proceed.lower() != 'y':
                browser.close()
                return

        context.storage_state(path=AUTH_STATE_FILE)
        print(f"Authentication saved to {AUTH_STATE_FILE}")

        browser.close()


def get_cookies_dict():
    if not os.path.exists(AUTH_STATE_FILE):
        return None

    with open(AUTH_STATE_FILE, 'r') as f:
        auth_state = json.load(f)

    cookies = {}
    for cookie in auth_state.get('cookies', []):
        cookies[cookie['name']] = cookie['value']

    return cookies


def get_algolia_credentials():
    if not os.path.exists(AUTH_STATE_FILE):
        print("No authentication found. Please login first")
        return None, None

    print("Extracting Algolia credentials from Grailed")

    algolia_key = None
    algolia_app_id = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=AUTH_STATE_FILE)
        page = context.new_page()

        def capture_algolia_credentials(request):
            nonlocal algolia_key, algolia_app_id
            if "algolia.net" in request.url:
                headers = request.headers
                if 'x-algolia-api-key' in headers:
                    algolia_key = headers['x-algolia-api-key']
                if 'x-algolia-application-id' in headers:
                    algolia_app_id = headers['x-algolia-application-id']

        page.on("request", capture_algolia_credentials)

        try:
            page.goto("https://www.grailed.com/sold?query=test", wait_until="domcontentloaded", timeout=15000)

            for _ in range(10):
                if algolia_key and algolia_app_id:
                    break
                page.wait_for_timeout(500)
        except Exception:
            pass
        finally:
            browser.close()

    if algolia_key and algolia_app_id:
        print("Algolia credentials extracted successfully")
    else:
        print("Could not extract Algolia credentials automatically")
        print("Manual option: Open https://www.grailed.com/sold in your browser")
        print("Open DevTools Network tab and find request to algolia.net")
        print("Copy the x-algolia-api-key and x-algolia-application-id header values")
        manual_key = input("Paste Algolia API key here or press Enter to skip: ").strip()
        manual_app_id = input("Paste Algolia App ID here or press Enter to skip: ").strip()
        if manual_key:
            algolia_key = manual_key
        if manual_app_id:
            algolia_app_id = manual_app_id

    return algolia_key, algolia_app_id


def scrape_sold_listings_api(query, max_results=200, min_delay=2.0, max_delay=5.0):
    algolia_key, algolia_app_id = get_algolia_credentials()

    if not algolia_key or not algolia_app_id:
        print("Failed to get Algolia credentials. Cannot continue")
        return []

    print(f"Scraping sold listings for {query}")
    print(f"Delay between pages: {min_delay}-{max_delay}s")

    url = "https://mnrwefss2q-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)%3B%20Browser%3B%20instantsearch.js%20(4.75.5)%3B%20react%20(18.2.0)%3B%20react-instantsearch%20(7.13.8)%3B%20react-instantsearch-core%20(7.13.8)%3B%20next.js%20(14.2.33)%3B%20JS%20Helper%20(3.22.5)"

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8,th;q=0.7',
        'Connection': 'keep-alive',
        'Origin': 'https://www.grailed.com',
        'Referer': 'https://www.grailed.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded',
        'dnt': '1',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-gpc': '1',
        'x-algolia-api-key': algolia_key,
        'x-algolia-application-id': algolia_app_id,
    }

    all_listings = []
    page = 0
    consecutive_errors = 0

    while len(all_listings) < max_results:
        payload = {
            "requests": [
                {
                    "indexName": "Listing_sold_production",
                    "params": f"analytics=true&clickAnalytics=true&enableABTest=true&facets=%5B%22badges%22%2C%22category_path%22%2C%22category_size%22%2C%22condition%22%2C%22department%22%2C%22designers.name%22%2C%22location%22%2C%22sold_price%22%2C%22strata%22%5D&getRankingInfo=true&highlightPostTag=__%2Fais-highlight__&highlightPreTag=__ais-highlight__&hitsPerPage=40&maxValuesPerFacet=165&numericFilters=%5B%22sold_price%3E%3D0%22%2C%22sold_price%3C%3D1000000%22%5D&page={page}&query={query.replace(' ', '%20')}"
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                consecutive_errors = 0

                if 'results' in data and len(data['results']) > 0:
                    hits = data['results'][0].get('hits', [])

                    if not hits:
                        print("No more results found")
                        break

                    all_listings.extend(hits)
                    print(f"Page {page + 1}: Retrieved {len(hits)} listings Total {len(all_listings)}")

                    page += 1
                else:
                    break

            elif response.status_code == 429:
                consecutive_errors += 1
                backoff = min(60, (2 ** consecutive_errors) + random.uniform(0, 1))
                print(f"Rate limited. Backing off for {backoff:.1f}s")
                time.sleep(backoff)
                continue

            else:
                print(f"Error HTTP {response.status_code}")
                print(response.text)
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    print("Too many consecutive errors. Stopping")
                    break
                time.sleep(10)
                continue

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print("Too many consecutive errors. Stopping")
                break
            time.sleep(10)
            continue

        # Random delay between requests to mimic human browsing
        if len(all_listings) < max_results:
            delay = random.uniform(min_delay, max_delay)
            # Gradually increase delay every 10 pages to be safer
            if page > 0 and page % 10 == 0:
                delay += random.uniform(2.0, 5.0)
                print(f"Extended pause after {page} pages: {delay:.1f}s")
            else:
                print(f"Waiting {delay:.1f}s")
            time.sleep(delay)

    print(f"Total listings scraped {len(all_listings)}")
    return all_listings


def extract_listing_details(listing):
    user = listing.get("user", {})
    cover_photo = listing.get("cover_photo", {})
    shipping = listing.get("shipping", {})

    return {
        # Basic info
        "id": listing.get("id"),
        "objectID": listing.get("objectID"),
        "title": listing.get("title"),
        "designer_names": listing.get("designer_names"),
        "designers": listing.get("designers", []),

        # Pricing
        "price": listing.get("price"),
        "sold_price": listing.get("sold_price"),
        "sold_price_includes_shipping": listing.get("sold_price_includes_shipping"),
        "sold_shipping_price": listing.get("sold_shipping_price"),
        "price_drops": listing.get("price_drops", []),

        # Dates
        "created_at": listing.get("created_at"),
        "sold_at": listing.get("sold_at"),
        "bumped_at": listing.get("bumped_at"),
        "price_updated_at": listing.get("price_updated_at"),

        # Item details
        "size": listing.get("size"),
        "category": listing.get("category"),
        "category_path": listing.get("category_path"),
        "category_size": listing.get("category_size"),
        "condition": listing.get("condition"),
        "color": listing.get("color"),
        "department": listing.get("department"),
        "location": listing.get("location"),
        "traits": listing.get("traits", []),
        "styles": listing.get("styles", []),
        "badges": listing.get("badges", []),

        # Photos
        "cover_photo_url": cover_photo.get("url") if cover_photo else None,
        "photo_count": listing.get("photo_count"),
        "measurement_count": listing.get("measurement_count"),

        # Seller info
        "seller_id": user.get("id") if user else None,
        "seller_username": user.get("username") if user else None,
        "seller_rating": user.get("seller_score", {}).get("rating_average") if user else None,
        "seller_rating_count": user.get("seller_score", {}).get("rating_count") if user else None,
        "seller_trusted": user.get("trusted_seller") if user else None,
        "seller_total_bought_sold": user.get("total_bought_and_sold") if user else None,

        # Shipping
        "shipping": shipping,

        # Marketplace info
        "marketplace": listing.get("marketplace"),
        "strata": listing.get("strata"),
        "buynow": listing.get("buynow"),
        "makeoffer": listing.get("makeoffer"),
        "dropped": listing.get("dropped"),

        # URL
        "listing_url": f"https://grailed.com/listings/{listing.get('id')}" if listing.get('id') else None,
    }


def main():
    import sys

    OUTPUT_FILE = "sold_listings.jsonl"

    print("Grailed Sold Listings API Scraper")

    if len(sys.argv) > 1 and sys.argv[1] == "login":
        login_and_save_cookies()
        return

    if not os.path.exists(AUTH_STATE_FILE):
        print("No authentication found. Running login")
        login_and_save_cookies()

    query = sys.argv[1] if len(sys.argv) > 1 else ""
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    listings = scrape_sold_listings_api(query, max_results=max_results)

    if listings:
        print(f"Saving {len(listings)} listings to {OUTPUT_FILE}")

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for i, listing in enumerate(listings, 1):
                details = extract_listing_details(listing)
                f.write(json.dumps(details, ensure_ascii=False) + "\n")

                if i % 10 == 0:
                    print(f"Processed {i}/{len(listings)} listings")

        print(f"Saved {len(listings)} listings to {OUTPUT_FILE}")

        if listings:
            print("SAMPLE LISTINGS")
            for i in range(min(3, len(listings))):
                sample = extract_listing_details(listings[i])
                print(f"{i+1} {sample['title']}")
                print(f"Designer {sample['designer_names']}")
                print(f"Sold Price {sample['sold_price']}")
                print(f"Original Price {sample['price']}")
                print(f"Size {sample['size']}")
                print(f"Condition {sample['condition']}")
                print(f"Seller {sample['seller_username']} Rating {sample['seller_rating']}")
                print(f"URL {sample['listing_url']}")
    else:
        print("No listings found")


if __name__ == "__main__":
    main()
    