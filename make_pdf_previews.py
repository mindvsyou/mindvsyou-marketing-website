#!/usr/bin/env python3
"""Make the chapter PDF preview images and data/chapter-pdf-stats.json for the chapter PDFs page.

Run:  python make_pdf_previews.py      (needs: pip install pymupdf)
Reads the Drive links from data/chapter-pdfs.csv (which stays on this laptop), downloads each PDF to a
temporary folder, and writes for every chapter:
  images/pdf-previews/<chapter>-thumb.jpg    small cover for the chapter card
  images/pdf-previews/<chapter>-<n>.jpg      the cover plus a few sample pages for the preview gallery
and the counts from each PDF's cover (questions, pages, figures, sections) into data/chapter-pdf-stats.json.
Run it again whenever a PDF is replaced, then run build_pyq_coverage.py. No links end up in these files.
"""
import csv
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

import pymupdf

from build_pyq_coverage import PDF_CSV, PDF_STATS, ROOT, drive_download, slug

OUT = ROOT / "images" / "pdf-previews"
# Sample pages after the cover: the first MCQ page, then the first page of these sections (whichever exist).
SECTIONS = ["Short Answer Questions", "Case-Based Questions", "Long Answer Questions"]
MAX_SAMPLES = 3
CAPTIONS = {"Multiple Choice Questions": "MCQs with the official answer and Mindy's explanation",
            "Short Answer Questions": "Short answer questions",
            "Case-Based Questions": "Case-based questions",
            "Long Answer Questions": "Long answer questions"}


def section_starts(doc):
    """{section heading: first page index} from headings like 'Short Answer Questions\\n21 questions'."""
    starts, counts = {}, {}
    for i, page in enumerate(doc):
        for name, n in re.findall(r"([A-Za-z -]+ Questions)\n(\d+) questions?", page.get_text()):
            starts.setdefault(name.strip(), i)
            counts[name.strip()] = int(n)
    return starts, counts


def main():
    rows = list(csv.DictReader(PDF_CSV.read_text(encoding="utf-8-sig").splitlines()))
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    with tempfile.TemporaryDirectory() as tmp:
        for row in rows:
            if not row.get("drive_link", "").strip():
                continue
            name = row["chapter"].strip()
            pdf = Path(tmp) / "chapter.pdf"
            req = urllib.request.Request(drive_download(row["drive_link"]), headers={"User-Agent": "Mozilla/5.0"})
            pdf.write_bytes(urllib.request.urlopen(req, timeout=180).read())
            doc = pymupdf.open(pdf)
            cover = doc[0].get_text()
            nums = {label: int(n) for n, label in re.findall(r"(\d+)\n(Questions|With figures|Years)", cover)}
            starts, sections = section_starts(doc)
            if nums.get("Questions") != sum(sections.values()):
                sys.exit(f"{name}: cover says {nums.get('Questions')} questions but sections add up to {sum(sections.values())}")

            base = slug(name)
            order = sorted(starts.values()) + [doc.page_count]

            def diagram_area(i):
                """Area of the diagrams on a page (questions' figures are the only images in these PDFs)."""
                return sum((b[2] - b[0]) * (b[3] - b[1]) for b in (x["bbox"] for x in doc[i].get_image_info())
                           if b[2] - b[0] >= 60 and b[3] - b[1] >= 40)

            def best_page(section):
                """The page of the section with the most diagram area, so previews show the figures; else its first page."""
                first = starts[section]
                end = next(i for i in order if i > first)
                best = max(range(first, end), key=lambda i: (diagram_area(i), -i))
                return best if diagram_area(best) else first

            def sample(section):
                idx = best_page(section)
                return idx, CAPTIONS[section] + (", with diagrams" if diagram_area(idx) else "")

            # A mix: the cover, the clean first MCQ page (section heading, question, official answer, Mindy's
            # explanation), then the most diagram-rich page of the later sections.
            pages = [(0, "Cover")]
            if "Multiple Choice Questions" in starts:
                pages.append((starts["Multiple Choice Questions"], CAPTIONS["Multiple Choice Questions"]))
            pages += [sample(s) for s in SECTIONS if s in starts]
            pages = pages[:1 + MAX_SAMPLES]
            gallery = []
            for n, (idx, caption) in enumerate(pages):
                file = f"{base}-{n}.jpg"
                doc[idx].get_pixmap(dpi=100).save(OUT / file, jpg_quality=75)
                gallery.append({"src": f"images/pdf-previews/{file}", "caption": caption, "page": idx + 1})
            doc[0].get_pixmap(dpi=36).save(OUT / f"{base}-thumb.jpg", jpg_quality=80)
            # "Peek" for the chapter card: top half of the first sample question page (question, answer, explanation)
            peek_page = doc[pages[1][0]] if len(pages) > 1 else doc[0]
            clip = pymupdf.Rect(0, 0, peek_page.rect.width, peek_page.rect.height * 0.5)
            peek_page.get_pixmap(dpi=90, clip=clip).save(OUT / f"{base}-peek.jpg", jpg_quality=72)

            stats[name] = {"pages": doc.page_count, "questions": nums.get("Questions"),
                           "with_figures": nums.get("With figures"), "sections": sections,
                           "thumb": f"images/pdf-previews/{base}-thumb.jpg",
                           "peek": f"images/pdf-previews/{base}-peek.jpg", "previews": gallery}
            print(f"{name}: {doc.page_count} pages, {nums.get('Questions')} questions, {len(gallery)} preview images")
            doc.close()
    PDF_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {PDF_STATS.relative_to(ROOT)} and {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
