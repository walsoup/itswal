from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create a new context to ensure clean state
        context = browser.new_context()
        page = context.new_page()

        request_count = 0

        def handle_route(route):
            nonlocal request_count
            print(f"Intercepted Request: {route.request.url}")
            request_count += 1
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"files": [{"id": "1", "name": "cat1.jpg", "thumbnailLink": "https://placehold.co/400", "mimeType": "image/jpeg"}, {"id": "2", "name": "cat2.jpg", "thumbnailLink": "https://placehold.co/400", "mimeType": "image/jpeg"}]}'
            )

        # Intercept Google Drive API calls
        page.route("**/drive/v3/files?*", handle_route)

        print("--- Run 1 (Cold Start) ---")
        page.goto("http://localhost:8000/index.html")
        page.wait_for_load_state("domcontentloaded")

        # Clear localStorage and reload
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        print("Navigating to #cat...")
        page.evaluate("window.location.hash = '#cat'")
        # Wait for API call
        page.wait_for_timeout(3000)

        print(f"Requests in Run 1: {request_count}")
        items_run1 = page.locator("#cat-album .album-item").count()
        print(f"Items in Run 1: {items_run1}")

        # Check cache explicitly
        cache_key = "wal-drive-cache-1Mt8jmm2s-qgYHm_JtZk_0zGkMZcrWCDM"
        cached_data = page.evaluate(f"localStorage.getItem('{cache_key}')")
        if cached_data:
            print("CACHE: Found data in localStorage!")
        else:
            print("CACHE: No data found in localStorage.")

        print("--- Run 2 (Reload / Cache Hit) ---")
        request_count = 0

        page.reload()
        page.wait_for_load_state("domcontentloaded")

        print("Navigating to #cat...")
        page.evaluate("window.location.hash = '#cat'")
        # Wait for potential API call
        page.wait_for_timeout(3000)

        print(f"Requests in Run 2: {request_count}")
        items_run2 = page.locator("#cat-album .album-item").count()
        print(f"Items in Run 2: {items_run2}")

        if request_count == 0 and items_run2 > 0:
            print("SUCCESS: Loaded from cache with 0 API calls!")
            page.screenshot(path="verification_success.png")
        else:
            print(f"FAILURE: Requests={request_count}, Items={items_run2}")
            page.screenshot(path="verification_failure.png")

        browser.close()

if __name__ == "__main__":
    run()
