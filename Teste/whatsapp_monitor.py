# whatsapp_monitor.py

import subprocess
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ====================== Configuration ======================

CHROMEDRIVER_PATH = r"./chromedriver.exe"  # Update this path if necessary
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'stickers')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
USER_DATA_DIR = os.path.abspath("User_Data_Selenium")
WA_WEB_URL = 'https://web.whatsapp.com/'
CHECK_INTERVAL = 10  # seconds
REMOTE_DEBUGGING_PORT = 9222  # Must match in sticker_handler.py

# ====================== Setup Chrome Options ======================

chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={USER_DATA_DIR}")  # Persist session
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument(f"--remote-debugging-port={REMOTE_DEBUGGING_PORT}")  # Enable remote debugging
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

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
    print("Failed to log in within the expected time.")
    driver.quit()
    exit()

# ====================== Helper Functions ======================

def download_and_send(sender, sticker_url):
    try:
        # Invoke the sticker_handler.py script with sender and sticker_url as arguments
        subprocess.Popen(['python', 'sticker_handler.py', sender, sticker_url])
        print(f"Invoked sticker_handler for sender: {sender}")
    except Exception as e:
        print(f"Failed to invoke sticker_handler: {e}")

def get_unread_chats():
    """
    Identifies all chats with unread messages by locating the green notification elements.
    Returns a list of sender names.
    """
    try:
        # Find all spans with aria-label containing 'unread message'
        notification_elements = driver.find_elements(By.XPATH, '//span[contains(@aria-label,"unread message")]')
        senders = []
        for notif in notification_elements:
            # Navigate up the DOM to find the chat title
            try:
                # Traverse up to the parent chat element
                parent = notif.find_element(By.XPATH, './../../../../../../..')
                chat_title = parent.find_element(By.XPATH, './/span[@title]').get_attribute('title')
                if chat_title:
                    senders.append(chat_title)
            except:
                continue
        return list(set(senders))  # Remove duplicates
    except Exception as e:
        print(f"Error finding unread chats: {e}")
        return []

def get_latest_message():
    """
    Retrieves the latest message type and content in the currently active chat.
    Returns a tuple (msg_type, content):
        - msg_type: "sticker", "text", or None
        - content: Sticker URL or text content
    """
    try:
        # Locate all incoming message containers
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

def send_text_message(sender, message):
    """
    Sends a text message to the specified sender.
    """
    try:
        # Locate the message input box using the provided XPath
        message_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span/div/div[2]/div[1]/div/div[1]/p'))
        )
        message_box.click()
        time.sleep(1)  # Wait for the input to be focused
        message_box.send_keys(message)
        time.sleep(1)  # Wait before sending
        # Locate and click the send button
        send_button = driver.find_element(By.XPATH, '//span[@data-icon="send"]')
        send_button.click()
        print(f"Sent message to {sender}: {message}")
    except Exception as e:
        print(f"Failed to send message to {sender}: {e}")

# ====================== Define Trigger Messages and Responses ======================

# List of possible trigger messages from senders
trigger_messages = [
    "hello",
    "how are you doing",
    "hello3"
]

# Corresponding responses for each trigger message
responses = [
    "Hello, I am starting your service, please send your sticker",
    "I'm doing well, thank you! How can I assist you today?",
    "Hello there! How can I help you?"
]

# ====================== Main Monitoring Loop ======================

processed_senders = set()
responded_messages = {}  # Dictionary to track which trigger messages have been responded to per sender
open_chats = {}  # Dictionary to track open chats and their statuses

print("Monitoring for new stickers and messages...")

try:
    while True:
        try:
            # 1. Process unread senders
            unread_senders = get_unread_chats()
            
            for sender in unread_senders:
                if sender in processed_senders:
                    continue  # Skip already processed senders unless reset is needed
                
                # Open the sender's chat
                try:
                    chat = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f'//span[@title="{sender}"]'))
                    )
                    chat.click()
                    print(f"Opened chat with {sender}.")
                    open_chats[sender] = True  # Mark chat as open
                except:
                    print(f"Failed to open chat with {sender}.")
                    continue
                
                time.sleep(1)  # Wait for chat to open
                
                # Get the latest message
                msg_type, content = get_latest_message()
                
                # Debugging: Print message type and content
                print(f"Latest message from {sender}: Type={msg_type}, Content='{content}'")
                
                if msg_type == "text":
                    # Check if the message matches any trigger message
                    for idx, trigger in enumerate(trigger_messages):
                        if content.lower() == trigger.lower():
                            # Initialize the set for sender if not present
                            if sender not in responded_messages:
                                responded_messages[sender] = set()
                            
                            # Check if this trigger has already been responded to
                            if trigger.lower() not in responded_messages[sender]:
                                response = responses[idx]
                                send_text_message(sender, response)
                                # Mark this trigger as responded to for the sender
                                responded_messages[sender].add(trigger.lower())
                            else:
                                print(f"Already responded to '{trigger}' from {sender}.")
                            break  # Exit the loop after finding a match
                    else:
                        # If the message is "0" or other text not in trigger_messages
                        if content.lower() == "0":
                            if sender in processed_senders:
                                processed_senders.remove(sender)
                                print(f"Reset received from {sender}. They can send a new sticker now.")
                            else:
                                print(f"Received '0' from {sender}, but they were not in processed_senders.")
                            # Remove any tracked responded message
                            responded_messages.pop(sender, None)
                elif msg_type == "sticker":
                    if sender not in processed_senders:
                        download_and_send(sender, content)
                        processed_senders.add(sender)
                        print(f"Processed sticker from {sender}. Awaiting reset command ('0').")
                        # Remove any tracked responded message
                        responded_messages.pop(sender, None)
                    else:
                        print(f"Sticker from {sender} ignored (already processed).")
                else:
                    print(f"No action taken for message from {sender}.")
                
                # Keep the chat open for this sender to monitor for reset commands
                # Do not close the chat
            
            # 2. Monitor open chats for new messages (like reset commands and additional triggers)
            for sender in list(open_chats.keys()):
                try:
                    # Ensure the chat is still open by checking if the chat window is active
                    active_chat = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, f'//span[@title="{sender}"]'))
                    )
                    # If chat is active, check for new messages
                    msg_type, content = get_latest_message()
                    
                    # Debugging: Print message type and content
                    print(f"Latest message in open chat with {sender}: Type={msg_type}, Content='{content}'")
                    
                    if msg_type == "text":
                        # Check if the message matches any trigger message
                        for idx, trigger in enumerate(trigger_messages):
                            if content.lower() == trigger.lower():
                                # Initialize the set for sender if not present
                                if sender not in responded_messages:
                                    responded_messages[sender] = set()
                                
                                # Check if this trigger has already been responded to
                                if trigger.lower() not in responded_messages[sender]:
                                    response = responses[idx]
                                    send_text_message(sender, response)
                                    # Mark this trigger as responded to for the sender
                                    responded_messages[sender].add(trigger.lower())
                                else:
                                    print(f"Already responded to '{trigger}' from {sender}.")
                                break  # Exit the loop after finding a match
                        else:
                            # If the message is "0" or other text not in trigger_messages
                            if content.lower() == "0":
                                if sender in processed_senders:
                                    processed_senders.remove(sender)
                                    print(f"Reset received from {sender}. They can send a new sticker now.")
                                else:
                                    print(f"Received '0' from {sender}, but they were not in processed_senders.")
                                # Remove any tracked responded message
                                responded_messages.pop(sender, None)
                    elif msg_type == "sticker":
                        if sender not in processed_senders:
                            download_and_send(sender, content)
                            processed_senders.add(sender)
                            print(f"Processed sticker from {sender}. Awaiting reset command ('0').")
                            # Remove any tracked responded message
                            responded_messages.pop(sender, None)
                        else:
                            print(f"Sticker from {sender} ignored (already processed).")
                    else:
                        print(f"No action taken for new message in chat with {sender}.")
                
                except:
                    # If chat is not active, it might have been closed manually; remove from open_chats
                    print(f"Chat with {sender} is no longer open.")
                    del open_chats[sender]
        
        except Exception as inner_e:
            print(f"Error during monitoring loop: {inner_e}")
        
        time.sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("Script terminated by user.")
finally:
    driver.quit()
