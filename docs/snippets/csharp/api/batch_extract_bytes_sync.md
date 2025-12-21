```csharp title="C#"
using Kreuzberg;

var items = new[]
{
    new BytesWithMime(File.ReadAllBytes("doc1.pdf"), "application/pdf"),
    new BytesWithMime(File.ReadAllBytes("doc2.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
};
var results = KreuzbergClient.BatchExtractBytesSync(items);

foreach (var result in results)
{
    Console.WriteLine($"Extracted: {result.Content.Length} chars, MIME: {result.MimeType}");
}
```
