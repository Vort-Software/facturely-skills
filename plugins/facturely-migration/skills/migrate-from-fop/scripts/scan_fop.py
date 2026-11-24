#!/usr/bin/env python3
"""Inventory of an Apache FOP project before moving it to Facturely.

Usage: python scan_fop.py <project-root> [--out report.md] [--json report.json]

Standard library only. Reads files, never changes them. Reports:
  - XSL-FO and XSLT files, and which XSLT version they declare;
  - fox: attributes and elements (FOP extensions), with file and line;
  - templates that rely on values FOP and Facturely default differently (font size, page size, border keywords);
  - FOP configuration files (fop.xconf ...): fonts, directories, auto-detect, other renderer settings;
  - font-family values used in the templates;
  - Java / build files that call FOP.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

FOX_NS = ("http://xmlgraphics.apache.org/fop/extensions", "http://xml.apache.org/fop/extensions")
FO_NS = "http://www.w3.org/1999/XSL/Format"
XSL_NS = "http://www.w3.org/1999/XSL/Transform"
SKIP_DIRS = {".git", ".svn", ".hg", "node_modules", "target", "build", "bin", "obj", ".idea", ".vs", ".gradle", "out", "dist"}
TEXT_EXT = {".fo", ".xsl", ".xslt", ".xml", ".xconf", ".java", ".kt", ".groovy", ".scala", ".gradle", ".kts", ".properties",
            ".sh", ".bat", ".cmd", ".ps1", ".py", ".cs", ".js", ".ts", ".rb", ".php", ".go"}
MAX_BYTES = 20 * 1024 * 1024

FOX_MAP = {
    "alt-text": "fx:alttext",
    "header": "fx:headers / fx:scope",
    "transform": "fx:transform (+ fx:transform-origin)",
    "bleed": "fx:bleed", "crop-offset": "fx:crop-offset", "crop-box": "fx:printer-marks",
    "disable-column-balancing": "fx:column-fill",
    "orphan-content-limit": "fx:table-row-orphans (rows, not length)",
    "widow-content-limit": "fx:table-row-widows (rows, not length)",
    "destination": "id + fo:basic-link internal-destination (+ fx:destination-type)",
    "outline": "fo:bookmark-tree (+ fx:outline-state)", "label": "fo:bookmark-title",
    "external-document": "supported unchanged (or fx:external-document)",
}


def fox_equivalent(local):
    if local in FOX_MAP:
        return FOX_MAP[local]
    if local.startswith("border-") and "radius" in local:
        return "fx:border-radius"
    return "no direct equivalent - see reference/fox-to-fx.md"


def read_text(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # ISO-8859-1 and similar legacy encodings: every byte decodes, markup and ASCII names stay readable
        return data.decode("latin-1")


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def prefixes_for(text, uris):
    """Namespace prefixes bound to any of the given URIs anywhere in the file."""
    out = set()
    for m in re.finditer(r'xmlns:([A-Za-z_][\w.-]*)\s*=\s*["\']([^"\']+)["\']', text):
        if m.group(2) in uris:
            out.add(m.group(1))
    return out


def scan_markup(path, text, rel, rep):
    fo_prefixes = prefixes_for(text, (FO_NS,))
    xsl_prefixes = prefixes_for(text, (XSL_NS,))
    fox_prefixes = prefixes_for(text, FOX_NS)
    is_fo = bool(fo_prefixes) or bool(re.search(r'<root[^>]+xmlns\s*=\s*["\']' + re.escape(FO_NS), text))
    is_xsl = bool(xsl_prefixes)
    if not (is_fo or is_xsl or fox_prefixes):
        return
    kind = "xslt" if is_xsl else "fo"
    entry = {"file": rel, "kind": kind, "fox": [], "defaults": [], "fonts": []}
    if is_xsl:
        m = re.search(r'<(?:\w+:)?(?:stylesheet|transform)\b[^>]*\bversion\s*=\s*["\']([\d.]+)["\']', text)
        entry["xslt_version"] = m.group(1) if m else "?"
        if m and not m.group(1).startswith("1"):
            rep["xslt2plus"].append(rel)
    # fox: usage
    for p in fox_prefixes:
        for m in re.finditer(r'<' + re.escape(p) + r':([\w.-]+)', text):
            entry["fox"].append({"line": line_of(text, m.start()), "kind": "element", "name": "fox:" + m.group(1),
                                 "facturely": fox_equivalent(m.group(1))})
        for m in re.finditer(r'\s' + re.escape(p) + r':([\w.-]+)\s*=', text):
            entry["fox"].append({"line": line_of(text, m.start()), "kind": "attribute", "name": "fox:" + m.group(1),
                                 "facturely": fox_equivalent(m.group(1))})
        # attributes created by XSLT: <xsl:attribute name="fox:...">
        for m in re.finditer(r'name\s*=\s*["\']' + re.escape(p) + r':([\w.-]+)["\']', text):
            entry["fox"].append({"line": line_of(text, m.start()), "kind": "xsl:attribute", "name": "fox:" + m.group(1),
                                 "facturely": fox_equivalent(m.group(1))})
    # defaults that differ (only meaningful where FO is written)
    if is_fo:
        has_font_size = bool(re.search(r'\bfont-size\s*=|name\s*=\s*["\']font-size["\']|\bfont\s*=', text))
        if not has_font_size:
            entry["defaults"].append({"line": 1, "what": "no font-size anywhere: FOP 12pt, Facturely 10pt"})
        for fp in fo_prefixes or {""}:
            tag = (fp + ":" if fp else "") + "simple-page-master"
            for m in re.finditer(r'<' + re.escape(tag) + r'\b([^>]*)>', text):
                attrs = m.group(1)
                if "page-width" not in attrs and "page-height" not in attrs and "size" not in attrs:
                    entry["defaults"].append({"line": line_of(text, m.start()),
                                              "what": "page master without page-width/page-height: FOP 8.26x11in, Facturely A4"})
        for m in re.finditer(r'\bborder(?:-[a-z]+)*(?:-width)?\s*=\s*["\'][^"\']*\b(thin|medium|thick)\b', text):
            entry["defaults"].append({"line": line_of(text, m.start()),
                                      "what": "border keyword '%s': FOP thin 0.5 / medium 1 / thick 2 pt, Facturely medium 3pt" % m.group(1)})
    for m in re.finditer(r'font-family\s*=\s*["\']([^"\']+)["\']', text):
        for fam in m.group(1).split(","):
            fam = fam.strip().strip("'\"")
            if fam and "{" not in fam:
                rep["families"][fam] += 1
    rep["templates"].append(entry)


def scan_xconf(path, text, rel, rep):
    if "<fop" not in text or ("<renderer" not in text and "<fonts" not in text and "<font " not in text):
        return
    conf = {"file": rel, "font_files": [], "triplets": [], "directories": [], "auto_detect": False, "other_settings": []}
    for m in re.finditer(r'<font\b[^>]*\b(?:embed-url|metrics-url)\s*=\s*["\']([^"\']+)["\']', text):
        conf["font_files"].append(m.group(1))
    for m in re.finditer(r'<font-triplet\b[^>]*\bname\s*=\s*["\']([^"\']+)["\'][^>]*>', text):
        style = re.search(r'style\s*=\s*["\']([^"\']+)', m.group(0))
        weight = re.search(r'weight\s*=\s*["\']([^"\']+)', m.group(0))
        conf["triplets"].append("%s (%s, %s)" % (m.group(1), style.group(1) if style else "?", weight.group(1) if weight else "?"))
    for m in re.finditer(r'<directory\b[^>]*>([^<]+)</directory>', text):
        conf["directories"].append(m.group(1).strip())
    conf["auto_detect"] = "<auto-detect" in text
    for tag in ("encryption-params", "version", "filterList", "pdf-a-mode", "pdf-ua-mode", "pdf-x-mode", "target-resolution",
                "source-resolution", "default-page-settings", "hyphenation-base", "hyphenation-pattern", "accessibility"):
        if "<" + tag in text:
            conf["other_settings"].append(tag)
    rep["configs"].append(conf)


CALL_PATTERNS = [
    (r'\bFopFactory\b', "FopFactory (Java API)"),
    (r'\bnewFop\s*\(', "newFop(...)"),
    (r'org\.apache\.fop\.', "org.apache.fop import"),
    (r'org\.apache\.xmlgraphics[:/]fop|<artifactId>\s*fop(?:-core)?\s*</artifactId>|xmlgraphics:fop', "FOP dependency (build file)"),
    (r'(?:^|[\s"\'/\\])fop(?:\.bat|\.cmd)?\s+(?:-c\s+\S+\s+)?-(?:xml|fo|xsl)\b', "fop command line"),
    (r'<fop\s[^>]*\b(?:fofile|xmlfile|xsltfile|outfile|outdir)\s*=', "Ant <fop> task"),
]


def scan_calls(path, text, rel, rep):
    for pat, what in CALL_PATTERNS:
        for m in re.finditer(pat, text, re.M):
            rep["calls"].append({"file": rel, "line": line_of(text, m.start()), "what": what})


def scan(root):
    rep = {"root": os.path.abspath(root), "templates": [], "configs": [], "calls": [], "families": Counter(), "xslt2plus": []}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT and fn.lower() not in ("pom.xml", "build.xml"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            text = read_text(path)
            if text is None:
                continue
            if ext in (".fo", ".xsl", ".xslt", ".xml"):
                scan_markup(path, text, rel, rep)
            if ext in (".xconf", ".xml"):
                scan_xconf(path, text, rel, rep)
            if ext not in (".fo", ".xsl", ".xslt"):
                scan_calls(path, text, rel, rep)
    return rep


def to_markdown(rep):
    t = rep["templates"]
    fox_total = sum(len(e["fox"]) for e in t)
    with_fox = [e for e in t if e["fox"]]
    with_defaults = [e for e in t if e["defaults"]]
    out = ["# FOP -> Facturely migration report", "", "Project: `%s`" % rep["root"], ""]
    out += ["## Summary", "",
            "| | |", "|---|---|",
            "| XSL-FO files | %d |" % sum(1 for e in t if e["kind"] == "fo"),
            "| XSLT stylesheets | %d |" % sum(1 for e in t if e["kind"] == "xslt"),
            "| XSLT 2.0 / 3.0 stylesheets (keep that step outside Facturely) | %d |" % len(rep["xslt2plus"]),
            "| Files using fox: extensions | %d (%d uses) |" % (len(with_fox), fox_total),
            "| Files relying on FOP defaults | %d |" % len(with_defaults),
            "| FOP configuration files | %d |" % len(rep["configs"]),
            "| Places calling FOP | %d |" % len(rep["calls"]), ""]
    if with_fox:
        out += ["## fox: extensions", "", "| File | Line | FOP | Facturely |", "|---|---|---|---|"]
        for e in with_fox:
            for f in e["fox"]:
                out.append("| `%s` | %d | `%s` (%s) | %s |" % (e["file"], f["line"], f["name"], f["kind"], f["facturely"]))
        names = Counter(f["name"] for e in with_fox for f in e["fox"])
        out += ["", "By name: " + ", ".join("`%s` %d" % kv for kv in names.most_common()), ""]
    if with_defaults:
        out += ["## Relies on FOP defaults (see reference/defaults.md)", "", "| File | Line | What |", "|---|---|---|"]
        for e in with_defaults:
            for d in e["defaults"]:
                out.append("| `%s` | %d | %s |" % (e["file"], d["line"], d["what"]))
        out.append("")
    if rep["xslt2plus"]:
        out += ["## XSLT 2.0 / 3.0", "", "Facturely runs XSLT 1.0. Keep these transformations in your pipeline and pass the XSL-FO:", ""]
        out += ["- `%s`" % f for f in rep["xslt2plus"]] + [""]
    if rep["configs"]:
        out += ["## FOP configuration (see reference/fonts.md)", ""]
        for c in rep["configs"]:
            out.append("### `%s`" % c["file"])
            out.append("- font files: " + (", ".join("`%s`" % x for x in c["font_files"]) or "none"))
            out.append("- font triplets: " + (", ".join(c["triplets"]) or "none"))
            out.append("- font directories: " + (", ".join("`%s`" % x for x in c["directories"]) or "none") +
                       ("; auto-detect on" if c["auto_detect"] else ""))
            if c["other_settings"]:
                out.append("- other renderer settings to map to Facturely output options: " + ", ".join(c["other_settings"]))
            out.append("")
    if rep["families"]:
        out += ["## font-family values in templates", "", ", ".join("`%s` (%d)" % kv for kv in rep["families"].most_common()), ""]
    if rep["calls"]:
        out += ["## Code and build files calling FOP (see reference/calling.md)", "", "| File | Line | What |", "|---|---|---|"]
        for c in rep["calls"]:
            out.append("| `%s` | %d | %s |" % (c["file"], c["line"], c["what"]))
        out.append("")
    if not t and not rep["configs"] and not rep["calls"]:
        out += ["No XSL-FO, XSLT, FOP configuration or FOP calls found under this folder.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--out", help="write the Markdown report here (default: stdout)")
    ap.add_argument("--json", help="also write the raw findings as JSON")
    a = ap.parse_args()
    if not os.path.isdir(a.root):
        sys.exit("not a folder: " + a.root)
    rep = scan(a.root)
    md = to_markdown(rep)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print("report: " + a.out)
    else:
        sys.stdout.write(md + "\n")
    if a.json:
        data = dict(rep)
        data["families"] = dict(rep["families"])
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)


if __name__ == "__main__":
    main()
