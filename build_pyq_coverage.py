#!/usr/bin/env python3
"""Generate class-10-science-pyq-coverage.html and class-10-science-chapter-pdfs.html
from the quiz app's public inventory endpoint.

Run:  python build_pyq_coverage.py
Fetches https://quiz.mindvsyou.io/api/public/pyq-inventory, saves the last good copy to
data/pyq-inventory.json and writes the page. If the fetch fails it reuses that copy;
if there is none it exits with an error. Numbers are never hardcoded or zero-filled.
Commit the regenerated HTML, data file and sitemap when the question bank changes.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
ENDPOINT = "https://quiz.mindvsyou.io/api/public/pyq-inventory"
SNAPSHOT = ROOT / "data" / "pyq-inventory.json"
OUT = ROOT / "class-10-science-pyq-coverage.html"
SITE = "https://mindvsyou.io"
PAGE_URL = f"{SITE}/class-10-science-pyq-coverage.html"
# The coverage page is facts + practice only; chapter PDFs (free and paid) live on their own page.
PDF_OUT = ROOT / "class-10-science-chapter-pdfs.html"
PDF_PAGE = PDF_OUT.name
PDF_PAGE_URL = f"{SITE}/{PDF_PAGE}"

TYPES = ["MCQ", "Assertion-Reason", "VSA", "SA", "LA", "Case-based"]
TYPE_NAMES = {
    "MCQ": "Multiple choice (MCQ, 1 mark)",
    "Assertion-Reason": "Assertion-Reason (an assertion and a reason, choose the correct option; counted separately from MCQ)",
    "VSA": "Very short answer (VSA, about 2 marks)",
    "SA": "Short answer (SA, about 3 marks)",
    "LA": "Long answer (LA, about 5 marks)",
    "Case-based": "Case-based (passage with sub-questions)",
}

# NCERT Class 10 Science chapter order. Names must match the endpoint's chapter names exactly;
# a chapter not listed here goes last, alphabetically, with no number.
NCERT_ORDER = [
    "Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-Metals",
    "Carbon and Its Compounds", "Life Processes", "Control and Coordination",
    "How Do Organisms Reproduce?", "Heredity", "Light – Reflection and Refraction",
    "The Human Eye and the Colourful World", "Electricity", "Magnetic Effects of Electric Current",
    "Our Environment",
]


def ncert_no(name):
    return NCERT_ORDER.index(name) + 1 if name in NCERT_ORDER else None


def label(name):
    n = ncert_no(name)
    return f"{n}. {name}" if n else name


# Samples that read badly out of context are hidden by an explicit rule, never edited.
# "OR" = the second half of an either/or question.
# Hand-picked samples to hide after reading them all: (chapter, type, year, first 40 chars of text).
SAMPLE_DENYLIST = {
    ("Electricity", "MCQ", 2025, "A piece of wire of resistance 'R' is cut"),  # options A/B are corrupted numbers
    ("Electricity", "LA", 2024, "(i) Which type of circuits \u2014 series or p"),  # refers to a circuit diagram image
    ("Heredity", "MCQ", 2025, "Mendel obtained F2 generation by"),  # answer is not a single letter
}


def sample_ok(chapter, s):
    if re.match(r"\s*OR\b", s["text"]):
        return False
    return (chapter, s["type"], s["year"], s["text"][:40]) not in SAMPLE_DENYLIST


def load():
    try:
        with urllib.request.urlopen(ENDPOINT, timeout=30) as r:
            data = json.load(r)
        assert data["chapters"] and data["totalQuestions"] > 0, "empty inventory"
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        return data
    except Exception as e:  # network, JSON or sanity failure
        if SNAPSHOT.exists():
            print(f"WARNING: fetch failed ({e}); reusing {SNAPSHOT}", file=sys.stderr)
            return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        sys.exit(f"Fetch failed ({e}) and there is no saved copy. Not writing the page.")


# All chapter PDF links live in data/chapter-pdfs.csv (one row per chapter, editable in Excel):
#   type = free  -> drive_link is shown as a "Free PDF" button
#   type = paid  -> razorpay_link is shown as a "Buy PDF" button; drive_link and thank_you_page are
#                   kept there as a record (the download button lives on the hand-made thank-you page)
#   type empty   -> "Coming soon"
PDF_CSV = ROOT / "data" / "chapter-pdfs.csv"
# Question/page counts read from each PDF's cover (no links, safe to publish). Refresh it when a PDF changes.
PDF_STATS = ROOT / "data" / "chapter-pdf-stats.json"
PDF_PRICE = "₹49"  # shown in the copy; keep equal to the Razorpay payment pages
PDF_LINKS = {}  # endpoint chapter name -> Razorpay payment page; filled by load_pdf_links()
FREE_PDFS = {}  # endpoint chapter name -> direct-download URL; filled by load_pdf_links()


def norm(name):
    """Loose chapter-name key, so Excel's re-saving of dashes, quotes or spacing doesn't break matching."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def drive_download(link):
    """Any Google Drive share link (…/file/d/ID/view, …?id=ID) -> direct-download URL."""
    m = re.search(r"/d/([\w-]+)", link) or re.search(r"[?&]id=([\w-]+)", link)
    if not m:
        sys.exit(f"{PDF_CSV.name}: can't find a Google Drive file id in {link!r}")
    return f"https://drive.google.com/uc?export=download&id={m.group(1)}"


# NCERT chapter numbers per subject, for grouping the chapter PDF cards.
SUBJECTS = [("Chemistry", "chem", [1, 2, 3, 4]), ("Biology", "bio", [5, 6, 7, 8, 13]), ("Physics", "phy", [9, 10, 11, 12])]
THANKS = {}  # endpoint chapter name -> (thank-you page file name, direct-download URL), paid chapters only


def load_pdf_links(chapters):
    """Fill FREE_PDFS, PDF_LINKS and THANKS from the CSV. A paid chapter with a Drive link but no
    thank_you_page gets a new random one, written back to the CSV (the address goes into Razorpay)."""
    import csv
    import secrets
    raw = PDF_CSV.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:  # Excel on Windows may save as cp1252
        text = raw.decode("cp1252")
    by_key = {norm(c["chapter"]): c["chapter"] for c in chapters}
    reader = csv.DictReader(text.splitlines())
    rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in reader]
    added = False
    for row in rows:
        kind = row.get("type", "").lower()
        if not kind:
            continue
        name = by_key.get(norm(row["chapter"]))
        if not name:
            sys.exit(f"{PDF_CSV.name}: chapter {row['chapter']!r} is not in the question bank")
        if kind not in ("free", "paid"):
            sys.exit(f"{PDF_CSV.name}: type for {row['chapter']!r} must be free, paid or empty, not {kind!r}")
        if kind == "paid" and row.get("drive_link"):
            # The CSV holds the full address (ready to paste into Razorpay); a bare file name also works.
            page = row.get("thank_you_page", "").rsplit("/", 1)[-1]
            if not re.fullmatch(r"thanks-[a-z0-9]+\.html", page):
                if page:
                    sys.exit(f"{PDF_CSV.name}: thank_you_page for {row['chapter']!r} should look like "
                             f"{SITE}/thanks-xxxx.html, not {row['thank_you_page']!r}")
                alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
                page = "thanks-" + "".join(secrets.choice(alphabet) for _ in range(22)) + ".html"
            if row.get("thank_you_page") != f"{SITE}/{page}":
                row["thank_you_page"] = f"{SITE}/{page}"
                added = True
            THANKS[name] = (page, drive_download(row["drive_link"]))
        if kind == "free" and row.get("drive_link"):
            FREE_PDFS[name] = drive_download(row["drive_link"])
        elif kind == "paid" and row.get("razorpay_link"):
            PDF_LINKS[name] = row["razorpay_link"]
        else:
            print(f"NOTE: {row['chapter']} is marked {kind} but has no link yet; showing Coming soon", file=sys.stderr)
    if added:
        try:  # utf-8 with BOM so Excel shows the dash in "Light – Reflection and Refraction" correctly
            with PDF_CSV.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=reader.fieldnames)
                w.writeheader()
                w.writerows(rows)
        except PermissionError:
            sys.exit(f"Close {PDF_CSV.name} in Excel and run again (new thank-you pages need to be saved into it).")


def build_thanks_page(c, page, download):
    """Unlisted Razorpay thank-you page for one paid chapter. See the comment inside for the rules."""
    name = c["chapter"]
    item_id = slug(name)
    price = re.sub(r"[^0-9]", "", PDF_PRICE)
    gtag, nav, footer = shared_chrome()
    gtag_id = re.search(r"G-[A-Z0-9]+", gtag).group(0)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <!-- Generated by build_pyq_coverage.py from data/chapter-pdfs.csv; don't hand-edit.
       Unlisted thank-you page for the Razorpay Payment Page redirect. Not in the sitemap and not linked
       from anywhere. If the link leaks, clear thank_you_page for this chapter in the CSV, rerun the script
       (a new address is made) and update the redirect URL in Razorpay; then delete the old file.
       Analytics: this page collects no personal data. It sends one purchase event (price and chapter only)
       and reports itself as /pdf-thank-you so neither this secret address nor Razorpay's payment id
       query string ever reaches GA. The count is approximate (a refresh or shared link can repeat it);
       Razorpay is the source of truth for revenue. -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={gtag_id}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{gtag_id}', {{ page_location: 'https://mindvsyou.io/pdf-thank-you', page_referrer: '' }});
    (function () {{
      var key = 'pdfPurchaseSent:{item_id}';
      try {{ if (localStorage.getItem(key)) return; localStorage.setItem(key, '1'); }} catch (e) {{}}
      var id = 'tx-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      gtag('event', 'purchase', {{
        transaction_id: id,
        currency: 'INR',
        value: {price},
        items: [{{ item_id: '{item_id}', item_name: {json.dumps(name + ' PDF', ensure_ascii=False)}, item_category: 'PDF', price: {price}, quantity: 1 }}]
      }});
    }})();
  </script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Thank You — Your {esc(name)} PDF | MindVsYou</title>
  <meta name="robots" content="noindex, nofollow" />
  <meta name="referrer" content="no-referrer" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <meta name="theme-color" content="#25D366" />
  <link rel="stylesheet" href="style.css?v=20261107" />
  <style>.contact-body p {{ margin: 0 0 16px; line-height: 1.6; }}</style>
</head>
<body>

{nav}  <section class="contact-hero">
    <div class="container">
      <span class="eyebrow" style="color:var(--green);">Payment received</span>
      <h1>Thank you! Your PDF is ready</h1>
      <p>CBSE Class 10 Science · {esc(name)}: previous year practice questions with the official answers and Mindy's step-by-step explanations.</p>
    </div>
  </section>

  <section class="contact-body">
    <div class="container" style="max-width:640px;margin:0 auto;padding:0 16px 48px;text-align:center;">
      <!-- PDF is on Google Drive (mindvsyou@gmail.com, "anyone with the link"). If the file is replaced
           with a new upload, keep the same Drive file (Manage versions) so this link keeps working. -->
      <p><a id="pdfDownload" class="btn btn-green" href="{esc(download)}" rel="noopener" download>Download your PDF &darr;</a></p>
      <p style="margin-top:20px;">Save the file to your phone or computer so you always have it. This page works as your receipt, so bookmark it if you like.</p>
      <p>This PDF is for your own exam preparation. Please don't share the download link or the file, as that is what lets us keep adding new chapters.</p>
      <p>Didn't get the PDF, or something looks wrong? Email <a href="mailto:hello@mindvsyou.io">hello@mindvsyou.io</a> with the payment id from your Razorpay receipt and we'll sort it out.</p>
      <p style="margin-top:24px;"><a class="btn btn-outline" href="{esc(practice_url("mcq", c))}">Practise {esc(name)} on MindVsYou &rarr;</a></p>
    </div>
  </section>

{footer}"""

QUIZ_PYQ ="https://quiz.mindvsyou.io/pyq?class=10&subject=science"


def practice_url(kind=None, chapter=None):
    """The one place practice links are built. kind: "mcq", "subjective" or "casebased".

    Prefers the endpoint's ready-made mcqUrl / subjectiveUrl / caseBasedUrl when a chapter provides them.
    The endpoint's own practiceUrl is deliberately ignored (it redirects to the app home page).
    """
    if kind is None:
        return QUIZ_PYQ
    ready = chapter.get({"mcq": "mcqUrl", "subjective": "subjectiveUrl", "casebased": "caseBasedUrl"}[kind])
    if ready:
        return ready
    t = "mcq-practice" if kind == "mcq" else "subjective-interactive"
    # case-based = the subjective flow narrowed with qtype (must be written exactly "Case-based")
    q = "&qtype=Case-based" if kind == "casebased" else ""
    # same escaping as JavaScript's encodeURIComponent; the app matches the chapter name exactly
    return f"{QUIZ_PYQ}&type={t}{q}&chapter={urllib.parse.quote(chapter['chapter'], safe=chr(33)+chr(39)+'()*~')}"


def answer_html(s):
    """Collapsed answer + explanation. The text stays in the HTML so crawlers can read it."""
    if not s.get("answer") and not s.get("explanation"):
        return ""
    parts = []
    if s.get("answer"):
        if s.get("options"):
            parts.append(f'<p><strong>Answer: {esc(s["answer"])}</strong>'
                         + (f' &ndash; {text_html(s["answerText"])}' if s.get("answerText") else "") + "</p>")
        else:
            parts.append(f'<p><strong>Answer:</strong><br>{text_html(s["answer"])}</p>')
    if s.get("explanation"):
        parts.append(f'<p><strong>AI Explanation</strong>:<br>{text_html(s["explanation"])}</p>')
    if s.get("truncated"):
        parts.append("<p><em>Full answer in practice mode.</em></p>")
    return '<details class="pyq-answer"><summary>Show answer</summary>' + "".join(parts) + "</details>"


RAIL_JS = r'''
  <script>
  (function () {
    var rail = document.getElementById('chapterRail'), btn = document.getElementById('railToggle');
    if (!rail || !btn) return;
    function set(open) { rail.classList.toggle('open', open); btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    btn.addEventListener('click', function () { set(!rail.classList.contains('open')); });
    rail.addEventListener('click', function (e) { if (e.target.closest('a')) set(false); });
    if (!('IntersectionObserver' in window)) return;
    var links = {};
    rail.querySelectorAll('a').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        Object.keys(links).forEach(function (k) { links[k].classList.remove('active'); });
        if (links[en.target.id]) links[en.target.id].classList.add('active');
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    Object.keys(links).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
  })();
  </script>
'''


# Chapter PDFs page only: chapter cards and the preview gallery. Kept here (not in style.css) so other pages
# and the style.css cache are untouched.
PDF_CSS = r'''  <style>
    .post-hero.pdf-hero { padding: 32px 24px 30px; }
    .pdf-hero .container { max-width: 1040px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 20px 40px; }
    .pdf-hero-text { flex: 1 1 420px; }
    .post-hero.pdf-hero h1 { margin: 10px 0 10px; }
    .pdf-hero-text p { color: #c9d4e0; margin: 0; font-size: 1.02rem; line-height: 1.5; max-width: 560px; }
    .pdf-hero-stats { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(118px, 1fr)); gap: 10px; flex: 0 0 auto; }
    .pdf-hero-stats li { margin: 0; background: rgba(255, 255, 255, 0.07); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 10px 14px; font-size: 0.8rem; color: #c9d4e0; line-height: 1.3; }
    .pdf-hero-stats b { display: block; font-family: var(--font-display); font-size: 1.35rem; font-weight: 800; color: var(--green); }
    .post-body.pdf-page { padding-top: 28px; }
    .post-body.pdf-page h2#chapter-pdfs { margin-top: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; }
    .pdf-h2-note { font-family: var(--font-body); font-size: 0.92rem; font-weight: 500; color: var(--text-light); }
    .post-body .pdf-trust { margin-top: 8px; }
    .pdf-wide { margin: 8px 0 32px; }
    @media (min-width: 900px) { .post-body .pdf-wide { width: min(1040px, calc(100vw - 48px)); position: relative; left: 50%; transform: translateX(-50%); } }
    .post-body .pdf-trust { list-style: none; padding: 0; margin: 0 0 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
    .post-body .pdf-trust li { margin: 0; display: flex; gap: 10px; align-items: flex-start; background: var(--off-white); border-radius: 12px; padding: 12px 14px; font-size: 0.9rem; line-height: 1.4; color: var(--text-mid); }
    .pdf-trust .ic { font-size: 1.2rem; line-height: 1.2; }
    .pdf-trust b { color: var(--text-dark); display: block; }
    .pdf-free { display: flex; flex-wrap: wrap; gap: 16px 24px; align-items: center; justify-content: space-between; background: linear-gradient(135deg, #0D1B2A 0%, #14324a 100%); color: #fff; border-radius: 20px; padding: 24px 28px; margin: 0 0 36px; }
    .pdf-free .tag { display: inline-block; background: var(--green); color: #0D1B2A; font-weight: 800; font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; padding: 4px 10px; border-radius: 999px; }
    .post-body .pdf-free h3 { color: #fff; font-size: 1.35rem; margin: 10px 0 6px; }
    .post-body .pdf-free p { color: #c9d4e0; margin: 0; font-size: 0.95rem; max-width: 520px; }
    .pdf-free .btns { display: flex; flex-direction: column; gap: 10px; min-width: 240px; }
    .post-body .pdf-free .btns a.btn { justify-content: center; text-align: center; }
    .pdf-group-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; margin: 8px 0 14px; }
    .post-body .pdf-group-head h3 { margin: 0; font-size: 1.4rem; }
    .pdf-group-head span { color: var(--text-light); font-size: 0.92rem; }
    .post-body .pdf-group-head h3 { scroll-margin-top: 90px; }
    .pdf-jump { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; }
    .post-body .pdf-jump a { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 999px; font-size: 0.9rem; font-weight: 700; text-decoration: none; color: var(--accent); background: var(--tint); }
    .pdf-jump span { font-size: 0.75rem; opacity: 0.75; }
    .pdf-jump-chem { --accent: #E8590C; --tint: #FFF1E8; }
    .pdf-jump-bio { --accent: #1AAE54; --tint: #E7F9EE; }
    .pdf-jump-phy { --accent: #2563EB; --tint: #EAF1FE; }
    .pdf-hero-short { display: none; }
    .pdf-mindy { display: block; width: 24px; height: 24px; margin: 0; }
    .pdf-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 18px; margin: 0 0 36px; }
    .pdf-card { --accent: var(--green); --tint: #E7F9EE; display: flex; flex-direction: column; background: var(--white); border: 1px solid var(--border); border-radius: 18px; overflow: hidden; box-shadow: 0 2px 10px rgba(13, 27, 42, 0.05); transition: transform .15s ease, box-shadow .15s ease; }
    .pdf-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(13, 27, 42, 0.12); }
    .pdf-card.subj-chem { --accent: #E8590C; --tint: #FFF1E8; }
    .pdf-card.subj-bio { --accent: #1AAE54; --tint: #E7F9EE; }
    .pdf-card.subj-phy { --accent: #2563EB; --tint: #EAF1FE; }
    .pdf-peek { position: relative; display: block; width: 100%; height: 190px; padding: 0; border: 0; border-bottom: 1px solid var(--border); background: var(--tint); overflow: hidden; cursor: zoom-in; }
    .pdf-peek img { display: block; width: 100%; height: 100%; object-fit: cover; object-position: top; margin: 0; }
    .pdf-peek::after { content: ""; position: absolute; inset: auto 0 0 0; height: 70px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,0.95)); }
    .pdf-peek .look { position: absolute; z-index: 1; left: 50%; bottom: 12px; transform: translateX(-50%); white-space: nowrap; background: #0D1B2A; color: #fff; font-size: 0.8rem; font-weight: 700; padding: 7px 14px; border-radius: 999px; box-shadow: 0 4px 12px rgba(13, 27, 42, 0.25); }
    .pdf-peek:hover .look { background: var(--accent); }
    .pdf-peek-empty { cursor: default; display: flex; align-items: center; justify-content: center; color: var(--text-light); font-weight: 700; }
    .pdf-body { display: flex; flex-direction: column; flex: 1; padding: 16px 18px 18px; }
    .pdf-top { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 8px; }
    .pdf-chip { font-size: 0.72rem; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase; color: var(--accent); background: var(--tint); padding: 4px 9px; border-radius: 999px; }
    .pdf-badge { font-size: 0.72rem; font-weight: 800; color: #7A4B00; background: #FFE8A3; padding: 4px 9px; border-radius: 999px; }
    .pdf-badge.free { color: #0D1B2A; background: var(--green); }
    .post-body .pdf-card h3 { font-size: 1.12rem; margin: 0 0 10px; line-height: 1.3; }
    .pdf-big { display: flex; align-items: baseline; gap: 8px; margin: 0 0 6px; }
    .pdf-big b { font-family: var(--font-display); font-size: 2rem; font-weight: 800; line-height: 1; color: var(--text-dark); }
    .pdf-big span { font-size: 0.9rem; color: var(--text-mid); line-height: 1.3; }
    .post-body .pdf-types { list-style: none; padding: 0; margin: 0 0 8px; display: flex; flex-wrap: wrap; gap: 6px; }
    .post-body .pdf-types li { margin: 0; font-size: 0.78rem; color: var(--text-mid); background: var(--off-white); border-radius: 6px; padding: 3px 8px; }
    .post-body .pdf-extra { font-size: 0.84rem; color: var(--text-mid); margin: 0 0 14px; }
    .pdf-buy { margin-top: auto; border-top: 1px dashed var(--border); padding-top: 14px; }
    .pdf-price-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
    .pdf-price { font-family: var(--font-display); font-weight: 800; font-size: 1.6rem; color: var(--text-dark); line-height: 1; }
    .pdf-ppq { font-size: 0.8rem; font-weight: 600; color: var(--accent); text-align: right; }
    .post-body a.btn.pdf-cta { display: flex; justify-content: center; width: 100%; box-sizing: border-box; font-size: 1rem; padding: 13px 18px; }
    .post-body .pdf-assure { font-size: 0.76rem; color: var(--text-light); text-align: center; margin: 8px 0 0; }
    .pdf-soon { display: block; text-align: center; font-weight: 700; color: var(--text-light); background: var(--off-white); border-radius: 10px; padding: 12px; }
    .pdf-samples { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin: 8px 0 16px; }
    .pdf-samples figure { margin: 0; }
    .pdf-samples figcaption { font-size: 0.8rem; color: var(--text-light); margin-top: 6px; line-height: 1.35; }
    .pdf-sample { display: block; width: 100%; padding: 0; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: none; cursor: zoom-in; }
    .pdf-sample img { display: block; width: 100%; height: auto; margin: 0; }
    .pdf-lightbox { border: 0; padding: 0; background: transparent; max-width: 100vw; max-height: 100vh; width: 100vw; height: 100vh; }
    .pdf-lightbox::backdrop { background: rgba(10, 16, 24, 0.88); }
    .pdf-lightbox figure { margin: 0; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 56px 16px; box-sizing: border-box; }
    .pdf-lightbox img { max-width: 100%; max-height: calc(100vh - 110px); width: auto; height: auto; border-radius: 6px; background: #fff; }
    .pdf-lightbox figcaption { color: #fff; font-size: 0.9rem; margin-top: 10px; text-align: center; }
    .pdf-lightbox button { position: absolute; background: rgba(255, 255, 255, 0.14); color: #fff; border: 0; border-radius: 50%; width: 44px; height: 44px; font-size: 1.8rem; line-height: 1; cursor: pointer; }
    .pdf-lightbox .lb-close { top: 10px; right: 10px; }
    .pdf-lightbox .lb-prev { left: 8px; top: 50%; transform: translateY(-50%); }
    .pdf-lightbox .lb-next { right: 8px; top: 50%; transform: translateY(-50%); }
    @media (max-width: 600px) {
      .post-hero.pdf-hero { padding: 18px 16px 18px; }
      .post-hero.pdf-hero h1 { font-size: 1.5rem; margin: 8px 0 0; }
      .pdf-hero-text p.pdf-hero-long { display: none; }
      .pdf-hero-text p.pdf-hero-short { display: block; font-size: 0.92rem; margin-top: 8px; }
      .post-body .pdf-types { display: none; }
      .post-body .pdf-card h3 { margin-bottom: 6px; }
      .pdf-body { padding: 14px 16px 16px; }
      .pdf-hero .container { gap: 14px; }
      .post-body.pdf-page h2#chapter-pdfs { font-size: 1.35rem; margin-bottom: 8px; }
      .pdf-group-head { margin: 4px 0 10px; }
      .post-body .pdf-group-head h3 { font-size: 1.2rem; }
      .pdf-hero-stats { grid-template-columns: repeat(4, 1fr); gap: 6px; width: 100%; }
      .pdf-hero-stats li { padding: 8px 6px; font-size: 0.68rem; text-align: center; }
      .pdf-hero-stats b { font-size: 1rem; }
      .post-body.pdf-page { padding-top: 20px; }
      .pdf-cards { grid-template-columns: 1fr; }
      .pdf-free { padding: 20px; }
      .pdf-free .btns { min-width: 0; width: 100%; }
      .pdf-peek { height: 140px; }
      .pdf-lightbox figure { padding: 52px 8px 72px; }
      .pdf-lightbox .lb-prev, .pdf-lightbox .lb-next { top: auto; bottom: 14px; transform: none; }
      .pdf-lightbox .lb-prev { left: calc(50% - 56px); } .pdf-lightbox .lb-next { right: calc(50% - 56px); }
    }
  </style>'''

PDF_JS = r'''
  <script>
  (function () {
    var box = document.getElementById('pdfLightbox'), data = document.getElementById('pdfGalleries');
    if (!box || !data || typeof box.showModal !== 'function') return;
    var galleries = JSON.parse(data.textContent), img = box.querySelector('img'), cap = box.querySelector('figcaption');
    var list = [], i = 0;
    function show() { img.src = list[i].src; img.alt = list[i].caption; cap.textContent = list[i].caption + '  (' + (i + 1) + ' of ' + list.length + ')'; }
    function step(d) { i = (i + d + list.length) % list.length; show(); }
    document.addEventListener('click', function (e) {
      var t = e.target.closest('[data-gallery]');
      if (!t || !galleries[t.dataset.gallery]) return;
      list = galleries[t.dataset.gallery]; i = Number(t.dataset.index) || 0; show(); box.showModal();
      if (typeof gtag === 'function') gtag('event', 'pdf_preview_open', { pdf_chapter: t.dataset.chapter || t.dataset.gallery });
    });
    box.querySelector('.lb-close').addEventListener('click', function () { box.close(); });
    box.querySelector('.lb-prev').addEventListener('click', function () { step(-1); });
    box.querySelector('.lb-next').addEventListener('click', function () { step(1); });
    box.addEventListener('click', function (e) { if (e.target === box || e.target.tagName === 'FIGURE') box.close(); });
    box.addEventListener('keydown', function (e) { if (e.key === 'ArrowLeft') step(-1); if (e.key === 'ArrowRight') step(1); });
    var x0 = null;
    box.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) { if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1); x0 = null; });
  })();
  </script>
'''


def action_links(c, cls, full=False):
    """MCQ, written-question and (where the chapter has any) case-based practice buttons."""
    name = esc(c["chapter"])
    out = (f'<a class="btn btn-green {cls}" href="{esc(practice_url("mcq", c))}" aria-label="Practise {name} MCQs">{f"Practise {name} MCQs &rarr;" if full else "MCQs"}</a>'
           f'<a class="btn btn-green {cls}" href="{esc(practice_url("subjective", c))}" aria-label="Practise {name} VSA, SA, LA questions">{f"Practise {name} VSA, SA, LA &rarr;" if full else "VSA, SA, LA"}</a>')
    if c["byType"].get("Case-based"):
        out += (f'<a class="btn btn-green {cls}" href="{esc(practice_url("casebased", c))}" aria-label="Practise {name} case-based questions">'
                f'{f"Practise {name} case-based questions &rarr;" if full else "Case-based"}</a>')
    return out


def pdf_button(c, label=None, cls="btn btn-green pdf-cta"):
    """'Download free PDF' or 'Get the PDF · ₹49' button for a chapter; empty until the chapter has a link.
    Keep the data-* attributes: main.js uses them for the free_pdf_click / buy_pdf_click / begin_checkout events."""
    name = esc(c["chapter"])
    free = FREE_PDFS.get(c["chapter"])
    if free:
        return (f'<a class="{cls}" href="{esc(free)}" data-free-pdf="{name}" rel="noopener" '
                f'aria-label="Download the free {name} PDF with Mindy explanations">{label or "Download free PDF &darr;"}</a>')
    url = PDF_LINKS.get(c["chapter"])
    if not url:
        return ""
    price = re.sub(r"[^0-9]", "", PDF_PRICE)
    return (f'<a class="{cls}" href="{esc(url)}" data-buy-pdf="{name}" data-price="{price}" '
            f'aria-label="Buy the {name} PDF with Mindy explanations for {esc(PDF_PRICE)}">{label or f"Get the PDF &middot; {esc(PDF_PRICE)}"}</a>')


def pdf_chapters(chapters):
    """Chapters that have a free or paid PDF, in the given (NCERT) order."""
    return [c for c in chapters if c["chapter"] in FREE_PDFS or c["chapter"] in PDF_LINKS]


def pdf_summary(chapters):
    """Plain-text 'Free to download: ... Available for ₹49 each: ...' line; empty if there are no PDFs."""
    names = {c["chapter"] for c in chapters}
    free_names = [k for k in FREE_PDFS if k in names]
    paid_names = [k for k in PDF_LINKS if k in names and k not in FREE_PDFS]
    parts = []
    if free_names:
        parts.append("Free to download: " + ", ".join(free_names) + ".")
    if paid_names:
        parts.append(f"Available for {PDF_PRICE} each: " + ", ".join(paid_names) + ".")
    return " ".join(parts)


def shared_chrome():
    """gtag snippet, nav and footer copied from an existing page so they stay identical."""
    ref = (ROOT / "cbse-class-10-science-pyq.html").read_text(encoding="utf-8")
    gtag = ref[ref.index("  <!-- Google tag"):ref.index("  <meta charset")]
    nav = ref[ref.index("  <nav id=\"navbar\">"):ref.index("  <div class=\"page-header\">")]
    footer = ref[ref.index("  <footer id=\"footer\">"):]
    return gtag, nav, footer


def esc(s):
    return html.escape(s, quote=True)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def span(years):
    return f"{min(years)}&ndash;{max(years)}" if len(years) > 1 else str(years[0])


def text_html(t):
    return esc(t.replace("\r\n", "\n").strip()).replace("\n", "<br>\n")


def build(d):
    ys = d["years"]
    chapters = sorted(d["chapters"], key=lambda c: (ncert_no(c["chapter"]) or 99, c["chapter"]))
    n = len(chapters)
    total = f'{d["totalQuestions"]:,}'
    y0, y1 = min(ys), max(ys)
    ydesc = ", ".join(map(str, ys))
    date = d["generatedAt"][:10]
    pretty_date = __import__("datetime").date.fromisoformat(date).strftime("%d %B %Y").lstrip("0")
    practice = practice_url()

    title = "CBSE Class 10 Science PYQs: Find & Fix Weak Chapters | MindVsYou"
    desc = (f"Practise CBSE Class 10 Science PYQs chapter by chapter. Questions you get wrong come back for another shot. "
            f"{n} chapters, board years {y0}–{y1}, with answers and AI explanations.")
    h1 = "CBSE Class 10 Science PYQs: know your weak chapters, fix them calmly"

    rows = []
    for c in chapters:
        cells = "".join(f'<td data-label="{t}"{" class=\"zero\"" if not c["byType"].get(t, 0) else ""}>{c["byType"].get(t, 0)}</td>'
                        for t in TYPES)
        rows.append(f'<tr><td><a href="#{slug(c["chapter"])}">{esc(label(c["chapter"]))}</a></td>{cells}'
                    f'<td data-label="Total"><strong>{c["total"]}</strong></td><td data-label="Board years">{span(c["years"])}</td>'
                    f'<td class="row-actions">{action_links(c, "btn-sm")}</td></tr>')
    table = ('<div class="table-scroll"><table class="cov-table"><thead><tr><th>Chapter</th>'
             + "".join(f"<th>{t}</th>" for t in TYPES)
             + "<th>Total</th><th>Board years</th><th>Click to practice</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div>")

    sections = []
    for c in chapters:
        counts = ", ".join(f'{c["byType"][t]} {t}' for t in TYPES if c["byType"].get(t))
        subs = "".join(f"<li>{esc(s)}</li>" for s in c["subtopics"])
        samples = []
        order = {t: i for i, t in enumerate(TYPES)}
        for s in sorted(filter(lambda x: sample_ok(c["chapter"], x), c["samples"]), key=lambda x: order.get(x["type"], 99)):
            opts = s.get("options")
            note = (' <em>(sample shows the question only; answer options appear in practice)</em>'
                    if s["type"] == "MCQ" and not opts else "")
            options_html = ('<ol class="pyq-options" type="A">'
                            + "".join(f"<li>{text_html(opts[k])}</li>" for k in "ABCD" if k in opts) + "</ol>") if opts else ""
            reveal = answer_html(s)
            samples.append(
                '<div class="chat-msg"><svg class="mindy" viewBox="3 2 114 108" aria-hidden="true" focusable="false">'
                '<use href="mindy.svg#face"/></svg>'
                f'<div class="chat-bubble"><p class="pyq-tag"><strong>{esc(s["type"])}</strong> '
                f'&middot; {s["year"]} &middot; {s["marks"]} mark{"s" if s["marks"] != 1 else ""}{note}</p>'
                f'<p>{text_html(s["text"])}</p>{options_html}{reveal}</div></div>')
        sections.append(
            f'<h3 id="{slug(c["chapter"])}">{esc(label(c["chapter"]))}</h3>\n'
            f'<p><strong>{c["total"]} practice questions</strong> from board years {span(c["years"])}: {counts}.</p>\n'
            f'<p>Subtopics:</p><ul>{subs}</ul>\n'
            f'<p>Sample questions:</p>\n{"".join(samples)}\n'
            f'<div class="chapter-actions">{action_links(c, "", True)}</div>')

    n_types = len({t for c in chapters for t in c["byType"]})
    by_size = sorted(chapters, key=lambda c: -c["total"])
    top3 = ", ".join(f'{esc(c["chapter"])} ({c["total"]})' for c in by_size[:3])
    top_line = (f"Most practice questions: {top3}. Fewest: {esc(by_size[-1]['chapter'])} "
                f"({by_size[-1]['total']} practice questions). Start with the chapters where you score lowest, "
                f"then use the case-based and assertion-reason questions to test how well you can apply a concept.")
    ar = sum(c["byType"].get("Assertion-Reason", 0) for c in chapters)
    ar_line = (f"MCQ practice includes {ar} assertion-reason question{'s' if ar != 1 else ''}. " if ar else "")
    pdf_line = pdf_summary(chapters)
    pdf_pointer = (f'<p>Prefer to study offline? <a href="{PDF_PAGE}">Chapter-wise PDFs of these practice questions</a> '
                   f'come with the official answers and Mindy&rsquo;s step-by-step explanations.</p>') if pdf_line else ""
    faqs = [
        ("Which years of CBSE Class 10 Science PYQs can I practise on MindVsYou?",
         f"The interactive question bank covers CBSE Class 10 Science board years {ydesc}."),
        ("Which question types are available?",
         "Multiple choice (MCQ), assertion-reason, very short answer (VSA), short answer (SA), long answer (LA) and case-based questions. "
         "Not every chapter has every type; the table above shows the exact counts."),
        ("Can I try PYQ practice without an account?",
         "Yes. You can start as a guest with both MCQ practice and written-question practice, no account needed, and the questions you miss still come back for you to redo."),
        ("Are there chapter-wise PDFs of CBSE Class 10 Science PYQs with answers?",
         "Yes. Each chapter PDF has every practice question for that chapter with the official answers and Mindy's step-by-step explanations. "
         + (pdf_line + " " if pdf_line else "") + f"They are listed on {PDF_PAGE_URL}"),
        ("How does the practice work?",
         "MCQ practice gives 10 questions per round by chapter, with optional subtopic, instant marking, official answers and AI explanations. " + ar_line +
         "Subjective practice gives 10 questions per round by chapter, subtopic and type; you attempt first, then rate yourself against the official answer."),
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)

    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Students", "item": SITE + "/students.html"},
            {"@type": "ListItem", "position": 3, "name": "Class 10 Science PYQ coverage", "item": PAGE_URL}]},
        {"@context": "https://schema.org", "@type": "Dataset",
         "name": "CBSE Class 10 Science PYQ coverage on MindVsYou",
         "description": (f"Chapter-wise inventory of {total} CBSE Class 10 Science previous year practice questions "
                         f"across {n} chapters, board years {y0}–{y1}, by question type."),
         "url": PAGE_URL, "temporalCoverage": f"{y0}/{y1}", "inLanguage": "en-IN",
         "isAccessibleForFree": True, "dateModified": date,
         "creator": {"@type": "Organization", "name": "MindVsYou", "url": SITE + "/"},
         "keywords": ["CBSE Class 10 Science", "PYQ", "previous year questions"] + [c["chapter"] for c in chapters]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
    ]
    ld_html = "".join(
        f'  <script type="application/ld+json">\n  {json.dumps(x, indent=2, ensure_ascii=False)}\n  </script>\n' for x in ld)

    gtag, nav, footer = shared_chrome()

    rail_links = "".join(f'<li><a href="#{slug(c["chapter"])}">{esc(label(c["chapter"]))}</a></li>' for c in chapters)
    rail = (f'<button type="button" class="rail-toggle" id="railToggle" aria-expanded="false" aria-controls="chapterRail">&#9776; Chapters</button>'
            f'<aside class="chapter-rail" id="chapterRail" aria-label="Jump to a chapter"><p class="rail-title">Contents</p>'
            f'<ul><li><a href="#coverage-table">Coverage table</a></li>{rail_links}<li><a href="#faq">FAQ</a></li></ul></aside>')
    toc = "".join(f'<li><a href="#{slug(c["chapter"])}">{esc(c["chapter"])}</a></li>' for c in chapters)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{gtag}  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{PAGE_URL}" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <meta name="theme-color" content="#25D366" />

  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="MindVsYou" />
  <meta property="og:title" content="{esc(h1)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{PAGE_URL}" />
  <meta property="og:locale" content="en_IN" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(h1)}" />
  <meta name="twitter:description" content="{esc(desc)}" />

  <link rel="stylesheet" href="style.css?v=20261107" />

{ld_html}</head>
<body>

{nav}  <div class="page-header">
    <div class="breadcrumb">
      <a href="/">Home</a> / <a href="students.html">Students</a> / Class 10 Science PYQ coverage
    </div>
  </div>

  <section class="post-hero">
    <div class="container">
      <span class="blog-tag">PYQ Practice</span>
      <h1>{esc(h1)}</h1>
      <div class="post-meta">Data last updated {pretty_date} &middot; By the MindVsYou team</div>
    </div>
  </section>

  <section class="post-body">
  <div class="cov-layout">
{rail}
    <div class="container">

      <p class="post-lede">Real CBSE board questions, chapter by chapter. Get one wrong and it comes back later for another shot, so you stop re-reading what you already know and fix what you don&rsquo;t. Here&rsquo;s everything inside.</p>
      <div class="stat-row">
        <div class="stat stat-hero"><span class="stat-icon" aria-hidden="true">&#11088;</span><span class="stat-num">{total}</span><span class="stat-label">practice questions</span></div>
        <div class="stat"><span class="stat-icon" aria-hidden="true">&#128214;</span><span class="stat-num">{n}</span><span class="stat-label">chapters</span></div>
        <div class="stat"><span class="stat-icon" aria-hidden="true">&#128197;</span><span class="stat-num">{y0}&ndash;{y1}</span><span class="stat-label">board years</span></div>
        <div class="stat"><span class="stat-icon" aria-hidden="true">&#10024;</span><span class="stat-num">{n_types}</span><span class="stat-label">question types</span></div>
      </div>
      <div class="quick-answer"><span class="qa-label">Quick answer</span><p><strong>Where can I practise CBSE Class 10 Science PYQs chapter-wise?</strong> On <a href="{esc(practice)}">quiz.mindvsyou.io</a>: {total} practice questions from board years {y0}&ndash;{y1}, in MCQ, assertion-reason, very short, short, long and case-based formats, with instant marking for MCQs. Miss a question and it comes back for another shot, and you can see which chapters are pulling your score down. You can start as a guest, no account needed.</p></div>
      <p>Some board questions have several parts, and each part can count as its own practice question.</p>
      <p>{top_line}</p>

      <h2 id="coverage-table">Coverage by chapter and question type</h2>
      <p>Number of practice questions. A zero means that chapter has none of that type in the bank. VSA = very short answer, SA = short answer, LA = long answer.</p>
      {table}

      <div class="mindy-say">
        <svg class="mindy" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="mindy.svg#cheer"/></svg>
        <div class="mindy-say-b">
          <p><strong>Why practise with Mindy?</strong> Mindy, the MindVsYou chat buddy, gives you one question at a time, so it never feels like a huge paper. MCQs are marked the second you answer, with the official answer and an AI explanation. For written questions you try first, then check the official answer and rate yourself. Missed one? It comes back. Your weak chapters show up too, so you know what to fix before boards. You can start as a guest.</p>
          <p>Pick MCQs, VSA, SA, LA or case-based questions for any chapter in the table above.</p>
          <a href="{esc(practice)}" class="btn btn-green">Start practising &rarr;</a>
        </div>
      </div>

      <h2 id="question-types">What the question types mean</h2>
      <ul>{"".join(f"<li>{esc(v)}</li>" for v in TYPE_NAMES.values())}</ul>

      <h2 id="chapters">Chapter-by-chapter inventory</h2>
      <nav class="post-toc" aria-label="Chapters"><h2>Jump to a chapter</h2><ol>{toc}</ol></nav>
{chr(10).join(sections)}

      <h2 id="how-practice-works">How practice works on quiz.mindvsyou.io</h2>
      <ul>
        <li><strong>MCQ practice:</strong> 10 questions per round, by chapter and optional subtopic, with instant marking, the official answer and an AI explanation. {ar_line}Guests can use it without an account.</li>
        <li><strong>Subjective practice:</strong> 10 questions per round by chapter, subtopic and type. You write your answer first, then rate yourself against the official answer.</li>
        <li><strong>Worksheets:</strong> chapter-wise worksheet PDFs for MCQ and subjective questions.</li>
        <li><strong>Redo what you missed:</strong> questions you got wrong come back for another shot, and your weak chapters show up so you know where to focus before boards.</li>
      </ul>
      <p>All practice is chat-style: one question at a time, with Mindy, the MindVsYou chat buddy.</p>
      {pdf_pointer}

      <h2 id="faq">Frequently asked questions</h2><div class="post-faq">{faq_html}</div>

      <div class="post-cta"><h3>Pick a chapter and start</h3><p>Open PYQ practice on quiz.mindvsyou.io. Miss one and it comes back.</p><div class="btn-row"><a href="{esc(practice)}" class="btn btn-green">Practise Class 10 Science PYQs &rarr;</a></div><p class="cta-sub"><a href="cbse-class-10-science-pyq.html">What PYQs are and how to use them →</a> · <a href="class-10-science-previous-year-question-paper.html">Question paper PDFs →</a>{f' · <a href="{PDF_PAGE}">Chapter PDFs →</a>' if pdf_line else ""}</p></div>


    </div>
  </div>
  </section>

{RAIL_JS}{footer}"""


def build_pdf_page(d):
    """The chapter PDFs page: the only place free and paid chapter PDFs are offered."""
    ys = d["years"]
    y0, y1 = min(ys), max(ys)
    all_chapters = sorted(d["chapters"], key=lambda c: (ncert_no(c["chapter"]) or 99, c["chapter"]))
    chapters = pdf_chapters(all_chapters)
    pdf_line = pdf_summary(chapters)
    more = " More chapters are added over time." if len(chapters) < len(all_chapters) else ""
    has_paid = any(c["chapter"] in PDF_LINKS and c["chapter"] not in FREE_PDFS for c in chapters)
    practice = practice_url()

    title = "CBSE Class 10 Science PYQ Chapter-wise PDFs with Answers | MindVsYou"
    h1 = "CBSE Class 10 Science PYQ: Chapter-wise PDFs with answers"
    # Kept short (Google shows about 155 characters); the full chapter list is in the page and its FAQ.
    n_free = sum(c["chapter"] in FREE_PDFS for c in chapters)
    n_paid = len(chapters) - n_free
    offer = " ".join(filter(None, [f"{n_free} free," if n_free else "", f"{n_paid} at {PDF_PRICE}." if n_paid else ""]))
    desc = (f"CBSE Class 10 Science PYQ PDFs, chapter by chapter, with official answers and step-by-step "
            f"explanations. {offer}").rstrip(",")

    def price(c):
        if c["chapter"] in FREE_PDFS:
            return "Free"
        return esc(PDF_PRICE) if c["chapter"] in PDF_LINKS else "Coming soon"

    # Every chapter gets a card; chapters without a PDF yet show "Coming soon" and no button.
    # Counts and preview images come from data/chapter-pdf-stats.json (made by make_pdf_previews.py; no links in it).
    stats = {norm(k): v for k, v in json.loads(PDF_STATS.read_text(encoding="utf-8")).items()} if PDF_STATS.exists() else {}

    def stat(c, key):
        return (stats.get(norm(c["chapter"])) or {}).get(key) if c in chapters else None

    short = {"Multiple Choice Questions": "MCQ", "Very Short Answer Questions": "very short", "Short Answer Questions": "short answer",
             "Long Answer Questions": "long answer", "Case-Based Questions": "case-based"}
    galleries = {}
    # Factual badges only (no invented popularity): the chapter with the most questions / most figures.
    with_q = [c for c in chapters if stat(c, "questions")]
    badges = {}
    if with_q:
        badges.setdefault(max(with_q, key=lambda c: stat(c, "questions"))["chapter"], "Most questions")
        badges.setdefault(max(with_q, key=lambda c: stat(c, "with_figures") or 0)["chapter"], "Most diagrams")

    def card(c):
        name, sid = c["chapter"], slug(c["chapter"])
        no = ncert_no(name)
        subj = next((s for s in SUBJECTS if no in s[2]), None)
        previews, q = stat(c, "previews") or [], stat(c, "questions")
        is_free = name in FREE_PDFS
        is_paid = name in PDF_LINKS and not is_free
        if previews:
            galleries[sid] = [{"src": p["src"], "caption": f'{name} · page {p["page"]} · {p["caption"]}'} for p in previews]
            peek = (f'<button type="button" class="pdf-peek" data-gallery="{sid}" data-chapter="{esc(name)}" aria-label="Look inside the {esc(name)} PDF">'
                    f'<img src="{esc(stat(c, "peek") or previews[0]["src"])}" width="744" height="526" loading="lazy" '
                    f'alt="A page from the {esc(name)} PDF: a CBSE board question with its official answer and Mindy&rsquo;s explanation" />'
                    f'<span class="look">&#128065; Look inside &middot; {len(previews)} pages</span></button>')
        else:
            peek = '<div class="pdf-peek pdf-peek-empty">Coming soon</div>'
        tags = f'<span class="pdf-chip">{subj[0] + " · " if subj else ""}Ch {no or ""}</span>'
        if is_free:
            tags += '<span class="pdf-badge free">Free</span>'
        if badges.get(name):
            tags += f'<span class="pdf-badge">{badges[name]}</span>'
        big = (f'<p class="pdf-big"><b>{q}</b><span>board questions<br>{y0}&ndash;{y1}</span></p>' if q else "")
        types = "".join(f"<li>{n} {short.get(k, k)}</li>" for k, n in (stat(c, "sections") or {}).items())
        extra = " · ".join(filter(None, [f'{stat(c, "with_figures")} with diagrams' if stat(c, "with_figures") else "",
                                         f'{stat(c, "pages")} pages' if stat(c, "pages") else ""]))
        if is_free:
            price_row = '<span class="pdf-price">Free</span><span class="pdf-ppq">No payment, no sign-up</span>'
            assure = "Instant download &middot; print or read on your phone"
        elif is_paid:
            price_row = f'<span class="pdf-price">{esc(PDF_PRICE)}</span>'
            assure = "Instant download after payment &middot; UPI, card or netbanking"
        else:
            price_row, assure = "", ""
        cta = pdf_button(c) or '<span class="pdf-soon">Coming soon</span>'
        return (f'<article class="pdf-card{" subj-" + subj[1] if subj else ""}" id="pdf-{sid}">{peek}<div class="pdf-body">'
                f'<div class="pdf-top">{tags}</div><h3>{esc(name)}</h3>{big}'
                + (f'<ul class="pdf-types">{types}</ul>' if types else "")
                + (f'<p class="pdf-extra">{extra}</p>' if extra else "")
                + f'<div class="pdf-buy">' + (f'<div class="pdf-price-row">{price_row}</div>' if price_row else "")
                + cta + (f'<p class="pdf-assure">{assure}</p>' if assure else "") + "</div></div></article>")

    groups, jumps = [], []
    placed = set()
    for subject_name, key, nos in SUBJECTS:
        members = [c for c in all_chapters if ncert_no(c["chapter"]) in nos]
        if not members:
            continue
        placed.update(c["chapter"] for c in members)
        total = sum(stat(c, "questions") or 0 for c in members)
        jumps.append(f'<a class="pdf-jump-{key}" href="#pdf-{key}">{subject_name} <span>{len(members)}</span></a>')
        groups.append(f'<div class="pdf-group-head"><h3 id="pdf-{key}">{subject_name}</h3><span>{len(members)} chapters'
                      + (f' &middot; {total:,} board questions' if total else "") + '</span></div>'
                      f'<div class="pdf-cards">{"".join(card(c) for c in members)}</div>')
    rest = [c for c in all_chapters if c["chapter"] not in placed]
    if rest:
        groups.append(f'<div class="pdf-group-head"><h3>More chapters</h3></div><div class="pdf-cards">{"".join(card(c) for c in rest)}</div>')
    free_chapters = [c for c in chapters if c["chapter"] in FREE_PDFS]
    free_banner = (
        f'<div class="pdf-free"><div><span class="tag">Start free</span>'
        f'<h3>Try {len(free_chapters)} chapter{"s" if len(free_chapters) != 1 else ""} free. No payment, no sign-up.</h3>'
        f'<p>Download {" and ".join(esc(c["chapter"]) for c in free_chapters)} and see how Mindy explains every board question. '
        f'Like it? Every other chapter is just {esc(PDF_PRICE)}.</p></div>'
        f'<div class="btns">{"".join(pdf_button(c, esc(c['chapter']) + ' &darr;', "btn btn-green") for c in free_chapters)}</div></div>'
    ) if free_chapters else ""
    trust = ('<ul class="pdf-trust">'
             '<li><span class="ic">&#9989;</span><span><b>Official CBSE answers</b>from the marking scheme</span></li>'
             '<li><span class="ic"><svg class="pdf-mindy" viewBox="3 2 114 108" aria-hidden="true" focusable="false"><use href="mindy.svg#face"/></svg></span><span><b>Every question explained</b>step by step by Mindy</span></li>'
             '<li><span class="ic">&#9889;</span><span><b>Instant download</b>straight after payment</span></li>'
             '<li><span class="ic">&#128274;</span><span><b>Secure Razorpay checkout</b>UPI, card or netbanking</span></li></ul>')
    # Cards first (they sell); trust points and the free banner follow for anyone still deciding.
    # A div, not <nav>: style.css makes every <nav> the sticky site header.
    jump_nav = f'<div class="pdf-jump" role="navigation" aria-label="Jump to subject">{"".join(jumps)}</div>' if len(jumps) > 1 else ""
    cards = (f'<div class="pdf-wide"><h2 id="chapter-pdfs">Pick your chapter <span class="pdf-h2-note">Tap any page to look inside</span></h2>'
             f'{jump_nav}{"".join(groups)}{trust}{free_banner}</div>')
    lightbox = (
        '<dialog class="pdf-lightbox" id="pdfLightbox" aria-label="PDF preview">'
        '<button type="button" class="lb-close" aria-label="Close preview">&times;</button>'
        '<button type="button" class="lb-prev" aria-label="Previous page">&lsaquo;</button>'
        '<figure><img alt="" /><figcaption></figcaption></figure>'
        '<button type="button" class="lb-next" aria-label="Next page">&rsaquo;</button></dialog>'
        f'<script type="application/json" id="pdfGalleries">{json.dumps(galleries, ensure_ascii=False)}</script>')
    n_questions = sum(stat(c, "questions") or 0 for c in chapters)
    n_figures = sum(stat(c, "with_figures") or 0 for c in chapters)
    free_sample = next((c for c in chapters if c["chapter"] in FREE_PDFS and stat(c, "previews")), None)
    samples = ""
    if free_sample:
        figs = "".join(
            f'<figure><button type="button" class="pdf-sample" data-gallery="{slug(free_sample["chapter"])}" data-chapter="{esc(free_sample["chapter"])}" data-index="{i}">'
            f'<img src="{esc(p["src"])}" width="827" height="1170" loading="lazy" alt="{esc(free_sample["chapter"])} PYQ PDF, page {p["page"]}: {esc(p["caption"])}" />'
            f'</button><figcaption>{esc(p["caption"])}</figcaption></figure>'
            for i, p in enumerate(stat(free_sample, "previews")))
        samples = (f'\n      <div class="pdf-samples">{figs}</div>\n'
                   f'      <p>These pages are from the free {esc(free_sample["chapter"])} PDF. <a href="{esc(FREE_PDFS[free_sample["chapter"]])}" '
                   f'data-free-pdf="{esc(free_sample["chapter"])}" rel="noopener">Download it</a> to see the whole thing, '
                   f'or tap <strong>Look inside</strong> on any chapter above.</p>')
    inside = f'''
      <h2 id="whats-inside">What&rsquo;s inside each chapter PDF</h2>
      <ul>
        <li><strong>Every board question on the chapter, {y0}&ndash;{y1}.</strong> {f"{n_questions:,} questions across {len(chapters)} chapters, " if n_questions else ""}grouped by type: multiple choice (MCQ), very short answer, short answer, long answer and case-based questions.</li>
        <li><strong>Year, marks and subtopic</strong> on every question, so you know how often a topic comes up and how much it is worth.</li>
        <li><strong>The official CBSE answer</strong> right under each question.</li>
        <li><strong>Mindy&rsquo;s step-by-step explanation</strong> of the reasoning. For MCQs it also says why each wrong option is wrong.</li>
        <li><strong>The original diagrams and figures</strong>{f" ({n_figures} questions with figures in all)" if n_figures else ""}, for ray diagrams, circuits, structures and experiments.</li>
        <li><strong>QR codes on the last page</strong> to practice the same chapter online with Mindy, with instant marking.</li>
      </ul>{samples}
'''

    faqs = [
        ("What is in a CBSE Class 10 Science chapter PDF?",
         f"Every CBSE board question on that chapter from {y0} to {y1}, grouped into MCQ, very short answer, short answer, "
         "long answer and case-based questions. Each question shows its year, marks and subtopic, the official CBSE answer and "
         "Mindy's step-by-step explanation, with the original diagrams. Print it or read it on your phone."),
        ("Which chapter PDFs are available?", pdf_line + more),
    ]
    if has_paid:
        faqs.append(("How do I get a paid chapter PDF?",
                     f"Click Get the PDF on the chapter, pay {PDF_PRICE} on the secure Razorpay page with UPI, card or netbanking, and you are taken straight to a page with your download button. "
                     "If anything goes wrong, email hello@mindvsyou.io with your payment id."))
    faqs.append(("Can I practice the same questions online instead?",
                 f"Yes. The same CBSE Class 10 Science PYQs can be practiced chapter by chapter on quiz.mindvsyou.io, where questions you get wrong come back for another shot. "
                 f"See {PAGE_URL} for what each chapter covers."))
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)

    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Students", "item": SITE + "/students.html"},
            {"@type": "ListItem", "position": 3, "name": "Class 10 Science chapter PDFs", "item": PDF_PAGE_URL}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
        # Each PDF with its price, so search engines and AI assistants can answer "how much / is it free".
        {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "url": PDF_PAGE_URL,
         "itemListElement": [
             {"@type": "ListItem", "position": i, "item": {
                 "@type": "Product", "name": f"CBSE Class 10 Science {c['chapter']} PYQ PDF",
                 "description": (f"{stat(c, 'questions')} " if stat(c, "questions") else "")
                                + f"CBSE Class 10 Science previous year questions on {c['chapter']} ({y0}–{y1}), "
                                "with official answers and Mindy's step-by-step explanations.",
                 **({"numberOfPages": stat(c, "pages")} if stat(c, "pages") else {}),
                 **({"image": f'{SITE}/{stat(c, "previews")[0]["src"]}'} if stat(c, "previews") else {}),
                 "brand": {"@type": "Brand", "name": "MindVsYou"}, "category": "Study material",
                 "offers": {"@type": "Offer", "priceCurrency": "INR",
                            "price": "0" if c["chapter"] in FREE_PDFS else re.sub(r"[^0-9]", "", PDF_PRICE),
                            "availability": "https://schema.org/InStock",
                            "url": f"{PDF_PAGE_URL}#chapter-pdfs"}}}
             for i, c in enumerate(chapters, 1)]},
    ]
    ld_html = "".join(
        f'  <script type="application/ld+json">\n  {json.dumps(x, indent=2, ensure_ascii=False)}\n  </script>\n' for x in ld)

    buy_steps = (f'''
      <h2 id="how-to-buy">How buying a chapter PDF works</h2>
      <ol>
        <li>Click <strong>Get the PDF</strong> on the chapter.</li>
        <li>Pay {esc(PDF_PRICE)} on the secure Razorpay page with UPI, card or netbanking.</li>
        <li>You are taken straight to a page with your download button.</li>
      </ol>
      <p>Something went wrong? Email <a href="mailto:hello@mindvsyou.io">hello@mindvsyou.io</a> with the payment id from your Razorpay receipt. See also our <a href="refund-policy.html">refund policy</a>.</p>
''' if has_paid else "")

    # Share preview (WhatsApp, Instagram): the free sample chapter's cover page.
    og_src = stat(free_sample, "previews")[0]["src"] if free_sample else ""
    og_image = (f'  <meta property="og:image" content="{SITE}/{esc(og_src)}" />\n'
                f'  <meta property="og:image:alt" content="Cover of the free {esc(free_sample["chapter"])} CBSE Class 10 Science PYQ PDF" />\n'
                f'  <meta name="twitter:image" content="{SITE}/{esc(og_src)}" />\n') if og_src else ""

    gtag, nav, footer = shared_chrome()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{gtag}  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{PDF_PAGE_URL}" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <meta name="theme-color" content="#25D366" />

  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="MindVsYou" />
  <meta property="og:title" content="{esc(h1)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{PDF_PAGE_URL}" />
  <meta property="og:locale" content="en_IN" />
{og_image}  <meta name="twitter:card" content="{"summary_large_image" if og_image else "summary"}" />
  <meta name="twitter:title" content="{esc(h1)}" />
  <meta name="twitter:description" content="{esc(desc)}" />

  <link rel="stylesheet" href="style.css?v=20261107" />
{PDF_CSS}
{ld_html}</head>
<body>

{nav}  <div class="page-header">
    <div class="breadcrumb">
      <a href="/">Home</a> / <a href="students.html">Students</a> / Class 10 Science chapter PDFs
    </div>
  </div>

  <section class="post-hero pdf-hero">
    <div class="container">
      <div class="pdf-hero-text">
        <span class="blog-tag">Chapter PDFs</span>
        <h1>{esc(h1)}</h1>
        <p class="pdf-hero-long">Every board question from {y0}&ndash;{y1}, chapter by chapter, with the official answer and Mindy&rsquo;s step-by-step explanation. For every MCQ, Mindy also shows why each wrong option is wrong.</p>
        <p class="pdf-hero-short">Every board question, with the official answer, a step-by-step explanation and why each wrong MCQ option is wrong.</p>
      </div>
      <ul class="pdf-hero-stats">
        <li><b>{n_questions:,}</b>board questions</li>
        <li><b>{len(chapters)}</b>chapters</li>
        <li><b>{y0}&ndash;{str(y1)[2:]}</b>board years</li>
        <li><b>{n_free} free</b>chapters to try</li>
      </ul>
    </div>
  </section>

  <section class="post-body pdf-page">
    <div class="container">

      {cards}
      {lightbox}
      <div class="quick-answer"><span class="qa-label">Quick answer</span><p><strong>Where can I get chapter-wise CBSE Class 10 Science PYQ PDFs with answers?</strong> Right here. {esc(pdf_line)}{more}</p></div>
{inside}{buy_steps}
      <h2 id="faq">Frequently asked questions</h2><div class="post-faq">{faq_html}</div>

      <div class="post-cta"><h3>Rather practice online?</h3><p>Do the same questions one at a time with Mindy. Miss one and it comes back.</p><div class="btn-row"><a href="{esc(practice)}" class="btn btn-green">Practice Class 10 Science PYQs &rarr;</a></div><p class="cta-sub"><a href="class-10-science-pyq-coverage.html">See what each chapter covers →</a></p></div>

    </div>
  </section>
{PDF_JS}
{footer}"""


if __name__ == "__main__":
    data = load()
    load_pdf_links(data["chapters"])
    OUT.write_text(build(data), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.name}")
    PDF_OUT.write_text(build_pdf_page(data), encoding="utf-8", newline="\n")
    print(f"Wrote {PDF_OUT.name}")
    by_name = {c["chapter"]: c for c in data["chapters"]}
    for name, (page, download) in THANKS.items():
        (ROOT / page).write_text(build_thanks_page(by_name[name], page, download), encoding="utf-8", newline="\n")
        print(f"Wrote thank-you page for {name}: {SITE}/{page}")
