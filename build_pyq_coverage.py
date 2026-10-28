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
  <meta name="theme-color" content="#25D366" />
  <link rel="stylesheet" href="style.css?v=20261019" />
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


def action_links(c, cls, full=False):
    """MCQ, written-question and (where the chapter has any) case-based practice buttons."""
    name = esc(c["chapter"])
    out = (f'<a class="btn btn-green {cls}" href="{esc(practice_url("mcq", c))}" aria-label="Practise {name} MCQs">{f"Practise {name} MCQs &rarr;" if full else "MCQs"}</a>'
           f'<a class="btn btn-green {cls}" href="{esc(practice_url("subjective", c))}" aria-label="Practise {name} VSA, SA, LA questions">{f"Practise {name} VSA, SA, LA &rarr;" if full else "VSA, SA, LA"}</a>')
    if c["byType"].get("Case-based"):
        out += (f'<a class="btn btn-green {cls}" href="{esc(practice_url("casebased", c))}" aria-label="Practise {name} case-based questions">'
                f'{f"Practise {name} case-based questions &rarr;" if full else "Case-based"}</a>')
    return out


def pdf_button(c):
    """'Free PDF' or 'Buy PDF' button for a chapter; empty until the chapter has a link."""
    name = esc(c["chapter"])
    free = FREE_PDFS.get(c["chapter"])
    if free:
        return (f'<a class="btn btn-green btn-sm" href="{esc(free)}" data-free-pdf="{name}" rel="noopener" '
                f'aria-label="Download the free {name} PDF with Mindy explanations">Free PDF</a>')
    url = PDF_LINKS.get(c["chapter"])
    if not url:
        return ""
    price = re.sub(r"[^0-9]", "", PDF_PRICE)
    return (f'<a class="btn btn-green btn-sm" href="{esc(url)}" data-buy-pdf="{name}" data-price="{price}" '
            f'aria-label="Buy {name} PDF with Mindy explanations">Buy PDF</a>')


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

  <link rel="stylesheet" href="style.css?v=20261019" />

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

    title = "CBSE Class 10 Science Chapter-wise PYQ PDFs with Answers | MindVsYou"
    h1 = "CBSE Class 10 Science PYQ: Chapter-wise PDFs with answers"
    desc = (f"Printable chapter-wise PDFs of CBSE Class 10 Science previous year questions ({y0}–{y1}) "
            f"with official answers and step-by-step explanations. {pdf_line}")

    def price(c):
        if c["chapter"] in FREE_PDFS:
            return "Free"
        return esc(PDF_PRICE) if c["chapter"] in PDF_LINKS else "Coming soon"

    # Every chapter is listed; chapters without a PDF yet show "Coming soon" and no button.
    rows = "".join(
        f'<tr><td>{esc(label(c["chapter"]))}</td>'
        f'<td data-label="Price">{price(c)}</td>'
        f'<td class="row-actions">{pdf_button(c)}</td></tr>' for c in all_chapters)
    table = ('<div class="table-scroll"><table class="cov-table"><thead><tr><th>Chapter</th><th>Price</th><th>PDF</th></tr></thead>'
             f'<tbody>{rows}</tbody></table></div>')

    faqs = [
        ("What is in a CBSE Class 10 Science chapter PDF?",
         "Every practice question for that chapter from the MindVsYou PYQ bank, with the official answers and Mindy's step-by-step explanations. "
         "Print it or read it on your phone."),
        ("Which chapter PDFs are available?", pdf_line + more),
    ]
    if has_paid:
        faqs.append(("How do I get a paid chapter PDF?",
                     f"Click Buy PDF for the chapter, pay {PDF_PRICE} on the secure Razorpay page with UPI, card or netbanking, and you are taken straight to a page with your download button. "
                     "If anything goes wrong, email hello@mindvsyou.io with your payment id."))
    faqs.append(("Can I practise the same questions online instead?",
                 f"Yes. The same CBSE Class 10 Science PYQs can be practised chapter by chapter on quiz.mindvsyou.io, where questions you get wrong come back for another shot. "
                 f"See {PAGE_URL} for what each chapter covers."))
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)

    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Students", "item": SITE + "/students.html"},
            {"@type": "ListItem", "position": 3, "name": "Class 10 Science chapter PDFs", "item": PDF_PAGE_URL}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
    ]
    ld_html = "".join(
        f'  <script type="application/ld+json">\n  {json.dumps(x, indent=2, ensure_ascii=False)}\n  </script>\n' for x in ld)

    buy_steps = (f'''
      <h2 id="how-to-buy">How buying a chapter PDF works</h2>
      <ol>
        <li>Click <strong>Buy PDF</strong> next to the chapter.</li>
        <li>Pay {esc(PDF_PRICE)} on the secure Razorpay page with UPI, card or netbanking.</li>
        <li>You are taken straight to a page with your download button.</li>
      </ol>
      <p>Something went wrong? Email <a href="mailto:hello@mindvsyou.io">hello@mindvsyou.io</a> with the payment id from your Razorpay receipt. See also our <a href="refund-policy.html">refund policy</a>.</p>
''' if has_paid else "")

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
  <meta name="theme-color" content="#25D366" />

  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="MindVsYou" />
  <meta property="og:title" content="{esc(h1)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{PDF_PAGE_URL}" />
  <meta property="og:locale" content="en_IN" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(h1)}" />
  <meta name="twitter:description" content="{esc(desc)}" />

  <link rel="stylesheet" href="style.css?v=20261019" />

{ld_html}</head>
<body>

{nav}  <div class="page-header">
    <div class="breadcrumb">
      <a href="/">Home</a> / <a href="students.html">Students</a> / Class 10 Science chapter PDFs
    </div>
  </div>

  <section class="post-hero">
    <div class="container">
      <span class="blog-tag">Chapter PDFs</span>
      <h1>{esc(h1)}</h1>
    </div>
  </section>

  <section class="post-body">
    <div class="container">

      <p class="post-lede">One printable PDF per chapter: every practice question for that chapter from CBSE board years {y0}&ndash;{y1}, with the official answers and Mindy&rsquo;s step-by-step explanations. Study offline, at your own pace.</p>
      <div class="quick-answer"><span class="qa-label">Quick answer</span><p><strong>Where can I get chapter-wise CBSE Class 10 Science PYQ PDFs with answers?</strong> Right here. {esc(pdf_line)}{more}</p></div>

      <h2 id="chapter-pdfs">Chapter PDFs</h2>
      {table}
{buy_steps}
      <h2 id="faq">Frequently asked questions</h2><div class="post-faq">{faq_html}</div>

      <div class="post-cta"><h3>Rather practise online?</h3><p>Do the same questions one at a time with Mindy. Miss one and it comes back.</p><div class="btn-row"><a href="{esc(practice)}" class="btn btn-green">Practise Class 10 Science PYQs &rarr;</a></div><p class="cta-sub"><a href="class-10-science-pyq-coverage.html">See what each chapter covers →</a></p></div>

    </div>
  </section>

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
