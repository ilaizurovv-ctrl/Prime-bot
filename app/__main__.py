import asyncio
import hashlib
import hmac
import logging
import os
import signal

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from app.config import settings
from app.db import engine, init_db
from app.handlers.start import router as start_router
from app.handlers.deals import router as deals_router
from app.handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prime_bot")


async def healthcheck(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "prime-bot"})


async def telegram_webhook(request: web.Request) -> web.Response:
    expected = request.app["webhook_secret"]
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(supplied, expected):
        return web.Response(status=403, text="Forbidden")

    try:
        payload = await request.json()
        update = Update.model_validate(payload, context={"bot": request.app["bot"]})
        await request.app["dispatcher"].feed_update(request.app["bot"], update)
    except Exception:
        logger.exception("Failed to process Telegram webhook update")
        return web.Response(status=500, text="Update processing failed")

    return web.Response(text="OK")


async def main() -> None:
    await init_db()

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(deals_router)
    dispatcher.include_router(admin_router)

    webhook_secret = settings.webhook_secret or hashlib.sha256(
        (settings.bot_token + ":prime-bot-webhook-v1").encode()
    ).hexdigest()

    hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if not hostname:
        raise RuntimeError("RENDER_EXTERNAL_HOSTNAME is missing; webhook hosting requires Render")

    webhook_url = f"https://{hostname}/telegram/webhook"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=webhook_secret,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )

    app = web.Application()
    app["bot"] = bot
    app["dispatcher"] = dispatcher
    app["webhook_secret"] = webhook_secret
    app.router.add_get("/healthz", healthcheck)
    app.router.add_post("/telegram/webhook", telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info("Prime Bot webhook server listening on port %s", port)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    finally:
        await runner.cleanup()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
