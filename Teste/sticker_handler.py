# sticker_handler.py

import sys
import os
import time
import base64
import requests
from PIL import Image  # Importing PIL for image processing
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ====================== Configuration ======================

if len(sys.argv) != 3:
    print("Usage: python sticker_handler.py <sender_name> <sticker_url>")
    sys.exit(1)

sender_name = sys.argv[1]
sticker_url = sys.argv[2]

CHROMEDRIVER_PATH = r"./chromedriver.exe"  # Update if necessary
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'stickers')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
USER_DATA_DIR = os.path.abspath("User_Data_Selenium")
REMOTE_DEBUGGING_PORT = 9222  # Must match in whatsapp_monitor.py

# Base image for overlay
BASE_IMAGE_PATH = os.path.join(os.getcwd(), 'camisetabasica.jpg')
if not os.path.exists(BASE_IMAGE_PATH):
    print(f"Base image '{BASE_IMAGE_PATH}' not found. Please ensure it exists.")
    sys.exit(1)

# ====================== Setup Chrome Options ======================

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{REMOTE_DEBUGGING_PORT}")
chrome_options.add_argument(f"--user-data-dir={USER_DATA_DIR}")  # Ensure same user data
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver connected to existing Chrome instance
service = ChromeService(executable_path=CHROMEDRIVER_PATH)
try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
except Exception as e:
    print(f"Failed to connect to Chrome instance: {e}")
    sys.exit(1)

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
                filename = f"sticker_{int(time.time())}.png"
                with open(os.path.join(path, filename), 'wb') as f:
                    f.write(binary_data)
                print(f"Sticker downloaded: {filename}")
                return os.path.join(path, filename)
            else:
                print("Failed to retrieve blob data.")
                return None
        else:
            # Handle regular URLs
            response = requests.get(url)
            if response.status_code == 200:
                parsed = requests.utils.urlparse(url)
                filename = os.path.basename(parsed.path) or f"sticker_{int(time.time())}.png"
                filename = f"{int(time.time())}_{filename}"
                filepath = os.path.join(path, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"Sticker downloaded: {filename}")
                return filepath
            else:
                print(f"Failed to download sticker. Status Code: {response.status_code}")
                return None
    except Exception as e:
        print(f"Download error: {e}")
        return None

def edit_sticker(base_image_path, overlay_image_path, output_image_path):
    try:
        # Open the base and overlay images
        base_image = Image.open(base_image_path).convert("RGBA")
        overlay_image = Image.open(overlay_image_path).convert("RGBA")

        # Get dimensions
        base_width, base_height = base_image.size
        overlay_width, overlay_height = overlay_image.size

        # Resize the overlay image to 80% of its original size
        new_size = (int(overlay_width * 0.5), int(overlay_height * 0.5))
        overlay_image = overlay_image.resize(new_size, Image.LANCZOS)

        # Get new dimensions after resizing
        overlay_width, overlay_height = overlay_image.size

        # Calculate position to center the overlay
        position = (
            (base_width - overlay_width) // 2,
            (base_height - overlay_height) // 2
        )

        # Paste the overlay image onto the base image with transparency
        base_image.paste(overlay_image, position, overlay_image)

        # Save the result in WEBP format to ensure compatibility with WhatsApp stickers
        base_image.save(output_image_path, 'WEBP')
        print(f"Edited sticker saved as: {output_image_path}")
        return output_image_path
    except Exception as e:
        print(f"Image editing error: {e}")
        return None

def send_sticker(sender, sticker_path):
    try:
        # Search for the sender's chat
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.clear()
        search_box.send_keys(sender)
        time.sleep(2)  # Wait for search results

        # Click on the sender's chat
        try:
            chat = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//span[@title="{sender}"]'))
            )
            chat.click()
            print(f"Opened chat with {sender}.")
        except:
            print(f"Chat with {sender} not found.")
            return

        time.sleep(1)

        # Click the attachment button
        try:
            attach_btn = driver.find_element(By.XPATH, '//div[@title="Attach"]')
            attach_btn.click()
            print("Clicked attachment button.")
        except:
            print("Attachment button not found.")
            return

        time.sleep(1)

        # Upload the edited sticker
        try:
            image_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]'))
            )
            image_input.send_keys(sticker_path)
            print(f"Uploaded edited sticker from {sticker_path}.")
        except:
            print("Image upload input not found.")
            return

        time.sleep(2)  # Wait for upload

        # Click the send button
        try:
            send_btn = driver.find_element(By.XPATH, '//span[@data-icon="send"]')
            send_btn.click()
            print(f"Edited sticker sent back to {sender}.")
        except:
            print("Send button not found.")

    except Exception as e:
        print(f"Send error: {e}")

# ====================== Execution ======================

print(f"Handling sticker from {sender_name}...")

# Step 1: Download the sticker
downloaded_sticker_path = download_sticker(sticker_url, DOWNLOAD_DIR)

if downloaded_sticker_path:
    # Step 2: Edit the sticker by overlaying it onto the base image
    edited_sticker_path = os.path.join(DOWNLOAD_DIR, f"edited_{os.path.basename(downloaded_sticker_path)}")
    result_sticker_path = edit_sticker(BASE_IMAGE_PATH, downloaded_sticker_path, edited_sticker_path)

    if result_sticker_path:
        # Step 3: Send the edited sticker back to the sender
        send_sticker(sender_name, result_sticker_path)
    else:
        print("Failed to edit the sticker. Cannot send back.")
else:
    print("Sticker download failed. Cannot proceed with editing and sending.")

# Do NOT close the browser to maintain the session
# driver.quit()
