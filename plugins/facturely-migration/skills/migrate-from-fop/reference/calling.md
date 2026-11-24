# Replacing the FOP call

Typical FOP code: `FopFactory.newInstance(...)`, `fopFactory.newFop(MimeConstants.MIME_PDF, out)`, a JAXP `Transformer` feeding
`fop.getDefaultHandler()`; or the command line `fop -xml data.xml -xsl template.xsl -pdf out.pdf`, or an Ant / Maven task.

## Option A - .NET: Facturely.XmlServer

NuGet package `Facturely.XmlServer` (net8.0 and net10.0; Windows, Linux, macOS; managed code only).

```csharp
using Facturely.XmlServer;

// once per process (ASP.NET Core: register as a singleton); thread-safe
var service = new FacturelyService(new FacturelyOptions
{
    LicenseKey = Environment.GetEnvironmentVariable("FACTURELY_LICENSE"), // none: evaluation mode (watermark)
    FontsPath = "/app/fonts",                                            // optional, see fonts.md
});

// XML + your XSLT 1.0 stylesheet (the FOP "-xml -xsl" case); compile once, reuse
CompiledTemplate template = await service.CompileAsync(File.ReadAllText("template.xsl"), TemplateTrust.BuiltIn, "template.xsl");
ConvertResult r = await service.ConvertAsync(template, File.ReadAllBytes("data.xml"), new ConvertOptions { Format = "pdf" });

// an XSL-FO file directly (the FOP "-fo" case)
ConvertResult fo = await service.ConvertDocumentAsync(File.ReadAllBytes("doc.fo"), InputKind.Fo, new ConvertOptions { Format = "pdf" });

if (!r.Success) foreach (var e in r.Errors) Console.Error.WriteLine(e.Text);
else File.WriteAllBytes("out.pdf", r.Pdf);
```

- `TemplateTrust.BuiltIn` is for stylesheets your team wrote; stylesheets or FO from end users run in the sandbox
  (`TemplateTrust.User`, the default): no file or network access, time and recursion limits. Relative image paths in FO need
  `ConvertOptions.ResourcesPath` (the folder they are relative to) in the sandbox.
- Formats: `pdf`, `pdfa-3b`, `pdfa-3a+ua`, `pdfua-1`, `pdfua-2`, and for e-invoices `pdfa-3b+xml`, `facturx`, `facturx+ua`,
  `orderx` (the invoice XML embedded with the matching metadata).
- Parallel conversions: enable the server garbage collector in the host (`<ServerGarbageCollection>true</ServerGarbageCollection>`
  or `DOTNET_gcServer=1`).

## Option B - Cloud API (any language, including Java)

Asynchronous jobs over HTTPS; authentication `Authorization: Bearer <API key>`.

1. `POST https://api.facturely.io/v1/job` (multipart/form-data):
   - `document` - the `.xml` data file or an `.fo` file;
   - `stylesheet` - your `.xsl` / `.xslt` (omit for `.fo` input), or `stylesheet_id` of a stored / built-in stylesheet;
   - `output_format` - one of the formats above (`GET /v1/facturely/output_formats` lists them);
   - optional `callback_url` (+ `callback_secret`) for a webhook instead of polling.
   Response: `{"id": "<job id>", "status": "created"}`.
2. `GET /v1/job/{id}/status` until the status is `completed` (or `failed`; then `GET /v1/job/{id}/log`).
3. `GET /v1/job/{id}` downloads the PDF.

For a Java service, replace the FOP call with an HTTP client doing these three steps (java.net.http.HttpClient with a multipart
body, or any HTTP library already in the project). Keep an XSLT 2.0 / 3.0 step (Saxon) in Java and upload the resulting `.fo`.

## Build files

Remove the FOP dependencies (`org.apache.xmlgraphics:fop`, `fop-core`, Batik, XML Graphics Commons) only after the new path works,
and only if nothing else in the project uses them (Batik is sometimes used directly for SVG).
