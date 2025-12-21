```csharp title="C#"
using Kreuzberg;

var data = await File.ReadAllBytesAsync("document.pdf");
var result = await KreuzbergClient.ExtractBytesAsync(data, "application/pdf");

Console.WriteLine(result.Content[..Math.Min(100, result.Content.Length)]);
Console.WriteLine($"Tables extracted: {result.Tables.Count}");
```
