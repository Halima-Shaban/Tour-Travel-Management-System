# Deployment checklist

1. `.env`: `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain`, SMTP settings, `GROQ_API_KEY`.
2. Install a WSGI server: `pip install gunicorn` → `gunicorn config.wsgi --bind 0.0.0.0:8000`.
3. `python manage.py migrate && python manage.py collectstatic --noinput`.
4. Serve `staticfiles/` and `media/` from your web server (nginx) or add WhiteNoise for static files.
   `media/` holds uploads - back it up.
5. Create a real admin: `python manage.py createsuperuser`; remove/rotate demo accounts.
6. Put the site behind HTTPS (secure cookies are enabled automatically when `DEBUG=False`).
7. For multiple processes, configure a shared cache (Redis/Memcached) so the chatbot rate limit and
   settings cache are shared between workers.
8. Stripe: switch to live keys and register the webhook `https://your-domain/payments/webhook/`
   (see [payments.md](payments.md)).
9. Consider PostgreSQL for production traffic (`DATABASES` in `config/settings.py`).
