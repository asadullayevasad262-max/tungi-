from aiogram import Bot
from aiogram.types import ChatMember
from database.db import get_required_channels, update_required_channel_invite_link

ADMIN_IDS = [1490312159, 8089597197]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


import logging

async def get_channel_links(bot: Bot, channels: list) -> dict:
    log = logging.getLogger(__name__)
    links = {}
    for ch in channels:
        stored = ch.get('invite_link')
        if stored:
            links[ch['channel_id']] = stored
            continue
        try:
            link = await bot.create_chat_invite_link(
                ch['channel_id'],
                creates_join_request=True
            )
            links[ch['channel_id']] = link.invite_link
            await update_required_channel_invite_link(ch['channel_id'], link.invite_link)
        except Exception as e:
            log.warning(f"get_channel_links failed for {ch['channel_id']}: {e}")
            links[ch['channel_id']] = None
    return links


async def check_user_subscriptions(bot: Bot, user_id: int, channels: list) -> dict:
    statuses = {}
    from database.db import has_pending_request
    for ch in channels:
        pending = await has_pending_request(ch['channel_id'], user_id)
        if pending:
            statuses[ch['channel_id']] = True
            continue
        try:
            member: ChatMember = await bot.get_chat_member(
                chat_id=ch['channel_id'],
                user_id=user_id
            )
            is_sub = member.status not in ('left', 'kicked', 'banned')
            statuses[ch['channel_id']] = is_sub
        except Exception:
            statuses[ch['channel_id']] = False
    return statuses


async def is_user_subscribed_all(bot: Bot, user_id: int) -> bool:
    channels = await get_required_channels(active_only=True)
    if not channels:
        return True
    statuses = await check_user_subscriptions(bot, user_id, channels)
    return all(statuses.values())


def format_number(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def ordinal_uz(n: int) -> str:
    return f"{n}-o'rin"
