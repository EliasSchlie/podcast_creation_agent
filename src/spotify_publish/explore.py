from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Opens visible browser
    context = browser.new_context()
    page = context.new_page()
    
    page.goto("https://creators.spotify.com")
    
    print("Browser is open. Explore the site, log in manually.")
    print("When done, press Enter here to save session and close.")
    input()
    
    # Save session (cookies, localStorage) for later
    context.storage_state(path=".spotify_session.json")
    print("Session saved to .spotify_session.json")
    
    browser.close()