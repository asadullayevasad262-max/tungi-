from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatJoinRequest
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from database.db import (
    get_user, create_user, get_required_channels,
    mark_user_verified, get_setting, get_user_by_referral,
    update_user_points, save_pending_request
)
from utils.keyboards import (
    main_menu_keyboard, required_channels_keyboard,
    generate_captcha, captcha_keyboard
)
from utils.helpers import check_user_subscriptions, get_channel_links, is_user_subscribed_all

router = Router()

@router.message(Command("id"))
async def id_handler(message: Message):
    reply = message.reply_to_message
    if reply and reply.forward_from_chat:
        ch = reply.forward_from_chat
        text = (
            f"📢 <b>Kanal ma'lumotlari</b>\n\n"
            f"🏷 Nomi: <b>{ch.title}</b>\n"
            f"🆔 ID: <code>{ch.id}</code>\n"
        )
        if ch.username:
            text += f"🌐 Username: @{ch.username}\n"
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(
            "Kanal ID sini olish uchun kanaldan xabarni forward qilib, "
            "so'ng o'sha xabarga reply qilib /id yozing.\n\n"
            "Misol: kanaldan xabar forward qiling → reply → /id",
            parse_mode="HTML"
        )


# Store captcha answers temporarily (in production, use FSM or Redis)
captcha_store = {}


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split()
    ref_code = args[1] if len(args) > 1 else None

    # Check referral
    referrer_id = None
    if ref_code:
        referrer = await get_user_by_referral(ref_code)
        if referrer and referrer['telegram_id'] != user_id:
            referrer_id = referrer['telegram_id']

    user = await get_user(user_id)
    is_new = user is None

    if is_new:
        user = await create_user(
            telegram_id=user_id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name or "",
            referred_by=referrer_id
        )
        user = await get_user(user_id)

    # Check required channels
    channels = await get_required_channels(active_only=True)
    if channels:
        statuses = await check_user_subscriptions(bot, user_id, channels)
        not_subscribed = [ch for ch in channels if not statuses.get(ch['channel_id'], False)]
        if not_subscribed:
            text = (
                "👋 <b>Xush kelibsiz!</b>\n\n"
                "Botdan foydalanish uchun quyidagi kanallarga qo'shiling yoki "
                "so'rov yuboring, so'ng \"✅ Tekshirish\" tugmasini bosing:"
            )
            links = await get_channel_links(bot, channels)
            kb = required_channels_keyboard(channels, statuses, links)
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
            return

    # Show captcha if not verified
    if not user['is_verified']:
        await show_captcha(message.answer, user_id)
        return

    await show_main_menu(message, is_new, referrer_id, user_id)


async def show_captcha(answer_fn, user_id: int):
    correct, options = generate_captcha()
    captcha_store[user_id] = correct
    await answer_fn(
        "🔐 <b>Tasdiqlash</b>\n\n"
        "Bot emasligingizni isbotlash uchun quyidagi 4 xonali raqamni toping va bosing:\n\n"
        f"<b>Kerakli raqam: <code>{correct}</code></b>",
        reply_markup=captcha_keyboard(correct, options),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("captcha_"))
async def captcha_answer(callback: CallbackQuery, bot: Bot):
    _, chosen, correct = callback.data.split("_")
    user_id = callback.from_user.id

    if int(chosen) == int(correct):
        await mark_user_verified(user_id)
        captcha_store.pop(user_id, None)

        # Check referral bonus
        user = await get_user(user_id)
        if user and user['referred_by']:
            pts = int(await get_setting("points_per_referral") or 20)
            await update_user_points(user['referred_by'], pts)
            try:
                await bot.send_message(
                    user['referred_by'],
                    f"🎉 Taklif bonusi! Yangi foydalanuvchi taklif havolangiz orqali qo'shildi.\n"
                    f"+{pts} ball sizning hisobingizga qo'shildi! 🏅"
                )
            except Exception:
                pass

        # Send auto message
        auto_msg = await get_setting("auto_message")
        await callback.message.edit_text(
            f"✅ <b>Tabriklaymiz! Siz muvaffaqiyatli tasdiqlandingiz!</b>\n\n{auto_msg}",
            parse_mode="HTML"
        )
        await show_main_menu(callback.message, True, user['referred_by'] if user else None, user_id)
    else:
        correct_val, options = generate_captcha()
        captcha_store[user_id] = correct_val
        await callback.message.edit_text(
            "❌ <b>Noto'g'ri!</b> Qaytadan urinib ko'ring:\n\n"
            f"<b>Kerakli raqam: <code>{correct_val}</code></b>",
            reply_markup=captcha_keyboard(correct_val, options),
            parse_mode="HTML"
        )
    await callback.answer()


async def show_main_menu(message: Message, is_new: bool, referrer_id, user_id: int):
    if is_new:
        welcome = "🌟 <b>Botimizga xush kelibsiz!</b>\n\nQuyidagi menyudan foydalaning:"
    else:
        welcome = "🏠 <b>Asosiy menyu</b>\n\nQuyidagi bo'limlardan birini tanlang:"
    await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    channels = await get_required_channels(active_only=True)
    statuses = await check_user_subscriptions(bot, user_id, channels)
    not_subscribed = [ch for ch in channels if not statuses.get(ch['channel_id'], False)]

    if not_subscribed:
        links = await get_channel_links(bot, channels)
        kb = required_channels_keyboard(channels, statuses, links)
        await callback.message.edit_text(
            "⏳ Hali barcha kanallarga qo'shilmagansiz.\n\n"
            "Iltimos, barcha kanallarga qo'shiling yoki so'rov yuboring:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer("❌ Hali barcha kanallarga qo'shilmagansiz!", show_alert=True)
    else:
        user = await get_user(user_id)
        if not user['is_verified']:
            await callback.message.delete()
            await show_captcha(callback.message.answer, user_id)
        else:
            await callback.message.delete()
            await show_main_menu(callback.message, False, None, user_id)
        await callback.answer("✅ Ajoyib!")


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# Handle join requests for private channels
@router.chat_join_request()
async def join_request_handler(event: ChatJoinRequest, **kwargs):
    msg = f"[JOIN_REQUEST] user={event.from_user.id}, channel={event.chat.id}, channel_type={event.chat.type}"
    print(msg)
    import logging
    logging.getLogger(__name__).info(msg)
    try:
        await save_pending_request(str(event.chat.id), event.from_user.id)
        print(f"[JOIN_REQUEST] Saved OK")
    except Exception as e:
        print(f"[JOIN_REQUEST] ERROR: {e}")
