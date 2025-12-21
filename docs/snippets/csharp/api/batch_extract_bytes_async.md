```csharp title="C#"
using Kreuzberg;

var data1 = await File.ReadAllBytesAsync("doc1.pdf");
var data2 = await File.ReadAllBytesAsync("doc2.docx");

var items = new[]
{
    new BytesWithMime(data1, "application/pdf"),
    new BytesWithMime(data2, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
};

var results = await KreuzbergClient.BatchExtractBytesAsync(items);

Console.WriteLine($"Processed {results.Count} documents");
```
