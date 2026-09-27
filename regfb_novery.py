import random
from selenium.webdriver.support.ui import Select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import requests
import time,re

def checkuid(cookie_string):
    headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'vi-VN,vi;q=0.9',
    'dpr': '1',
    'priority': 'u=0, i',
    'sec-ch-prefers-color-scheme': 'light',
    'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-full-version-list': '"Google Chrome";v="137.0.7151.69", "Chromium";v="137.0.7151.69", "Not/A)Brand";v="24.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"10.0.0"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'viewport-width': '821',
    'cookie': cookie_string,
    }
    params = ''
    response = requests.get('https://www.facebook.com/confirmemail.php', params=params, headers=headers).text
    print(response)
    pattern = r'"ACCOUNT_ID":\s*"(.*?)"\s*'

    # Find the match
    match = re.search(pattern, response)

    # Extract and print the ACCOUNT_ID
    if match:
        account_id = match.group(1)  # Gets "12345"
        print(f"ACCOUNT_ID: {account_id}")
        return account_id
    else:
        print("No ACCOUNT_ID found")
        return account_id

def search_google(args):
    thread_id, num_accounts = args

    for _ in range(num_accounts):
        driver = None
        try:
            # Hardcoded list of user-agents
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
            ]
            user_agent = random.choice(user_agents)

            chrome_options = Options()
            chrome_options.add_argument(f"user-agent={user_agent}")
            x_pos = thread_id * 320
            chrome_options.add_argument("--window-size=300,800")
            chrome_options.add_argument(f"--window-position={x_pos},0")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            # Use webdriver-manager to handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            if "chrome://welcome" in driver.current_url or "chrome://profile" in driver.current_url:
                driver.quit()
                continue

            driver.execute_script("""
                let blocker = document.querySelector('.overlay');
                if (blocker) blocker.remove();
            """)

            ho_list = ["Nguyễn", "Trần", "Lê", "Phạm", "Huỳnh", "Hoàng", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
            ten_list = ["Nam", "Long", "Huy", "Tuấn", "Khoa", "Tài", "Duy", "Sơn", "Phúc", "Trí", "Linh", "Trang", "Lan", "Hương", "Nhung", "Mai", "Yến", "Thảo", "Vy", "Ngân"]

            ho = random.choice(ho_list)
            ten = random.choice(ten_list)

            driver.get("https://m.facebook.com/reg/")
            time.sleep(random.uniform(1, 3))

            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for idx, button in enumerate(buttons):
                    try:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text.strip()
                            print(f"Luồng {thread_id}: Click button #{idx + 1} - Nội dung: {button_text}")
                            button.click()
                            time.sleep(1)
                    except Exception as inner_e:
                        print(f"Luồng {thread_id}: Lỗi khi click button #{idx + 1}: {inner_e}")
            except Exception as outer_e:
                print(f"Luồng {thread_id}: Lỗi khi quét các button: {outer_e}")

            driver.find_element(By.NAME, 'lastname').send_keys(ten)
            driver.find_element(By.NAME, 'firstname').send_keys(ho)
            time.sleep(random.uniform(1, 3))

            select_day = Select(driver.find_element(By.ID, "day"))
            random_day = random.choice([opt.get_attribute("value") for opt in select_day.options])
            select_day.select_by_value(random_day)

            select_month = Select(driver.find_element(By.ID, "month"))
            random_month = random.choice([opt.get_attribute("value") for opt in select_month.options])
            select_month.select_by_value(random_month)

            select_year = Select(driver.find_element(By.ID, "year"))
            random_year = random.choice([str(y) for y in range(2004, 1953, -1)])
            select_year.select_by_value(random_year)

            random_value = random.choice(["1", "2"])
            try:
                gender_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f"input[name='sex'][value='{random_value}']"))
                )
                gender_input.click()
            except Exception as e:
                print(f"Luồng {thread_id}: Không thể click input giới tính: {str(e)}")

            random_number = '093' + str(random.randint(1000000, 9999999))
            passss = 'Hoanghuy6456@@'
            driver.find_element(By.NAME, 'reg_email__').send_keys(random_number)
            driver.find_element(By.NAME, 'reg_passwd__').send_keys(passss)

            try:
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.NAME, 'websubmit'))
                )
                submit_button.click()
            except Exception as e:
                print(f"Luồng {thread_id}: Không thể click button submit: {str(e)}")
            try:
                element=WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Enter the confirmation code from the text message')]"))
                )

                print("Element found!")
            except:
                print('lỗi check bước 1 , nick vẫn có thể sống')

            print('get cookie,id')
            cookies = driver.get_cookies()
            cookie_string = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies) + ";"
            uid=checkuid(cookie_string)
            if uid != 0:
                try:
                    with open('TK.txt', "a") as email:
                        email.write(f"{uid}|{random_number}|{passss}|{cookie_string}\n")
                    print(f"Luồng {thread_id}: Xong")
                except Exception as e:
                    print(f"Luồng {thread_id}: Không tìm thấy element: {e}")
            else:
                print('lỗi tạo rồi')
            driver.quit()
        except Exception as e:
            print(f"Luồng {thread_id}: Lỗi - {e}")
            if driver is not None:
                driver.quit()

def extract_uids():
    try:
        with open('TK.txt', 'r') as tk_file:
            lines = tk_file.readlines()
            uids = [line.split('|')[0] for line in lines if '|' in line]
            with open('uid.txt', 'w') as uid_file:
                for uid in uids:
                    uid_file.write(f"{uid}\n")
            print("UIDs đã được tách và ghi vào uid.txt")
    except Exception as e:
        print(f"Lỗi khi tách UID: {e}")

def main():
    choice = int(input('Chọn chức năng (1: Chạy đăng ký, 2: Tách UID): '))
    if choice == 1:
        num_threads = int(input('SỐ LUỒNG MUỐN CHẠY: '))
        total_accounts = int(input('NHẬP TỔNG SỐ ACC MUỐN REG: '))
        accounts_per_thread = (total_accounts + num_threads - 1) // num_threads  # Divide accounts evenly
        print(f"Running with {num_threads} threads to create {total_accounts} accounts")

        args_list = [(i, accounts_per_thread) for i in range(num_threads)]

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            executor.map(search_google, args_list)
    elif choice == 2:
        extract_uids()
    else:
        print("Lựa chọn không hợp lệ")

if __name__ == "__main__":
    main()