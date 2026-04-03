import csv
import time
import random
import requests
import json
import os
import re
import logging
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
PINTEREST_ACCESS_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "YOUR_PINTEREST_ACCESS_TOKEN")
PINTEREST_BOARD_ID     = os.environ.get("PINTEREST_BOARD_ID", "YOUR_BOARD_ID")
CSV_FILE               = "products.csv"
PINS_PER_RUN           = 30
DELAY_BETWEEN_PINS     = 60
LOG_FILE               = "activity_log.txt"
# ─────────────────────────────────────────────

AMAZON_TITLES = [
    "This Amazon Deal Is Actually Worth Buying",
    "Amazon Favorite That Changed My Routine",
    "Best Amazon Pick for Home Organization",
    "Amazon Buy Everyone Is Talking About",
    "I Tried This Amazon Product & Wow",
    "Amazon Hidden Gem for Under $15",
    "This Amazon Gadget Is Life-Changing",
    "Amazon Find You Didn't Know You Needed",
    "Most Popular Amazon Product Right Now",
    "Amazon Must-Grab for Less Than $10",
    "Amazon Item That's Always Sold Out",
    "My Go-To Amazon Purchase This Year",
    "You Won't Believe This Amazon Deal",
    "Amazon Essential That Makes Life Easier",
    "Trending on Amazon: Top Buy Today",
    "Amazon Favorite That Works Perfectly",
    "Amazon Bestseller You'll Love",
    "Viral Amazon Find Worth the Hype",
    "Amazon Product I Can't Live Without",
    "Best Amazon Purchase Under $25",
    "Epic Amazon Deal You Must See",
    "Amazon Item Every Home Needs",
    "This Amazon Product Saves Time",
    "Amazon Buy That Exceeded Expectations",
    "Amazon Find That Changed My Day",
    "Popular Amazon Product Under $30",
    "Amazon Discovery You'll Thank Yourself For",
    "Amazon Item That's Always in Stock",
    "Amazon Favorite That's Surprisingly Cheap",
    "Life-Improving Amazon Gadget Under $20",
    "Top Trending Amazon Buy Today",
    "Amazon Find Everyone Should Try",
    "Amazon Best Value Purchase of the Month",
    "Amazon Product That's Worth It",
    "This Amazon Buy Made a Big Difference",
    "Amazon Gem with Amazing Reviews",
    "Amazon Pick That's Going Viral",
    "Amazon Deal You Can't Miss",
    "Amazon Product That Works Better Than Expected",
    "Amazon Favorite for Daily Use",
    "Amazon Buy That Actually Delivers",
    "Cheap Amazon Find That Performs Amazing",
    "Amazon Must-Try Trending Item",
    "Amazon Product You'll Repurchase",
    "This Amazon Find Is Officially My Favorite",
    "Amazon Deal That's Too Good to Pass Up",
    "Amazon Item Boosting My Productivity",
    "Amazon Favorite Under $15 You Should Try",
    "Amazon Product Everyone Is Obsessing Over",
]

TAGS = [
    "Bathroom", "Home", "HomeKitchen", "Kitchen",
    "KitchenEssentials", "KitchenStorage", "KitchenGadgets",
    "KitchenTools", "HomeDecor", "CookingTools", "Outdoor", "Flower",
]

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

POSTED_FILE = "posted.json"

# Rotate user agents to avoid blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "TE": "trailers",
    }


def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []


def save_posted(posted):
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f, indent=2)


def extract_asin(url):
    """Extract ASIN from Amazon URL."""
    match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    return None


def get_amazon_image_via_asin(asin):
    """Get Amazon product image using ASIN directly from image CDN."""
    # Try multiple Amazon image URL formats
    image_urls = [
        f"https://m.media-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_.jpg",
        f"https://m.media-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg",
        f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg",
    ]
    for img_url in image_urls:
        try:
            resp = requests.head(img_url, timeout=10)
            if resp.status_code == 200:
                return img_url
        except:
            continue
    return None


def scrape_amazon(url):
    """Scrape title and image from Amazon product page."""
    try:
        time.sleep(random.uniform(2, 4))
        session = requests.Session()
        response = session.get(url, headers=get_headers(), timeout=20, allow_redirects=True)

        title = None
        image_url = None

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Get title
            title_tag = soup.find(id="productTitle")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Method 1: landingImage tag
            img_tag = soup.find(id="landingImage") or soup.find(id="imgBlkFront")
            if img_tag:
                # Try data-old-hires first (highest quality)
                image_url = img_tag.get("data-old-hires") or img_tag.get("src")

            # Method 2: Parse JSON image data from scripts
            if not image_url:
                scripts = soup.find_all("script")
                for script in scripts:
                    text = str(script.string or "")
                    if "colorImages" in text or "ImageBlockATF" in text:
                        matches = re.findall(r'https://m\.media-amazon\.com/images/I/[^"\']+\.jpg', text)
                        if matches:
                            # Pick largest image
                            best = max(matches, key=len)
                            image_url = best
                            break

            # Method 3: og:image meta tag
            if not image_url:
                og_image = soup.find("meta", property="og:image")
                if og_image:
                    image_url = og_image.get("content")

        # Method 4: Direct ASIN image CDN (fallback)
        if not image_url:
            asin = extract_asin(url)
            if asin:
                image_url = get_amazon_image_via_asin(asin)

        return title, image_url

    except Exception as e:
        logging.error(f"Amazon scrape error {url}: {e}")
        # Last resort: try ASIN CDN
        try:
            asin = extract_asin(url)
            if asin:
                return None, get_amazon_image_via_asin(asin)
        except:
            pass
        return None, None


def scrape_walmart(url):
    """Scrape title and image from Walmart product page."""
    try:
        time.sleep(random.uniform(2, 4))
        session = requests.Session()
        response = session.get(url, headers=get_headers(), timeout=20, allow_redirects=True)

        if response.status_code != 200:
            logging.warning(f"Walmart fetch failed {url} — {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title = None
        title_tag = soup.find("h1", {"itemprop": "name"}) or soup.find("h1")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Image — Method 1: meta og:image
        image_url = None
        og_image = soup.find("meta", property="og:image")
        if og_image:
            image_url = og_image.get("content")

        # Method 2: JSON script tags
        if not image_url:
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                text = str(script.string or "")
                matches = re.findall(r'https://i5\.walmartimages\.com/[^"\']+\.jpg', text)
                if matches:
                    image_url = matches[0]
                    break

        # Method 3: img tags
        if not image_url:
            img_tag = soup.find("img", {"data-testid": "hero-image"})
            if img_tag:
                image_url = img_tag.get("src")

        return title, image_url

    except Exception as e:
        logging.error(f"Walmart scrape error {url}: {e}")
        return None, None


def create_pin(title, description, image_url, link):
    """Post a pin to Pinterest."""
    api_url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    tags_text = " ".join([f"#{tag}" for tag in TAGS])
    full_description = f"{description}\n\n{tags_text}\n\n👉 Shop here: {link}"

    payload = {
        "board_id": PINTEREST_BOARD_ID,
        "title": title[:100],
        "description": full_description[:500],
        "link": link,
        "media_source": {
            "source_type": "image_url",
            "url": image_url
        }
    }

    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        logging.info(f"✅ Pin posted: {title[:50]}")
        return True
    else:
        logging.error(f"❌ Pin failed: {response.status_code} — {response.text}")
        print(f"❌ Pinterest error: {response.status_code} — {response.text}")
        return False


def load_products():
    products = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = row.get("Product Link", "").strip()
            ptype = row.get("Type", "").strip().lower()
            if link and ptype:
                products.append({"link": link, "type": ptype})
    return products


def run_scheduler():
    print("✅ Pinterest Content Scheduler Starting...")
    logging.info("Scheduler started")

    posted = load_posted()
    products = load_products()
    pending = [p for p in products if p["link"] not in posted]

    if not pending:
        print("✅ All products posted! Add more links to CSV.")
        return

    print(f"📦 {len(pending)} pending | Posting up to {PINS_PER_RUN} this run")

    count = 0
    for product in pending:
        if count >= PINS_PER_RUN:
            break

        link = product["link"]
        ptype = product["type"]

        print(f"\n🔍 Scraping ({ptype}): {link}")

        if ptype == "amazon":
            product_title, image_url = scrape_amazon(link)
            pin_title = random.choice(AMAZON_TITLES)
            description = product_title if product_title else "Amazing Amazon find!"

        elif ptype == "walmart":
            product_title, image_url = scrape_walmart(link)
            pin_title = product_title[:100] if product_title else "Amazing Walmart find!"
            description = product_title if product_title else "Check out this Walmart deal!"

        else:
            print(f"⚠️ Unknown type: {ptype} — skipping")
            continue

        if not image_url:
            print(f"⚠️ No image found — skipping: {link}")
            logging.warning(f"No image: {link}")
            continue

        print(f"🖼️ Image found!")
        print(f"📌 Posting: {pin_title[:60]}...")
        success = create_pin(pin_title, description, image_url, link)

        if success:
            posted.append(link)
            save_posted(posted)
            count += 1
            print(f"✅ Pin {count}/{PINS_PER_RUN} posted!")
            time.sleep(DELAY_BETWEEN_PINS)
        else:
            print(f"❌ Failed to post: {link}")
            time.sleep(10)

    print(f"\n🎉 Done! Total pins posted: {count}")
    logging.info(f"Scheduler finished. Pins posted: {count}")


if __name__ == "__main__":
    run_scheduler()
