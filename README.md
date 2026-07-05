# 🤖 Telegram Konkurs Boti

Foydalanuvchilar uchun ball yig'ish, sovg'a va konkurs tizimi bilan jihozlangan to'liq funksional Telegram boti.

---

## 📋 Xususiyatlar

### Foydalanuvchilar uchun:
- 🔐 **Kaptcha tekshiruv** — bot emasligini tasdiqlash (4 xonali raqam)
- 📢 **Majburiy kanallar** — qo'shilish / so'rov yuborish
- 🎁 **Sovg'alar** — konkurs va sovg'alar ro'yxati
- 💰 **Bal yig'ish** — taklif + kanallarga qo'shilish
- 👤 **Shaxsiy sahifa** — ID, ball, reyting
- 🏆 **Top 100** — yetakchi foydalanuvchilar
- 📋 **Qoidalar** & **💝 Donat**

### Admin uchun (`/admin`):
- 📊 **Statistika** — foydalanuvchilar soni, bugungi, ball
- 📢 **Majburiy kanallar** — qo'shish / o'chirish / faollashtirish
- 💰 **Bal kanallar** — ketma-ket tartib bilan
- ✉️ **Xabar yuborish** — barcha foydalanuvchilarga broadcast
- ✏️ **Matnlarni tahrirlash** — barcha botdagi matnlar
- ⚙️ **Sozlamalar** — kaptcha, taklif bali
- 📩 **Eski so'rovlarni qabul qilish** — miqdor belgilab

---

## 🚀 O'rnatish

### 1. Python o'rnatish
Python 3.10+ talab qilinadi.

### 2. Paketlarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. `.env` fayl yaratish
```bash
cp .env.example .env
```
`.env` faylini oching va to'ldiring:
```
BOT_TOKEN=1234567890:ABCdef...   # @BotFather dan olingan token
ADMIN_IDS=123456789,987654321    # Admin Telegram ID lari (vergul bilan)
```

### 4. Botni ishga tushirish
```bash
python main.py
```

---

## ⚙️ Kanal qo'shish formati

### Majburiy kanal:
```
kanal_id|kanal_nomi|@username|turi|ball
```
- `turi`: `public` (ochiq), `private` (maxfiy), `request` (so'rovli)
- `ball`: qo'shilganda beriladigan ball (0 ham bo'ladi)

**Misol:**
```
-1001234567890|Mening Kanalim|@mychannel|public|0
-1009876543210|Maxfiy Kanal|@privatech|request|10
```

### Bal kanali:
```
kanal_id|kanal_nomi|@username|ball
```
**Misol:**
```
-1001111111111|Yangi Kanal|@newch|15
```

---

## 🔧 Bot sozlamalari (Telegram'da)

1. **@BotFather** da botingizni yarating
2. `/setprivacy` → **Disable** qiling (guruhlarda ishlash uchun)
3. Botni kanalga **admin** sifatida qo'shing:
   - Majburiy kanallar uchun: **Users management** ruxsatini bering
   - Agar so'rov qabul qilsa: **Invite users** ruxsatini bering

---

## 📁 Fayl tuzilmasi

```
telegram_bot/
├── main.py                 # Asosiy kirish nuqtasi
├── requirements.txt
├── .env                    # Token va admin ID lar
├── database/
│   ├── __init__.py
│   ├── db.py               # Ma'lumotlar bazasi
│   └── bot.db              # SQLite fayl (avtomatik yaratiladi)
├── handlers/
│   ├── __init__.py
│   ├── start.py            # /start, kaptcha, obuna tekshirish
│   ├── menu.py             # Asosiy menyu
│   └── admin.py            # Admin panel
└── utils/
    ├── __init__.py
    ├── keyboards.py        # Barcha tugmalar
    └── helpers.py          # Yordamchi funksiyalar
```

---

## 💡 Maslahatlar

- Katta auditoriyaga broadcast yuborishda spam filtri tufayli ba'zi xabarlar yetmasdan qolishi mumkin — bu normal holat.
- So'rov kanallar uchun (`request` turi) bot kanalda admin bo'lishi shart.
- Admin ID sini `@userinfobot` orqali topishingiz mumkin.

---

## 🛡 Texnologiyalar

- **aiogram 3.4** — Telegram Bot API
- **aiosqlite** — asinxron SQLite
- **Python 3.10+**
