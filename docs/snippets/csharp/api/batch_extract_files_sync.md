```csharp title="C#"
using Kreuzberg;

var files = new[] { "doc1.pdf", "doc2.docx", "doc3.xlsx" };
var results = KreuzbergClient.BatchExtractFilesSync(files);

foreach (var (i, result) in results.Index())
{
    Console.WriteLine($"File {i + 1}: {result.Content.Length} characters");
    Console.WriteLine($"  Success: {result.Success}");
}
```
