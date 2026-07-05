import logging, asyncio, inspect
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_stats, get_setting, set_setting, get_all_users,
    get_required_channels, add_required_channel, toggle_required_channel, delete_required_channel,
    get_points_channels, add_points_channel, toggle_points_channel, delete_points_channel,
    get_old_pending_requests, mark_request_processed,
    get_managed_channels, get_old_pending_requests_by_channel, count_pending_requests_by_channel,
    update_required_channel_invite_link, update_required_channel_type
)
from utils.keyboards import (
    admin_main_keyboard, admin_texts_keyboard, admin_channels_keyboard,
    back_keyboard, accept_requests_channels_keyboard
)
from utils.helpers import is_admin, ADMIN_IDS

router = Router()


class AdminStates(StatesGroup):
    editing_text = State()
    adding_req_channel = State()
    adding_pts_channel = State()
    setting_pts_amount = State()
    broadcasting = State()
    setting_requests_count = State()


TEXT_KEYS = {
    "edit_auto_message": ("auto_message", "Avto xabar matni"),
    "edit_gifts_text": ("gifts_text", "Sovg'alar matni"),
    "edit_points_welcome_text": ("points_welcome_text", "Bal yig'ish matni"),
    "edit_referral_ad_text": ("referral_ad_text", "Taklif matni"),
    "edit_rules_text": ("rules_text", "Qoidalar matni"),
    "edit_donate_text": ("donate_text", "Donat matni"),
}


def admin_only(func):
    async def wrapper(obj, *args, **kwargs):
        user_id = obj.from_user.id if hasattr(obj, 'from_user') else None
        if user_id and not is_admin(user_id):
            if isinstance(obj, Message):
                await obj.answer("❌ Ruxsat yo'q.")
            elif isinstance(obj, CallbackQuery):
                await obj.answer("❌ Ruxsat yo'q.", show_alert=True)
            return
        return await func(obj, *args, **kwargs)
    return wrapper


async def leave_chat_safely(bot: Bot, channel_id: str):
    try:
        await bot.leave_chat(channel_id)
        return True
    except Exception:
        return False


def status_value(status) -> str:
    return getattr(status, "value", str(status))


async def ensure_required_channel_registered(bot: Bot, chat, log=None):
    ch_id = str(chat.id)
    ch_name = chat.title or f"Kanal {ch_id}"
    ch_username = chat.username or ""

    existing = await get_required_channels(active_only=False)
    ch = next((c for c in existing if c['channel_id'] == ch_id), None)
    if not ch:
        await add_required_channel(ch_id, ch_name, ch_username, "request", 0)
        if log:
            log.info(f"Kanal/guruh bazaga saqlandi: {ch_name} ({ch_id})")
    elif ch.get("channel_type") != "request":
        await update_required_channel_type(ch_id, "request")

    try:
        link = await bot.create_chat_invite_link(ch_id, creates_join_request=True)
        await update_required_channel_invite_link(ch_id, link.invite_link)
    except Exception as e:
        if log:
            log.warning(f"Zayavka link yaratib bo'lmadi ({ch_id}): {e}")


@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message, **kwargs):
    await message.answer(
        "⚙️ <b>Admin paneli</b>\n\nXush kelibsiz!",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("claim"))
@admin_only
async def claim_channel(message: Message, bot: Bot, **kwargs):
    log = logging.getLogger(__name__)
    if not message.forward_from_chat:
        await message.answer(
            "❌ Kanalga botni admin qilib qo'shib, kanaldagi birorta xabarni "
            "botga forward qiling.\n\n"
            "Misol: kanalga post tashlang ➡️ uni botga forward qiling",
            parse_mode="HTML"
        )
        return

    chat = message.forward_from_chat
    if chat.type != "channel":
        await message.answer("❌ Bu kanal emas. Iltimos, kanaldan forward qiling.")
        return

    ch_id = str(chat.id)
    try:
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
    except Exception as e:
        await message.answer(f"❌ Bot kanalda admin emas yoki xatolik: {e}")
        return

    if status_value(member.status) != "administrator":
        await message.answer("❌ Bot kanalda admin emas. Admin qilib qo'shing.")
        return

    await ensure_required_channel_registered(bot, chat, log)
    await message.answer(
        f"✅ <b>{chat.title}</b> muvaffaqiyatli qo'shildi!\n\n"
        "Endi foydalanuvchilar kanalga zayafka yuborib qo'shilishi mumkin.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_back")
@admin_only
async def admin_back(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.message.edit_text(
        "⚙️ <b>Admin paneli</b>",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── STATS ────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
@admin_only
async def admin_stats(callback: CallbackQuery, **kwargs):
    stats = await get_stats()
    text = (
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total']}</b>\n"
        f"✅ Tasdiqlangan: <b>{stats['verified']}</b>\n"
        f"🆕 Bugun qo'shilgan: <b>{stats['today']}</b>\n"
        f"⭐ Jami tarqatilgan ball: <b>{stats['total_points']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="HTML")
    await callback.answer()


# ── EDIT TEXTS ───────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_edit_texts")
@admin_only
async def admin_edit_texts(callback: CallbackQuery, **kwargs):
    await callback.message.edit_text(
        "📋 <b>Matnlarni tahrirlash</b>\n\nQaysi matnni tahrirlashni xohlaysiz?",
        reply_markup=admin_texts_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_"))
@admin_only
async def admin_edit_text_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    key_name = callback.data.replace("admin_", "")
    if key_name not in TEXT_KEYS:
        await callback.answer("Noma'lum kalit.", show_alert=True)
        return
    db_key, label = TEXT_KEYS[key_name]
    current = await get_setting(db_key)
    await state.set_state(AdminStates.editing_text)
    await state.update_data(text_key=db_key, label=label)
    await callback.message.edit_text(
        f"✏️ <b>{label}</b>\n\n"
        f"<b>Hozirgi matni:</b>\n{current}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "Yangi matnni yuboring (HTML teglari ishlatiladi):",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.editing_text)
@admin_only
async def admin_save_text(message: Message, state: FSMContext, **kwargs):
    data = await state.get_data()
    await set_setting(data['text_key'], message.text)
    await state.clear()
    await message.answer(
        f"✅ <b>{data['label']}</b> muvaffaqiyatli yangilandi!",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )


# ── REQUIRED CHANNELS ────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_req_channels")
@admin_only
async def admin_req_channels(callback: CallbackQuery, **kwargs):
    channels = await get_required_channels(active_only=False)
    await callback.message.edit_text(
        "📢 <b>Majburiy kanallar</b>\n\nKanallarni boshqarish:",
        reply_markup=admin_channels_keyboard(channels, "req"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_req")
@admin_only
async def admin_add_req_channel(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(AdminStates.adding_req_channel)
    await callback.message.edit_text(
        "➕ <b>Majburiy kanal qo'shish</b>\n\n"
        "Kanaldagi istalgan xabarni <b>forward</b> qiling.\n\n"
        "Agar bot hali kanalda admin bo'lmasa, avval admin qilib qo'shing, "
        "keyin xabarni forward qiling.",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.adding_req_channel)
@admin_only
async def admin_save_req_channel(message: Message, state: FSMContext, bot: Bot, **kwargs):
    log = logging.getLogger(__name__)
    if not message.forward_from_chat:
        await message.answer("❌ Kanal xabarini forward qiling, matn emas.")
        return

    chat = message.forward_from_chat
    if chat.type != "channel":
        await message.answer("❌ Bu kanal emas. Kanal xabarini forward qiling.")
        return

    ch_id = str(chat.id)
    try:
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
        if status_value(member.status) != "administrator":
            await message.answer(
                f"❌ Bot <b>{chat.title}</b> kanalida admin emas.\n"
                "Botni kanalga admin qilib qo'shib, xabarni qayta forward qiling.",
                parse_mode="HTML"
            )
            return
    except Exception as e:
        await message.answer(
            f"❌ Bot <b>{chat.title}</b> kanalida admin emas.\n"
            f"Xatolik: {e}\n\nBotni admin qilib qo'shib, qayta forward qiling.",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    ch_username = chat.username or ""
    ch_name = chat.title or f"Kanal {ch_id}"
    await add_required_channel(ch_id, ch_name, ch_username, "request", 0)
    await state.clear()

    await ensure_required_channel_registered(bot, chat, log)
    await message.answer(
        f"✅ <b>{ch_name}</b> majburiy kanallarga qo'shildi!\n\n"
        "Foydalanuvchilar start bosganda bu kanalga zayafka yuborishlari kerak.",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_toggle_req_"))
@admin_only
async def admin_toggle_req(callback: CallbackQuery, **kwargs):
    ch_id = int(callback.data.split("_")[-1])
    channels = await get_required_channels(active_only=False)
    ch = next((c for c in channels if c['id'] == ch_id), None)
    if ch:
        new_status = 0 if ch['is_active'] else 1
        await toggle_required_channel(ch_id, new_status)
        status_text = "✅ Faollashtirildi!" if new_status else "❌ O'chirildi!"
        await callback.answer(status_text)
        channels = await get_required_channels(active_only=False)
        await callback.message.edit_reply_markup(
            reply_markup=admin_channels_keyboard(channels, "req")
        )


@router.callback_query(F.data.startswith("admin_del_req_"))
@admin_only
async def admin_del_req(callback: CallbackQuery, bot: Bot, **kwargs):
    ch_id = int(callback.data.split("_")[-1])
    channels = await get_required_channels(active_only=False)
    ch = next((c for c in channels if c['id'] == ch_id), None)
    await delete_required_channel(ch_id)
    if ch:
        points_channels = await get_points_channels(active_only=False)
        still_used = any(c['channel_id'] == ch['channel_id'] for c in points_channels)
        if not still_used:
            await leave_chat_safely(bot, ch['channel_id'])
    await callback.answer("🗑 O'chirildi!")
    channels = await get_required_channels(active_only=False)
    await callback.message.edit_reply_markup(
        reply_markup=admin_channels_keyboard(channels, "req")
    )


# ── POINTS CHANNELS ──────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_pts_channels")
@admin_only
async def admin_pts_channels(callback: CallbackQuery, **kwargs):
    channels = await get_points_channels(active_only=False)
    await callback.message.edit_text(
        "💰 <b>Bal kanallar</b>\n\nKanallarni boshqarish:",
        reply_markup=admin_channels_keyboard(channels, "pts"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_pts")
@admin_only
async def admin_add_pts_channel(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(AdminStates.adding_pts_channel)
    await callback.message.edit_text(
        "➕ <b>Bal kanali qo'shish</b>\n\n"
        "Kanaldagi istalgan xabarni <b>forward</b> qiling.\n\n"
        "Agar bot hali kanalda admin bo'lmasa, avval admin qilib qo'shing, "
        "keyin xabarni forward qiling.",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.adding_pts_channel)
@admin_only
async def admin_save_pts_channel(message: Message, state: FSMContext, bot: Bot, **kwargs):
    if not message.forward_from_chat:
        await message.answer("❌ Kanal xabarini forward qiling, matn emas.")
        return

    chat = message.forward_from_chat
    if chat.type != "channel":
        await message.answer("❌ Bu kanal emas. Kanal xabarini forward qiling.")
        return

    ch_id = str(chat.id)
    try:
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
        if status_value(member.status) != "administrator":
            await message.answer(
                f"❌ Bot <b>{chat.title}</b> kanalida admin emas.\n"
                "Botni kanalga admin qilib qo'shib, xabarni qayta forward qiling.",
                parse_mode="HTML"
            )
            return
    except Exception as e:
        await message.answer(
            f"❌ Bot <b>{chat.title}</b> kanalida admin emas.\n"
            f"Xatolik: {e}\n\nBotni admin qilib qo'shib, qayta forward qiling.",
            parse_mode="HTML"
        )
        return

    ch_username = chat.username or ""
    ch_name = chat.title or f"Kanal {ch_id}"
    await state.update_data(ch_id=ch_id, ch_name=ch_name, ch_username=ch_username)
    await state.set_state(AdminStates.setting_pts_amount)
    await message.answer(
        f"✅ Bot <b>{ch_name}</b> kanalida admin.\n\n"
        "Necha ball beriladi? Raqamni yuboring (masalan: 10):",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.setting_pts_amount)
@admin_only
async def admin_save_pts_amount(message: Message, state: FSMContext, **kwargs):
    try:
        points = int(message.text.strip())
        if points <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, musbat son kiriting (masalan: 10).")
        return

    data = await state.get_data()
    await add_points_channel(data["ch_id"], data["ch_name"], data["ch_username"], points)
    _pending_additions.pop(data.get("ch_id"), None)
    await state.clear()
    await message.answer(
        f"✅ <b>{data['ch_name']}</b> bal kanallarga qo'shildi! Ball: {points}",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_toggle_pts_"))
@admin_only
async def admin_toggle_pts(callback: CallbackQuery, **kwargs):
    ch_id = int(callback.data.split("_")[-1])
    channels = await get_points_channels(active_only=False)
    ch = next((c for c in channels if c['id'] == ch_id), None)
    if ch:
        new_status = 0 if ch['is_active'] else 1
        await toggle_points_channel(ch_id, new_status)
        status_text = "✅ Faollashtirildi!" if new_status else "❌ O'chirildi!"
        await callback.answer(status_text)
        channels = await get_points_channels(active_only=False)
        await callback.message.edit_reply_markup(
            reply_markup=admin_channels_keyboard(channels, "pts")
        )


@router.callback_query(F.data.startswith("admin_del_pts_"))
@admin_only
async def admin_del_pts(callback: CallbackQuery, bot: Bot, **kwargs):
    ch_id = int(callback.data.split("_")[-1])
    channels = await get_points_channels(active_only=False)
    ch = next((c for c in channels if c['id'] == ch_id), None)
    await delete_points_channel(ch_id)
    if ch:
        required_channels = await get_required_channels(active_only=False)
        still_used = any(c['channel_id'] == ch['channel_id'] for c in required_channels)
        if not still_used:
            await leave_chat_safely(bot, ch['channel_id'])
    await callback.answer("🗑 O'chirildi!")
    channels = await get_points_channels(active_only=False)
    await callback.message.edit_reply_markup(
        reply_markup=admin_channels_keyboard(channels, "pts")
    )


# ── BROADCAST ────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_broadcast")
@admin_only
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(AdminStates.broadcasting)
    await callback.message.edit_text(
        "✉️ <b>Xabar yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n\n"
        "📌 Matn, rasm, video, audio yoki Forward xabar — hammasi qabul qilinadi!\n\n"
        "⚠️ <i>Katta auditoriyaga xabar yuborish biroz vaqt olishi mumkin.</i>",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.broadcasting)
@admin_only
async def admin_do_broadcast(message: Message, bot: Bot, state: FSMContext, **kwargs):
    await state.clear()
    users = await get_all_users()
    total = len(users)
    sent = 0
    failed = 0

    status_msg = await message.answer(f"📤 Yuborish boshlandi... (0/{total})")

    for i, user in enumerate(users):
        try:
            await message.copy_to(user['telegram_id'])
            sent += 1
        except Exception:
            failed += 1

        if (i + 1) % 25 == 0:
            try:
                await status_msg.edit_text(f"📤 Yuborish davom etmoqda... ({i+1}/{total})")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"📤 Muvaffaqiyatli: <b>{sent}</b>\n"
        f"❌ Xato: <b>{failed}</b>\n"
        f"👥 Jami: <b>{total}</b>",
        parse_mode="HTML"
    )


@router.message(Command("check_channels"))
@admin_only
async def check_channels(message: Message, bot: Bot, **kwargs):
    channels = await get_required_channels(active_only=False)
    if not channels:
        await message.answer("Hech qanday kanal qo'shilmagan.")
        return
    lines = ["🔍 <b>Kanal tekshiruvi</b>\n"]
    for ch in channels:
        try:
            chat = await bot.get_chat(ch['channel_id'])
            member = await bot.get_chat_member(ch['channel_id'], (await bot.me()).id)
            lines.append(f"📢 {ch['channel_name']}")
            lines.append(f"   ID: {ch['channel_id']}")
            lines.append(f"   Status: {member.status}")
            lines.append(f"   Type: {chat.type}")
            lines.append(f"   Username: {chat.username or '—'}")
            lines.append(f"   Invite link: {chat.invite_link or '—'}")
            if hasattr(member, 'can_invite_users'):
                lines.append(f"   can_invite_users: {member.can_invite_users}")
        except Exception as e:
            lines.append(f"❌ {ch['channel_name']}: {e}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("kanal_tuzat"))
@admin_only
async def fix_all_channels_command(message: Message, bot: Bot, **kwargs):
    """Kutmasdan, hoziroq — barcha ro'yxatdagi kanallarni "zayavka"
    turiga o'tkazadi va har biri uchun yangi creates_join_request
    silka yaratadi. Eski (oddiy) uslubdagi kanallarni tuzatish uchun."""
    channels = await get_required_channels(active_only=False)
    if not channels:
        await message.answer("Hech qanday kanal qo'shilmagan.")
        return

    lines = ["🔧 <b>Kanallarni tuzatish</b>\n"]
    for ch in channels:
        ch_id = ch['channel_id']
        try:
            member = await bot.get_chat_member(ch_id, (await bot.me()).id)
            if member.status != "administrator":
                lines.append(f"❌ {ch['channel_name']}: bot admin emas, o'tkazib yuborildi")
                continue

            if ch.get("channel_type") != "request":
                await update_required_channel_type(ch_id, "request")

            link = await bot.create_chat_invite_link(ch_id, creates_join_request=True)
            await update_required_channel_invite_link(ch_id, link.invite_link)
            lines.append(f"✅ {ch['channel_name']}: yangi zayavka-silka yaratildi")
        except Exception as e:
            lines.append(f"❌ {ch['channel_name']}: {e}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("diag"))
@admin_only
async def diag(message: Message, bot: Bot, **kwargs):
    from database.db import count_pending_requests_by_channel, get_old_pending_requests_by_channel, get_required_channels
    channels = await get_required_channels(active_only=False)
    lines = ["📋 <b>Diagnostika</b>\n"]
    for ch in channels:
        count = await count_pending_requests_by_channel(ch['channel_id'])
        lines.append(f"📢 {ch['channel_name']}: {count} ta zayafka")
        if count:
            rows = await get_old_pending_requests_by_channel(ch['channel_id'], 3)
            for r in rows:
                lines.append(f"   👤 user_id={r['user_id']}, vaqt={r['requested_at']}")
    await message.answer("\n".join(lines), parse_mode="HTML")

    if not channels:
        await message.answer("Hech qanday kanal qo'shilmagan.")
        return

    lines = ["🔍 <b>Kanal tekshiruvi</b>\n"]
    for ch in channels:
        try:
            chat = await bot.get_chat(ch['channel_id'])
            member = await bot.get_chat_member(ch['channel_id'], (await bot.me()).id)
            lines.append(f"📢 {ch['channel_name']}")
            lines.append(f"   ID: <code>{ch['channel_id']}</code>")
            lines.append(f"   DB'dagi turi (channel_type): <b>{ch.get('channel_type')}</b>")
            invite_link_display = ch.get('invite_link') or "yo'q"
            lines.append(f"   DB'dagi invite_link: <code>{invite_link_display}</code>")
            lines.append(f"   Telegram chat.type: {chat.type}")
            lines.append(f"   Telegram chat.username: {chat.username or '—'}")
            lines.append(f"   Bot statusi: {member.status}")
            if hasattr(member, 'can_invite_users'):
                lines.append(f"   can_invite_users: {member.can_invite_users}")
        except Exception as e:
            lines.append(f"❌ {ch['channel_name']}: {e}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("tasdiqla"))
@admin_only
async def confirm_pending_command(message: Message, state: FSMContext, **kwargs):
    """Admin /tasdiqla deb yozsa — avval qaysi kanal uchun zayavkalarni
    tasdiqlash kerakligi so'raladi, kanal tanlangandan so'ng nechta
    zayavkani tasdiqlash kerakligi so'raladi, admin sonni yozgandan
    keyingina o'sha kanal uchun shuncha zayavka tasdiqlanadi."""
    await state.clear()
    channels = await get_managed_channels()

    if not channels:
        await message.answer(
            "📩 <b>Zayavkalarni tasdiqlash</b>\n\n"
            "❌ Hozircha hech qanday kanal qo'shilmagan.\n"
            "Avval \"Majburiy kanallar\" yoki \"Bal kanallari\" bo'limidan kanal qo'shing.",
            parse_mode="HTML"
        )
        return

    pending_counts = {}
    for ch in channels:
        count = await count_pending_requests_by_channel(ch['channel_id'])
        if count:
            pending_counts[ch['channel_id']] = count

    await message.answer(
        "📩 <b>Zayavkalarni tasdiqlash</b>\n\n"
        "Qaysi kanal uchun zayavkalarni tasdiqlaysiz? Kanalni tanlang:",
        reply_markup=accept_requests_channels_keyboard(channels, pending_counts),
        parse_mode="HTML"
    )


@router.message(Command("pending"))
@admin_only
async def pending_list(message: Message, **kwargs):
    channels = await get_managed_channels()
    if not channels:
        await message.answer("Hech qanday kanal qo'shilmagan.")
        return
    lines = ["📩 <b>Kutilayotgan zayavkalar</b>\n"]
    has_pending = False
    for ch in channels:
        count = await count_pending_requests_by_channel(ch['channel_id'])
        if count:
            has_pending = True
            lines.append(f"• {ch['channel_name']}: <b>{count} ta</b>")
    if not has_pending:
        lines.append("Hech qanday zayafka yo'q.")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ── ACCEPT REQUESTS (ZAYAVKALARNI TASDIQLASH) ────────────────────────────────
@router.callback_query(F.data == "admin_accept_requests")
@admin_only
async def admin_accept_requests(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    channels = await get_managed_channels()

    if not channels:
        await callback.message.edit_text(
            "📩 <b>Zayavkalarni tasdiqlash</b>\n\n"
            "❌ Hozircha hech qanday kanal qo'shilmagan.\n"
            "Avval \"Majburiy kanallar\" yoki \"Bal kanallari\" bo'limidan kanal qo'shing.",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    pending_counts = {}
    for ch in channels:
        count = await count_pending_requests_by_channel(ch['channel_id'])
        if count:
            pending_counts[ch['channel_id']] = count

    await callback.message.edit_text(
        "📩 <b>Zayavkalarni tasdiqlash</b>\n\n"
        "Qaysi kanal uchun zayavkalarni tasdiqlaysiz? Kanalni tanlang:",
        reply_markup=accept_requests_channels_keyboard(channels, pending_counts),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("accept_ch_"))
@admin_only
async def admin_accept_requests_select_channel(callback: CallbackQuery, state: FSMContext, **kwargs):
    channel_id = callback.data[len("accept_ch_"):]

    channels = await get_managed_channels()
    ch = next((c for c in channels if c['channel_id'] == channel_id), None)
    ch_name = ch['channel_name'] if ch else channel_id

    pending_count = await count_pending_requests_by_channel(channel_id)

    await state.set_state(AdminStates.setting_requests_count)
    await state.update_data(accept_channel_id=channel_id, accept_channel_name=ch_name)

    await callback.message.edit_text(
        f"📩 <b>Zayavkalarni tasdiqlash</b>\n\n"
        f"📢 Tanlangan kanal: <b>{ch_name}</b>\n"
        f"⏳ Kutilayotgan zayavkalar: <b>{pending_count}</b>\n\n"
        "Nechta zayavkani tasdiqlashni xohlaysiz? Sonini kiriting (masalan: 50):",
        reply_markup=back_keyboard("admin_accept_requests"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.setting_requests_count)
@admin_only
async def admin_accept_requests_do(message: Message, bot: Bot, state: FSMContext, **kwargs):
    data = await state.get_data()
    channel_id = data.get("accept_channel_id")
    ch_name = data.get("accept_channel_name", channel_id)

    if not channel_id:
        await state.clear()
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", reply_markup=admin_main_keyboard())
        return

    try:
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, musbat butun son kiriting (masalan: 50).")
        return

    await state.clear()
    requests = await get_old_pending_requests_by_channel(channel_id, count)

    if not requests:
        await message.answer(
            f"📢 <b>{ch_name}</b> uchun zayavkalar topilmadi.",
            reply_markup=admin_main_keyboard(),
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer(f"⏳ {len(requests)} ta zayavka tasdiqlanmoqda...")
    accepted = 0
    failed = 0
    auto_msg = await get_setting("auto_message")

    for req in requests:
        try:
            await bot.approve_chat_join_request(req['channel_id'], req['user_id'])
            await mark_request_processed(req['id'])
            accepted += 1
            try:
                await bot.send_message(req['user_id'], f"✅ So'rovingiz qabul qilindi!\n\n{auto_msg}", parse_mode="HTML")
            except Exception:
                pass
        except Exception:
            failed += 1
        await asyncio.sleep(0.1)

    await status_msg.edit_text(
        f"✅ <b>Jarayon yakunlandi!</b>\n\n"
        f"📢 Kanal: <b>{ch_name}</b>\n"
        f"✅ Tasdiqlandi: <b>{accepted}</b>\n"
        f"❌ Xato: <b>{failed}</b>",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )


# ── SETTINGS ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_settings")
@admin_only
async def admin_settings(callback: CallbackQuery, **kwargs):
    captcha = await get_setting("captcha_enabled")
    pts_ref = await get_setting("points_per_referral")
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if captcha == '1' else '❌'} Kaptcha",
        callback_data="toggle_captcha"
    ))
    builder.row(InlineKeyboardButton(
        text=f"👥 Taklif bali: {pts_ref}",
        callback_data="set_referral_pts"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))

    captcha_text = "✅ Yoqilgan" if captcha == '1' else "❌ O'chirilgan"
    await callback.message.edit_text(
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"Kaptcha: {captcha_text}\n"
        f"Taklif bali: {pts_ref}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_captcha")
@admin_only
async def toggle_captcha(callback: CallbackQuery, **kwargs):
    current = await get_setting("captcha_enabled")
    new = "0" if current == "1" else "1"
    await set_setting("captcha_enabled", new)
    await admin_settings(callback)


# ── AUTO-DETECT BOT ADDED/REMOVED ───────────────────────────────────────────
_pending_additions = {}

@router.my_chat_member()
async def bot_chat_member_handler(event: ChatMemberUpdated, bot: Bot, **kwargs):
    log = logging.getLogger(__name__)
    chat = event.chat

    if chat.type not in ("channel", "supergroup", "group"):
        return

    ch_id = str(chat.id)
    ch_name = chat.title or f"Kanal {ch_id}"
    ch_username = chat.username or ""

    new = status_value(event.new_chat_member.status)
    old = status_value(event.old_chat_member.status)

    if new == "administrator":
        existing_req = await get_required_channels(active_only=False)
        existing_pts = await get_points_channels(active_only=False)
        in_req = any(c['channel_id'] == ch_id for c in existing_req)
        in_pts = any(c['channel_id'] == ch_id for c in existing_pts)

        if not in_req and not in_pts:
            _pending_additions[ch_id] = {"name": ch_name, "username": ch_username}
            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="📢 Majburiy", callback_data=f"pend_req_{ch_id}"),
                InlineKeyboardButton(text="💰 Balli", callback_data=f"pend_pts_{ch_id}"),
                InlineKeyboardButton(text="❌", callback_data=f"pend_ignore_{ch_id}"),
            )
            for uid in ADMIN_IDS:
                try:
                    await bot.send_message(
                        uid,
                        f"📢 <b>{ch_name}</b> kanaliga bot qo'shildi.\n\n"
                        "Bu kanal qanday turdagi?",
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    log.warning(f"Admin {uid} ga xabar yuborib bo'lmadi: {e}")
        else:
            log.info(f"Kanal allaqachon bazada: {ch_name} ({ch_id})")

    elif new in ("left", "kicked") and old in ("administrator", "member"):
        for lst in [get_required_channels, get_points_channels]:
            channels = await lst(active_only=False)
            for ch in channels:
                if ch['channel_id'] == ch_id:
                    if lst == get_required_channels:
                        await delete_required_channel(ch['id'])
                    else:
                        await delete_points_channel(ch['id'])
                    log.info(f"Bot chiqarildi, bazadan o'chirildi: {ch_name} ({ch_id})")
                    break


# ── AUTO-CREATE ZAYAVKA (JOIN REQUEST) SILKASI KANALGA POST TASHLANGANDA ────
# Ishlash tartibi: kanalga botni admin qilib qo'yasiz → kanalga istalgan
# post tashlaysiz → bot shu postni ko'radi, kanalni bazaga (agar hali
# qo'shilmagan bo'lsa) qo'shadi va o'zi uchun "zayavka talab qiladigan"
# yangi taklif silkasi (invite link) yaratadi. Botdagi obunachilar aynan
# shu silka orqali o'tishadi va ular avtomatik "zayavka" sifatida saqlanadi.
@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_message_auto_register(message: Message, bot: Bot, **kwargs):
    log = logging.getLogger(__name__)
    chat = message.chat
    ch_id = str(chat.id)

    try:
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
    except Exception as e:
        log.warning(f"group auto-register: get_chat_member xato: {e}")
        return

    if status_value(member.status) != "administrator":
        return

    await ensure_required_channel_registered(bot, chat, log)


@router.channel_post()
async def channel_post_auto_link(message: Message, bot: Bot, **kwargs):
    log = logging.getLogger(__name__)
    chat = message.chat
    ch_id = str(chat.id)

    try:
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
    except Exception as e:
        log.warning(f"channel_post: get_chat_member xato: {e}")
        return

    if status_value(member.status) != "administrator":
        # Bot admin emas — silka yaratib bo'lmaydi
        return

    existing_req = await get_required_channels(active_only=False)
    existing_pts = await get_points_channels(active_only=False)
    ch = next((c for c in existing_req if c['channel_id'] == ch_id), None)
    in_pts = any(c['channel_id'] == ch_id for c in existing_pts)

    if ch:
        needs_new_link = False
        if ch.get("channel_type") != "request":
            await update_required_channel_type(ch_id, "request")
            needs_new_link = True
        if needs_new_link or not ch.get("invite_link"):
            try:
                link = await bot.create_chat_invite_link(chat.id, creates_join_request=True)
                await update_required_channel_invite_link(ch_id, link.invite_link)
                log.info(f"Kanal uchun yangi zayavka-silkasi yaratildi: {ch_id}")
            except Exception as e:
                log.warning(f"Invite link yaratib bo'lmadi ({ch_id}): {e}")
    elif in_pts:
        log.info(f"channel_post: kanal bal kanallarida bor, o'tkazib yuborildi: {ch_id}")
    else:
        if ch_id not in _pending_additions:
            _pending_additions[ch_id] = {"name": chat.title or ch_id, "username": chat.username or ""}
            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="📢 Majburiy", callback_data=f"pend_req_{ch_id}"),
                InlineKeyboardButton(text="💰 Balli", callback_data=f"pend_pts_{ch_id}"),
                InlineKeyboardButton(text="❌", callback_data=f"pend_ignore_{ch_id}"),
            )
            for uid in ADMIN_IDS:
                try:
                    await bot.send_message(
                        uid,
                        f"📢 <b>{chat.title or ch_id}</b> kanaliga post tashlandi.\n\n"
                        "Bu kanal qanday turdagi?",
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        log.info(f"channel_post orqali yangi kanal topildi, admin kutilyapti: {ch_id}")


@router.callback_query(F.data.startswith("pend_req_"))
@admin_only
async def pending_required(callback: CallbackQuery, bot: Bot, **kwargs):
    log = logging.getLogger(__name__)
    ch_id = callback.data[len("pend_req_"):]
    info = _pending_additions.pop(ch_id, None)
    if not info:
        await callback.answer("Bu kanal bo'yicha so'rov muddati o'tgan.", show_alert=True)
        return
    await callback.message.edit_text(f"📢 <b>{info['name']}</b> majburiy kanal sifatida qo'shilmoqda...", parse_mode="HTML")
    try:
        chat = await bot.get_chat(ch_id)
        await ensure_required_channel_registered(bot, chat, log)
        await callback.message.edit_text(
            f"✅ <b>{info['name']}</b> majburiy kanalga qo'shildi!\n\n"
            "Foydalanuvchilar start bosganda bu kanalga zayafka yuborishlari kerak.",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pend_pts_"))
@admin_only
async def pending_points(callback: CallbackQuery, state: FSMContext, **kwargs):
    ch_id = callback.data[len("pend_pts_"):]
    info = _pending_additions.get(ch_id)
    if not info:
        await callback.answer("Bu kanal bo'yicha so'rov muddati o'tgan.", show_alert=True)
        return
    await state.set_state(AdminStates.setting_pts_amount)
    await state.update_data(ch_id=ch_id, ch_name=info["name"], ch_username=info.get("username", ""))
    await callback.message.edit_text(
        f"💰 <b>{info['name']}</b> uchun necha ball beriladi?\n\n"
        "Sonni yuboring (masalan: 10):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pend_ignore_"))
@admin_only
async def pending_ignore(callback: CallbackQuery, **kwargs):
    ch_id = callback.data[len("pend_ignore_"):]
    info = _pending_additions.pop(ch_id, None)
    await callback.message.edit_text(
        f"❌ <b>{info['name'] if info else ch_id}</b> o'tkazib yuborildi.",
        parse_mode="HTML"
    )
    await callback.answer()
