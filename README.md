# ⚽ Real Madrid News Bot

ربات تلگرام اخبار باشگاه فوتبال رئال مادرید — هر ۳ ساعت خودکار اخبار ارسال می‌شود.

## ویژگی‌ها

- 🔔 ارسال خودکار اخبار هر ۳ ساعت
- 📰 ۳ منبع خبری (Google News + BBC Sport)
- 🎨 منوی زیبا با دکمه‌های اینلاین
- 🔄 جلوگیری از ارسال اخبار تکراری
- 🆓 کاملاً رایگان

## نصب و اجرای محلی

```bash
cd real-madrid-bot
pip install -r requirements.txt
python main.py
```

## deployment رایگان روی Render

### مرحله ۱: آپلود کد روی GitHub
```bash
git init
git add .
git commit -m "Real Madrid News Bot"
git remote add origin https://github.com/YOUR_USERNAME/real-madrid-bot.git
git push -u origin main
```

### مرحله ۲: اتصال به Render
1. برو به [render.com](https://render.com) و ثبت‌نام کن (رایگان)
2. روی **New +** کلیک کن → **Background Worker**
3. گیت‌هاب رو connect کن
4. پروژه `real-madrid-bot` رو انتخاب کن
5. تنظیمات:
   - **Name:** `real-madrid-news-bot`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`

### مرحله ۳: متغیرهای محیطی
در صفحه Environment اضافه کن:

| متغیر | مقدار |
|--------|-------|
| `BOT_TOKEN` | `8792366937:AAFQTvY79e5YwOhqdDgB9HZOb8bEEMVF1wM` |
| `ADMIN_CHAT_ID` | `580003433` |
| `GEMINI_API_KEY` | کلید API گوگل جمینای (رایگان) |

### گرفتن کلید Gemini API (رایگان):
1. برو به [aistudio.google.com](https://aistudio.google.com/apikey)
2. با اکانت گوگل لاگین کن
3. روی **Create API Key** کلیک کن
4. کلید رو کپی کن و به عنوان `GEMINI_API_KEY` اضافه کن
5. **رایگان:** ۱۵ درخواست در دقیقه، بدون نیاز به کارت اعتباری

### مرحله ۴: Deploy
روی **Deploy** کلیک کن. ربات ظرف چند دقیقه فعال میشه! ✅

## deployment رایگان روی Railway

### مرحله ۱: آپلود کد روی GitHub (مثل بالا)

### مرحله ۲: اتصال به Railway
1. برو به [railway.app](https://railway.app)
2. با گیت‌هاب ثبت‌نام کن
3. **New Project** → **Deploy from GitHub**
4. پروژه رو انتخاب کن
5. متغیرهای محیطی رو اضافه کن (مثل بالا)

## فایل‌های پروژه

```
real-madrid-bot/
├── main.py           # نقطه شروع
├── bot.py            # هندلرهای ربات
├── news_fetcher.py   # دریافت و پردازش اخبار
├── config.py         # تنظیمات
├── requirements.txt  # وابستگی‌ها
├── Procfile          # فایل deployment
├── render.yaml       # تنظیمات Render
└── README.md         # این فایل
```

## منابع خبری

| منبع | نوع | توضیح |
|------|------|-------|
| Google News | RSS | اخبار لحظه‌ای رئال مادرید |
| Google News Transfer | RSS | نقل و انتقالات |
| BBC Sport | RSS | اخبار فوتبال جهان |

## ساخته شده با ❤️ برای هواداران رئال مادرید

**Hala Madrid!** ⚪
