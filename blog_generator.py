import csv
import time
import random
import requests
import re
import logging
import os
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
CSV_FILE       = "products.csv"
OUTPUT_FILE    = "blog_post.html"
LOG_FILE       = "blog_log.txt"
BLOG_NICHE     = "home"  # home | kitchen | beauty | decor
# ─────────────────────────────────────────────

TITLES = {
    "home":    ["Best Home Finds on Amazon Under $20","Viral Home Finds on Amazon Everyone's Buying","Must Have Home Finds on Amazon Right Now","Life Changing Home Finds on Amazon","Trending Home Finds on Amazon 2026"],
    "kitchen": ["Best Kitchen Products on Amazon Under $25","Viral Kitchen Products on Amazon Everyone Loves","Must Have Kitchen Products on Amazon Right Now","Trending Kitchen Products on Amazon 2026","Best Kitchen Gadgets on Amazon Right Now"],
    "beauty":  ["Best Beauty & Skincare on Amazon Under $15","Viral Beauty & Skincare on Amazon Everyone Loves","Must Have Beauty & Skincare on Amazon Right Now","Trending Beauty & Skincare on Amazon 2026","Best Beauty Finds on Amazon Right Now"],
    "decor":   ["Best Home Decor on Amazon Under $30","Viral Home Decor on Amazon Everyone's Buying","Must Have Home Decor on Amazon Right Now","Trending Home Decor on Amazon 2026","Best Home Decor Finds on Amazon Right Now"],
}

INTROS = {
    "home":    ["If you're tired of scrolling endlessly for useful stuff, these Amazon home finds might just solve that problem.","These Amazon home finds are the kind of buys that make you wonder why you didn't get them sooner."],
    "kitchen": ["Cooking and cleaning just got a lot easier thanks to these clever Amazon kitchen products.","These Amazon kitchen products get used every single day — not just once and forgotten."],
    "beauty":  ["Good skincare doesn't have to be expensive. These Amazon beauty and skincare finds prove it.","These Amazon beauty and skincare finds are the ones people quietly repurchase again and again."],
    "decor":   ["If your space feels empty, these Amazon home decor finds are the fix.","Want to transform your room without a full renovation? These Amazon decor picks make it easy."],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }


def pick(arr):
    return arr[random.randint(0, len(arr) - 1)]


def extract_asin(url):
    match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    return None


def get_amazon_image_via_asin(asin):
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


def resolve_short_url(url):
    """Follow amzn.to redirects to get full Amazon URL."""
    try:
        resp = requests.head(url, headers=get_headers(), allow_redirects=True, timeout=15)
        return resp.url
    except:
        try:
            resp = requests.get(url, headers=get_headers(), allow_redirects=True, timeout=15)
            return resp.url
        except:
            return url


def scrape_amazon(url):
    """Scrape title and image from Amazon product page."""
    try:
        # Resolve short URLs like amzn.to
        if "amzn.to" in url or "amzn.com" in url:
            print(f"   🔗 Resolving short URL...")
            url = resolve_short_url(url)
            print(f"   ✅ Resolved: {url[:80]}...")

        time.sleep(random.uniform(2, 4))
        session = requests.Session()
        response = session.get(url, headers=get_headers(), timeout=20, allow_redirects=True)

        title     = None
        image_url = None

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Title
            title_tag = soup.find(id="productTitle")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Image Method 1: landingImage
            img_tag = soup.find(id="landingImage") or soup.find(id="imgBlkFront")
            if img_tag:
                image_url = img_tag.get("data-old-hires") or img_tag.get("src")

            # Image Method 2: JSON in scripts
            if not image_url:
                for script in soup.find_all("script"):
                    text = str(script.string or "")
                    if "colorImages" in text or "ImageBlockATF" in text:
                        matches = re.findall(r'https://m\.media-amazon\.com/images/I/[^"\']+\.jpg', text)
                        if matches:
                            image_url = max(matches, key=len)
                            break

            # Image Method 3: og:image
            if not image_url:
                og_image = soup.find("meta", property="og:image")
                if og_image:
                    image_url = og_image.get("content")

        # Image Method 4: ASIN CDN fallback
        if not image_url:
            asin = extract_asin(url)
            if asin:
                image_url = get_amazon_image_via_asin(asin)

        return title, image_url, url

    except Exception as e:
        logging.error(f"Scrape error {url}: {e}")
        try:
            asin = extract_asin(url)
            if asin:
                return None, get_amazon_image_via_asin(asin), url
        except:
            pass
        return None, None, url


def generate_blog_html(products, niche):
    """Generate full blog HTML from scraped products."""
    blog_title = pick(TITLES[niche])
    intro      = pick(INTROS[niche])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{blog_title}</title>
<style>
  body {{ font-family: 'Georgia', serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7; }}
  h1 {{ color: #b5451b; font-size: 2rem; margin-bottom: 10px; }}
  h2 {{ color: #b5451b; font-size: 1.3rem; margin-top: 40px; }}
  p {{ font-size: 1rem; color: #444; }}
  .product-card {{ border: 1px solid #eee; border-radius: 10px; padding: 20px; margin: 30px 0; display: flex; gap: 20px; align-items: flex-start; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .product-card img {{ width: 150px; height: 150px; object-fit: contain; border-radius: 8px; background: #f9f9f9; padding: 6px; flex-shrink: 0; }}
  .product-info {{ flex: 1; }}
  .product-info h2 {{ margin-top: 0; }}
  .btn {{ display: inline-block; background: #f0a500; color: #000; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 10px; font-family: sans-serif; }}
  .btn:hover {{ background: #d4920a; }}
  .disclosure {{ font-size: 0.8rem; color: #888; margin-top: 40px; padding-top: 16px; border-top: 1px solid #eee; }}
</style>
</head>
<body>

<h1>{blog_title}</h1>
<p>{intro}</p>

"""

    for i, product in enumerate(products, 1):
        title     = product["title"] or f"Amazon Product {i}"
        image_url = product["image"] or ""
        link      = product["link"]

        img_tag = f'<img src="{image_url}" alt="{title}" />' if image_url else ""

        html += f"""<div class="product-card">
  {img_tag}
  <div class="product-info">
    <h2>{i}. {title}</h2>
    <p>This is one of the most popular Amazon finds right now. Highly rated and worth every penny.</p>
    <a href="{link}" target="_blank" rel="nofollow" class="btn">✅ Check Price on Amazon →</a>
  </div>
</div>

"""

    html += """<p class="disclosure">Disclosure: This post contains affiliate links. I may earn a small commission at no extra cost to you. Thank you for supporting this blog!</p>

</body>
</html>"""

    return html


def load_products_from_csv():
    products = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = row.get("Product Link", "").strip()
            if link:
                products.append(link)
    return products


def run():
    print("🚀 Blog Generator Starting...")
    print(f"📂 Reading links from {CSV_FILE}...")

    links = load_products_from_csv()
    if not links:
        print("❌ No links found in CSV. Add links and try again.")
        return

    print(f"✅ Found {len(links)} links\n")

    scraped_products = []

    for i, link in enumerate(links, 1):
        print(f"🔍 [{i}/{len(links)}] Scraping: {link}")
        title, image_url, resolved_url = scrape_amazon(link)

        if title:
            print(f"   ✅ Title: {title[:60]}...")
        else:
            print(f"   ⚠️ No title found")

        if image_url:
            print(f"   🖼️ Image found!")
        else:
            print(f"   ⚠️ No image found")

        scraped_products.append({
            "title": title,
            "image": image_url,
            "link": resolved_url
        })

        time.sleep(random.uniform(2, 3))

    print(f"\n✍️ Generating blog HTML...")
    html = generate_blog_html(scraped_products, BLOG_NICHE)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Blog saved to {OUTPUT_FILE}")
    print(f"📋 Open {OUTPUT_FILE} in browser to preview")
    print(f"📋 Copy HTML content and paste into Blogger HTML editor")
    logging.info(f"Blog generated with {len(scraped_products)} products")


if __name__ == "__main__":
    run()