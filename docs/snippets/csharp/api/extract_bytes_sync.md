```csharp title="C#"
using Kreuzberg;

var data = File.ReadAllBytes("document.pdf");
var result = KreuzbergClient.ExtractBytesSync(data, "application/pdf");

Console.WriteLine($"Content length: {result.Content.Length} characters");
Console.WriteLine($"Format type: {result.Metadata.FormatType}");
```
