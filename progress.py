from database import db
from datetime import datetime, date

class Progress(db.Model):
    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey("folders.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.String(500), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(200), nullable=True)
    stored_filename = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    quiz_sessions = db.relationship("QuizSession", backref="progress", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "folder_id": self.folder_id,
            "title": self.title,
            "link": self.link,
            "file_name": self.file_name,
            "notes": self.notes,
            "date": self.date.isoformat(),
            "created_at": self.created_at.isoformat()
        }
