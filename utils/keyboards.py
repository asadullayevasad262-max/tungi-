from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import random


def main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎁 Sovg'alar"),
        KeyboardButton(text="💰 Bal yig'ish")
    )
    builder.row(
        KeyboardButton(text="👤 Men haqimda"),
        KeyboardButton(text="🏆 Top 100")
    )
    builder.row(
        KeyboardButton(text="📋 Qoidalar"),
        KeyboardButton(text="💝 Donat qilish")
    )
    return builder.as_markup(resize_keyboard=True)


def points_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Taklif orqali bal yig'ish", callback_data="earn_referral"))
    builder.row(InlineKeyboardButton(text="📢 Kanallarga qo'shilib bal yig'ish", callback_data="earn_channels"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main"))
    return builder.as_markup()


def required_channels_keyboard(channels: list, user_statuses: dict, invite_links: dict = None):
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = user_statuses.get(ch['channel_id'], False)
        username = (ch.get('channel_username') or '').strip('@')
        ctype = ch.get('channel_type') or 'request'
        link = None
        if ctype in ('request', 'private') and invite_links and ch['channel_id'] in invite_links and invite_links[ch['channel_id']]:
            link = invite_links[ch['channel_id']]
        elif username:
            link = f"https://t.me/{username}"
        elif invite_links and ch['channel_id'] in invite_links and invite_links[ch['channel_id']]:
            link = invite_links[ch['channel_id']]
        icon = '✅' if status else ('📩' if ctype in ('private', 'request') else '➕')
        if link:
            builder.row(InlineKeyboardButton(
                text=f"{icon} {ch['channel_name']}",
                url=link
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"{icon} {ch['channel_name']}",
                callback_data="noop"
            ))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return builder.as_markup()


def generate_captcha():
    correct = random.randint(1000, 9999)
    options = {correct}
    while len(options) < 4:
        options.add(random.randint(1000, 9999))
    options = list(options)
    random.shuffle(options)
    return correct, options


def captcha_keyboard(correct: int, options: list):
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(
            text=str(opt),
            callback_data=f"captcha_{opt}_{correct}"
        )
    builder.adjust(2)
    return builder.as_markup()


def points_channels_keyboard(channel, index: int, total: int, already_earned: bool):
    builder = InlineKeyboardBuilder()
    username = (channel.get('channel_username') or '').strip('@')
    if username:
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if already_earned else '📢'} {channel['channel_name']}",
            url=f"https://t.me/{username}"
        ))
    if not already_earned:
        builder.row(InlineKeyboardButton(
            text="✅ Qo'shildim, bal olish",
            callback_data=f"claim_channel_{channel['id']}"
        ))
    if index + 1 < total:
        builder.row(InlineKeyboardButton(
            text=f"Keyingisi ➡️ ({index+2}/{total})",
            callback_data=f"next_channel_{index+1}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="earn_channels"))
    return builder.as_markup()


def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"))
    builder.row(
        InlineKeyboardButton(text="📢 Majburiy kanallar", callback_data="admin_req_channels"),
        InlineKeyboardButton(text="💰 Bal kanallari", callback_data="admin_pts_channels")
    )
    builder.row(InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data="admin_broadcast"))
    builder.row(
        InlineKeyboardButton(text="📋 Matnlarni tahrirlash", callback_data="admin_edit_texts"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")
    )
    builder.row(InlineKeyboardButton(text="📩 Zayavkalarni tasdiqlash", callback_data="admin_accept_requests"))
    return builder.as_markup()


def admin_texts_keyboard():
    builder = InlineKeyboardBuilder()
    texts = [
        ("🤖 Avto xabar", "edit_auto_message"),
        ("🎁 Sovg'alar matni", "edit_gifts_text"),
        ("💰 Bal matni", "edit_points_welcome_text"),
        ("👥 Taklif matni", "edit_referral_ad_text"),
        ("📋 Qoidalar matni", "edit_rules_text"),
        ("💝 Donat matni", "edit_donate_text"),
    ]
    for label, cb in texts:
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin_{cb}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()


def admin_channels_keyboard(channels: list, ch_type: str):
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "✅" if ch['is_active'] else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{status} {ch['channel_name']}",
            callback_data=f"admin_toggle_{ch_type}_{ch['id']}"
        ))
        builder.row(InlineKeyboardButton(
            text=f"🗑 O'chirish",
            callback_data=f"admin_del_{ch_type}_{ch['id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data=f"admin_add_{ch_type}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()


def back_keyboard(cb: str = "admin_back"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb))
    return builder.as_markup()


def accept_requests_channels_keyboard(channels: list, pending_counts: dict = None):
    builder = InlineKeyboardBuilder()
    for ch in channels:
        count = (pending_counts or {}).get(ch['channel_id'], 0)
        label = f"📢 {ch['channel_name']} ({count} ta)" if count else f"📢 {ch['channel_name']}"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"accept_ch_{ch['channel_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()
