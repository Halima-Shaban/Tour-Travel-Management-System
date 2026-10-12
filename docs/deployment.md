# Deployment Checklist & Guide

## General Checklist

1. `.env`: `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain`, SMTP settings, `GROQ_API_KEY`.
2. Database: `python manage.py migrate`.
3. Static files: `python manage.py collectstatic --noinput`.
4. Admin account: `python manage.py createsuperuser`.
5. HTTPS / SSL: Enable HTTPS on your host. Secure cookies are enabled automatically when `DEBUG=False`.
6. Stripe: switch to live keys and register the webhook `https://your-domain/payments/webhook/` (see [payments.md](payments.md)).

---

## PythonAnywhere Deployment Guide

### 1. Clone Project in Bash Console
```bash
git clone https://github.com/<your-username>/<repo-name>.git halima
cd ~/halima
```

### 2. Create Virtual Environment
```bash
mkvirtualenv --python=/usr/bin/python3.11 halima-venv
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Setup `.env`
Create `/home/<your-username>/halima/.env`:
```env
DJANGO_SECRET_KEY=your-long-secure-random-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-username>.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-username>.pythonanywhere.com
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
GROQ_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_CURRENCY=usd
```

### 4. Database & Static Files
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 5. Configure Web Tab
1. **Manual Configuration** with **Python 3.11** (do NOT choose Django wizard).
2. **Virtualenv**: `/home/<your-username>/.virtualenvs/halima-venv`
3. **Source Code**: `/home/<your-username>/halima`
4. **Working Directory**: `/home/<your-username>/halima`
5. **Static files**:
   - `/static/` -> `/home/<your-username>/halima/staticfiles`
   - `/media/` -> `/home/<your-username>/halima/media`
6. **Force HTTPS**: Enable toggle.
7. **WSGI configuration file** (`/var/www/<your-username>_pythonanywhere_com_wsgi.py`):
```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

path = '/home/<your-username>/halima'
if path not in sys.path:
    sys.path.append(path)

load_dotenv(os.path.join(path, '.env'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
8. Click **Reload <your-username>.pythonanywhere.com**.
