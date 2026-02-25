# ARCHITECTURE

## Components
1) Telegram Mini App (TMA) — React/Vite inside Telegram
2) API Gateway — FastAPI (auth, jobs, results)
3) Queue — Redis
4) Workers — run MTProto jobs safely
5) tg_engine — Telethon/Pyrogram wrapper library
6) DB — Postgres (metadata only)
7) Security — session encryption + kill switch

## Core rules
- Read-only first
- Per-user rate limiting
- FloodWait is obeyed exactly
- No message content stored
- Sessions treated as cryptographic material

