from sqlalchemy.orm import Session
from app.database.models import User

def get_leaderboard(db: Session, bucket_scope: str = "daily", bucket_key: str = None, limit: int = 10):
    """
    מחזיר לידרבורד לפי טווח (daily/weekly). bucket_key לא בשימוש.
    """
    # פשוט מחזיר את המשתמשים עם total_xp הגבוה ביותר
    users = db.query(User).order_by(User.total_xp.desc()).limit(limit).all()
    leaderboard = []
    for user in users:
        leaderboard.append({
            'user_id': user.id,
            'username': user.username or str(user.id),
            'total_manh': float(user.balance_manh)  # או total_xp לפי הצורך
        })
    return leaderboard
