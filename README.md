# 📚 Belajar Tracker

Web app buat tracking progress belajar + quiz AI dari dokumen kamu sendiri.  
Dibangun pakai Flask (backend) + Vanilla JS (frontend), AI-powered by DeepSeek / Gemini / Claude.

---

## 🚀 Cara Pakai

### 1. Register Akun
- Buka aplikasi → klik tab **Register**
- Isi username dan password (minimal 6 karakter)
- Username otomatis disimpan **lowercase** — `abcd` dan `Abcd` dianggap sama
- Klik **Register** → langsung masuk ke dashboard

### 2. Login
- Masukkan username + password yang sudah didaftarkan
- Klik **Login**
- Sesi login disimpan di browser — tidak perlu login ulang kalau tidak logout

### 3. Tambah Progress Belajar
- Klik tab **Tambah** di navbar bawah
- Isi judul materi, link referensi (opsional), catatan (opsional)
- Bisa upload dokumen (PDF, DOCX, TXT, MD) sebagai lampiran
- Klik **Simpan**

### 4. Lihat Riwayat
- Klik tab **Riwayat**
- Bisa filter berdasarkan tanggal atau folder
- Bisa buat folder untuk mengelompokkan materi

### 5. Thea Challenge (Quiz AI)
- Klik tab **Challenge**
- Upload dokumen materi (PDF, DOCX, TXT, MD)
- Klik **Mulai Quiz** → AI akan generate 10 pertanyaan essay dari dokumen kamu
- Jawab satu per satu → Thea akan kasih feedback + skor per soal
- Selesai → dapat skor akhir + grade

> ⏳ Quiz hanya bisa dimainkan **1x setiap 2 jam** per akun

### 6. Logout
- Klik nama user di pojok kanan atas → **Logout**

---

## 🔐 Cara Kerja Login (Tanpa Google / OAuth)

Sistem autentikasi di app ini sepenuhnya **custom**, tidak pakai Google, GitHub, atau layanan pihak ketiga apapun. Berikut penjelasan teknisnya:

### Alur Register
```
User isi form → username di-lowercase → cek duplikat di DB
→ password di-hash (bcrypt via werkzeug) → simpan ke DB
→ session dibuat → user langsung masuk
```

### Alur Login
```
User isi form → username di-lowercase → cari user di DB
→ hash password yang diinput dibandingkan dengan hash di DB
→ kalau cocok → session dibuat → user masuk
→ kalau tidak cocok → error "Username atau password salah"
```

### Password Hashing
Password **tidak pernah disimpan dalam bentuk plain text**. Menggunakan `werkzeug.security`:

```python
# Saat register — password di-hash sebelum masuk DB
generate_password_hash(password)  # hasil: "scrypt:32768:8:1$salt$hash..."

# Saat login — bandingkan input dengan hash di DB
check_password_hash(stored_hash, input_password)  # return True/False
```

Artinya bahkan admin pun tidak bisa tahu password user dari database.

### Session
Setelah login berhasil, server menyimpan `user_id` di **server-side session** (Flask session dengan cookie terenkripsi):

```python
session["user_id"] = user.id
session["username"] = user.username
```

- Cookie di-sign dengan `SECRET_KEY` → tidak bisa dipalsukan dari luar
- `SESSION_COOKIE_HTTPONLY = True` → tidak bisa diakses via JavaScript
- `SESSION_COOKIE_SECURE = True` → hanya dikirim lewat HTTPS (di production)
- `SESSION_COOKIE_SAMESITE = "Lax"` → proteksi CSRF dasar

### Cek Login di Setiap Request
Setiap endpoint yang butuh login dilindungi decorator `@login_required`:

```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Belum login"}), 401
        return f(*args, **kwargs)
    return decorated
```

### Admin
Admin ditentukan saat **pertama kali register** — jika username yang didaftarkan sama dengan `ADMIN_USERNAME` di file `.env`, akun tersebut otomatis jadi admin. Tidak ada cara mendapat akses admin setelah register kecuali diset manual di database.

### Rate Limiting
- Register: **5x per menit** per IP
- Login: **10x per menit** per IP
- Global: **300x per hari**, **60x per jam** per IP

---

## ⚙️ Setup (untuk developer)

### Requirements
```bash
pip install -r requirements.txt
```

### Environment Variables (`.env`)
```
# App
SECRET_KEY=isi-random-string-panjang
DEBUG=True
PORT=5000

# Admin
ADMIN_USERNAME=username_admin_kamu

# Database (opsional, default SQLite)
DATABASE_URL=postgresql://...

# AI
AI_NAME=DeepSeek
AI_API_KEY=sk-or-v1-...
AI_MODEL=deepseek/deepseek-v3.2
AI_PROVIDER=openai
```

### Jalankan
```bash
python app.py
```

---

## 📁 Struktur Project
```
app_bljr/
├── app.py              # Entry point, blueprint register, security headers
├── config.py           # Konfigurasi dari .env
├── database.py         # Init SQLAlchemy
├── extensions.py       # Rate limiter
├── requirements.txt
├── frontend/
│   ├── index.html      # Single page app (semua UI di sini)
│   └── static/
│       └── sleepy_thea.webp
├── models/
│   ├── user.py         # Model user + password hashing
│   ├── progress.py     # Model progress belajar
│   ├── quiz.py         # Model quiz session + grading
│   └── folder.py       # Model folder
├── routes/
│   ├── auth.py         # Register, login, logout, /me
│   ├── progress.py     # CRUD progress + folder
│   └── quiz.py         # Start quiz, answer, cooldown, stats
└── utils/
    ├── ai_service.py   # Integrasi AI (Gemini/DeepSeek/Claude)
    └── extractor.py    # Ekstrak teks dari PDF/DOCX/TXT/MD
```

---

## 🤖 AI Provider yang Didukung
| Provider | `AI_PROVIDER` | Contoh Model |
|---|---|---|
| DeepSeek (via OpenRouter) | `openai` | `deepseek/deepseek-v3.2` |
| Google Gemini | `gemini` | `gemini-1.5-flash` |
| Anthropic Claude | `claude` | `claude-3-haiku-20240307` |

---

Made with ☕ + 🎵 by kyupii
