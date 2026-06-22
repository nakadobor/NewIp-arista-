import os
import re
import requests

TOKEN = "8256367510:AAH3sMbKF9yRgVz9aiTtmU-VjxCzK7sB6hc"
CHAT_ID = "@CleanIPServices" 

INPUT_FILE = os.path.join("output", "best_ips.txt")
CLEAN_FILE = "Best_Clean_IPs.txt"

DEFAULT_CAPTION = """🎯 *لیست جدید آی‌پی‌های تمیز آپدیت شد*

🔥 **وضعیت:** گلچین بهترین آی‌پی‌های اسکن شده
🔹 **مشخصات:** آی‌پی خالص (بدون پورت و متن اضافه)
🔹 **نحوه استفاده:** کپی و استفاده مستقیم در کلاینت‌ها (خط به خط)

🔄 به‌روزرسانی خودکار توسط گیت‌هاب اکشنز"""

CUSTOM_CAPTION = os.getenv("CUSTOM_CAPTION")

# 🔄 خواندن مقدار دکمه ربات از محیط گیت‌هاب؛ اگر دکمه‌ای زده نشده بود، پیش‌فرض ۲۰ قرار می‌گیرد
IP_LIMIT_RAW = os.getenv("IP_COUNT_LIMIT", "20")

def send_best_ips():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ فایل خروجی اسکنر در مسیر {INPUT_FILE} پیدا نشد!")
        return

    try:
        # تبدیل مقدار دکمه به عدد؛ اگر خطا داد همان ۲۰ اعمال می‌شود
        try:
            ip_limit = int(IP_LIMIT_RAW)
        except:
            ip_limit = 20

        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # رگکس پیشرفته برای جداسازی آی‌پی‌ها
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        raw_ips = re.findall(ip_pattern, content)
        
        unique_ips = []
        for ip in raw_ips:
            if ip not in unique_ips and not ip.startswith("0.") and not ip.startswith("255."):
                unique_ips.append(ip)
        
        if not unique_ips:
            print("⚠️ هیچ آی‌پی معتبری یافت نشد.")
            return
        
        # 🎯 حالا این بخش دقیقاً به تعداد دکمه رباتت (ip_limit) آی‌پی گلچین می‌کند
        final_ips = unique_ips[:ip_limit]
        
        with open(CLEAN_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(final_ips))
            
        print(f"✅ تعداد {len(final_ips)} آی‌پی استخراج شد.")
        count_text = f"📊 **تعداد آی‌پی‌های این پارت:** {len(final_ips)} عدد"

        if CUSTOM_CAPTION:
            caption_text = f"{CUSTOM_CAPTION}\n\n{count_text}"
        else:
            caption_text = DEFAULT_CAPTION.replace(
                "🔹 **نحوه استفاده:**", 
                f"{count_text}\n🔹 **نحوه استفاده:**"
            )

        url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
        with open(CLEAN_FILE, 'rb') as file_to_send:
            payload = {'chat_id': CHAT_ID, 'caption': caption_text, 'parse_mode': 'Markdown'}
            files = {'document': ('Best_IPs.txt', file_to_send)} 
            response = requests.post(url, data=payload, files=files)
            
            if response.status_code == 200:
                print("✅ فایل با موفقیت به کانال ارسال شد.")
            else:
                print(f"❌ خطا در ارسال به تلگرام: {response.text}")
                
        if os.path.exists(CLEAN_FILE):
            os.remove(CLEAN_FILE)

    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")

if __name__ == "__main__":
    send_best_ips()
