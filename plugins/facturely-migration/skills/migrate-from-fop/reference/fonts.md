# Fonts: from fop.xconf to Facturely

FOP needs a configuration file (`fop.xconf`) to use TrueType / OpenType fonts: `<font embed-url=... kerning=...>` entries with
`<font-triplet name=... style=... weight=...>`, or `<auto-detect/>` / `<directory>` entries. Without it FOP uses the 14 standard
PDF fonts and does not embed them.

Facturely needs no configuration and no metrics files:
- **.NET (`Facturely.XmlServer`)**: `FacturelyOptions.FontsPath` = one folder (subfolders included) - only that folder is used.
  Without `FontsPath` the fonts installed on the system are used (Windows, macOS, Linux font folders).
- **Cloud API**: the service has its own font set. Ask Facturely about fonts your templates need that are not common.
- Fonts are always embedded as subsets (required for PDF/A). Families are matched by the name inside the font file
  (`font-family="Arial"`), not by file name. Missing glyphs fall back Office-style, including CJK, Arabic, Hebrew and Indic scripts.

## Migration

1. From the scanner report, take every font file in `embed-url` / `directory` entries and every `font-triplet name`.
2. Propose one folder with those files for the server (for example `/app/fonts` in a container) and set `FontsPath` to it, so the
   output does not depend on what happens to be installed.
3. Check every `font-family` value used in the templates (the scanner lists them) against the folder. FOP `font-triplet` aliases
   (a triplet name that differs from the real family name) do not exist in Facturely: change `font-family` in the templates to the
   real family name, or keep a copy of the font whose family name matches.
4. Generic families (`serif`, `sans-serif`, `monospace`) and the standard PDF names (`Helvetica`, `Times`, `Courier`) resolve to
   installed TrueType fonts (on Windows Arial, Times New Roman, Courier New). On Linux, make sure suitable fonts are in the folder
   (for example the metric-compatible `fonts-liberation` set) and verify the result with the comparison in step 6.
5. Font licences: embedding requires that the licence of each font allows it. Mention this; do not decide for the user.
