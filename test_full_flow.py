from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state=".spotify_session.json")
    page = context.new_page()
    
    # Step 1: Go to wizard
    page.goto("https://creators.spotify.com/pod/show/6pNib4l9No9D5Dynz8e0jZ/episode/wizard")
    page.wait_for_load_state("networkidle")
    
    # Step 2: Upload file
    print("Uploading file...")
    file_input = page.locator('input[type="file"]')
    file_input.set_input_files("research_podcast_Laplace_transformation.wav")
    
    # Step 3: Wait for title field to appear (page transition)
    print("Waiting for form to load...")
    page.get_by_role("textbox", name="Title (required)").wait_for(state="visible", timeout=30000)
    
    # Step 4: Fill title
    print("Filling title...")
    page.get_by_role("textbox", name="Title (required)").fill("Test Episode - DELETE ME")
    
    # Step 5: Fill description (uses filter because no name attribute)
    print("Filling description...")
    page.get_by_role("textbox").filter(has_text="What else do you want your").fill("This is a test description.")
    
    # Step 6: Click Next
    print("Clicking Next...")
    page.get_by_role("button", name="Next").click()
    page.wait_for_load_state("networkidle")
    
    # Step 7: Wait for Publish button to be visible
    print("Waiting for Publish button...")
    publish_btn = page.get_by_role("button", name="Publish")
    publish_btn.wait_for(state="visible", timeout=120000)
    
    # Step 8: Click Publish (this might show Now/Schedule options)
    print("Clicking Publish...")
    publish_btn.click()
    
    # Step 9: Select "Now" option (publish immediately)
    print("Selecting 'Now' option...")
    page.get_by_text("Now", exact=True).wait_for(state="visible", timeout=10000)
    page.get_by_text("Now", exact=True).click()
    
    print("\n✅ Ready to publish! 'Now' is selected.")
    print("Press Enter to close WITHOUT final confirmation.")
    input()
    
    browser.close()