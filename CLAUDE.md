# mindvsyou.io marketing site

Static HTML site (no build step), deployed from `main` to https://mindvsyou.io.
The web app it sends students to is https://quiz.mindvsyou.io (separate repo).
Nav and footer markup is written directly into every page so crawlers see the links;
keep them identical across pages. Shared JS is `main.js`.

Local preview: `python -m http.server 8765` (configured in `.claude/launch.json`).

## Google Analytics (GA4)

- Measurement ID: `G-JM406K6TT0`, under the Google account mindvsyou@gmail.com, GA account "mindvsyou".
- The gtag snippet is pasted at the top of `<head>` on every page. New pages need it too,
  except the pages listed under "Privacy rule" below.
- CTA conversions: `main.js` → `initCtaTracking()` sends a `cta_click` event for every link
  to `CONFIG.appLink` (quiz.mindvsyou.io), with `cta_text`, `cta_location` and `link_url`.
  `cta_click` should be marked as a key event in GA4 (Admin → Data display → Events).

## Privacy rule (DPDP Act)

Most visitors are CBSE students under 18. India's DPDP Act restricts tracking children, so:
- Never send names, student IDs, phone numbers, emails or any other personal data to GA,
  in event parameters or in URLs.
- `forgot-login.html` has NO gtag on purpose: students enter their name, student ID and phone there.
  Do not add it back. Apply the same rule to any future page that collects student details.

## Google Search Console

- Property: `https://mindvsyou.io/`, verified by the HTML file `googleff08a779fb1c9da0.html`.
  **Never delete or rename that file.** Deleting it breaks verification.
- Sitemap: `sitemap.xml` (also listed in `robots.txt`). Add new pages to it.

## Content

- The site is built around PYQ (previous-year question) practice for CBSE Class 10 Science.
- Copy should use specific, entity-rich terms (CBSE, Class 10, PYQ, chapter names) for SEO/AEO/GEO.
