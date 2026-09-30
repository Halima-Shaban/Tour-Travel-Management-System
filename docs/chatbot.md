# Chatbot

A floating assistant on every public page (`templates/partials/_chatbot.html`,
`static/js/chatbot.js`). It recommends tours, answers pricing/booking/cancellation questions and
replies in the visitor's language (Arabic and English tested).

## Engines

1. **Groq LLM** (when `GROQ_API_KEY` is set) - OpenAI-compatible API at
   `https://api.groq.com/openai/v1/chat/completions`. Default model `llama-3.3-70b-versatile`,
   automatic retry on `GROQ_FALLBACK_MODEL` (`llama-3.1-8b-instant`) if the first call fails.
   Groq was chosen for its very low latency and generous free tier.
2. **Offline assistant** - used when no key is configured or Groq is unreachable. Keyword/intent
   matching (English + Arabic) that searches the real tour database, so it never breaks.

The response JSON includes `source` (`groq` / `offline`) and `tours` (cards rendered under the
answer, linking to the tour pages).

## Grounding (no hallucinated tours)

`chatbot/knowledge.py` builds the system prompt from live data on each request (cached 2 minutes):
company info, contact details, cancellation policy, booking steps, all destinations and up to 60
active tours with price, discount, duration, rating, guide and URL. The prompt instructs the model
to use only that data, answer in the user's language, link tours, never collect payment details and
stay on topic. Admins can append rules in **Customization → Chatbot → Extra instructions**
(e.g. "Mention the 10% summer discount").

## Safety & limits
- Messages capped at 1000 characters; last 10 messages sent as history.
- Per-session rate limit (`CHATBOT_MAX_MESSAGES_PER_HOUR`, returns HTTP 429).
- CSRF-protected endpoints; the widget escapes all HTML and only renders **bold**, bullet lists
  and links to relative or `https://` URLs.
- The API key is read from the environment only - never stored in the database or sent to the browser.

## Endpoints
| Method | URL | |
|--------|-----|---|
| POST | `/chatbot/message/` | `{"message": "..."}` → `{"reply", "source", "tours"}` |
| GET | `/chatbot/history/` | Messages of the current session's conversation |
| POST | `/chatbot/reset/` | Start a new conversation |

## Switching provider
All LLM I/O is in `chatbot/services.call_groq()`. Any OpenAI-compatible provider works by changing
`GROQ_API_URL` in `config/settings.py` plus the key/model variables; for other APIs replace that
one function - the rest (grounding, fallback, storage, widget) is provider-agnostic.
