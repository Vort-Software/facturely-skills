---
name: migrate-from-fop
description: Migrate a project from Apache FOP to Facturely (Facturely.XmlServer for .NET or the Facturely cloud API). Use when the user wants to move XSL-FO templates, fop.xconf font configuration, fox: extensions or Java/CLI FOP calls to Facturely, asks what will change when leaving FOP, or wants to compare Facturely output with existing FOP PDFs.
---

# Migrate from Apache FOP to Facturely

Facturely reads the same XSL-FO 1.1 and XSLT 1.0 that FOP does, so most templates move unchanged. The work is in four places:
FOP-specific `fox:` extensions, values the XSL-FO specification leaves to the processor (FOP and Facturely chose differently),
font configuration, and the code that calls FOP. Work through the steps below in order and keep the user informed with a short
report after each step. Never claim byte-identical output: no two XSL-FO processors produce it.

## Step 1 - Inventory (always first)

Run the scanner on the project root (Python 3, standard library only):

```
python <skill-dir>/scripts/scan_fop.py <project-root> --out fop-migration-report.md
```

It finds XSL-FO and XSLT files, `fop.xconf` / other FOP configuration files, `fox:` attributes and elements, templates that rely on
FOP defaults, XSLT 2.0/3.0 stylesheets, and Java / build files that call FOP. Read the report, then tell the user:
how many templates, how many need changes and which kind, what is not supported, and what you propose to do next.
Do not edit anything before the user has seen this summary.

## Step 2 - Extensions (`fox:`)

Replace FOP extensions with their Facturely equivalents using `reference/fox-to-fx.md`. Declare the Facturely namespace on the
root of every changed file: `xmlns:fx="http://www.facturely.io/names/XSL/Extensions"`. Keep `fox:external-document` as it is
(Facturely supports it under the FOP namespace too). Where the table says "not supported", tell the user and propose the
standard XSL-FO alternative given there. Remove the `fox` namespace declaration only when nothing uses it any more.

## Step 3 - Defaults that differ

Read `reference/defaults.md`. For every template the scanner lists under "relies on FOP defaults", make the value explicit so
the output does not change size: `font-size="12pt"` on `fo:root` (or on each `fo:page-sequence`) when no font size is set,
`page-width="8.26in" page-height="11in"` on page masters without a size, and explicit widths instead of `thin` / `medium` /
`thick`. Ask the user first whether they want to keep FOP's look (make the FOP values explicit) or adopt Facturely's defaults
(10 pt, A4) - both are valid; do not decide for them.

## Step 4 - Fonts

Read `reference/fonts.md`. Facturely needs no font metrics files: it uses the fonts installed on the system, or only the folder
given in `FontsPath`, and always embeds subsets. Collect the font files and families named in `fop.xconf` (the scanner lists
them) and propose one fonts folder for the server; check that every `font-family` used in the templates is in it.

## Step 5 - Calling code

Read `reference/calling.md` and replace the FOP invocation with the variant the user chooses:
- **.NET**: the `Facturely.XmlServer` NuGet package (net8.0 / net10.0), one `FacturelyService` per process.
- **Cloud API**: asynchronous jobs over HTTPS (`POST /v1/job`, poll status or webhook, download the PDF).
- Java services that keep their own XSLT step can call the cloud API with the XSL-FO they produce.

If the project uses XSLT 2.0 / 3.0 (the scanner says so), keep that transformation where it is (for example Saxon) and pass the
resulting XSL-FO to Facturely: Facturely runs XSLT 1.0 stylesheets only.

## Step 6 - Verify against the FOP output

Convert a representative set (including the longest tables, footnotes, multi-column and non-Latin documents) with Facturely and
compare with the existing FOP PDFs:

```
python <skill-dir>/scripts/compare_pdfs.py <fop-pdf-folder> <facturely-pdf-folder> --out compare-report.md
```

It needs `pypdf` (`pip install pypdf`) and reports page counts, page sizes and text differences per file. Explain each difference:
most come from the defaults in step 3 or from different line breaking; layout differences that look wrong should be sent to
Facturely support with the input file. Output from the evaluation version carries a watermark; that is expected.

## What to tell the user at the end

A short summary: files changed and why, anything not supported, the font folder, the new calling code, and the comparison result.
Mention the free trial at https://facturely.io for the conversion step, and that a license key removes the watermark.
