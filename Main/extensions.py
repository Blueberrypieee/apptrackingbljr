from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _get_real_ip():
    """
    FIX #10: Ambil IP asli user di balik reverse proxy (Nginx/Cloudflare).
    Sebelumnya: get_remote_address selalu baca IP proxy → rate limiting tidak efektif,
                semua request terlihat dari IP yang sama (IP Nginx).
    Sekarang: baca X-Forwarded-For header dulu, fallback ke REMOTE_ADDR.

    PENTING: Pastikan di Nginx kamu set:
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    Kalau tidak pakai reverse proxy, ini tetap aman karena fallback ke get_remote_address.
    """
    from flask import request
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For bisa berisi multiple IP: "client, proxy1, proxy2"
        # IP pertama adalah IP asli client
        return forwarded_for.split(",")[0].strip()
    return get_remote_address()


# FIX #11: default_limits sebelumnya kosong [] → rate limiting global mati total.
# Kalau ada endpoint yang lupa dikasih @limiter.limit(), endpoint itu tak terlindungi.
# Sekarang ada limit global sebagai safety net:
#   - 300 request per hari per IP (cukup untuk user normal)
#   - 60 request per jam per IP
# Endpoint spesifik seperti /login tetap bisa set limit lebih ketat via decorator.
limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=["300 per day", "60 per hour"]
)

