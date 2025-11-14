import requests
import os
import sys
import time
import json 
import datetime # 用來抓取時間

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- (V17) 狀態管理函式 (完全不變) ---
def load_previous_cars(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f"成功讀取快取檔案: {filename}")
            return json.load(f)
    except FileNotFoundError:
        print("未找到快取檔案，將建立新的。")
        return {} 
    except json.JSONDecodeError:
        print("快取檔案格式錯誤，將建立新的。")
        return {}

def save_current_cars(cars_dict, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cars_dict, f, ensure_ascii=False, indent=4)
            print(f"成功將目前 {len(cars_dict)} 筆車輛狀態儲存到: {filename}")
    except Exception as e:
        print(f"儲存快取檔案失敗: {e}")

def find_new_cars(current_dict, previous_dict):
    current_ids = set(current_dict.keys())
    previous_ids = set(previous_dict.keys())
    new_car_ids = current_ids - previous_ids
    return [current_dict[car_id] for car_id in new_car_ids]

# --- 爬蟲主函式 (完全不變) ---
def scrape_kia_sportage():
    # (和 V17 一樣，這裡省略 100+ 行的爬蟲程式碼)
    # --- 
    start_url = "https://select.kiatw.com/tw/buy-car.html?vehicle_model=48"
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36")
    chrome_options.add_argument("--start-maximized")
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)
        print(f"--- 階段一：載入 {start_url} 以獲取所有分頁 ---")
        driver.get(start_url)
        page_urls_to_scrape = set()
        page_urls_to_scrape.add(start_url)
        try:
            print("等待頁面載入 (等待 product-item)...")
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-item")))
            print("等待分頁列 'pages-items' 載入...")
            time.sleep(3) 
            pagination_bar = driver.find_element(By.CLASS_NAME, "pages-items")
            page_links = pagination_bar.find_elements(By.TAG_NAME, "a")
            for link in page_links:
                href = link.get_attribute("href")
                if href:
                    page_urls_to_scrape.add(href)
        except NoSuchElementException:
            print("未找到 'pages-items' 分頁列。假設只有一頁。")
        except TimeoutException:
            print("等待 'product-item' 超時。可能此車款目前無車。")
            return {}
        page_list = sorted(list(page_urls_to_scrape))
        print(f"--- 總共找到 {len(page_list)} 個頁面準備爬取 ---")
        master_stock_available = {} 
        for i, page_url in enumerate(page_list):
            print(f"\n--- 正在爬取頁面 {i + 1}/{len(page_list)} ---")
            driver.get(page_url)
            try:
                print("步驟 1: 等待 'product-item'...")
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-item")))
                print("步驟 2: 額外等待 3 秒...")
                time.sleep(3)
                print("步驟 3: 抓取所有 'product-item'...")
                product_items = driver.find_elements(By.CLASS_NAME, "product-item")
                if not product_items:
                    print("       此頁面無 'product-item'，跳過。")
                    continue 
                print("步驟 4: 開始遍歷、抓取所有資訊並分類...")
                for item in product_items:
                    try:
                        overlay = item.find_elements(By.CLASS_NAME, "out-of-stock-overlay")
                        if len(overlay) > 0:
                            continue
                        product_id = f"unknown_id_{time.time()}" 
                        try:
                            price_box = item.find_element(By.CSS_SELECTOR, "div.price-box")
                            product_id = price_box.get_attribute("data-product-id")
                        except NoSuchElementException: pass
                        h3_tag = item.find_element(By.CSS_SELECTOR, "div.product-item-brand h3")
                        h3_text = h3_tag.text.strip()
                        if "sportage" in h3_text.lower():
                            trim_text = ""
                            try:
                                trim_p = item.find_element(By.CSS_SELECTOR, "div.product-item-trim p")
                                trim_text = trim_p.text.strip()
                            except NoSuchElementException: pass 
                            price_text = "N/A"
                            try:
                                price_element = item.find_element(By.CSS_SELECTOR, "span[id^='product-price-'] span.price")
                                price_text = price_element.text.strip()
                            except NoSuchElementException: pass 
                            mileage_text = "N/A"
                            location_text = "N/A"
                            try:
                                all_p_tags = item.find_elements(By.TAG_NAME, "p")
                                for p in all_p_tags:
                                    if "km •" in p.text:
                                        parts = p.text.strip().split("•")
                                        if len(parts) == 2:
                                            mileage_text = parts[0].strip() 
                                            location_text = parts[1].strip() 
                                        break 
                            except Exception: pass
                            img_url = "N/A"
                            try:
                                img_tag = item.find_element(By.CSS_SELECTOR, "img.product-image-photo")
                                img_url = img_tag.get_attribute("src")
                            except NoSuchElementException: pass
                            car_link = "N/A"
                            try:
                                link_tag = item.find_element(By.CSS_SELECTOR, "a.product-item-photo")
                                car_link = link_tag.get_attribute("href")
                            except NoSuchElementException:
                                try:
                                    link_tag = item.find_element(By.TAG_NAME, "a")
                                    car_link = link_tag.get_attribute("href")
                                except NoSuchElementException: pass
                            car_data_obj = {
                                "name": h3_text, "trim": trim_text, "price": price_text,
                                "mileage": mileage_text, "location": location_text,
                                "image_url": img_url, "link": car_link 
                            }
                            print(f"還在 (ID: {product_id})：{car_data_obj['name']} {car_data_obj['trim']}")
                            master_stock_available[product_id] = car_data_obj
                    except NoSuchElementException: pass 
            except Exception as page_error:
                print(f"       爬取頁面 {page_url} 時發生錯誤: {page_error}")
                driver.save_screenshot(f"error_page_{i+1}.png")
        print(f"\n--- 所有 {len(page_list)} 個頁面均搜尋完畢 ---")
        print(f"總結：找到 {len(master_stock_available)} 台可購買車輛。")
        return master_stock_available
    except Exception as e:
        print(f"爬取或處理時發生嚴重錯誤：{e}")
        driver.save_screenshot("error_screenshot_main.png")
        return {} 
    finally:
        if driver:
            print("爬蟲執行完畢，關閉瀏覽器。")
            driver.quit()

# --- Discord 發送函式 (V18 - 升級) ---
def send_to_discord(cars_to_notify_list, is_mandatory_notify, timestamp_utc):
    """
    (V18 - 增加時間戳記)
    - 增加 timestamp_utc 參數
    """
    
    if not cars_to_notify_list and not is_mandatory_notify:
        print("--- send_to_discord 收到 0 台新車，不發送。 ---")
        return 
    
    # (V18) 將 datetime 物件轉換為 Discord 接受的 ISO 8601 格式字串
    iso_timestamp = timestamp_utc.isoformat() + "Z"

    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("重大錯誤：找不到 DISCORD_WEBHOOK_URL 環境變數！")
        sys.exit(1)

    embeds = []
    for car in cars_to_notify_list:
        embed = {
            "title": f"{car['name']} {car['trim']}",
            "url": car['link'],
            "color": 3447003 if is_mandatory_notify else 5763719, 
            "description": (
                f"**價格:** {car['price']}\n"
                f"**里程:** {car['mileage']}\n"
                f"**地點:** {car['location']}"
            ),
            "image": {
                "url": car['image_url']
            },
            # --- (V18 新增欄位) ---
            "timestamp": iso_timestamp
        }
        embeds.append(embed)

    # (V17) 根據通知類型決定標題
    total_cars = len(cars_to_notify_list)
    if is_mandatory_notify:
        content_message = f"KIA Sportage 每日報告 (共 {total_cars} 台可購買)：\n"
        if total_cars == 0:
            # 即使是 0 台，也要發送報告
            content_message = "KIA Sportage 每日報告：目前無可購買車輛。"
            # (V18 新增) 建立一個假的 embed 才能傳送 timestamp
            embeds.append({
                "description": "本次報告時間",
                "color": 8421504, # 灰色
                "timestamp": iso_timestamp
            })
    else:
        content_message = f"KIA Sportage 新車上架！ (共 {total_cars} 台新車)：\n"
    
    embed_chunks = [embeds[i:i + 10] for i in range(0, len(embeds), 10)]
    
    for i, chunk in enumerate(embed_chunks):
        payload = {
            "content": content_message if i == 0 else f"(...接續 {i+1}/{len(embed_chunks)})",
            "embeds": chunk
        }
        
        try:
            print(f"--- 正在發送第 {i+1} 則訊息到 Discord ({'強制' if is_mandatory_notify else '新車'}) ---")
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print("       成功發送！")
            time.sleep(1) 
        except requests.RequestException as e:
            print(f"       發送 Discord 失敗：{e}")

# --- (V18) 程式主執行區塊 (修改) ---
if __name__ == "__main__":
    
    print("--- 啟動 V18 (增加時間戳記) 爬蟲腳本 ---")
    
    CACHE_FILE = 'previous_cars.json'
    
    # 1. 讀取「上個小時」的結果
    previous_cars_dict = load_previous_cars(CACHE_FILE)
    print(f"已載入 {len(previous_cars_dict)} 筆先前的車輛資料。")
    
    # 2. 爬取「現在」的結果
    current_cars_dict = scrape_kia_sportage()
    
    # 3. 比對「新車」
    new_cars_list = find_new_cars(current_cars_dict, previous_cars_dict)
    
    # 4. (V18 修改) 取得「一次」UTC 時間，供後續所有函式使用
    now_utc = datetime.datetime.utcnow()
    current_hour_utc = now_utc.hour # 只取小時
    print(f"目前 UTC 時間: {now_utc.isoformat()} (小時: {current_hour_utc})")
    
    is_mandatory_notify_time = (current_hour_utc == 4 or current_hour_utc == 10)
    
    # 5. 決定是否發送通知
    if is_mandatory_notify_time:
        print("觸發「強制通知時間」(CST 12:00 / 18:00)。")
        # (V18 修改) 傳入 now_utc
        send_to_discord(list(current_cars_dict.values()), is_mandatory_notify=True, timestamp_utc=now_utc)
        
    elif len(new_cars_list) > 0:
        print(f"觸發「新車通知」，發現 {len(new_cars_list)} 台新車。")
        # (V18 修改) 傳入 now_utc
        send_to_discord(new_cars_list, is_mandatory_notify=False, timestamp_utc=now_utc)
        
    else:
        print("非強制通知時間，且無新車上架。本次不發送 Discord 通知。")

    # 6. 儲存「現在」的結果，供「下個小時」使用
    save_current_cars(current_cars_dict, CACHE_FILE)
    
    print("--- 腳本執行完畢 ---")