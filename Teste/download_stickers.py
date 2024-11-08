from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from urllib.parse import urlparse
import base64
import requests

# ====================== Configuration ======================

CHROMEDRIVER_PATH = r"./chromedriver.exe"  # Update if necessary
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'stickers')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
USER_DATA_DIR = os.path.abspath("User_Data_Selenium")
WA_WEB_URL = 'https://web.whatsapp.com/'
CHECK_INTERVAL = 10  # seconds

# ====================== Setup Chrome Options ======================

chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

# Initialize WebDriver
service = ChromeService(executable_path=CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

# ====================== Wait for Login ======================

driver.get(WA_WEB_URL)
print("Please scan the QR code to log in to WhatsApp Web.")

try:
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    print("Logged in successfully!")
except:
    print("Failed to log in.")
    driver.quit()
    exit()

# ====================== Helper Functions ======================

def download_sticker(url, path):
    try:
        if url.startswith('blob:'):
            # Handle blob URLs by extracting base64 data via JavaScript
            data_url = driver.execute_async_script("""
                const blobUrl = arguments[0];
                const callback = arguments[1];
                fetch(blobUrl)
                    .then(response => response.blob())
                    .then(blob => {
                        const reader = new FileReader();
                        reader.onloadend = () => callback(reader.result);
                        reader.readAsDataURL(blob);
                    })
                    .catch(() => callback(null));
            """, url)
            if data_url:
                _, encoded = data_url.split(',', 1)
                binary_data = base64.b64decode(encoded)
                filename = f"sticker_{int(time.time())}.webp"
                with open(os.path.join(path, filename), 'wb') as f:
                    f.write(binary_data)
                print(f"Sticker downloaded: {filename}")
                return filename
        else:
            # Handle regular URLs
            response = requests.get(url)
            if response.status_code == 200:
                parsed = urlparse(url)
                filename = os.path.basename(parsed.path) or f"sticker_{int(time.time())}.webp"
                filename = f"{int(time.time())}_{filename}"
                with open(os.path.join(path, filename), 'wb') as f:
                    f.write(response.content)
                print(f"Sticker downloaded: {filename}")
                return filename
    except Exception as e:
        print(f"Download error: {e}")
    return None

def send_sticker(sender, sticker_path):
    try:
        # Click on the search box
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.clear()
        search_box.send_keys(sender)
        time.sleep(2)
        
        # Click on the chat with the sender
        chat = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{sender}"]'))
        )
        chat.click()
        time.sleep(1)
        
        # Click the attachment button
        attach = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@title="Attach"]'))
        )
        attach.click()
        time.sleep(1)
        
        # Click the image upload button and send the sticker
        image = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]'))
        )
        image.send_keys(sticker_path)
        time.sleep(2)
        
        # Click the send button
        send_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
        )
        send_btn.click()
        print(f"Sticker sent back to {sender}.")
    except Exception as e:
        print(f"Send error: {e}")

def get_sender():
    try:
        header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//header//div[@role="button"]//span[@dir="auto"]'))
        )
        return header.get_attribute('title') or header.text
    except:
        return None

def get_latest_message():
    try:
        # Locate all message elements (both text and stickers)
        messages = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in")]')
        if not messages:
            return None, None
        
        latest_message = messages[-1]
        
        # Check if the latest message contains an image (sticker)
        try:
            sticker = latest_message.find_element(By.XPATH, './/img')
            return "sticker", sticker.get_attribute('src')
        except:
            pass
        
        # If not a sticker, get the text content
        try:
            text = latest_message.find_element(By.XPATH, './/span[@class="_ao3e selectable-text copyable-text"]').text.strip()
            return "text", text
        except:
            return None, None
    except:
        return None, None

# ====================== Main Loop ======================

processed_senders = set()

print("Monitoring for new stickers...")

try:
    while True:
        sender = get_sender()
        if not sender:
            time.sleep(CHECK_INTERVAL)
            continue

        msg_type, content = get_latest_message()
        
        if msg_type == "text" and content == "0":
            if sender in processed_senders:
                processed_senders.remove(sender)
                print(f"Reset received from {sender}. They can send a new sticker now.")
            time.sleep(CHECK_INTERVAL)
            continue

        if msg_type == "sticker" and sender not in processed_senders:
            filename = download_sticker(content, DOWNLOAD_DIR)
            if filename:
                sticker_path = os.path.join(DOWNLOAD_DIR, filename)
                send_sticker(sender, sticker_path)
                processed_senders.add(sender)
                print(f"Processed sticker from {sender}. Awaiting reset command ('0').")
        
        time.sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("Script terminated by user.")
finally:
    driver.quit()
