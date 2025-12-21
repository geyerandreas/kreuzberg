```csharp title="C#"
using Kreuzberg;

var files = new[] { "doc1.pdf", "doc2.docx", "doc3.xlsx" };
var results = await KreuzbergClient.BatchExtractFilesAsync(files);

foreach (var (i, result) in results.Index())
{
    if (result.Success)
    {
        Console.WriteLine($"File {i + 1}: {result.MimeType}");
    }
}
```
