from database import db
from datetime import datetime

class QuizSession(db.Model):
    __tablename__ = "quiz_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    progress_id = db.Column(db.Integer, db.ForeignKey("progress.id"), nullable=True)
    document_text = db.Column(db.Text, nullable=False)
    questions = db.Column(db.JSON, nullable=True)
    current_question = db.Column(db.Integer, default=0)
    answers = db.Column(db.JSON, default=list)
    feedbacks = db.Column(db.JSON, default=list)
    score = db.Column(db.Integer, nullable=True)
    is_finished = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "progress_id": self.progress_id,
            "current_question": self.current_question,
            "total_questions": len(self.questions) if self.questions else 0,
            "answers": self.answers,
            "feedbacks": self.feedbacks,
            "score": self.score,
            "is_finished": self.is_finished,
            "created_at": self.created_at.isoformat()
        }

    @staticmethod
    def get_grade(avg_score):
        """Konversi rata-rata skor (0-10) ke grade."""
        if avg_score is None:
            return None
        if avg_score >= 9.8: return "S++"
        if avg_score >= 9.0: return "S+"
        if avg_score >= 8.0: return "S"
        if avg_score >= 7.0: return "A+"
        if avg_score >= 6.0: return "A"
        if avg_score >= 5.0: return "B+"
        if avg_score >= 4.0: return "B"
        if avg_score >= 3.0: return "C+"
        if avg_score >= 2.0: return "C"
        return "C-"

    @staticmethod
    def get_grade_color(grade):
        """Warna per grade buat frontend."""
        colors = {
            "S++": "#ffd700", "S+": "#ffd700", "S": "#ffd700",
            "A+": "#4ade80", "A": "#4ade80",
            "B+": "#7c6aff", "B": "#7c6aff",
            "C+": "#fbbf24", "C": "#fbbf24", "C-": "#f87171"
        }
        return colors.get(grade, "#6b6b80")
