# Pinterest Content Scheduler

Automatically scrapes product images & titles from Amazon and Walmart and posts them as Pinterest pins.

---

## Files
- `scheduler.py` — Main scheduler script
- `products.csv` — Your affiliate product links
- `requirements.txt` — Python dependencies
- `.github/workflows/run_scheduler.yml` — Manual GitHub Actions trigger

---

## CSV Format
```
Product Link,Type
https://amzn.to/xxxxx,amazon
https://walmart.sjv.io/xxxxx,walmart
```
- **amazon** → uses catchy random title
- **walmart** → uses actual product name as title

---

## GitHub Secrets Required
Go to repo → Settings → Secrets → Actions → New secret:
- `PINTEREST_ACCESS_TOKEN`
- `PINTEREST_BOARD_ID`

---

## How to Run
1. Update `products.csv` with new affiliate links
2. Upload to GitHub
3. Go to **Actions → Pinterest Scheduler → Run workflow**
4. Click **Run workflow** ✅

Runs manually whenever you want — no fixed schedule!
