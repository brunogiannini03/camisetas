from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import os
import time
from urllib.parse import urlparse
import base64
import json

# ====================== Configuration ======================

# Path to ChromeDriver
CHROMEDRIVER_PATH = r"./chromedriver.exe"  # Update this path if necessary

# Directory to save downloaded stickers
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'stickers')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Define an absolute path for user data to persist session
USER_DATA_DIR = os.path.abspath("User_Data_Selenium")

# WhatsApp Web URL
WA_WEB_URL = 'https://web.whatsapp.com/'

# Time to wait between checks (in seconds)
CHECK_INTERVAL = 10

# Path to the JSON file tracking processed senders
PROCESSED_SENDERS_FILE = os.path.join(os.getcwd(), 'processed_senders.json')

# ====================== Initialize Processed Senders Log ======================

def load_processed_senders(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

def save_processed_senders(file_path, senders_dict):
    with open(file_path, 'w') as file:
        json.dump(senders_dict, file)

processed_senders = load_processed_senders(PROCESSED_SENDERS_FILE)

# ====================== Setup Chrome Options ======================

chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={USER_DATA_DIR}")  # Use absolute path for persistence
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--start-maximized")  # Open browser in maximized mode
# chrome_options.add_argument("--headless")  # Uncomment to run in headless mode (no UI)
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-popup-blocking")
# Prevent DevToolsActivePort error
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

# Initialize Chrome service
chrome_service = ChromeService(executable_path=CHROMEDRIVER_PATH)

# ====================== Initialize WebDriver ======================

try:
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    print("ChromeDriver initiated successfully.")
except Exception as e:
    print(f"Failed to initiate ChromeDriver: {e}")
    exit()

# ====================== Open WhatsApp Web ======================

driver.get(WA_WEB_URL)

# ====================== Wait for User to Scan QR Code ======================

print("Please scan the QR code to log in to WhatsApp Web.")
try:
    # Wait until the search box is visible, indicating successful login
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    print("Logged in successfully!")
except Exception as e:
    print(f"Timeout waiting for QR code scan: {e}")
    driver.quit()
    exit()

# ====================== Helper Function to Download Stickers ======================

def download_sticker(url, download_path):
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
                # Extract base64 data
                header, encoded = data_url.split(',', 1)
                binary_data = base64.b64decode(encoded)
                # Generate filename
                filename = f"sticker_{int(time.time())}.webp"
                file_full_path = os.path.join(download_path, filename)
                # Save the binary data as a file
                with open(file_full_path, 'wb') as file:
                    file.write(binary_data)
                print(f"Sticker downloaded: {filename}")
                return filename
            else:
                print(f"Failed to retrieve blob data from {url}")
                return None
        else:
            # Handle regular URLs
            response = requests.get(url)
            if response.status_code == 200:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                if not filename:
                    filename = f"sticker_{int(time.time())}.webp"
                else:
                    filename = f"{int(time.time())}_{filename}"
                file_full_path = os.path.join(download_path, filename)
                with open(file_full_path, 'wb') as file:
                    file.write(response.content)
                print(f"Sticker downloaded: {filename}")
                return filename
            else:
                print(f"Failed to download sticker from {url} - Status Code: {response.status_code}")
                return None
    except Exception as e:
        print(f"Error downloading sticker from {url}: {e}")
        return None

# ====================== Helper Function to Send Stickers ======================

def send_sticker_back(sender_name, sticker_path):
    try:
        # Click on the search box
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.clear()
        search_box.send_keys(sender_name)
        time.sleep(2)  # Wait for search results to populate
        
        # Click on the chat with the sender
        chat = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{sender_name}"]'))
        )
        chat.click()
        time.sleep(1)
        
        # Click the attachment button
        attachment_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@title="Attach"]'))
        )
        attachment_button.click()
        time.sleep(1)
        
        # Click the image upload button (input[type="file"])
        image_upload = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]'))
        )
        image_upload.send_keys(sticker_path)
        time.sleep(2)  # Wait for the image to upload
        
        # Click the send button
        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
        )
        send_button.click()
        print(f"Sticker sent back to {sender_name}.")
        
    except Exception as e:
        print(f"Failed to send sticker back to {sender_name}: {e}")

# ====================== Helper Function to Get Current Chat Name ======================

def get_current_chat_name():
    try:
        chat_name_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//header//div[@role="button"]//span[@dir="auto"]'))
        )
        return chat_name_element.get_attribute('title') or chat_name_element.text
    except Exception as e:
        print(f"Failed to retrieve current chat name: {e}")
        return None

# ====================== Helper Function to Get All Text Messages ======================

def get_all_text_messages():
    try:
        # Locate all message bubbles that are text messages
        messages = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in")]//div[@data-testid="conversation-panel-messages"]//span[contains(@class, "_11JPr selectable-text copyable-text")]')
        text_messages = []
        for msg in messages:
            text = msg.text.strip()
            if text:
                text_messages.append(text)
        return text_messages
    except Exception as e:
        print(f"Failed to retrieve text messages: {e}")
        return []

# ====================== Main Monitoring Loop ======================

print("Monitoring incoming messages for stickers and control commands...")

try:
    while True:
        try:
            # Get the current chat's name
            sender_name = get_current_chat_name()
            if not sender_name:
                print("Sender name not found. Skipping this iteration.")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Check for control messages ("0")
            text_messages = get_all_text_messages()
            for message in text_messages:
                if message == "0":
                    # Reset the sender's status
                    if sender_name in processed_senders:
                        processed_senders[sender_name] = False
                        save_processed_senders(PROCESSED_SENDERS_FILE, processed_senders)
                        print(f"Sender '{sender_name}' has been reset and can send one more sticker.")
            
            # Locate all incoming sticker images using the updated class
            sticker_elements = driver.find_elements(By.XPATH, '//img[contains(@class, "_ajxb _ajxj _ajxd")]')
            
            # If no stickers found, continue
            if not sticker_elements:
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Assume the last sticker in the list is the most recent
            latest_sticker = sticker_elements[-1]
            src = latest_sticker.get_attribute('src')
            
            if src:
                # Check if the sender is allowed to have their sticker processed
                if sender_name not in processed_senders or not processed_senders[sender_name]:
                    # Download the sticker
                    filename = download_sticker(src, DOWNLOAD_DIR)
                    if filename:
                        sticker_path = os.path.join(DOWNLOAD_DIR, filename)
                        # Send the sticker back to the sender
                        send_sticker_back(sender_name, sticker_path)
                        # Mark the sender as processed
                        processed_senders[sender_name] = True
                        save_processed_senders(PROCESSED_SENDERS_FILE, processed_senders)
                        print(f"Processed sticker from '{sender_name}'. Further stickers from this sender will be ignored until they send '0'.")
                else:
                    print(f"Already processed sticker from '{sender_name}'. Waiting for control message '0'.")
            
        except Exception as inner_e:
            print(f"Error during sticker processing: {inner_e}")
        
        time.sleep(CHECK_INTERVAL)
        
except KeyboardInterrupt:
    print("Exiting script...")
finally:
    driver.quit()
