# NEXT — 1-Step Focus

## Step 1 (now)
Create MTProto POC (read-only scan) as a CLI:
- python -m tg_engine.poc_scan
- prompts for phone + code
- prints summary + writes out/scan_report.json

## Step 2
Add flood-safe wrapper + per-user limiter (sleep by server instructions)

## Step 3
Expose scan as a background job via API + worker
