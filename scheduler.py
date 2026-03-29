import csv
import time
import random
import requests
import json
import os
import logging
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION — Edit these values
# ─────────────────────────────────────────────
PINTEREST_ACCESS_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "YOUR_PINTEREST_ACCESS_TOKEN")
PINTEREST_BOARD_ID     = os.environ.get("PINTEREST_BOARD_ID", "YOUR_BOARD_ID")
CSV_FILE               = "products.csv"
PINS_PER_RUN           = 30
DELAY_BETWEEN_PINS     = 60  # seconds
LOG_FILE               = "activity_log.txt"
# ─────────────────────────────────────────────

# Amazon catchy titles
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

# Tags for all pins
TAGS = [
    "Bathroom",
    "Home",
    "Home kitchen",
    "Kitchen",
    "Kitchen essentials",
    "Kitchen Storage",
    "Kitchen gadgets",
    "Kitchen tools",
    "Home Decor",
    "Cooking tools",
    "Outdoor",
    "Flower",
]

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

HEADERS_SCRAPER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

POSTED_FILE = "posted.json"


def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []


def save_posted(posted):
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f, indent=2)


def scrape_amazon(url):
    """Scrape title and image from Amazon product page."""
    try:
        # Follow short link if needed
        response = requests.get(url, headers=HEADERS_SCRAPER, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch {url} — Status: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title_tag = soup.find(id="productTitle")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Image
        image_url = None
        img_tag = soup.find(id="landingImage") or soup.find(id="imgBlkFront")
        if img_tag:
            image_url = img_tag.get("src") or img_tag.get("data-src")

        if not image_url:
            scripts = soup.find_all("script", type="text/javascript")
            for script in scripts:
                text = str(script)
                if "colorImages" in text:
                    start = text.find("https://m.media-amazon.com")
                    if start != -1:
                        end = text.find('"', start)
                        image_url = text[start:end]
                        break

        return title, image_url

    except Exception as e:
        logging.error(f"Amazon scrape error {url}: {e}")
        return None, None


def scrape_walmart(url):
    """Scrape title and image from Walmart product page."""
    try:
        time.sleep(random.uniform(2, 5))
        response = requests.get(url, headers=HEADERS_SCRAPER, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch {url} — Status: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title = None
        title_tag = soup.find("h1", {"itemprop": "name"}) or soup.find("h1")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Image
        image_url = None
        img_tag = soup.find("img", {"data-testid": "hero-image"}) or soup.find("img", {"class": "db"})
        if img_tag:
            image_url = img_tag.get("src")

        # Try JSON data if image not found
        if not image_url:
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                text = str(script)
                if "imageInfo" in text or "productImageUrl" in text:
                    start = text.find("https://i5.walmartimages.com")
                    if start != -1:
                        end = text.find('"', start)
                        image_url = text[start:end]
                        break

        return title, image_url

    except Exception as e:
        logging.error(f"Walmart scrape error {url}: {e}")
        return None, None


def create_pin(title, description, image_url, link):
    """Post a pin to Pinterest."""
    url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Add tags to description
    tags_text = " ".join([f"#{tag.replace(' ', '')}" for tag in TAGS])
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

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        logging.info(f"✅ Pin posted: {title[:50]}")
        return True
    else:
        logging.error(f"❌ Pin failed: {response.status_code} — {response.text}")
        return False


def load_products():
    """Load products from CSV."""
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

    # Filter not yet posted
    pending = [p for p in products if p["link"] not in posted]

    if not pending:
        print("✅ All products already posted! Add more links to CSV.")
        logging.info("No pending products.")
        return

    print(f"📦 {len(pending)} products pending | Posting up to {PINS_PER_RUN} this run")

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
            print(f"⚠️ Could not get image — skipping: {link}")
            logging.warning(f"No image found: {link}")
            continue

        print(f"📌 Posting: {pin_title[:60]}...")
        success = create_pin(pin_title, description, image_url, link)

        if success:
            posted.append(link)
            save_posted(posted)
            count += 1
            print(f"✅ Pin {count}/{PINS_PER_RUN} posted!")
            time.sleep(DELAY_BETWEEN_PINS)
        else:
            print(f"❌ Failed: {link}")
            time.sleep(10)

    print(f"\n🎉 Scheduler finished! Total pins posted: {count}")
    logging.info(f"Scheduler finished. Pins posted: {count}")


if __name__ == "__main__":
    run_scheduler()
