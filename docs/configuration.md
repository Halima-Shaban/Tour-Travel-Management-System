# Configuration (`.env`)

Settings are read from environment variables (a `.env` file in the project root is loaded
automatically). **Never commit `.env`** - it is git-ignored.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | insecure dev key | Set a long random value in production |
| `DJANGO_DEBUG` | `True` | `False` in production (also enables secure cookies) |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost,testserver` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | - | e.g. `https://example.com` when served over HTTPS |
| `GROQ_API_KEY` | - | Enables the AI chatbot. Empty = offline assistant |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Primary model |
| `GROQ_FALLBACK_MODEL` | `llama-3.1-8b-instant` | Tried automatically if the primary fails |
| `CHATBOT_MAX_MESSAGES_PER_HOUR` | `40` | Per-visitor rate limit |
| `EMAIL_BACKEND` | console | Use `django.core.mail.backends.smtp.EmailBackend` for real mail |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | - | SMTP settings |
| `DEFAULT_FROM_EMAIL` | `noreply@example.com` | Sender address |
| `CONTACT_RECIPIENT_EMAIL` | - | Receives new-booking and contact-form notifications |
| `GOOGLE_MAPS_API_KEY` | - | Contact-page map. Without it an OpenStreetMap embed is used |

Everything *visual or content-related* (name, colours, texts, social links, chatbot persona...) is
**not** in `.env` - it is edited live from **Dashboard → Customization**. See
[customization.md](customization.md).
