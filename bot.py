"""
Telegram qrup mühafizə botu — yeni üzvlər üçün CAPTCHA / robot doğrulaması.

İş prinsipi:
  1. Bir nəfər qrupa daxil olanda dərhal SUSDURULUR (mute).
  2. Bota şəkildə təhrif olunmuş yazı + variant düymələri göndərir.
  3. Üzvün cavablamağa 30 saniyəsi var.
       • Düzgün seçərsə  -> mute götürülür, qrupda yaza bilər.
       • Yanlış seçərsə   -> mute davam edir.
       • Vaxt bitərsə      -> mute davam edir.

Konfiqurasiya (mühit dəyişənləri / environment variables):
  BOT_TOKEN          -> @BotFather-dən aldığınız token (MƏCBURİ)
  CAPTCHA_TIMEOUT    -> cavab vaxtı saniyə ilə (default 30)
  CAPTCHA_OPTIONS    -> variant sayı (default 4)
  KICK_ON_FAIL       -> "1" olarsa yanlış/vaxt bitəndə qrupdan atır (default 0 = sadəcə mute qalır)
"""
import logging
import os

from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from captcha import random_code, make_captcha_image, make_options

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("captcha-bot")

# --- Konfiqurasiya ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
TIMEOUT = int(os.environ.get("CAPTCHA_TIMEOUT", "30"))
N_OPTIONS = int(os.environ.get("CAPTCHA_OPTIONS", "4"))
KICK_ON_FAIL = os.environ.get("KICK_ON_FAIL", "0") == "1"

# İşləmə rejimi: "webhook" (Render Web Service) və ya "polling" (Background Worker / lokal)
MODE = os.environ.get("MODE", "polling").strip().lower()
# Render avtomatik təyin edir; lokal üçün default 10000
PORT = int(os.environ.get("PORT", "10000"))
# Webhook üçün public URL. Render avtomatik RENDER_EXTERNAL_URL verir.
WEBHOOK_BASE = (
    os.environ.get("WEBHOOK_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or ""
).strip().rstrip("/")
# İstəyə görə əlavə təhlükəsizlik (Telegram-ın göndərdiyini təsdiqləyir)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()

# Tam susdurma icazələri (heç nə yaza bilməz)
MUTED = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)

# Doğrulamadan keçəndən sonrakı icazələr:
# YALNIZ mətn mesajı göndərə bilir; şəkil/video/audio/sənəd/poll/link və s. YOX.
UNMUTED = ChatPermissions(
    can_send_messages=True,        # yalnız mətn mesajı
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,   # stiker/GIF/inline botlar
    can_add_web_page_previews=False,
)


def _key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}:{user_id}"


async def on_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yeni üzv qoşulanda işə düşür."""
    cmu = update.chat_member
    if cmu is None:
        return

    old = cmu.old_chat_member.status
    new = cmu.new_chat_member.status

    # Yalnız YENİ qoşulmaları tut (left/kicked -> member)
    joined = (
        new == ChatMemberStatus.MEMBER
        and old in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)
    )
    if not joined:
        return

    user = cmu.new_chat_member.user
    chat = cmu.chat

    if user.is_bot:
        return  # botları (məs. admin tərəfindən əlavə edilən) toxunmuruq

    # 1) Dərhal susdur
    try:
        await context.bot.restrict_chat_member(
            chat.id, user.id, permissions=MUTED
        )
    except Exception as e:
        log.error("Susdurmaq alınmadı (bot admin deyil?): %s", e)
        return

    # 2) CAPTCHA hazırla
    code = random_code()
    options = make_options(code, N_OPTIONS)
    image = make_captcha_image(code)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(opt, callback_data=f"cap:{user.id}:{opt}")
                for opt in options[i : i + 2]
            ]
            for i in range(0, len(options), 2)
        ]
    )

    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    caption = (
        f"👋 Salam {mention}!\n\n"
        f"🤖 Robot doğrulaması. Zəhmət olmasa şəkildəki yazını "
        f"aşağıdakı variantlardan seçin.\n"
        f"⏱ {TIMEOUT} saniyə vaxtınız var. Səhv seçim = susdurulmuş qalırsınız."
    )

    msg = await context.bot.send_photo(
        chat.id,
        photo=image,
        caption=caption,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

    # 3) Vəziyyəti saxla + 30 san. timeout planla
    k = _key(chat.id, user.id)
    context.bot_data.setdefault("pending", {})
    context.bot_data["pending"][k] = {
        "code": code,
        "msg_id": msg.message_id,
        "chat_id": chat.id,
        "user_id": user.id,
        "name": user.full_name,
    }

    context.job_queue.run_once(
        on_timeout,
        TIMEOUT,
        data={"key": k},
        name=k,
    )


async def on_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Vaxt bitdi və üzv cavablamayıb."""
    k = context.job.data["key"]
    pending = context.bot_data.get("pending", {})
    info = pending.pop(k, None)
    if not info:
        return  # artıq cavablanıb

    chat_id, user_id = info["chat_id"], info["user_id"]

    # CAPTCHA mesajını sil
    try:
        await context.bot.delete_message(chat_id, info["msg_id"])
    except Exception:
        pass

    if KICK_ON_FAIL:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)  # ban-ı götür ki, yenidən qoşula bilsin
        except Exception as e:
            log.error("Atmaq alınmadı: %s", e)
    # else: heç nə etmirik — üzv susdurulmuş qalır.
    log.info("Timeout: %s doğrulamadı, susdurulmuş qalır.", info["name"])


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Düymə basılanda işə düşür."""
    q = update.callback_query
    try:
        _, target_id, choice = q.data.split(":", 2)
        target_id = int(target_id)
    except ValueError:
        await q.answer()
        return

    clicker = q.from_user.id

    # Yalnız doğrulanan üzv öz düyməsinə basa bilər
    if clicker != target_id:
        await q.answer("Bu doğrulama sizin üçün deyil. 🙅", show_alert=True)
        return

    chat_id = q.message.chat.id
    k = _key(chat_id, target_id)
    pending = context.bot_data.get("pending", {})
    info = pending.get(k)

    if not info:
        await q.answer("Bu doğrulamanın vaxtı bitib.", show_alert=True)
        return

    if choice == info["code"]:
        # DÜZGÜN — mute götür
        pending.pop(k, None)
        # planlanmış timeout job-u ləğv et
        for job in context.job_queue.get_jobs_by_name(k):
            job.schedule_removal()
        try:
            await context.bot.restrict_chat_member(
                chat_id, target_id, permissions=UNMUTED
            )
        except Exception as e:
            log.error("Mute götürmək alınmadı: %s", e)
        await q.answer("✅ Doğrulama uğurlu! Xoş gəlmisiniz.", show_alert=False)
        try:
            await context.bot.delete_message(chat_id, info["msg_id"])
        except Exception:
            pass
    else:
        # YANLIŞ — susdurulmuş qalır
        await q.answer(
            "❌ Yanlış cavab. Susdurulmuş qalırsınız.", show_alert=True
        )
        if KICK_ON_FAIL:
            pending.pop(k, None)
            for job in context.job_queue.get_jobs_by_name(k):
                job.schedule_removal()
            try:
                await context.bot.delete_message(chat_id, info["msg_id"])
                await context.bot.ban_chat_member(chat_id, target_id)
                await context.bot.unban_chat_member(chat_id, target_id)
            except Exception as e:
                log.error("Atmaq alınmadı: %s", e)


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN mühit dəyişəni təyin edilməyib!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ChatMemberHandler(on_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(on_answer, pattern=r"^cap:"))

    if MODE == "webhook":
        if not WEBHOOK_BASE:
            raise SystemExit(
                "Webhook rejimi üçün WEBHOOK_URL və ya RENDER_EXTERNAL_URL lazımdır!"
            )
        webhook_url = f"{WEBHOOK_BASE}/{BOT_TOKEN}"
        log.info("Webhook rejimi işə düşdü: %s (port %s)", webhook_url, PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        log.info("Polling rejimi işə düşdü. CTRL+C ilə dayandırın.")
        # chat_member yeniliklərini almaq üçün allowed_updates vacibdir
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
