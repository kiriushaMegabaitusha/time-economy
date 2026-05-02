import asyncio
from playwright.async_api import async_playwright
import os

OUTPUT_DIR = "/home/kyrylo/Documents/50-59_fun/54_time_econ/time_econ_app/screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGES = [
    ("http://localhost:8001/", "01_dashboard.png", "Dashboard"),
    ("http://localhost:8001/members", "02_members.png", "Members"),
    ("http://localhost:8001/members/1", "03_member_detail.png", "Member Detail"),
    ("http://localhost:8001/transactions", "04_transactions.png", "Transactions"),
    ("http://localhost:8001/needs", "05_needs.png", "Needs"),
    ("http://localhost:8001/skills", "06_skills.png", "Skills"),
    ("http://localhost:8001/governance", "07_governance.png", "Governance"),
]

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()

        for url, filename, label in PAGES:
            print(f"Capturing {label}...")
            await page.goto(url, wait_until="networkidle")
            # Wait for fonts and charts to settle
            await page.wait_for_timeout(1500)
            # Ensure charts are rendered (only if canvas exists on this page)
            canvas_exists = await page.locator("canvas").count() > 0
            if canvas_exists:
                await page.wait_for_selector("canvas", state="visible", timeout=5000)
                await page.wait_for_timeout(500)

            path = os.path.join(OUTPUT_DIR, filename)
            await page.screenshot(path=path, full_page=True)
            print(f"  -> {path}")

        await browser.close()
        print("All screenshots captured!")

if __name__ == "__main__":
    asyncio.run(take_screenshots())
