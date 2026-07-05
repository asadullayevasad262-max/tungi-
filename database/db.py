from supabase import create_async_client, AsyncClient

_client: AsyncClient = None

SUPABASE_URL = "https://lstzekyhmkpmcutvbxxa.supabase.co"
SUPABASE_KEY = "sb_publishable_BjH5YzwN2KEbK30wIt_qzg_xEf374zB"


async def get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = await create_async_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


async def init_db():
    client = await get_client()
    defaults = [
        ("auto_message", "🎉 Botimizga xush kelibsiz! Siz muvaffaqiyatli ro'yxatdan o'tdingiz."),
        ("gifts_text", "🎁 <b>Sovg'alar va Konkurslar</b>\n\nHozircha faol konkurs mavjud emas. Kuzatib boring!"),
        ("points_welcome_text", "💰 <b>Bal yig'ish</b>\n\nQuyidagi usullar orqali ball yig'ishingiz mumkin:"),
        ("referral_ad_text", "👥 <b>Do'stlaringizni taklif qiling!</b>\n\nHar bir taklif uchun <b>20 ball</b> oling!"),
        ("rules_text", "📋 <b>Qoidalar</b>\n\n1. Botdan halol foydalaning.\n2. Spam yuborilmasin.\n3. Boshqa foydalanuvchilarga hurmat bilan munosabatda bo'ling.\n\nQoidalarni buzganlar bloklanadi."),
        ("donate_text", "💝 <b>Donat qilish</b>\n\nBotni rivojlantirish uchun qo'llab-quvvatlashingiz mumkin.\n\nRekvizitlar: ...\n\nHar bir donat uchun rahmat! 🙏"),
        ("points_per_referral", "20"),
        ("captcha_enabled", "1"),
    ]
    for key, value in defaults:
        result = await client.table("settings").select("key").eq("key", key).execute()
        if not result.data:
            await client.table("settings").insert({"key": key, "value": value}).execute()


async def get_setting(key: str) -> str:
    client = await get_client()
    result = await client.table("settings").select("value").eq("key", key).execute()
    return result.data[0]["value"] if result.data else ""


async def set_setting(key: str, value: str):
    client = await get_client()
    await client.table("settings").upsert({"key": key, "value": value}).execute()


async def get_user(telegram_id: int):
    client = await get_client()
    result = await client.table("users").select("*").eq("telegram_id", telegram_id).execute()
    return result.data[0] if result.data else None


async def create_user(telegram_id: int, username: str, full_name: str, referred_by: int = None):
    import random, string
    ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    client = await get_client()
    result = await client.table("users").insert({
        "telegram_id": telegram_id,
        "username": username,
        "full_name": full_name,
        "referral_code": ref_code,
        "referred_by": referred_by
    }).execute()
    return result.data[0] if result.data else None


async def update_user_points(telegram_id: int, points: int):
    client = await get_client()
    user = await get_user(telegram_id)
    if user:
        new_points = (user.get("points") or 0) + points
        await client.table("users").update({"points": new_points}).eq("telegram_id", telegram_id).execute()


async def get_user_rank(telegram_id: int) -> int:
    client = await get_client()
    user = await get_user(telegram_id)
    if not user:
        return 0
    result = await client.table("users").select("id", count="exact").gt("points", user.get("points") or 0).execute()
    return (result.count or 0) + 1


async def get_top_users(limit: int = 100):
    client = await get_client()
    result = await client.table("users").select("*").order("points", desc=True).limit(limit).execute()
    return result.data


async def get_all_users():
    client = await get_client()
    result = await client.table("users").select("*").execute()
    return result.data


async def get_required_channels(active_only=True):
    client = await get_client()
    query = client.table("required_channels").select("*")
    if active_only:
        query = query.eq("is_active", 1)
    result = await query.execute()
    return result.data


async def add_required_channel(channel_id: str, channel_name: str, channel_username: str, channel_type: str, points: int, invite_link: str = None):
    client = await get_client()
    data = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_username": channel_username,
        "channel_type": channel_type,
        "points_reward": points,
    }
    if invite_link is not None:
        data["invite_link"] = invite_link
    await client.table("required_channels").insert(data).execute()


async def update_required_channel_invite_link(channel_id: str, invite_link: str):
    client = await get_client()
    await client.table("required_channels").update({"invite_link": invite_link}).eq("channel_id", channel_id).execute()


async def update_required_channel_type(channel_id: str, channel_type: str):
    client = await get_client()
    await client.table("required_channels").update({"channel_type": channel_type}).eq("channel_id", channel_id).execute()


async def toggle_required_channel(channel_db_id: int, is_active: int):
    client = await get_client()
    await client.table("required_channels").update({"is_active": is_active}).eq("id", channel_db_id).execute()


async def delete_required_channel(channel_db_id: int):
    client = await get_client()
    await client.table("required_channels").delete().eq("id", channel_db_id).execute()


async def get_points_channels(active_only=True):
    client = await get_client()
    query = client.table("points_channels").select("*")
    if active_only:
        query = query.eq("is_active", 1)
    query = query.order("sort_order")
    result = await query.execute()
    return result.data


async def add_points_channel(channel_id: str, channel_name: str, channel_username: str, points: int):
    client = await get_client()
    result = await client.table("points_channels").select("sort_order").order("sort_order", desc=True).limit(1).execute()
    next_order = (result.data[0]["sort_order"] if result.data else 0) + 1
    await client.table("points_channels").insert({
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_username": channel_username,
        "points_reward": points,
        "sort_order": next_order
    }).execute()


async def toggle_points_channel(channel_db_id: int, is_active: int):
    client = await get_client()
    await client.table("points_channels").update({"is_active": is_active}).eq("id", channel_db_id).execute()


async def delete_points_channel(channel_db_id: int):
    client = await get_client()
    await client.table("points_channels").delete().eq("id", channel_db_id).execute()


async def check_user_earned_channel_points(user_id: int, channel_id: str) -> bool:
    client = await get_client()
    result = await client.table("user_channel_points").select("id").eq("user_id", user_id).eq("channel_id", channel_id).execute()
    return bool(result.data)


async def mark_user_channel_points(user_id: int, channel_id: str):
    client = await get_client()
    await client.table("user_channel_points").insert({
        "user_id": user_id,
        "channel_id": channel_id
    }).execute()


async def get_stats():
    from datetime import datetime, timedelta, timezone
    client = await get_client()
    total = await client.table("users").select("id", count="exact").execute()
    verified = await client.table("users").select("id", count="exact").eq("is_verified", 1).execute()
    total_points = await client.table("users").select("points").execute()
    points_sum = sum(u.get("points") or 0 for u in total_points.data)
    one_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    today = await client.table("users").select("id", count="exact").gte("joined_at", one_day_ago).execute()
    return {
        "total": total.count or 0,
        "verified": verified.count or 0,
        "total_points": points_sum,
        "today": today.count or 0
    }


async def get_user_by_referral(ref_code: str):
    client = await get_client()
    result = await client.table("users").select("*").eq("referral_code", ref_code).execute()
    return result.data[0] if result.data else None


async def mark_user_verified(telegram_id: int):
    client = await get_client()
    await client.table("users").update({"is_verified": 1}).eq("telegram_id", telegram_id).execute()


async def save_pending_request(channel_id: str, user_id: int):
    import logging
    try:
        client = await get_client()
        existing = await client.table("pending_join_requests").select("id").eq("channel_id", str(channel_id)).eq("user_id", user_id).eq("is_processed", 0).execute()
        if existing.data:
            return
        await client.table("pending_join_requests").insert({
            "channel_id": str(channel_id),
            "user_id": user_id
        }).execute()
    except Exception as e:
        logging.getLogger(__name__).error(f"save_pending_request error: {e}")


async def has_pending_request(channel_id: str, user_id: int) -> bool:
    try:
        client = await get_client()
        result = await client.table("pending_join_requests").select("id").eq("channel_id", str(channel_id)).eq("user_id", user_id).eq("is_processed", 0).execute()
        return bool(result.data)
    except Exception:
        return False


async def get_old_pending_requests(limit: int = 50):
    client = await get_client()
    result = await client.table("pending_join_requests").select("*").eq("is_processed", 0).order("requested_at").limit(limit).execute()
    return result.data


async def get_managed_channels():
    client = await get_client()
    req = await client.table("required_channels").select("channel_id, channel_name, channel_username").execute()
    pts = await client.table("points_channels").select("channel_id, channel_name, channel_username").execute()
    seen = set()
    result = []
    for row in (req.data or []) + (pts.data or []):
        if row["channel_id"] not in seen:
            seen.add(row["channel_id"])
            result.append(row)
    return result


async def get_old_pending_requests_by_channel(channel_id: str, limit: int = 50):
    client = await get_client()
    result = await client.table("pending_join_requests").select("*").eq("channel_id", channel_id).eq("is_processed", 0).order("requested_at").limit(limit).execute()
    return result.data


async def count_pending_requests_by_channel(channel_id: str) -> int:
    client = await get_client()
    result = await client.table("pending_join_requests").select("id", count="exact").eq("channel_id", channel_id).eq("is_processed", 0).execute()
    return result.count or 0


async def mark_request_processed(req_id: int):
    client = await get_client()
    await client.table("pending_join_requests").update({"is_processed": 1}).eq("id", req_id).execute()
