from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state=".spotify_session.json")
    page = context.new_page()
    
    page.goto("https://creators.spotify.com/pod/show/6pNib4l9No9D5Dynz8e0jZ/episode/wizard")
    page.wait_for_load_state("networkidle")
    
    # Find file input elements
    file_inputs = page.locator('input[type="file"]')
    count = file_inputs.count()
    
    print(f"Found {count} file input(s)")
    
    for i in range(count):
        el = file_inputs.nth(i)
        print(f"  Input {i}: accept={el.get_attribute('accept')}")
    
    print("\nBrowser is open. Press Enter to close.")
    input()
    
    browser.close()