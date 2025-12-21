```csharp title="C#"
using Kreuzberg;

var result = KreuzbergClient.ExtractFileSync("document.pdf");

Console.WriteLine(result.Content);
Console.WriteLine($"MIME Type: {result.MimeType}");
Console.WriteLine($"Tables: {result.Tables.Count}");
```
