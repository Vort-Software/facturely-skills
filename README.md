# Facturely skills for Claude Code

Skills that let [Claude Code](https://claude.com/claude-code) move XSL-FO projects to [Facturely](https://facturely.io).

## migrate-from-fop

Migrates a project from **Apache FOP** to Facturely (the `Facturely.XmlServer` .NET library or the Facturely cloud API).
Ask Claude something like *"migrate this project from FOP to Facturely"* and it will:

1. **Inventory** the project with a scanner (no changes): XSL-FO and XSLT files, `fox:` extensions, templates that rely on FOP
   defaults, `fop.xconf` fonts and settings, XSLT 2.0 / 3.0 stylesheets, and Java / build files that call FOP.
2. **Replace `fox:` extensions** with their `fx:` equivalents (or standard XSL-FO), and tell you what has no equivalent.
3. **Make defaults explicit** where FOP and Facturely differ (default font size 12 vs 10 pt, page size 8.26 × 11 in vs A4,
   `thin` / `medium` / `thick` borders) - after asking whether you want to keep FOP's look.
4. **Move fonts** from `fop.xconf` to one fonts folder (no metrics files needed; subsets are always embedded).
5. **Replace the FOP call** with `Facturely.XmlServer` in .NET or with the asynchronous cloud API (any language, including Java).
6. **Compare** Facturely output with your existing FOP PDFs: pages, page sizes, text present in both.

Templates themselves mostly move unchanged: Facturely reads standard XSL-FO 1.1 and XSLT 1.0. The skill never promises
byte-identical output - no two XSL-FO processors produce it - and keeps XSLT 2.0 / 3.0 steps in your own pipeline.

## Install

In Claude Code:

```
/plugin marketplace add Vort-Software/facturely-skills
/plugin install facturely-migration@facturely
```

Or copy `plugins/facturely-migration/skills/migrate-from-fop` into `.claude/skills/` of your project (or `~/.claude/skills/`).

The scanner needs Python 3 (standard library only); the comparison needs `pypdf` (`pip install pypdf`). Converting documents
needs Facturely: a free trial is at <https://facturely.io> (without a license key the output carries a watermark).

## Use the scripts without Claude

```
python plugins/facturely-migration/skills/migrate-from-fop/scripts/scan_fop.py <project> --out fop-migration-report.md
python plugins/facturely-migration/skills/migrate-from-fop/scripts/compare_pdfs.py <fop-pdfs> <facturely-pdfs> --out compare.md
```

The reference files next to the skill (`reference/fox-to-fx.md`, `defaults.md`, `fonts.md`, `calling.md`) are plain Markdown
and double as a migration guide.

## License

MIT - see [LICENSE](LICENSE). Facturely is commercial software of Vort Software LLC and is not part of this repository.
Apache FOP is a trademark of The Apache Software Foundation; this project is not affiliated with or endorsed by it.
