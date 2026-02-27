from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Counter for Drive API requests
        request_count = 0

        def handle_request(request):
            nonlocal request_count
            if "googleapis.com/drive/v3/files" in request.url:
                print(f"Drive API Request detected: {request.url}")
                request_count += 1

        page.on("request", handle_request)

        print("--- Run 1 ---")
        print("Loading page...")
        page.goto("http://localhost:8000/index.html")
        page.wait_for_load_state("domcontentloaded")

        print("Navigating to #cat...")
        # We can trigger hash change or click the link
        page.evaluate("window.location.hash = '#cat'")
        # Wait for potential API call
        page.wait_for_timeout(5000)

        print(f"Requests after Run 1: {request_count}")

        print("--- Run 2 (Reload) ---")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        # Re-attach listener? No, page object is same but reload clears event listeners usually?
        # Actually page.on works for the page instance.

        print("Navigating to #cat...")
        page.evaluate("window.location.hash = '#cat'")
        page.wait_for_timeout(5000)

        print(f"Total requests: {request_count}")

        browser.close()

if __name__ == "__main__":
    run()
