import os
import uuid
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from models.quiz import QuizSession
from database import db
from utils.extractor import extract_text
from utils.ai_service import generate_questions, evaluate_answer
from config import Config
from datetime import datetime, date, timedelta, timezone

WIB = timezone(timedelta(hours=7))

quiz_bp = Blueprint("quiz", __name__, url_prefix="/api/quiz")

QUIZ_COOLDOWN_HOURS = 2

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Belum login"}), 401
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@quiz_bp.route("/start", methods=["POST"])
@login_required
def start_quiz():
    user_id = session["user_id"]
    progress_id = request.form.get("progress_id")

    from models.user import User
    user = db.session.get(User, user_id)

    # Cek cooldown dari DB
    # NOTE: if True = admin juga kena cooldown (sengaja untuk testing)
    # Ganti ke "if not user.is_admin:" kalau mau admin skip cooldown di production
    if True:
        now = datetime.utcnow()
        if user.quiz_cooldown_until and user.quiz_cooldown_until > now:
            remaining = int((user.quiz_cooldown_until - now).total_seconds())
            return jsonify({
                "error": f"Quiz hanya bisa dimainkan 1x setiap {QUIZ_COOLDOWN_HOURS} jam",
                "remaining_seconds": remaining
            }), 429

    if "file" not in request.files:
        return jsonify({"error": "File dokumen wajib diupload"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "File tidak valid"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Format file tidak didukung. Gunakan PDF, DOCX, TXT, atau MD"}), 400

    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit(".", 1)[1].lower()
    temp_filename = f"quiz_tmp_{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, temp_filename)
    file.save(file_path)

    try:
        document_text = extract_text(file_path)
    except Exception as e:
        return jsonify({"error": f"Gagal membaca dokumen: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    if not document_text or len(document_text.strip()) < 100:
        return jsonify({"error": "Dokumen terlalu pendek atau kosong"}), 400

    # Admin cheat mode - skip AI langsung S+
    if user and user.is_admin:
        fake_questions = [f"Pertanyaan admin {i+1}?" for i in range(10)]
        fake_answers = ["jawaban admin"] * 10
        fake_feedbacks = [{"score": 10, "feedback": "Perfect! ^^", "correct_answer": "—"} for _ in range(10)]
        quiz = QuizSession(
            user_id=user_id,
            progress_id=int(progress_id) if progress_id else None,
            document_text=document_text,
            questions=fake_questions,
            current_question=10,
            answers=fake_answers,
            feedbacks=fake_feedbacks,
            score=10.0,
            is_finished=True
        )
        db.session.add(quiz)
        db.session.commit()
        user.quiz_cooldown_until = datetime.utcnow() + timedelta(hours=QUIZ_COOLDOWN_HOURS)
        db.session.commit()
        return jsonify({
            "message": "Quiz selesai!",
            "quiz_id": quiz.id,
            "total_questions": 10,
            "is_finished": True,
            "final_score": 10.0,
            "admin_cheat": True,
            "ai_name": Config.AI_NAME
        }), 201

    try:
        questions = generate_questions(document_text)
    except Exception as e:
        return jsonify({"error": f"Gagal generate soal dari AI: {str(e)}"}), 500

    if not questions or len(questions) < 1:
        return jsonify({"error": "AI tidak berhasil generate soal"}), 500

    quiz = QuizSession(
        user_id=user_id,
        progress_id=int(progress_id) if progress_id else None,
        document_text=document_text,
        questions=questions,
        current_question=0,
        answers=[],
        feedbacks=[]
    )
    db.session.add(quiz)
    db.session.commit()

    # Set cooldown di DB
    user.quiz_cooldown_until = datetime.utcnow() + timedelta(hours=QUIZ_COOLDOWN_HOURS)
    db.session.commit()

    return jsonify({
        "message": "Quiz dimulai!",
        "quiz_id": quiz.id,
        "total_questions": len(questions),
        "current_question_index": 0,
        "question": questions[0],
        "ai_name": Config.AI_NAME
    }), 201


@quiz_bp.route("/cooldown", methods=["GET"])
@login_required
def quiz_cooldown():
    from models.user import User
    user = db.session.get(User, session["user_id"])
    now = datetime.utcnow()
    if user.is_admin or not user.quiz_cooldown_until or user.quiz_cooldown_until <= now:
        return jsonify({"remaining_seconds": 0}), 200
    remaining = int((user.quiz_cooldown_until - now).total_seconds())
    return jsonify({"remaining_seconds": remaining}), 200


@quiz_bp.route("/<int:quiz_id>", methods=["GET"])
@login_required
def get_quiz(quiz_id):
    user_id = session["user_id"]
    quiz = QuizSession.query.filter_by(id=quiz_id, user_id=user_id).first()

    if not quiz:
        return jsonify({"error": "Sesi quiz tidak ditemukan"}), 404

    if quiz.is_finished:
        return jsonify({"error": "Quiz sudah selesai"}), 400

    return jsonify({
        "quiz_id": quiz.id,
        "total_questions": len(quiz.questions),
        "current_question_index": quiz.current_question,
        "question": quiz.questions[quiz.current_question],
        "questions_done": quiz.current_question,
        "ai_name": Config.AI_NAME
    }), 200


@quiz_bp.route("/<int:quiz_id>/answer", methods=["POST"])
@login_required
def answer_question(quiz_id):
    user_id = session["user_id"]
    quiz = QuizSession.query.filter_by(id=quiz_id, user_id=user_id).first()

    if not quiz:
        return jsonify({"error": "Sesi quiz tidak ditemukan"}), 404

    if quiz.is_finished:
        return jsonify({"error": "Quiz sudah selesai"}), 400

    data = request.get_json()
    user_answer = data.get("answer", "").strip()

    if not user_answer:
        return jsonify({"error": "Jawaban tidak boleh kosong"}), 400

    current_idx = quiz.current_question
    current_question = quiz.questions[current_idx]

    try:
        result = evaluate_answer(current_question, user_answer, quiz.document_text)
    except Exception as e:
        return jsonify({"error": f"Gagal evaluasi jawaban: {str(e)}"}), 500

    answers = quiz.answers or []
    feedbacks = quiz.feedbacks or []
    answers.append(user_answer)
    feedbacks.append(result)

    next_idx = current_idx + 1
    is_finished = next_idx >= len(quiz.questions)

    final_score = None
    if is_finished:
        total = sum(f.get("score", 0) for f in feedbacks)
        final_score = round(total / len(feedbacks), 1)

    quiz.answers = answers
    quiz.feedbacks = feedbacks
    quiz.current_question = next_idx
    quiz.is_finished = is_finished
    quiz.score = final_score
    db.session.commit()

    response = {
        "feedback": result.get("feedback"),
        "score_this_question": result.get("score"),
        "correct_answer": result.get("correct_answer"),
        "is_finished": is_finished,
        "questions_done": next_idx,
        "total_questions": len(quiz.questions),
    }

    if not is_finished:
        response["next_question"] = quiz.questions[next_idx]
        response["next_question_index"] = next_idx
    else:
        response["final_score"] = final_score
        response["message"] = f"Quiz selesai! Skor akhir kamu: {final_score}/10"

    return jsonify(response), 200


@quiz_bp.route("/history", methods=["GET"])
@login_required
def history():
    user_id = session["user_id"]
    sessions = QuizSession.query.filter_by(user_id=user_id).order_by(QuizSession.created_at.desc()).limit(20).all()
    return jsonify({"sessions": [s.to_dict() for s in sessions]}), 200


@quiz_bp.route("/ai-info", methods=["GET"])
def ai_info():
    return jsonify({
        "ai_name": Config.AI_NAME,
        "ai_model": Config.AI_MODEL,
        "ai_provider": Config.AI_PROVIDER
    }), 200


@quiz_bp.route("/stats", methods=["GET"])
@login_required
def stats():
    user_id = session["user_id"]

    finished = QuizSession.query.filter_by(
        user_id=user_id, is_finished=True
    ).order_by(QuizSession.created_at.desc()).all()

    avg_score = None
    grade = None
    grade_color = "#6b6b80"
    if finished:
        scores = [q.score for q in finished if q.score is not None]
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)
            grade = QuizSession.get_grade(avg_score)
            grade_color = QuizSession.get_grade_color(grade)

    streak = 0
    quizzed_today = False
    if finished:
        today = datetime.now(WIB).date()
        quiz_dates = sorted(set(
            (q.created_at.replace(tzinfo=timezone.utc).astimezone(WIB)).date()
            for q in finished
        ), reverse=True)

        quizzed_today = quiz_dates[0] == today if quiz_dates else False

        # Kalau belum quiz hari ini, mulai cek dari kemarin
        expected = today if quizzed_today else today - timedelta(days=1)
        for d in quiz_dates:
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break

    return jsonify({
        "avg_score": avg_score,
        "grade": grade,
        "grade_color": grade_color,
        "total_quiz": len(finished),
        "streak": streak,
        "quizzed_today": quizzed_today
    }), 200



