#!/usr/bin/env python3
"""Generate class-10-science-pyq-coverage.html from the quiz app's public inventory endpoint.

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


# Chapter name (as in the endpoint) -> checkout/sales-page URL. The "Chapter PDF" column and
# "Buy PDF" buttons appear only once at least one chapter has a URL here.
PDF_LINKS = {"Carbon and Its Compounds": "https://rzp.io/rzp/Lr17Ptc"}
PDF_PRICE = "₹49"  # shown in the copy; keep equal to the Razorpay payment pages
# Chapter name -> direct-download URL of a free PDF (shows a green "Free PDF" button).
FREE_PDFS = {"Chemical Reactions and Equations":
             "https://drive.google.com/uc?export=download&id=14Q032KIVndqRPSXAc3zhxQKfL2xhDgeU",
             "Acids, Bases and Salts":
             "https://drive.google.com/uc?export=download&id=14fBsK_70GJ7eSGJRbc5kc-Xw-J5AMsdb"}

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
    """Green 'Free PDF' or grey 'Buy PDF' button for a chapter; empty until the chapter has a link."""
    name = esc(c["chapter"])
    free = FREE_PDFS.get(c["chapter"])
    if free:
        return (f'<a class="btn btn-green btn-sm" href="{esc(free)}" data-free-pdf="{name}" rel="noopener" '
                f'aria-label="Download the free {name} PDF with Mindy explanations">Free PDF</a>')
    url = PDF_LINKS.get(c["chapter"])
    if not url:
        return ""
    price = re.sub(r"[^0-9]", "", PDF_PRICE)
    return (f'<a class="btn btn-grey btn-sm" href="{esc(url)}" data-buy-pdf="{name}" data-price="{price}" '
            f'aria-label="Buy {name} PDF with Mindy explanations">Buy PDF</a>')


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

    title = f"CBSE Class 10 Science PYQs: {total} Practice Questions | MindVsYou"
    desc = (f"{n} chapters of CBSE Class 10 Science PYQs: {total} practice questions, {y0}–{y1}, "
            f"plus chapter PDFs with answers and explanations (some free).")
    h1 = "CBSE Class 10 Science PYQs by chapter: what you can practise"

    rows = []
    for c in chapters:
        cells = "".join(f'<td data-label="{t}"{" class=\"zero\"" if not c["byType"].get(t, 0) else ""}>{c["byType"].get(t, 0)}</td>'
                        for t in TYPES)
        pdf = (f'<td class="row-actions">{pdf_button(c)}</td>') if (PDF_LINKS or FREE_PDFS) else ""
        rows.append(f'<tr><td><a href="#{slug(c["chapter"])}">{esc(label(c["chapter"]))}</a></td>{cells}'
                    f'<td data-label="Total"><strong>{c["total"]}</strong></td><td data-label="Board years">{span(c["years"])}</td>'
                    f'<td class="row-actions">{action_links(c, "btn-sm")}</td>{pdf}</tr>')
    table = ('<div class="table-scroll"><table class="cov-table"><thead><tr><th>Chapter</th>'
             + "".join(f"<th>{t}</th>" for t in TYPES)
             + "<th>Total</th><th>Board years</th><th>Click to practice</th>"
             + ("<th>Chapter PDF</th>" if (PDF_LINKS or FREE_PDFS) else "") + "</tr></thead><tbody>"
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
    names = {c["chapter"] for c in chapters}
    free_names = [k for k in FREE_PDFS if k in names]
    paid_names = [k for k in PDF_LINKS if k in names and k not in FREE_PDFS]
    pdf_parts = []
    if free_names:
        pdf_parts.append("Free to download: " + ", ".join(free_names) + ".")
    if paid_names:
        pdf_parts.append(f"Available for {PDF_PRICE} each: " + ", ".join(paid_names) + ".")
    pdf_line = " ".join(pdf_parts)
    pdf_block = (f'<div class="quick-answer"><span class="qa-label">Chapter PDFs</span><p><strong>Want to study offline?</strong> '
                 f'Each chapter PDF has every practice question for that chapter with the official answers and Mindy&rsquo;s '
                 f'step-by-step explanations. {esc(pdf_line)} More chapters are added over time. '
                 f'Find the buttons in the Chapter PDF column of the table below.</p></div>') if pdf_parts else ""
    faqs = [
        ("Which years of CBSE Class 10 Science PYQs can I practise on MindVsYou?",
         f"The interactive question bank covers CBSE Class 10 Science board years {ydesc}."),
        ("Which question types are available?",
         "Multiple choice (MCQ), assertion-reason, very short answer (VSA), short answer (SA), long answer (LA) and case-based questions. "
         "Not every chapter has every type; the table above shows the exact counts."),
        ("Can I try PYQ practice without an account?",
         "Yes. Guests can use both MCQ practice and written-question practice without creating an account. Sign in to save your progress and revise the questions you missed."),
        ("Are there chapter-wise PDFs of CBSE Class 10 Science PYQs with answers?",
         "Yes. Each chapter PDF has every practice question for that chapter with the official answers and Mindy's step-by-step explanations. "
         + (pdf_line + " " if pdf_line else "") + "More chapters are added over time."),
        ("How do I get a paid chapter PDF?",
         f"Click Buy PDF for the chapter, pay {PDF_PRICE} on the secure Razorpay page with UPI, card or netbanking, and you are taken straight to a page with your download button. "
         "If anything goes wrong, email hello@mindvsyou.io with your payment id."),
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

    # Head and nav/footer copied from an existing page so they stay identical.
    ref = (ROOT / "cbse-class-10-science-pyq.html").read_text(encoding="utf-8")
    gtag = ref[ref.index("  <!-- Google tag"):ref.index("  <meta charset")]
    nav = ref[ref.index("  <nav id=\"navbar\">"):ref.index("  <div class=\"page-header\">")]
    footer = ref[ref.index("  <footer id=\"footer\">"):]

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

      <p class="post-lede">Previous year questions (PYQs) from CBSE Class 10 Science board papers, ready to practise chapter by chapter. Here is exactly what is inside.</p>
      <div class="stat-row">
        <div class="stat stat-hero"><span class="stat-icon" aria-hidden="true">&#11088;</span><span class="stat-num">{total}</span><span class="stat-label">practice questions</span></div>
        <div class="stat"><span class="stat-icon" aria-hidden="true">&#128214;</span><span class="stat-num">{n}</span><span class="stat-label">chapters</span></div>
        <div class="stat"><span class="stat-icon" aria-hidden="true">&#128197;</span><span class="stat-num">{y0}&ndash;{y1}</span><span class="stat-label">board years</span></div>
        <div class="stat"><span class="stat-icon" aria-hidden="true">&#10024;</span><span class="stat-num">{n_types}</span><span class="stat-label">question types</span></div>
      </div>
      <div class="quick-answer"><span class="qa-label">Quick answer</span><p><strong>Where can I practise CBSE Class 10 Science PYQs chapter-wise?</strong> On <a href="{esc(practice)}">quiz.mindvsyou.io</a>: {total} practice questions from board years {y0}&ndash;{y1}, in MCQ, assertion-reason, very short, short, long and case-based formats, with instant marking for MCQs. Guests can try it without an account.</p></div>
      {pdf_block}
      <p>Some board questions have several parts, and each part can count as its own practice question.</p>
      <p>{top_line}</p>

      <h2 id="coverage-table">Coverage by chapter and question type</h2>
      <p>Number of practice questions. A zero means that chapter has none of that type in the bank. VSA = very short answer, SA = short answer, LA = long answer.</p>
      {table}

      <div class="mindy-say">
        <svg class="mindy" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="mindy.svg#cheer"/></svg>
        <div class="mindy-say-b">
          <p><strong>Why practise with Mindy?</strong> Mindy, the MindVsYou chat buddy, gives you one question at a time. MCQs are marked the moment you answer, with the official answer and an AI explanation. For written questions you attempt first, then compare with the official answer and rate yourself. Sign in to save your progress and get the questions you missed back for revision. Guests can start without an account.</p>
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
        <li><strong>Revision:</strong> sign in and the questions you answered wrong come back for revision.</li>
      </ul>
      <p>All practice is chat-style: one question at a time, with Mindy, the MindVsYou chat buddy.</p>

      <h2 id="faq">Frequently asked questions</h2><div class="post-faq">{faq_html}</div>

      <div class="post-cta"><h3>Start with any chapter, free to try</h3><p>Open PYQ practice on quiz.mindvsyou.io and pick a chapter.</p><div class="btn-row"><a href="{esc(practice)}" class="btn btn-green">Practise Class 10 Science PYQs &rarr;</a></div><p class="cta-sub"><a href="cbse-class-10-science-pyq.html">What PYQs are and how to use them →</a> · <a href="class-10-science-previous-year-question-paper.html">Question paper PDFs →</a></p></div>


    </div>
  </div>
  </section>

{RAIL_JS}{footer}"""


if __name__ == "__main__":
    OUT.write_text(build(load()), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.name}")
