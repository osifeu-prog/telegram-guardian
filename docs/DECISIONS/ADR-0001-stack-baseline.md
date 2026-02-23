# ADR-0001: Stack baseline

## Context
We need a privacy-first Telegram product with MTProto capabilities, safe rate limiting, and a UI inside Telegram.

## Decision
- Python backend + Telethon/Pyrogram engine
- FastAPI API gateway
- Redis queue + worker processes
- React/Vite Telegram Mini App

## Consequences
- MTProto runs only in workers
- API stays thin and safe
