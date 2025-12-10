from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    
    # Load saved session
    context = browser.new_context(storage_state=".spotify_session.json")
    page = context.new_page()
    
    # Go directly to episode wizard
    page.goto("https://creators.spotify.com/pod/show/6pNib4l9No9D5Dynz8e0jZ/episode/wizard")
    
    print("Did it load without asking you to log in? (Press Enter to close)")
    input()
    
    browser.close()