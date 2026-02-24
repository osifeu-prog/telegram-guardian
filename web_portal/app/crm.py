from sqlalchemy import text
from sqlalchemy.orm import Session

def add_tag(db: Session, user_id: int, tag: str):
    db.execute(
        text("INSERT INTO user_tags (user_id, tag) VALUES (:uid, :tag) ON CONFLICT DO NOTHING"),
        {"uid": user_id, "tag": tag}
    )
    db.commit()

def get_users_by_tag(db: Session, tag: str):
    return db.execute(
        text("SELECT user_id FROM user_tags WHERE tag = :tag"),
        {"tag": tag}
    ).scalars().all()

def log_marketing_event(db: Session, event_type: str, user_id: int = None, details: dict = None):
    import json
    db.execute(
        text("INSERT INTO marketing_events (event_type, user_id, details) VALUES (:et, :uid, :details)"),
        {"et": event_type, "uid": user_id, "details": json.dumps(details) if details else None}
    )
    db.commit()
