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
PLACEHOLDER = "see image file"  # leftover text in some PDFs; preview pages containing it are skipped
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

            def clean_page(section):
                """First page of the section without leftover '(see image file)' placeholder text."""
                first = starts[section]
                end = next(i for i in order if i > first)
                return next((i for i in range(first, end) if PLACEHOLDER not in doc[i].get_text()), first)

            pages = [(0, "Cover")]
            if "Multiple Choice Questions" in starts:
                pages.append((clean_page("Multiple Choice Questions"), CAPTIONS["Multiple Choice Questions"]))
            pages += [(clean_page(s), CAPTIONS[s]) for s in SECTIONS if s in starts]
            pages = pages[:1 + MAX_SAMPLES]
            gallery = []
            for n, (idx, caption) in enumerate(pages):
                file = f"{base}-{n}.jpg"
                doc[idx].get_pixmap(dpi=100).save(OUT / file, jpg_quality=75)
                gallery.append({"src": f"images/pdf-previews/{file}", "caption": caption, "page": idx + 1})
            doc[0].get_pixmap(dpi=36).save(OUT / f"{base}-thumb.jpg", jpg_quality=80)

            stats[name] = {"pages": doc.page_count, "questions": nums.get("Questions"),
                           "with_figures": nums.get("With figures"), "sections": sections,
                           "thumb": f"images/pdf-previews/{base}-thumb.jpg", "previews": gallery}
            print(f"{name}: {doc.page_count} pages, {nums.get('Questions')} questions, {len(gallery)} preview images")
            doc.close()
    PDF_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {PDF_STATS.relative_to(ROOT)} and {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
