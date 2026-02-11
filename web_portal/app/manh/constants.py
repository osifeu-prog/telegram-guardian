from __future__ import annotations
from datetime import datetime, timezone

# Immutable launch epoch (UTC). Change requires code+commit.
MANH_LAUNCH_EPOCH_UTC = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)

# Leaderboard timezone for daily/weekly buckets
LEADERBOARD_TZ = "Asia/Jerusalem"

# Decimal scale in DB (DECIMAL(38, 9))
MANH_SCALE = 9
