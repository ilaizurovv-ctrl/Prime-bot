# Prime Bot — OTC Escrow starter

Python 3.12, aiogram 3, PostgreSQL. Configured for TON testnet and a 1.5% fee.

## Implemented in this starter
- Telegram user registration
- create demo deal with `/createdemo amount description`
- unique invite deep-link for buyer
- buyer joins by opening the deep-link
- `/mydeals`, `/deal CODE`, `/dispute CODE`
- deal records and fee snapshot in PostgreSQL
- NFT deal records for Telegram Gifts and TON NFTs
- manager workflow with manual NFT status confirmations
- internal TON, RUB and Telegram Stars ledgers with admin adjustments

## Run
1. Create a bot with Telegram BotFather.
2. Copy `.env.example` to `.env`.
3. Set `BOT_TOKEN` and `BOT_USERNAME` (without @).
4. Run `docker compose up --build`.
5. Open your bot and send `/start`.

## Admin commands
- `/admin` — overview and command list.
- `/user TELEGRAM_ID` — view TON, RUB and Stars ledger balances.
- `/credit TELEGRAM_ID TON|RUB|STARS amount reason` — manual internal credit.
- `/debit TELEGRAM_ID TON|RUB|STARS amount reason` — manual internal debit.
- `/transactions TELEGRAM_ID` — recent balance ledger entries.
- `/nftreceived CODE`, `/nftverified CODE`, `/nftdelivered CODE` — manually mark NFT workflow stages.

Admin Telegram ID is configured through `ADMIN_IDS`. The configured manager username is `korhoul`.

## Safety / current limitations
This is a testnet-first workflow scaffold, **not a live escrow/custody system**.
No payment address is generated, no blockchain payment is verified, and no TON is held, released, or refunded. Balances are internal test ledger entries, not real deposits or assets. Real payment rails and withdrawals are not connected.

NFT references are stored as text only. The bot does not verify ownership, receive, custody, or transfer Telegram Gifts or TON NFTs. The manager/user must perform and verify these actions manually.

A production release needs a separately secured signer or audited escrow/multisig contract, trusted TON transaction indexing and finality checks, unique transaction/memo matching, idempotent release/refund logic, reconciliation, admin dual control, rate limits, monitoring, database migrations, and independent security/legal review. Never place a seed phrase or bot token in the repository.

For a fresh database, tables are created at startup. Existing databases need migrations when the schema changes; automatic migrations are not included.
