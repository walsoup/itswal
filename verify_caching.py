from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        request_count = 0

        def handle_request(request):
            nonlocal request_count
            if "googleapis.com/drive/v3/files" in request.url:
                print(f"Drive API Request detected: {request.url}")
                request_count += 1

        # Listen for console logs
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("request", handle_request)

        print("--- Run 1 (Cold Start) ---")
        page.goto("http://localhost:8000/index.html")
        page.wait_for_load_state("domcontentloaded")

        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        print("Navigating to #cat...")
        page.evaluate("window.location.hash = '#cat'")
        page.wait_for_timeout(5000)

        requests_run1 = request_count
        items_run1 = page.locator("#cat-album .album-item").count()
        print(f"Requests in Run 1: {requests_run1}")
        print(f"Items in Run 1: {items_run1}")

        print("--- Run 2 (Reload / Cache Hit) ---")
        request_count = 0

        page.reload()
        page.wait_for_load_state("domcontentloaded")

        print("Navigating to #cat...")
        page.evaluate("window.location.hash = '#cat'")
        page.wait_for_timeout(5000)

        requests_run2 = request_count
        items_run2 = page.locator("#cat-album .album-item").count()
        print(f"Requests in Run 2: {requests_run2}")
        print(f"Items in Run 2: {items_run2}")

        browser.close()

if __name__ == "__main__":
    run()
