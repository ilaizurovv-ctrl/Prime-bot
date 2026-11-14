# Prime Bot — OTC testnet scaffold

Python 3.12, aiogram 3, PostgreSQL. Configured for TON Testnet and a 1.5% fee.

## Implemented
- Telegram user registration and buyer deep-links
- Demo deals with `/createdemo amount description`
- NFT deal records for Telegram Gifts and TON NFTs
- `/mydeals`, `/deal CODE`, `/dispute CODE`
- Manual manager workflow: `/nftreceived CODE`, `/nftverified CODE`, `/nftdelivered CODE`
- Internal TON, RUB and Telegram Stars ledgers with admin adjustments
- Telegram webhook endpoint and `/healthz` health check for Render Web Services

## Free deployment architecture
- Render Free Web Service runs the Telegram webhook (not long polling).
- Neon Free PostgreSQL stores users, deals and ledger records.
- No Render Postgres database or paid Render worker is created.
- Render's free web service may spin down when idle; the first request after idle can be delayed. Telegram retries webhook deliveries when the service is unavailable, but this is not an always-on SLA.

### Setup
1. Create a free PostgreSQL project on Neon.
2. Copy its pooled or direct connection string. It must use SSL; Neon provides a connection string with SSL enabled. In Render, set it as `DATABASE_URL`. The application converts `postgres://` / `postgresql://` to the SQLAlchemy asyncpg driver URL.
3. Create a bot with Telegram BotFather and copy its token.
4. In the Render service Environment page, set:
   - `BOT_TOKEN` — token from BotFather
   - `DATABASE_URL` — Neon connection string
5. Deploy the service. Render supplies `RENDER_EXTERNAL_HOSTNAME` and `PORT`; the application registers the Telegram webhook automatically.
6. Check `https://YOUR-SERVICE.onrender.com/healthz`.

The webhook secret is derived from the bot token unless `WEBHOOK_SECRET` is explicitly supplied. Never commit tokens or database credentials.

## Prime Bot configuration
- Bot: `@PrimeGarantBft_bot`
- Network: TON Testnet
- Fee: 1.5%
- Admin Telegram ID: `8717928428`
- Deal manager: `@korhoul`

## Admin commands
- `/admin` — overview and command list.
- `/user TELEGRAM_ID` — view internal ledger balances.
- `/credit TELEGRAM_ID TON|RUB|STARS amount reason` — internal credit.
- `/debit TELEGRAM_ID TON|RUB|STARS amount reason` — internal debit.
- `/transactions TELEGRAM_ID` — recent ledger entries.
- `/nftreceived CODE`, `/nftverified CODE`, `/nftdelivered CODE` — manually mark NFT workflow stages.

## Safety and limitations
This is a testnet-first workflow scaffold, **not a live escrow/custody system**. No payment address is generated, no blockchain payment is verified, and no TON is held, released, or refunded. Balances are internal ledger entries, not real deposits or assets. Real payment rails and withdrawals are not connected.

NFT references are stored as text only. The bot does not verify ownership, receive, custody, or transfer Telegram Gifts or TON NFTs. The manager/user must perform and verify these actions manually.

A production release needs a separately secured signer or audited escrow/multisig contract, trusted TON transaction indexing and finality checks, unique transaction/memo matching, idempotent release/refund logic, reconciliation, admin dual control, rate limits, monitoring, database migrations, and independent security/legal review. Never place a seed phrase or bot token in the repository.

For a fresh database, tables are created at startup. Existing databases need migrations when the schema changes; automatic migrations are not included.
