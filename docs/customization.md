# Customization

Go to **Dashboard → Customization** (`/dashboard/settings/`). Changes apply instantly to the public
site *and* both dashboards; a live preview shows colour/font/radius changes before saving.
Settings are stored in a single `core.SiteSettings` row and cached for 5 minutes (the cache is
cleared on save).

| Tab | Fields |
|-----|--------|
| **Branding** | Site name, tagline, logo (replaces the text logo), favicon |
| **Theme** | Primary, accent and dark colours · font family (Poppins, Inter, Montserrat, Cairo, Playfair Display) · corner radius (0-32 px) |
| **Home page** | Hero title/subtitle/image (upload or URL) · about title/text · toggle stats band, testimonials, blog section |
| **Contact & social** | Email, phone, address, WhatsApp, Facebook, Instagram, X, YouTube, footer text |
| **Booking** | Currency symbol · enable/disable online booking · cancellation policy (shown on tour pages and used by the chatbot) |
| **Chatbot** | Enable/disable · assistant name · welcome message · extra instructions appended to the AI system prompt |

## How theming works (for developers)

`templates/partials/_head.html` writes the settings into CSS custom properties:

```css
:root { --brand: …; --accent: …; --ink: …; --radius: …px; --font: "…"; }
```

`static/css/theme.css` derives everything else (`--brand-soft`, `--brand-dark`, Bootstrap's
`--bs-*` variables, buttons, badges, focus rings) with `color-mix()`, so a single colour change
re-skins the whole product. Charts read the same variables at render time.

Light/dark mode: every page has a toggle (`static/js/theme.js`); the choice is remembered per
browser and the default follows the OS preference.

## Content

- **Tours, destinations, blog posts** - managed in the dashboard. Each item accepts an uploaded
  image or an image URL; if neither is set a placeholder photo is used so cards never look broken.
- **Highlights / itinerary / included** fields are "one item per line".
- Blog bodies use blank lines between paragraphs.
