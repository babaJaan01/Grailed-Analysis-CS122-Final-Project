import json
import os
import random
import sys
import time
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright


SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_STATE_FILE = os.path.join(SCRAPER_DIR, "grailed_auth.json")
ALGOLIA_CREDS_FILE = os.path.join(SCRAPER_DIR, "algolia_creds.json")
QUERIES_FILE = os.path.join(SCRAPER_DIR, "queries.txt")
OUTPUT_FILE = os.path.join(SCRAPER_DIR, "sold_listings.jsonl")
SEEN_IDS_FILE = os.path.join(SCRAPER_DIR, "seen_ids.txt")
LOG_FILE = os.path.join(SCRAPER_DIR, "scraper.log")

ALGOLIA_URL = (
    "https://mnrwefss2q-dsn.algolia.net/1/indexes/*/queries"
    "?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)%3B%20Browser"
    "%3B%20instantsearch.js%20(4.75.5)%3B%20react%20(18.2.0)"
    "%3B%20react-instantsearch%20(7.13.8)%3B%20react-instantsearch-core%20(7.13.8)"
    "%3B%20next.js%20(14.2.33)%3B%20JS%20Helper%20(3.22.5)"
)

DEFAULT_HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Origin': 'https://www.grailed.com',
    'Referer': 'https://www.grailed.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


def log(msg):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except OSError:
        pass


# --------------------------- auth + credentials ---------------------------

def login_and_save_cookies():
    log("Opening browser for login. Please log in to Grailed manually.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        try:
            page.goto("https://www.grailed.com", timeout=30000)
            page.wait_for_timeout(2000)
        except Exception:
            log("Page took longer to load but continuing.")
        input("Press ENTER after you have logged in: ")
        page.wait_for_timeout(2000)
        context.storage_state(path=AUTH_STATE_FILE)
        log(f"Authentication saved to {AUTH_STATE_FILE}")
        browser.close()


def extract_algolia_credentials():
    if not os.path.exists(AUTH_STATE_FILE):
        log("No authentication found. Run with 'login' first.")
        return None, None

    log("Extracting Algolia credentials via Playwright (browser will open briefly)...")
    algolia_key = None
    algolia_app_id = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=AUTH_STATE_FILE,
                                      viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        def capture(request):
            nonlocal algolia_key, algolia_app_id
            if "algolia.net" in request.url:
                h = request.headers
                if 'x-algolia-api-key' in h:
                    algolia_key = h['x-algolia-api-key']
                if 'x-algolia-application-id' in h:
                    algolia_app_id = h['x-algolia-application-id']

        page.on("request", capture)

        urls_to_try = [
            "https://www.grailed.com/sold?query=test",
            "https://www.grailed.com/sold",
            "https://www.grailed.com/",
        ]
        try:
            for url in urls_to_try:
                if algolia_key and algolia_app_id:
                    break
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    log(f"  goto {url} failed: {e}")
                    continue
                # Poll up to 15s per URL for an algolia request to fire
                for _ in range(30):
                    if algolia_key and algolia_app_id:
                        break
                    page.wait_for_timeout(500)
        finally:
            browser.close()

    if not (algolia_key and algolia_app_id):
        log("Automatic extraction failed.")
        log("Manual fallback: open https://www.grailed.com/sold in your browser,")
        log("open DevTools → Network, filter for 'algolia.net', click any request,")
        log("and copy the x-algolia-api-key and x-algolia-application-id headers.")
        try:
            manual_key = input("Paste x-algolia-api-key (or Enter to abort): ").strip()
            manual_app = input("Paste x-algolia-application-id (or Enter to abort): ").strip()
            if manual_key and manual_app:
                algolia_key, algolia_app_id = manual_key, manual_app
        except EOFError:
            pass

    return algolia_key, algolia_app_id


def load_cached_credentials():
    if not os.path.exists(ALGOLIA_CREDS_FILE):
        return None, None
    try:
        with open(ALGOLIA_CREDS_FILE, 'r') as f:
            data = json.load(f)
        return data.get('api_key'), data.get('app_id')
    except (OSError, json.JSONDecodeError):
        return None, None


def save_cached_credentials(api_key, app_id):
    tmp = ALGOLIA_CREDS_FILE + ".tmp"
    with open(tmp, 'w') as f:
        json.dump({'api_key': api_key, 'app_id': app_id,
                   'cached_at': datetime.now().isoformat()}, f)
    os.replace(tmp, ALGOLIA_CREDS_FILE)


def get_algolia_credentials(force_refresh=False):
    if not force_refresh:
        key, app_id = load_cached_credentials()
        if key and app_id:
            return key, app_id
    key, app_id = extract_algolia_credentials()
    if key and app_id:
        save_cached_credentials(key, app_id)
        log("Algolia credentials cached.")
    return key, app_id


# --------------------------- dedup index ---------------------------

def load_seen_ids():
    if not os.path.exists(SEEN_IDS_FILE):
        return set()
    seen = set()
    with open(SEEN_IDS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                seen.add(line)
    return seen


def append_seen_id(handle, listing_id):
    handle.write(f"{listing_id}\n")


# --------------------------- listing extraction ---------------------------

def extract_listing_details(listing):
    user = listing.get("user", {}) or {}
    cover_photo = listing.get("cover_photo", {}) or {}
    shipping = listing.get("shipping", {})
    seller_score = (user.get("seller_score") or {}) if user else {}

    return {
        "id": listing.get("id"),
        "objectID": listing.get("objectID"),
        "title": listing.get("title"),
        "designer_names": listing.get("designer_names"),
        "designers": listing.get("designers", []),
        "price": listing.get("price"),
        "sold_price": listing.get("sold_price"),
        "sold_price_includes_shipping": listing.get("sold_price_includes_shipping"),
        "sold_shipping_price": listing.get("sold_shipping_price"),
        "price_drops": listing.get("price_drops", []),
        "created_at": listing.get("created_at"),
        "sold_at": listing.get("sold_at"),
        "bumped_at": listing.get("bumped_at"),
        "price_updated_at": listing.get("price_updated_at"),
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
        "cover_photo_url": cover_photo.get("url") if cover_photo else None,
        "photo_count": listing.get("photo_count"),
        "measurement_count": listing.get("measurement_count"),
        "seller_id": user.get("id"),
        "seller_username": user.get("username"),
        "seller_rating": seller_score.get("rating_average"),
        "seller_rating_count": seller_score.get("rating_count"),
        "seller_trusted": user.get("trusted_seller"),
        "seller_total_bought_sold": user.get("total_bought_and_sold"),
        "shipping": shipping,
        "marketplace": listing.get("marketplace"),
        "strata": listing.get("strata"),
        "buynow": listing.get("buynow"),
        "makeoffer": listing.get("makeoffer"),
        "dropped": listing.get("dropped"),
        "listing_url": f"https://grailed.com/listings/{listing.get('id')}" if listing.get('id') else None,
        "scraped_at": datetime.now().isoformat(),
    }


# --------------------------- single-query scrape ---------------------------

def _build_payload(query, page):
    safe_query = query.replace(' ', '%20')
    return {
        "requests": [{
            "indexName": "Listing_sold_production",
            "params": (
                "analytics=true&clickAnalytics=true&enableABTest=true"
                "&facets=%5B%22badges%22%2C%22category_path%22%2C%22category_size%22"
                "%2C%22condition%22%2C%22department%22%2C%22designers.name%22"
                "%2C%22location%22%2C%22sold_price%22%2C%22strata%22%5D"
                "&getRankingInfo=true&highlightPostTag=__%2Fais-highlight__"
                "&highlightPreTag=__ais-highlight__&hitsPerPage=40"
                "&maxValuesPerFacet=165"
                "&numericFilters=%5B%22sold_price%3E%3D0%22%2C%22sold_price%3C%3D1000000%22%5D"
                f"&page={page}&query={safe_query}"
            ),
        }]
    }


def scrape_query(query, creds, seen_ids, output_handle, seen_handle,
                 min_delay=2.0, max_delay=5.0, allow_creds_refresh=True):
    """
    Returns dict with: new_count, dup_count, status.
    status: 'ok' | 'auth_failed' | 'aborted'
    Mutates: seen_ids, creds (if refreshed). creds is a dict {api_key, app_id}.
    """
    headers = dict(DEFAULT_HEADERS)
    headers['x-algolia-api-key'] = creds['api_key']
    headers['x-algolia-application-id'] = creds['app_id']

    new_count = 0
    dup_count = 0
    page = 0
    consecutive_errors = 0

    while True:
        payload = _build_payload(query, page)
        try:
            resp = requests.post(ALGOLIA_URL, headers=headers, json=payload, timeout=30)
        except requests.RequestException as e:
            consecutive_errors += 1
            log(f"  network error on page {page}: {e}")
            if consecutive_errors >= 3:
                return {'new_count': new_count, 'dup_count': dup_count, 'status': 'aborted'}
            time.sleep(10)
            continue

        if resp.status_code == 200:
            consecutive_errors = 0
            data = resp.json()
            results = data.get('results') or []
            if not results:
                break
            hits = results[0].get('hits', [])
            if not hits:
                break

            page_new = 0
            for h in hits:
                oid = str(h.get('objectID') or h.get('id') or '')
                if not oid:
                    continue
                if oid in seen_ids:
                    dup_count += 1
                    continue
                seen_ids.add(oid)
                details = extract_listing_details(h)
                output_handle.write(json.dumps(details, ensure_ascii=False) + "\n")
                append_seen_id(seen_handle, oid)
                new_count += 1
                page_new += 1

            output_handle.flush()
            seen_handle.flush()
            log(f"  page {page + 1}: {len(hits)} hits, +{page_new} new, {dup_count} dup so far")

            if len(hits) < 40:
                break  # last page
            page += 1

        elif resp.status_code in (401, 403):
            log(f"  auth failed (HTTP {resp.status_code})")
            if allow_creds_refresh:
                log("  refreshing Algolia credentials...")
                new_key, new_app = get_algolia_credentials(force_refresh=True)
                if new_key and new_app:
                    creds['api_key'] = new_key
                    creds['app_id'] = new_app
                    headers['x-algolia-api-key'] = new_key
                    headers['x-algolia-application-id'] = new_app
                    allow_creds_refresh = False  # only retry once
                    continue
            return {'new_count': new_count, 'dup_count': dup_count, 'status': 'auth_failed'}

        elif resp.status_code == 429:
            consecutive_errors += 1
            backoff = min(120, (2 ** consecutive_errors) + random.uniform(0, 1))
            log(f"  rate limited, backing off {backoff:.1f}s")
            time.sleep(backoff)
            continue

        else:
            consecutive_errors += 1
            log(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            if consecutive_errors >= 3:
                return {'new_count': new_count, 'dup_count': dup_count, 'status': 'aborted'}
            time.sleep(10)
            continue

        time.sleep(random.uniform(min_delay, max_delay))

    return {'new_count': new_count, 'dup_count': dup_count, 'status': 'ok'}


# --------------------------- broad-scrape driver ---------------------------

def load_queries(path=QUERIES_FILE):
    if not os.path.exists(path):
        log(f"Queries file not found: {path}")
        return []
    queries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            queries.append(line)
    # dedup while preserving order
    seen = set()
    out = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def run_broad_scrape(min_query_delay=5.0, max_query_delay=15.0,
                     long_pause_every=50, long_pause_min=60, long_pause_max=120):
    queries = load_queries()
    if not queries:
        log("No queries to run.")
        return

    api_key, app_id = get_algolia_credentials()
    if not api_key or not app_id:
        log("Could not obtain Algolia credentials. Aborting.")
        return
    creds = {'api_key': api_key, 'app_id': app_id}

    seen_ids = load_seen_ids()
    log(f"Loaded {len(seen_ids)} previously-seen IDs.")
    log(f"Running {len(queries)} queries.")

    started_at = time.time()
    total_new = 0
    total_dup = 0

    with open(OUTPUT_FILE, 'a', encoding='utf-8') as out_f, \
         open(SEEN_IDS_FILE, 'a', encoding='utf-8') as seen_f:

        for i, query in enumerate(queries, 1):
            log(f"[{i}/{len(queries)}] query: {query!r}")
            result = scrape_query(query, creds, seen_ids, out_f, seen_f)
            total_new += result['new_count']
            total_dup += result['dup_count']
            log(f"  done: +{result['new_count']} new, {result['dup_count']} dup, "
                f"status={result['status']}, total_new={total_new}")

            if result['status'] == 'auth_failed':
                log("Auth failed and refresh exhausted. Stopping.")
                break

            if i < len(queries):
                if i % long_pause_every == 0:
                    pause = random.uniform(long_pause_min, long_pause_max)
                    log(f"Long pause: {pause:.1f}s")
                    time.sleep(pause)
                else:
                    time.sleep(random.uniform(min_query_delay, max_query_delay))

    elapsed = time.time() - started_at
    log(f"DONE. {total_new} new listings, {total_dup} dup hits, "
        f"{elapsed/60:.1f} min elapsed. Total seen: {len(seen_ids)}.")


# --------------------------- single-query CLI mode ---------------------------

def run_single_query(query, max_results=200, min_delay=2.0, max_delay=5.0):
    api_key, app_id = get_algolia_credentials()
    if not api_key or not app_id:
        log("Could not obtain Algolia credentials. Aborting.")
        return
    creds = {'api_key': api_key, 'app_id': app_id}
    seen_ids = load_seen_ids()
    log(f"Single-query mode: {query!r} (max_results={max_results})")

    with open(OUTPUT_FILE, 'a', encoding='utf-8') as out_f, \
         open(SEEN_IDS_FILE, 'a', encoding='utf-8') as seen_f:
        # naive cap: scrape_query has no max_results — single mode just runs to exhaustion
        result = scrape_query(query, creds, seen_ids, out_f, seen_f,
                              min_delay=min_delay, max_delay=max_delay)
    log(f"Single-query done: +{result['new_count']} new, {result['dup_count']} dup.")


# --------------------------- main ---------------------------

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        login_and_save_cookies()
        return

    if not os.path.exists(AUTH_STATE_FILE):
        log("No auth state. Running login flow first.")
        login_and_save_cookies()

    if len(sys.argv) > 1 and sys.argv[1] == "broad":
        run_broad_scrape()
        return

    if len(sys.argv) > 1:
        query = sys.argv[1]
        max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        run_single_query(query, max_results=max_results)
        return

    # default: broad mode
    run_broad_scrape()


if __name__ == "__main__":
    main()
