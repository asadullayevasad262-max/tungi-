-- Supabase SQL Editor ga yozib run qiling
-- Barcha jadvallarni yaratadi

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    referral_code TEXT UNIQUE,
    referred_by BIGINT,
    points INTEGER DEFAULT 0,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    is_verified INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS required_channels (
    id BIGSERIAL PRIMARY KEY,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_username TEXT,
    channel_type TEXT DEFAULT 'public',
    points_reward INTEGER DEFAULT 10,
    is_active INTEGER DEFAULT 1,
    invite_link TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Existing jadvalga ustun qo'shish (agar mavjud bo'lmasa):
ALTER TABLE required_channels ADD COLUMN IF NOT EXISTS invite_link TEXT;

CREATE TABLE IF NOT EXISTS points_channels (
    id BIGSERIAL PRIMARY KEY,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_username TEXT,
    points_reward INTEGER DEFAULT 5,
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_channel_points (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    channel_id TEXT,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, channel_id)
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id BIGSERIAL PRIMARY KEY,
    message_text TEXT,
    sent_by BIGINT,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    total_sent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pending_join_requests (
    id BIGSERIAL PRIMARY KEY,
    channel_id TEXT,
    user_id BIGINT,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    is_processed INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS pending_join_requests_open_unique
ON pending_join_requests (channel_id, user_id)
WHERE is_processed = 0;

-- Default settings (run only once, or use INSERT ON CONFLICT)
INSERT INTO settings (key, value) VALUES
    ('auto_message', '🎉 Botimizga xush kelibsiz! Siz muvaffaqiyatli ro''yxatdan o''tdingiz.'),
    ('gifts_text', '🎁 <b>Sovg''alar va Konkurslar</b>\n\nHozircha faol konkurs mavjud emas. Kuzatib boring!'),
    ('points_welcome_text', '💰 <b>Bal yig''ish</b>\n\nQuyidagi usullar orqali ball yig''ishingiz mumkin:'),
    ('referral_ad_text', '👥 <b>Do''stlaringizni taklif qiling!</b>\n\nHar bir taklif uchun <b>20 ball</b> oling!'),
    ('rules_text', '📋 <b>Qoidalar</b>\n\n1. Botdan halol foydalaning.\n2. Spam yuborilmasin.\n3. Boshqa foydalanuvchilarga hurmat bilan munosabatda bo''ling.\n\nQoidalarni buzganlar bloklanadi.'),
    ('donate_text', '💝 <b>Donat qilish</b>\n\nBotni rivojlantirish uchun qo''llab-quvvatlashingiz mumkin.\n\nRekvizitlar: ...\n\nHar bir donat uchun rahmat! 🙏'),
    ('points_per_referral', '20'),
    ('captcha_enabled', '1')
ON CONFLICT (key) DO NOTHING;
