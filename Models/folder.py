from database import db
from datetime import datetime
from sqlalchemy import func


class Folder(db.Model):
    __tablename__ = "folders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # FIX #12: Ganti lazy=True ke lazy="dynamic" bukan solusi terbaik untuk count.
    # Solusi terbaik: jangan load seluruh relasi hanya untuk len().
    # Gunakan _progress_count sebagai kolom tambahan yang di-inject saat query
    # (lihat cara pakai di bawah), atau gunakan property dengan subquery.
    # Untuk backward compatibility, relasi tetap ada tapi to_dict() tidak lagi
    # memanggil len(self.progresses) yang trigger N+1 query.
    progresses = db.relationship("Progress", backref="folder", lazy=True)

    def to_dict(self, progress_count: int = None):
        """
        FIX #12: Sebelumnya to_dict() memanggil len(self.progresses) yang
        trigger lazy load — 1 query per folder (N+1 problem).
        Kalau ada 20 folder → 20 query tambahan hanya untuk tampilkan total.

        Sekarang: terima progress_count dari luar (di-inject dari route/query)
        sehingga bisa pakai 1 query COUNT di level database, jauh lebih efisien.

        Di route, gunakan seperti ini:
            from sqlalchemy import func
            from models.progress import Progress

            folders = Folder.query.filter_by(user_id=user_id).all()
            counts = dict(
                db.session.query(Progress.folder_id, func.count(Progress.id))
                .filter(Progress.folder_id.in_([f.id for f in folders]))
                .group_by(Progress.folder_id)
                .all()
            )
            result = [f.to_dict(progress_count=counts.get(f.id, 0)) for f in folders]
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "total": progress_count if progress_count is not None else len(self.progresses),
            "created_at": self.created_at.isoformat()
        }

