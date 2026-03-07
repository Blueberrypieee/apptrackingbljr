from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    quiz_cooldown_until = db.Column(db.DateTime, nullable=True, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progresses = db.relationship("Progress", backref="user", lazy=True)
    quiz_sessions = db.relationship("QuizSession", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        now = datetime.utcnow()
        remaining = 0
        if self.quiz_cooldown_until and self.quiz_cooldown_until > now:
            remaining = int((self.quiz_cooldown_until - now).total_seconds())
        return {
            "id": self.id,
            "username": self.username,
            "is_admin": self.is_admin,
            "quiz_cooldown_remaining": remaining,
            "created_at": self.created_at.isoformat()
        }


