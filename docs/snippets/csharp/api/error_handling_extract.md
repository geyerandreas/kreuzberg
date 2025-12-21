```csharp title="C#"
using Kreuzberg;

try
{
    var result = KreuzbergClient.ExtractFileSync("document.pdf");
    Console.WriteLine(result.Content);
}
catch (KreuzbergValidationException ex)
{
    Console.WriteLine($"Validation error: {ex.Message}");
}
catch (KreuzbergParsingException ex)
{
    Console.WriteLine($"Parsing error: {ex.Message}");
}
catch (KreuzbergOcrException ex)
{
    Console.WriteLine($"OCR error: {ex.Message}");
}
catch (KreuzbergException ex)
{
    Console.WriteLine($"General error: {ex.Message}");
}
```
