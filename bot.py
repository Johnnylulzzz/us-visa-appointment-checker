import io 

from selenium import webdriver
from datetime import datetime, timedelta
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, UnexpectedAlertPresentException

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import Select
import random
from selenium.webdriver.common.action_chains import ActionChains
import smtplib
from email.mime.text import MIMEText
from fake_useragent import UserAgent
import os 
from dotenv import load_dotenv
import logging
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import base64
import uuid

from PIL import Image
from openai import OpenAI
from seleniumbase import Driver


"""
Will need 2 things:
1.  OPEN AI API to automate captcha solving, 
    Tried a lot with free stuff but did not work, 
    Even tried with GOOGLE-CLOUD-VISION API
    or you can just manually solve the captcha.

2.  For Email Alert you can use sendgrid if you prefer, 
    I just rolled with smtplib 
    (Need to create an APP Password in google account manager)

    """

"""
Your .env file could look something like this:

EMAIL_USER = youremail@email.com
EMAIL_PASS = xxxx xxxx xxxx xxxx  (Yes, it works with spaces)
OPENAI_API_KEY = YOUR_API_KEY

"""


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


#Appointment Site
target_site = os.getenv("SITE_URL") 

# User credentials
user_name = os.getenv("USER_NAME")
user_passwd = os.getenv("USER_PASS") 



#Can be replaced as per each application can be turned into user input as well
secure_ans1 = os.getenv("SECURE_ANS1") 
secure_ans2 = os.getenv("SECURE_ANS2") 
secure_ans3 = os.getenv("SECURE_ANS3") 

#These KBA fields are dynamic and can be changed as per application
#So if user used different security questions then you gotta check the divs for this and change the fields accordingly
answer_fields = {
    "kba1_response": secure_ans1,
    "kba2_response": secure_ans2,
    "kba3_response": secure_ans3,
}



# Location IDs for different VACs
newdelhi_vac = "4a6bf614-b0db-ec11-a7b4-001dd80234f6"
mumbai_vac = "486bf614-b0db-ec11-a7b4-001dd80234f6"
kolkata_vac = "466bf614-b0db-ec11-a7b4-001dd80234f6"
hyderabad_vac = "436bf614-b0db-ec11-a7b4-001dd80234f6"
chennai_vac = "3f6bf614-b0db-ec11-a7b4-001dd80234f6"

# List of location(s) to check for slots
# To check for multiple location create a list of locations and loop through them
location = newdelhi_vac

today = datetime.today()
next_30_days = today + timedelta(days=55) #it searches for slot for next 35 days, in current two month panels


##############################
### RANDOM DELAY Functions ###
def random_delay():
    """Introduce a random delay before scanning again."""
    delay = random.uniform(30, 60)  
    print(f"⏳ Waiting {delay:.2f} seconds before next scan...")
    time.sleep(delay)

def human_delay():
    time.sleep(random.uniform(2, 7))

#Yo why dont we type like human?
def human_typing(element, text):
    """Types text character by character with random delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))

def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)

def little_delay(min_seconds=0.5, max_seconds=1.0):
    """Random delay to mimic human timing."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def move_to_element(driver, element):
    """Simulate human-like mouse movement to an element."""
    actions = ActionChains(driver)
    actions.move_to_element(element).pause(random.uniform(0.2, 0.8)).perform()
    little_delay()

def safe_click(driver, element):
    """Safely click an element with human-like behavior."""
    move_to_element(driver, element)  # Move mouse first
    actions = ActionChains(driver)
    actions.click(element).perform()  # Use ActionChains for click
    


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

client = OpenAI()


#Login with error exception
def user_login():
    
    while True:
        try:
            driver.get(target_site)
            print(driver.title)  

            WebDriverWait(driver, 200).until(EC.presence_of_element_located((By.ID, "signInName")))
            print("Page loaded successfully.")

            #human_like_interaction()

            # Enter Username
            username_field = WebDriverWait(driver, 1000).until(
                EC.presence_of_element_located((By.ID, "signInName"))
            )
            actions.move_to_element(username_field).perform()
            human_typing(username_field, user_name)
            print("Username entered successfully.")
            human_delay()

            # Enter Password
            userpasswd_field = WebDriverWait(driver, 1000).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            actions.move_to_element(userpasswd_field).perform()
            human_typing(userpasswd_field, user_passwd)
            print("Password entered successfully.")

            # Wait for the captcha image to appear (adjust the ID or locator as needed)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "captchaImage"))
            )

            # Wait until the image is fully loaded
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.getElementById('captchaImage').complete")
            )

            # JavaScript to capture the image via canvas
            script = """
                const img = document.getElementById('captchaImage');
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                return canvas.toDataURL('image/png');
            """
            data_url = driver.execute_script(script)

            if data_url is None:
                raise Exception("Image not fully loaded or not found.")

            # Decode and save the image
            ranImgname = f"captcha_{uuid.uuid4().hex}.png"
            base64_string = data_url.split(",")[1]
            image_bytes = base64.b64decode(base64_string)
            with open(ranImgname, "wb") as f:
                f.write(image_bytes)
            print(f"Captcha image saved as {ranImgname}")

            image_path = ranImgname

            # Getting the Base64 string
            base64_image = encode_image(image_path)

            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            { "type": "text", "text": "Extract and return only the 5 alphanumeric characters present in the given image without any additional text, formatting, or explanation." },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
            )

            captcha_ans = completion.choices[0].message.content
            
            capansw_field = WebDriverWait(driver, 1000).until(
                EC.presence_of_element_located((By.ID, "extension_atlasCaptchaResponse"))
            )
            actions.move_to_element(capansw_field).perform()
            human_typing(capansw_field, captcha_ans)
            print("captcha entered successfully.")
            human_delay()
        
            loginConButton = WebDriverWait(driver, 200).until(
            EC.element_to_be_clickable((By.ID, "continue"))
            )
            actions.move_to_element(loginConButton).perform()
            human_delay()
            safe_click(driver, loginConButton)
            print("Continue button clicked successfully.")

            # Verify login success (wait for security questions to appear)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[id^='kba']"))
            )
            
            print("Login successful!")
            return True
        
        except Exception as e:
            print(f"Failed to login: {e}")
            driver.quit()  #You dont really need to quit the browse, you can also do driver.refresh()
            main()  # Restart the process

######################################################################################################
####################################### Security Question function ###################################
def sec_questions():
 # Loop through the dictionary and attempt to fill each field
    for field_id, answer in answer_fields.items():
        try:
            # Check if the field is present and visible
            
            answer_field = WebDriverWait(driver,10).until(
                EC.presence_of_element_located((By.ID, field_id))
            )
            print(answer_field)
            if answer_field.is_enabled():
                
                actions.move_to_element(answer_field).perform()
                
                answer_field.click()
                human_delay()
                human_typing(answer_field, answer)
                print(f"Answered question for {field_id}")
            else: 
                print(f"Field {field_id} is not enabled")

        except Exception as e:
            print(f"Failed to fill {field_id}: {e}")
            continue  # Move to the next field if this one is not visible

        # Click on the Continue button
    try:
        human_delay()
        continue_button = WebDriverWait(driver, 200).until(
        EC.element_to_be_clickable((By.ID, "continue"))
        )
        actions.move_to_element(continue_button).perform()
        human_delay()
        safe_click(driver, continue_button)
        print("Continue button clicked successfully.")
        WebDriverWait(driver, 200).until(
            EC.presence_of_element_located((By.ID, "continue_application"))
        )
        return True

        
    except Exception as e:
        print(f"Failed to click Continue button: {e}")
        return False



######################################################################################################
####################################### Schedule button click ########################################
def schedule_butt():
    try:
        
        schedule_link = WebDriverWait(driver, 200).until(
            EC.visibility_of_element_located((By.ID, "reschedule_appointment")) #can be replaced with "continue_application" if new application
        )
        human_delay()
        safe_click(driver, schedule_link)
        print("Schedule Appointment link clicked successfully.")

        return True
    
    except Exception as e:
        print(f"Failed in schedule_butt function: {e}")
        return False


######################################################################################################
######################################## Email Alert for slots #######################################
def send_alert(message):
    """Send an instant email alert when a slot is found."""
    sender_email = EMAIL_USER  # Replace with your email
    receiver_email = "travelhubkkr@gmail.com"  # Replace with recipient email
    password = EMAIL_PASS  # Use an app password for Gmail 
    
    msg = MIMEText(message)
    msg["Subject"] = "🚨 Visa Slot Found!"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("📩 Email notification sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")


######################################################################################################
######################################## Slot Checker Function #######################################
def check_slots():
    counter = 0
    THRESHOLD = 40

    while True:
        try:
            driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            wait = WebDriverWait(driver, 200)

            dropdown = wait.until(EC.visibility_of_element_located((By.ID, "post_select")))
            actions.move_to_element(dropdown)
            select_vac = Select(dropdown)
            select_vac.select_by_index(0)
            print("Resetting dropdown selection.")
            human_delay()

            wait.until(lambda d: any(option.get_attribute("value") == location for option in select_vac.options))
            select_vac.select_by_value(location)
            print(f"Selected location {location} successfully.")

            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-group")))
            available_slots = []
            month_panels = driver.find_elements(By.CLASS_NAME, "ui-datepicker-group")
            for panel in month_panels:
                panel_slots = panel.find_elements(By.CLASS_NAME, "greenday")
                available_slots.extend(panel_slots)

            sorted_slots = []
            for slot in available_slots:
                try:
                    day = int(slot.text)
                except Exception as conv_err:
                    print(f"Couldn't convert slot text to int: {conv_err}")
                    continue
                month = int(slot.get_attribute("data-month")) + 1
                year = int(slot.get_attribute("data-year"))
                slot_date = datetime(year, month, day)
                if today <= slot_date <= next_30_days:
                    sorted_slots.append((slot_date, slot))

            if not sorted_slots:
                counter += 1
                print("No valid slot found. Skipping booking and retrying...")
                print(f"Counter: {counter}")
                if counter >= THRESHOLD:
                    try:
                        human_delay()
                        visa_home_link = wait.until(EC.element_to_be_clickable(
                            (By.XPATH, '//a[@title="Visa Application Home"]')
                        ))
                        safe_click(driver, visa_home_link)
                        print("Clicked Visa Application Home.")
                        schedule_butt()
                        print("Navigation complete. Resetting counter.")
                    except Exception as nav_err:
                        print(f"Failed to navigate home: {nav_err}")
                    counter = 0
                random_delay()
                continue

            else:
                sorted_slots.sort(key=lambda x: x[0])
                selected_date, selected_slot = sorted_slots[0]
                print(f"Attempting to click first available slot: {selected_date.strftime('%d-%m-%Y')}")
                slot_link = selected_slot.find_element(By.TAG_NAME, "a")
                wait.until(EC.element_to_be_clickable(slot_link))
                safe_click(driver, slot_link)

                wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='schedule-entries' and @onclick='onSelectScheduleEntry(this)']")))
                print("Found appointment times and clicking on it now")

                radio_xpath = "//input[@type='radio' and @name='schedule-entries' and @onclick='onSelectScheduleEntry(this)']"
                time_slots = driver.find_elements(By.XPATH, radio_xpath)
                if not time_slots:
                    print("No appointment radio buttons found after selecting date.")
                    continue

                best_slot = max(time_slots, key=lambda el: int(el.get_attribute("data-slots") or 0))
                safe_click(driver, best_slot)
                print("clicked on the best available slot")

                time.sleep(1)
                submit_button = wait.until(EC.element_to_be_clickable((By.ID, "submitbtn")))
                safe_click(driver, submit_button)
                print("Submitted appointment selection. Waiting for response...")
                
                print("Waiting 5 seconds to monitor post-submit behavior...")
                time.sleep(5)

                # Check URL change
                current_url = driver.current_url
                print(f"Current URL after submit: {current_url}")

                # Capture any alerts (silent or blocking)
                try:
                    alert = driver.switch_to.alert
                    print(f"⚠️ JS Alert appeared: {alert.text}")
                    alert.accept()
                except:
                    print("No blocking alert present.")

                # Print page source or key content block
                print("🔍 Page snapshot:")
                print(driver.page_source[:1000])  # Trim to avoid flooding
                
                """
                try:
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//div[contains(@class, 'alert-danger') and contains(text(), 'no longer available')]")
                        )
                    )
                    print("Alert received: Appointment time not available, will retry...")
                    send_alert("Appointment time not available.")
                    continue
                except TimeoutException:
                    print("Time slot accepted!")
                    send_alert("Appointment booked!")
                    input("Press Enter once you've completed any required manual steps...")
                    return

                """
       

        except Exception as e:
            print(f"Slot check failed: {e}")
            time.sleep(5)
            input("Something went wrong ")
            

            
        


def main():
    global driver, actions

    ua = UserAgent()
    randome_user_agent = ua.random
    print("random user agent used: ", randome_user_agent)

    profile_id = uuid.uuid4().hex
    profile_dir = os.path.abspath(f"./profiles/profile_{profile_id}")
    os.makedirs(profile_dir, exist_ok=True)



    driver = Driver(
        browser="chrome",
        uc=True,
        user_data_dir=profile_dir,
        incognito=True,
        headless=False,
        agent=randome_user_agent,
    )

    # Stealth patches
    driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            window.chrome = undefined;
            delete navigator.__proto__.webdriver;
        """
    })

    actions = ActionChains(driver)

    start_time = datetime.now()
    try:
        print("Script started")
        if user_login():
            message = "script started"
            send_alert(message)
            print("Login successful. Proceeding to security questions...")
            if sec_questions():
                print("Security questions completed. Proceeding to schedule...")
                if schedule_butt():
                    print("Schedule Button steps completed!")
                    if check_slots():
                        print("Location selected successfully!")
                    else:
                        print("Failed at location selection step. Process halted.")
                else:
                    print("Failed at scheduling step. Process halted.")
            else:
                print("Failed at security questions step. Process halted.")
        else:
            print("Failed at login step. Process halted.")
    except Exception as e:
        print(f"Critical error: {str(e)}")
    finally:
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        print(f"Script finished. Total execution time: {elapsed_time}")


        



main()

