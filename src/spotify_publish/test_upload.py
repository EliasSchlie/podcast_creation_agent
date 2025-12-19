from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state=".spotify_session.json")
    page = context.new_page()
    
    page.goto("https://creators.spotify.com/pod/show/6pNib4l9No9D5Dynz8e0jZ/episode/wizard")
    page.wait_for_load_state("networkidle")
    
    # Find the file input and upload
    file_input = page.locator('input[type="file"]')
    file_input.set_input_files("research_podcast_Laplace_transformation.wav")
    
    print("File uploaded! Look at the browser.")
    print("Note the form fields you see (title, description, etc.)")
    print("Press Enter when ready to close.")
    input()
    
    browser.close()