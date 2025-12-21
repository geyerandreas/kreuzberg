```csharp title="C#"
using Kreuzberg;

var config = new ExtractionConfig
{
    UseCache = true,
    EnableQualityProcessing = true
};

var result = KreuzbergClient.ExtractFileSync("document.pdf", config);

if (result.Success)
{
    Console.WriteLine($"Content: {result.Content[..Math.Min(200, result.Content.Length)]}");
    Console.WriteLine($"Metadata: {result.Metadata.Language ?? "Unknown"}");
}
```
