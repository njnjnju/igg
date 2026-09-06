import time
import random
import secrets
import string
import csv
import re
import pyotp
import requests
import os
import sys
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# ⚙️ USER CONFIGURATION BLOCK
# =====================================================================
# PROXY CONFIGURATION (Format: username:password@host:port)
PROXY_STRING = "8008:MidzRjvmA592@p105.squidproxies.com:9140"

ADSPOWER_API = "http://127.0.0.1:50325/api/v1/browser/start"

# Asset pool folders inside the script directory
AVATAR_FOLDER = os.path.join(BASE_DIR, "avatar_pool")
POST_FOLDER = os.path.join(BASE_DIR, "post_pool")

FIRST_NAMES = [
    "rahul", "ramesh", "harshit", "vivek", "rehan", "ankit", "naman", "sushant", "payal", "rakhi", 
    "deep", "deepak", "deepali", "rohan", "devansh", "devanshu", "shiva", "shiv", "shivani", "amit",
    "raman", "naaz", "naazo", "akshat", "ashtham", "yash", "kirti", "bhavesh", "sia", "arjun"
]
LAST_NAMES = [
    "agarwal", "gupta", "khan", "singh", "gupta", "patel", "sharma", "reddy", "nair", "sophia", 
    "devi", "kumar", "kaur", "shukla", "shah", "kulkarni", "dubey", "reddy", "devi", "kaur",
    "kumar", "joshi", "tendulkar", "gavaskar", "sophia", "yadav", "tiwari", "tripathi", "chauhan", "dwivedi"
]

INSTAGRAM_QUOTES = [
    "Chasing dreams and catching flights. ✈️🌟",
    "Creating the life I love, one day at a time.",
    "Simplicity is the ultimate sophistication. ✨",
    "Focus on the step in front of you, not the whole staircase. 🏔️",
    "Escape the ordinary, embrace the journey. 🚀",
    "Do what makes your soul shine. ☀️💖",
    "Collect moments, not things. 📸🍃",
    "Keep moving forward. Great things take time. ⏳",
    "Consistency is the secret code to success.🔑",
    "Radiate positive vibes only. 🌈✌️",
    "Living life on my own terms. 💫",
    "Every day is a fresh start to write a new story. 📖"
]

def log(msg):
    print(msg, flush=True)

def parse_proxy(proxy_str):
    """Parses 'user:pass@host:port' string into Playwright proxy dictionary format."""
    if not proxy_str:
        return None
    try:
        user_pass, host_port = proxy_str.split("@")
        username, password = user_pass.split(":")
        return {
            "server": f"http://{host_port}",
            "username": username,
            "password": password
        }
    except Exception as e:
        log(f"⚠️ Failed to parse PROXY_STRING '{proxy_str}': {e}")
        return None

def get_random_image(folder_path):
    """Picks a random image file from the specified folder to ensure unique uploads."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        raise Exception(f"❌ Folder '{folder_path}' missing. Please add images inside it!")
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        raise Exception(f"❌ No .jpg or .png images found in '{folder_path}'. Please add some items.")
    
    selected_file = random.choice(files)
    return os.path.abspath(os.path.join(folder_path, selected_file))

def generate_profile_data():
    """Prompts for email manually and generates unique identity and username in format ramankumar02sf9d."""
    log("--------------------------------------------------")
    email_address = input("📧 Enter email address for registration: ").strip()
    
    fn_raw = random.choice(FIRST_NAMES).lower().replace(" ", "")
    ln_raw = random.choice(LAST_NAMES).lower().replace(" ", "")
    full_name = f"{fn_raw.capitalize()} {ln_raw.capitalize()}"
    
    # Format: ramankumar + 2 digits + 4 random chars -> e.g. ramankumar02sf9d
    digits_part = f"{secrets.randbelow(90) + 10:02d}"
    random_str_part = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    username = f"{fn_raw}{ln_raw}{digits_part}{random_str_part}"
    
    allowed_chars = string.ascii_letters + string.digits + "!@#$%*"
    password = "".join(secrets.choice(allowed_chars) for _ in range(14))
    
    return full_name, username, password, email_address

def create_browser_profile():
    """Calls AdsPower API to initialize an isolated environment context."""
    response = requests.get(ADSPOWER_API, timeout=3).json()
    return response['data']['ws']['puppeteer']

def type_human(page, locator, text):
    """Simulates realistic human typing and dispatches input/change events for React state updates."""
    try:
        locator.scroll_into_view_if_needed()
        locator.click()
        time.sleep(0.1)
        locator.fill(text)
        time.sleep(0.1)
        locator.evaluate("""el => {
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""")
        time.sleep(0.2)
    except Exception as err:
        log(f"⚠️ Typing warning: {err}")

def get_otp_input(page):
    """Locates the active, visible Confirmation Code input field, filtering out hidden or previous form inputs."""
    try:
        # 1. Check specific confirmation code input locators
        specific = page.locator("input[name='email_confirmation_code'], input[name='confirmationCode'], input[name='code'], input[placeholder*='Confirmation' i], input[placeholder*='code' i], input[aria-label*='Confirmation' i], input[aria-label*='code' i]").all()
        for inp in specific:
            if inp.is_visible():
                return inp
        
        # 2. Check visible inputs excluding email address and name fields
        all_inputs = page.locator("input").all()
        for inp in all_inputs:
            if inp.is_visible():
                val = inp.evaluate("el => el.value") or ""
                ph = (inp.get_attribute("placeholder") or "").lower()
                name = (inp.get_attribute("name") or "").lower()
                if "@" not in val and "email" not in name and "fullname" not in name and "name" not in name:
                    return inp
    except Exception:
        pass
    return None

def click_otp_submit(page):
    """Finds and clicks the visible Continue/Next/Submit button or falls back to Enter key."""
    try:
        buttons = page.locator("button, [role='button']").all()
        for btn in buttons:
            if btn.is_visible():
                txt = btn.inner_text().strip().lower()
                if any(k in txt for k in ["continue", "next", "confirm", "submit"]):
                    log(f"🚀 Clicking OTP submit button: '{btn.inner_text().strip()}'...")
                    btn.click()
                    return True
    except Exception:
        pass
    log("⚠️ Submit button not visible by text. Pressing Enter key...")
    page.keyboard.press("Enter")
    return False

def fill_dob(page):
    """Autofills random Date of Birth (Month, Day 1-28, Year 1990-2005)."""
    FULL_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    target_m_num = random.randint(1, 12)
    target_m_name = FULL_MONTHS[target_m_num - 1]
    target_m_short = SHORT_MONTHS[target_m_num - 1]
    target_d_num = random.randint(1, 28)
    target_y_num = random.randint(1990, 2005)
    
    log(f"📅 Autofilling Date of Birth: {target_m_name} {target_d_num}, {target_y_num}...")
    time.sleep(1)
    
    try:
        # Strategy A: Native HTML <select> elements
        selects = [s for s in page.locator("select").all() if "language" not in (s.get_attribute("aria-label") or "").lower()]
        if len(selects) >= 3:
            # Month selection
            m_sel = selects[0]
            try:
                m_sel.select_option(value=str(target_m_num))
            except:
                try:
                    m_sel.select_option(label=target_m_name)
                except:
                    m_sel.select_option(index=target_m_num)
            m_sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            time.sleep(0.3)

            # Day selection
            d_sel = selects[1]
            try:
                d_sel.select_option(value=str(target_d_num))
            except:
                try:
                    d_sel.select_option(label=str(target_d_num))
                except:
                    d_sel.select_option(index=target_d_num)
            d_sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            time.sleep(0.3)

            # Year selection
            y_sel = selects[2]
            try:
                y_sel.select_option(value=str(target_y_num))
            except:
                y_sel.select_option(label=str(target_y_num))
            y_sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            time.sleep(0.3)

            log(f"✅ DOB set via native <select> elements: {target_m_name} {target_d_num}, {target_y_num}")
            return

        # Strategy B: Custom React Comboboxes (Instagram Web UI)
        m_combo = page.locator("[aria-label='Select Month'], [aria-label*='Month' i], [title*='Month' i]").first
        d_combo = page.locator("[aria-label='Select Day'], [aria-label*='Day' i], [title*='Day' i]").first
        y_combo = page.locator("[aria-label='Select Year'], [aria-label*='Year' i], [title*='Year' i]").first
        
        combos = page.locator("[role='combobox']").all()
        
        m_target_combo = m_combo if m_combo.is_visible() else (combos[0] if len(combos) >= 1 else None)
        d_target_combo = d_combo if d_combo.is_visible() else (combos[1] if len(combos) >= 2 else None)
        y_target_combo = y_combo if y_combo.is_visible() else (combos[2] if len(combos) >= 3 else None)

        if m_target_combo and d_target_combo and y_target_combo:
            # 1. Select Month (Must match full/short month name ONLY, avoid raw digits)
            log(f"  └ Selecting Month: {target_m_name}")
            m_target_combo.click()
            time.sleep(0.5)
            opts = page.locator("[role='listbox'] [role='option'], [role='option']").all()
            for o in opts:
                txt = o.inner_text().strip()
                if txt in (target_m_name, target_m_short):
                    o.evaluate("el => el.click()")
                    break
            time.sleep(0.6)

            # 2. Select Day (Exact match for day string, e.g. "24")
            log(f"  └ Selecting Day: {target_d_num}")
            d_target_combo.click()
            time.sleep(0.5)
            opts = page.locator("[role='listbox'] [role='option'], [role='option']").all()
            for o in opts:
                txt = o.inner_text().strip()
                if txt == str(target_d_num) or txt == f"{target_d_num:02d}":
                    o.evaluate("el => el.click()")
                    break
            time.sleep(0.6)

            # 3. Select Year (Exact match for year string, e.g. "1990")
            log(f"  └ Selecting Year: {target_y_num}")
            y_target_combo.click()
            time.sleep(0.5)
            opts = page.locator("[role='listbox'] [role='option'], [role='option']").all()
            for o in opts:
                txt = o.inner_text().strip()
                if txt == str(target_y_num):
                    o.evaluate("el => el.click()")
                    break
            time.sleep(0.6)

            log(f"✅ Date of birth successfully selected: {target_m_name} {target_d_num}, {target_y_num}!")
            return
            
        log("⚠️ DOB dropdown elements could not be identified.")
    except Exception as dob_err:
        log(f"⚠️ DOB autofill note: {dob_err}")

def register_account():
    full_name, username, password, email_address = generate_profile_data()
    avatar_path = get_random_image(AVATAR_FOLDER)
    post_path = get_random_image(POST_FOLDER)
    proxy_config = parse_proxy(PROXY_STRING)
    
    log(f"🚀 Attempting Account Creation: {username} ({email_address})")
    if proxy_config:
        log(f"📡 Using Proxy: {proxy_config['server']}")

    ws_url = None
    try:
        ws_url = create_browser_profile()
    except Exception:
        log("ℹ️ AdsPower local API not detected. Launching Playwright Chromium browser...")

    with sync_playwright() as p:
        if ws_url:
            browser = p.chromium.connect_over_cdp(ws_url)
            if proxy_config:
                context = browser.new_context(proxy=proxy_config, viewport={"width": 1280, "height": 720})
            else:
                context = browser.contexts[0]
        else:
            headless_setting = os.getenv("HEADLESS", "false").lower() == "true"
            browser = p.chromium.launch(headless=headless_setting, proxy=proxy_config)
            context = browser.new_context(viewport={"width": 1280, "height": 720})

        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})
        
        # --- SUBMISSION STEP ---
        log("🌐 Navigating to Instagram Signup Page...")
        page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        
        log(f"✍️ Autofilling registration fields for {username}...")
        
        inputs = page.locator("input").all()
        if len(inputs) >= 4:
            log("✅ Identified form inputs by positional index. Filling fields...")
            type_human(page, inputs[0], email_address)
            log(f"✅ Email Address autofilled: {email_address}")

            type_human(page, inputs[1], password)
            log("✅ Password autofilled.")

            type_human(page, inputs[2], full_name)
            log(f"✅ Full Name autofilled: {full_name}")

            type_human(page, inputs[3], username)
            log(f"✅ Username autofilled: {username}")
        else:
            log("⚠️ Inputs count < 4, using attribute selector fallbacks...")
            email_field = page.locator("input[placeholder*='Mobile' i], input[placeholder*='email' i], input[name='emailOrPhone'], input[name='email']").first
            email_field.wait_for(state="visible", timeout=20000)
            type_human(page, email_field, email_address)

            pass_field = page.locator("input[type='password'], input[placeholder*='Password' i], input[name='password']").first
            type_human(page, pass_field, password)

            name_field = page.locator("input[placeholder*='Full name' i], input[placeholder*='Name' i], input[name='fullName'], input[name='name']").first
            if name_field.is_visible():
                type_human(page, name_field, full_name)

            user_field = page.locator("input[placeholder*='Username' i], input[name='username']").first
            if user_field.is_visible():
                type_human(page, user_field, username)

        dob_filled = False
        
        # Check if DOB dropdowns are present on Step 1 form
        m_combo = page.locator("[aria-label='Select Month'], [aria-label*='Month' i], [title*='Month' i]").first
        if m_combo.is_visible() or len(page.locator("select").all()) >= 3 or len(page.locator("[role='combobox']").all()) >= 3:
            fill_dob(page)
            dob_filled = True

        log("🚀 Submitting signup form...")
        submit_btn = page.locator("[role='button']:has-text('Submit'), button:has-text('Submit'), button[type='submit'], button:has-text('Sign up'), button:has-text('Next')").first
        submit_btn.click()
        time.sleep(5)
        
        # If DOB was not on Step 1, check if shown on Step 2
        if not dob_filled:
            time.sleep(3)
            has_dob = False
            for _ in range(3):
                if page.locator("select").count() >= 3 or page.locator("[role='combobox']").count() >= 3 or page.locator("text=/date of birth|birthday|add your birthday/i").is_visible():
                    has_dob = True
                    break
                time.sleep(1)
                
            if has_dob:
                log("📅 Setting birthdate on Step 2...")
                fill_dob(page)
                dob_filled = True
                time.sleep(1)
                next_dob_btn = page.locator("button:has-text('Next'), button[type='submit']").first
                if next_dob_btn.is_visible():
                    next_dob_btn.click()
                    log("✅ Submitted Date of Birth step!")
                time.sleep(5)
            
        # --- MANUAL EMAIL VERIFICATION STEP ---
        log("📩 Waiting for Confirmation Code screen...")
        time.sleep(3)

        log(f"📩 Awaiting 6-digit OTP verification code sent to {email_address}...")
        verification_code = input(f"👉 Enter the 6-digit code sent to {email_address}: ").strip().replace(" ", "")
        
        log(f"🔑 Submitting OTP code: '{verification_code}'...")
        
        # Locate visible OTP input field
        otp_field = None
        for _ in range(10):
            otp_field = get_otp_input(page)
            if otp_field:
                break
            time.sleep(1)
            
        if otp_field:
            log("✅ Found visible OTP input field. Filling code...")
            type_human(page, otp_field, verification_code)
        else:
            log("⚠️ OTP field fallback: typing code via page keyboard...")
            page.keyboard.type(verification_code, delay=80)

        time.sleep(1)
        click_otp_submit(page)
        log("⏳ Waiting for signup completion and session initialization...")
        time.sleep(6)
        
        # Dismiss post-signup popups ("Save Info", "Turn on Notifications", "Not Now")
        for _ in range(3):
            try:
                save_btn = page.locator("button:has-text('Save info'), button:has-text('Save Info'), button:has-text('Not Now')").first
                if save_btn.is_visible():
                    save_btn.click()
                    log("✅ Dismissed post-signup dialog popup.")
                    time.sleep(2)
            except Exception:
                pass

        # If redirected to login page or sitting on emailsignup URL, navigate to home feed
        if "login" in page.url.lower() or "emailsignup" in page.url.lower():
            log("🌐 Navigating to Instagram main page to establish active session...")
            page.goto("https://www.instagram.com/", wait_until="networkidle")
            time.sleep(4)

        # If Instagram redirected to login page, re-authenticate automatically
        user_login_field = page.locator("input[name='username']").first
        if user_login_field.is_visible():
            log(f"🔑 Logged out after registration. Auto-logging in as {username}...")
            type_human(page, user_login_field, username)
            pass_login_field = page.locator("input[name='password']").first
            type_human(page, pass_login_field, password)
            page.locator("button[type='submit']").click()
            time.sleep(6)

        # --- AUTOMATED 2FA ACTIVATION PHASE ---
        log("🔐 Configuring structural App-Based Two-Factor Authentication...")
        two_fa_seed = "NOT_CONFIGURED"
        try:
            page.goto("https://accountscenter.instagram.com/password_and_security", wait_until="networkidle")
            time.sleep(4)
            
            two_fa_link = page.locator("a[href*='two_factor'], [role='link']:has-text('Two-factor authentication'), text=/Two-factor authentication/i").first
            if two_fa_link.is_visible(timeout=8000):
                two_fa_link.click()
                time.sleep(3)
                
                user_item = page.locator(f"text={username}, [role='button']:has-text('{username}')").first
                if user_item.is_visible(timeout=5000):
                    user_item.click()
                    time.sleep(3)
                    
                auth_app_btn = page.locator("text=/Authentication app/i, [role='button']:has-text('Authentication app')").first
                if auth_app_btn.is_visible(timeout=5000):
                    auth_app_btn.click()
                    time.sleep(2)
                    page.locator("button:has-text('Next')").first.click()
                    time.sleep(3)
                    
                    secret_element = page.locator("div[role='dialog'] text=/^[A-Z0-9]{32}$/").first
                    if not secret_element.is_visible():
                        secret_element = page.locator("span:has-text('Copy Key')").locator("xpath=../preceding-sibling::div").first
                        
                    if secret_element.is_visible():
                        two_fa_seed = secret_element.inner_text().replace(" ", "")
                        log(f"🔑 Found 2FA Seed: {two_fa_seed}")
                        
                        totp = pyotp.TOTP(two_fa_seed)
                        live_token = totp.now()
                        
                        page.locator("button:has-text('Next')").first.click()
                        time.sleep(2)
                        token_field = page.locator("input[type='text']").first
                        type_human(page, token_field, live_token)
                        page.locator("button:has-text('Next')").first.click()
                        time.sleep(4)
                        done_btn = page.locator("button:has-text('Done')").first
                        if done_btn.is_visible():
                            done_btn.click()
                        log("✅ 2FA setup completed successfully!")
            else:
                log("ℹ️ 2FA section not immediately visible in Accounts Center.")
        except Exception as twofa_err:
            log(f"⚠️ 2FA configuration note: {twofa_err}")

        # --- PROFILE PHOTO UPLOAD PHASE ---
        try:
            log("📸 Navigating to profile dashboard to upload avatar picture...")
            page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            time.sleep(4)

            file_input_avatar = page.locator("input[type='file']").first
            if file_input_avatar.is_visible() or file_input_avatar.count() > 0:
                log(f"🖼️ Uploading avatar: {avatar_path}")
                file_input_avatar.set_input_files(avatar_path)
                time.sleep(6)
        except Exception as avatar_err:
            log(f"⚠️ Avatar upload note: {avatar_err}")

        # --- FIRST POST CREATION PHASE ---
        try:
            log("➕ Initiating new post creation...")
            create_btn = page.locator("span:has-text('Create'), svg[aria-label='New post']").first
            if create_btn.is_visible(timeout=5000):
                create_btn.click()
                time.sleep(3)

                file_input_post = page.locator("input[type='file']").first
                log(f"📤 Uploading post content: {post_path}")
                file_input_post.set_input_files(post_path)
                time.sleep(3)

                page.locator("button:has-text('Next')").first.click()
                time.sleep(2)
                page.locator("button:has-text('Next')").first.click()
                time.sleep(2)

                selected_quote = random.choice(INSTAGRAM_QUOTES)
                caption_text = f"{selected_quote} #{username}"
                
                log(f"📝 Writing caption: '{caption_text}'")
                caption_div = page.locator("div[aria-label='Write a caption...']").first
                type_human(page, caption_div, caption_text)
                time.sleep(2)

                log("🚀 Publishing post...")
                page.locator("button:has-text('Share')").first.click()
                time.sleep(10)
        except Exception as post_err:
            log(f"⚠️ Post creation note: {post_err}")

        # --- PROFESSIONAL BUSINESS ACCOUNT CONVERSION PHASE ---
        try:
            log("💼 Converting to Professional Business Profile...")
            page.goto("https://www.instagram.com/accounts/edit/", wait_until="networkidle")
            time.sleep(4)
            
            switch_btn = page.locator("span:has-text('Switch to professional account'), text=Switch to Professional Account").first
            if switch_btn.is_visible(timeout=5000):
                switch_btn.click()
                time.sleep(3)
                
                page.locator("input[value='business']").first.click()
                page.locator("button:has-text('Next')").first.click()
                time.sleep(2)
                page.locator("button:has-text('Next')").first.click()
                time.sleep(2)
                
                page.locator("select").first.select_option(label="Entrepreneur")
                page.locator("button:has-text('Save')").first.click()
                time.sleep(4)
                skip_fb_btn = page.locator("button:has-text('Don\'t Connect to Facebook'), span:has-text('Skip')").first
                if skip_fb_btn.is_visible():
                    skip_fb_btn.click()
                time.sleep(3)
                log("✅ Account conversion complete!")
        except Exception as bus_err:
            log(f"⚠️ Business profile note: {bus_err}")

        # --- SAVE DATABASE RECORDS ---
        csv_path = os.path.join(BASE_DIR, "instagram_accounts.csv")
        file_exists = os.path.exists(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if not file_exists:
                writer.writerow(["Email", "Username", "Password", "2FA Seed", "Created At"])
            writer.writerow([email_address, username, password, two_fa_seed, time.strftime("%Y-%m-%d %H:%M:%S")])
            
        log(f"✨ Account {username} ({email_address}) successfully created and saved to {csv_path}!")
        try:
            browser.close()
        except:
            pass

if __name__ == "__main__":
    for i in range(1):
        try:
            register_account()
        except Exception as global_err:
            log(f"❌ Automation error: {global_err}")
            time.sleep(5)
