#!/usr/bin/env python3
"""Compare PDFs made by Apache FOP with PDFs made by Facturely from the same inputs.

Usage: python compare_pdfs.py <fop-pdf-folder> <facturely-pdf-folder> [--out report.md]

Files are paired by name (relative path). Needs pypdf (pip install pypdf). Reports per file: page counts, page sizes, the share
of words present in both outputs, and words found in only one of them (a hint where text was lost, added or broken differently).
Layout is not compared pixel by pixel: two XSL-FO processors never produce identical pages.
"""
import argparse
import os
import re
import sys
from collections import Counter

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pypdf is required: pip install pypdf")

WATERMARK_HINTS = ("evaluation", "facturely")


def pdfs(folder):
    out = {}
    for dirpath, _, files in os.walk(folder):
        for fn in files:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dirpath, fn)
                out[os.path.relpath(p, folder).replace(os.sep, "/").lower()] = p
    return out


def info(path):
    r = PdfReader(path)
    sizes = Counter()
    words = Counter()
    for page in r.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        sizes["%.0fx%.0f pt" % (w, h)] += 1
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        for word in re.findall(r"\w+", text.lower()):
            words[word] += 1
    return len(r.pages), sizes, words


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fop")
    ap.add_argument("facturely")
    ap.add_argument("--out")
    a = ap.parse_args()
    left, right = pdfs(a.fop), pdfs(a.facturely)
    rows, notes = [], []
    for key in sorted(set(left) | set(right)):
        if key not in right:
            notes.append("- `%s`: no Facturely PDF" % key)
            continue
        if key not in left:
            notes.append("- `%s`: no FOP PDF" % key)
            continue
        try:
            pl, sl, wl = info(left[key])
            pr, sr, wr = info(right[key])
        except Exception as e:
            notes.append("- `%s`: could not read (%s)" % (key, e))
            continue
        for hint in WATERMARK_HINTS:
            wr.pop(hint, None)
        common = sum((wl & wr).values())
        total = max(sum(wl.values()), 1)
        only_fop = [w for w, _ in (wl - wr).most_common(8)]
        only_fx = [w for w, _ in (wr - wl).most_common(8)]
        size_note = "" if set(sl) == set(sr) else " (FOP %s / Facturely %s)" % (", ".join(sl), ", ".join(sr))
        rows.append("| `%s` | %d | %d%s | %.1f %% | %s | %s |" % (
            key, pl, pr, size_note, 100.0 * common / total, " ".join(only_fop) or "-", " ".join(only_fx) or "-"))
    md = ["# FOP vs Facturely output", "",
          "| File | FOP pages | Facturely pages | Words in both | Only in FOP (top) | Only in Facturely (top) |",
          "|---|---|---|---|---|---|"] + rows
    if notes:
        md += ["", "## Not compared", ""] + notes
    md += ["", "Page-count differences usually come from the default font size or page size (reference/defaults.md);",
           "words only on one side usually mean different hyphenation or line breaks, or text that one processor did not render.",
           "Text extraction sometimes joins two words (\"containersthe\"): look at the PDFs before concluding that text is missing.", ""]
    text = "\n".join(md)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("report: " + a.out)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
