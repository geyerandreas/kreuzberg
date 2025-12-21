```csharp title="C#"
using Kreuzberg;

var result = await KreuzbergClient.ExtractFileAsync("document.pdf");

Console.WriteLine(result.Content);
Console.WriteLine($"Success: {result.Success}");
Console.WriteLine($"Detected Languages: {string.Join(", ", result.DetectedLanguages ?? new())}");
```
