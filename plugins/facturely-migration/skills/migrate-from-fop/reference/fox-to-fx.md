# FOP extensions (`fox:`) and their Facturely equivalents

FOP namespace: `http://xmlgraphics.apache.org/fop/extensions` (very old templates: `http://xml.apache.org/fop/extensions`).
Facturely namespace: `xmlns:fx="http://www.facturely.io/names/XSL/Extensions"`.

Facturely ignores unknown extension attributes safely (the template does not fail), and skips unknown extension elements with a
warning. So an unconverted `fox:` attribute is silently without effect - convert every one the scanner reports.

| Apache FOP | Facturely | Notes |
|---|---|---|
| `fox:alt-text` | `fx:alttext` | Alternate text of images and graphics in tagged PDF (PDF/UA). |
| `fox:header` (header cells in tagged PDF) | `fx:headers`, `fx:scope` | Header-cell references and scope in tagged PDF. |
| `fox:border-before-start-radius` and the other `fox:border-*-radius-*` | `fx:border-radius` | Rounded corners. One shorthand instead of per-corner attributes; check corners that differ. |
| `fox:transform` | `fx:transform`, `fx:transform-origin` | Rotate, scale, skew an area. |
| `fox:bleed`, `fox:crop-offset`, `fox:crop-box` | `fx:bleed`, `fx:crop-offset`, `fx:printer-marks` | Crop marks and bleed. Per-side bleed values and mark colours are not supported yet. |
| `fox:disable-column-balancing` | `fx:column-fill` | Turn column balancing on or off. |
| `fox:orphan-content-limit`, `fox:widow-content-limit` (tables) | `fx:table-row-orphans`, `fx:table-row-widows` | Counted in rows, not in length: convert the length to a number of rows. |
| `fox:destination` | `id` + `fo:basic-link internal-destination`, `fx:destination-type` | Named destinations come from `id`; `fx:destination-type` sets how the viewer shows the target. |
| `fox:outline`, `fox:label` (old bookmarks) | `fo:bookmark-tree` | Standard XSL-FO 1.1 bookmarks; `fx:outline-state` sets open / closed. |
| `fox:external-document` | `fox:external-document` (unchanged) or `fx:external-document` | Inserts the pages of a PDF (vector content, fonts and images kept), the frames of a multi-page TIFF, or a PNG / JPEG / GIF / SVG image as pages. `pages="2-5"` or `src="file.pdf#page=3"` for part of a PDF. Bookmarks, links and form fields of the inserted PDF are not carried over; encrypted PDFs are refused. For PDF/A output the inserted PDF must itself conform. |

## Not supported - propose an alternative

| Apache FOP | Alternative |
|---|---|
| `fox:continued-label`, `fox:page-index-*`, `fox:auto-toggle` and other rarely used FOP elements | No direct equivalent. Check the Facturely extension reference for a replacement; if there is none, list the places, explain what the template loses, and let the user decide. |
| FOP renderer configuration in `fop.xconf` other than fonts (PDF encryption, version, filters) | Facturely output options: the output format (`pdf`, `pdfa-3b`, `pdfua-2`, `facturx` ...) chooses the PDF level; ask the user which features they used. |
| Custom FOP extension elements written in Java | Not portable. List them and ask what they did. |

Anything the scanner reports that is not in these tables: search the Facturely extension reference
(https://facturely.io, Extensions) and, if there is no equivalent, report it to the user rather than guessing.
