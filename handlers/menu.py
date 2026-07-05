from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from database.db import (
    get_user, get_setting, get_top_users, get_user_rank,
    get_points_channels, check_user_earned_channel_points,
    mark_user_channel_points, update_user_points
)
from utils.keyboards import (
    points_menu_keyboard, points_channels_keyboard,
    main_menu_keyboard
)
from utils.helpers import check_user_subscriptions, format_number, ordinal_uz
import os

router = Router()

BOT_USERNAME = None


async def get_bot_username(bot: Bot) -> str:
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await bot.get_me()
        BOT_USERNAME = me.username
    return BOT_USERNAME


# ── GIFTS ───────────────────────────────────────────────────────────────────
@router.message(F.text == "🎁 Sovg'alar")
async def gifts_handler(message: Message):
    text = await get_setting("gifts_text")
    await message.answer(text or "🎁 Hozircha faol konkurs mavjud emas.", parse_mode="HTML")


# ── POINTS ──────────────────────────────────────────────────────────────────
@router.message(F.text == "💰 Bal yig'ish")
async def points_handler(message: Message):
    text = await get_setting("points_welcome_text")
    await message.answer(text, reply_markup=points_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "earn_referral")
async def earn_referral_callback(callback: CallbackQuery, bot: Bot):
    user = await get_user(callback.from_user.id)
    bot_username = await get_bot_username(bot)
    ref_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    ad_text = await get_setting("referral_ad_text")
    pts = await get_setting("points_per_referral")

    text = (
        f"{ad_text}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 Har bir yangi foydalanuvchi uchun: <b>+{pts} ball</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=points_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "earn_channels")
async def earn_channels_callback(callback: CallbackQuery, bot: Bot):
    channels = await get_points_channels(active_only=True)
    if not channels:
        await callback.answer("Hozircha ball kanallar mavjud emas.", show_alert=True)
        return
    await show_channel_step(callback.message, bot, callback.from_user.id, channels, 0, edit=True)
    await callback.answer()


async def show_channel_step(message: Message, bot: Bot, user_id: int, channels, index: int, edit=False):
    ch = channels[index]
    earned = await check_user_earned_channel_points(user_id, ch['channel_id'])
    kb = points_channels_keyboard(ch, index, len(channels), earned)

    status_line = (
        "✅ Siz bu kanaldan ball oldingiz!" if earned
        else "Quyidagi kanalga qo'shilib, so'ng \"✅ Qo'shildim\" tugmasini bosing."
    )
    text = (
        f"📢 <b>{index+1}/{len(channels)} — {ch['channel_name']}</b>\n\n"
        f"💰 Bu kanalga qo'shilish uchun: <b>+{ch['points_reward']} ball</b>\n\n"
        f"{status_line}"
    )
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("next_channel_"))
async def next_channel_callback(callback: CallbackQuery, bot: Bot):
    index = int(callback.data.split("_")[-1])
    channels = await get_points_channels(active_only=True)
    await show_channel_step(callback.message, bot, callback.from_user.id, channels, index, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("claim_channel_"))
async def claim_channel_callback(callback: CallbackQuery, bot: Bot):
    ch_db_id = int(callback.data.split("_")[-1])
    channels = await get_points_channels(active_only=True)
    ch = next((c for c in channels if c['id'] == ch_db_id), None)
    if not ch:
        await callback.answer("Kanal topilmadi.", show_alert=True)
        return

    user_id = callback.from_user.id
    already = await check_user_earned_channel_points(user_id, ch['channel_id'])
    if already:
        await callback.answer("Siz bu kanaldan allaqachon ball oldingiz!", show_alert=True)
        return

    # Verify membership
    try:
        from aiogram.types import ChatMemberStatus
        member = await bot.get_chat_member(ch['channel_id'], user_id)
        if member.status in ('left', 'kicked', 'banned'):
            await callback.answer(
                "❌ Siz hali bu kanalga qo'shilmagansiz! Avval qo'shiling.",
                show_alert=True
            )
            return
    except Exception:
        # For channels with join requests, trust the user
        pass

    await mark_user_channel_points(user_id, ch['channel_id'])
    await update_user_points(user_id, ch['points_reward'])

    # Find current index
    index = next((i for i, c in enumerate(channels) if c['id'] == ch_db_id), 0)
    await callback.answer(f"✅ +{ch['points_reward']} ball qo'shildi!", show_alert=True)
    await show_channel_step(callback.message, bot, user_id, channels, index, edit=True)


# ── ME ───────────────────────────────────────────────────────────────────────
@router.message(F.text == "👤 Men haqimda")
async def me_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Ma'lumot topilmadi.")
        return
    rank = await get_user_rank(message.from_user.id)
    username_display = f"@{user['username']}" if user['username'] else "—"
    joined = user['joined_at'][:10] if user['joined_at'] else "—"

    text = (
        "👤 <b>Shaxsiy ma'lumotlaringiz</b>\n\n"
        f"🏷 <b>Ism:</b> {user['full_name']}\n"
        f"📛 <b>Foydalanuvchi nomi:</b> {username_display}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user['telegram_id']}</code>\n"
        f"📅 <b>Botga qo'shilgan sana:</b> {joined}\n"
        f"⭐ <b>To'plangan ball:</b> {format_number(user['points'])}\n"
        f"🏆 <b>Reyting o'rni:</b> {ordinal_uz(rank)}\n\n"
        "🌟 Faolligingizni oshiring va yuqori o'rinlarni egallab qoling!"
    )
    await message.answer(text, parse_mode="HTML")


# ── TOP 100 ─────────────────────────────────────────────────────────────────
@router.message(F.text == "🏆 Top 100")
async def top_handler(message: Message):
    users = await get_top_users(100)
    if not users:
        await message.answer("Hali ro'yxat bo'sh.")
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 <b>Top 100 foydalanuvchilar</b>\n"]
    for i, u in enumerate(users, 1):
        name = u['full_name'] or u['username'] or "Foydalanuvchi"
        medal = medals.get(i, f"{i}.")
        lines.append(f"{medal} {name} — <b>{format_number(u['points'])} ball</b>")

    # Split if too long
    text = "\n".join(lines)
    if len(text) > 4000:
        text = "\n".join(lines[:50]) + "\n\n<i>...va boshqalar</i>"

    await message.answer(text, parse_mode="HTML")


# ── RULES ────────────────────────────────────────────────────────────────────
@router.message(F.text == "📋 Qoidalar")
async def rules_handler(message: Message):
    text = await get_setting("rules_text")
    await message.answer(text, parse_mode="HTML")


# ── DONATE ───────────────────────────────────────────────────────────────────
@router.message(F.text == "💝 Donat qilish")
async def donate_handler(message: Message):
    text = await get_setting("donate_text")
    await message.answer(text, parse_mode="HTML")


# ── BACK ─────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "back_main")
async def back_main_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🏠 <b>Asosiy menyu</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()
