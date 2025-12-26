using System.Text.Json;
using Kreuzberg;

namespace KreuzbergSmokeTest;

internal sealed class Program
{
    private sealed class TestResult
    {
        public bool Success { get; set; }
        public string File { get; set; } = string.Empty;
        public int? TextLength { get; set; }
        public string? Preview { get; set; }
        public bool ForceOcr { get; set; }
        public string? Error { get; set; }
        public string? ErrorType { get; set; }
    }

    private static TestResult TestDocument(string filePath, bool forceOcr = false)
    {
        try
        {
            var config = new ExtractionConfig
            {
                ForceOcr = forceOcr
            };

            var result = KreuzbergClient.ExtractFileSync(filePath, config);

            var extractedText = result.Content ?? string.Empty;
            var textPreview = extractedText.Length > 100
                ? extractedText[..100].Replace("\n", " ")
                : extractedText.Replace("\n", " ");

            return new TestResult
            {
                Success = true,
                File = Path.GetFileName(filePath),
                TextLength = extractedText.Length,
                Preview = textPreview,
                ForceOcr = forceOcr
            };
        }
        catch (Exception ex)
        {
            return new TestResult
            {
                Success = false,
                File = Path.GetFileName(filePath),
                Error = ex.Message,
                ErrorType = ex.GetType().Name,
                ForceOcr = forceOcr
            };
        }
    }

    private static int Main()
    {
        var testDocsDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "test_documents");
        testDocsDir = Path.GetFullPath(testDocsDir);

        if (!Directory.Exists(testDocsDir))
        {
            Console.WriteLine($"ERROR: test_documents directory not found at {testDocsDir}");
            return 1;
        }

        var version = KreuzbergClient.GetVersion();
        Console.WriteLine($"Starting kreuzberg {version} test suite");
        Console.WriteLine($"Test documents directory: {testDocsDir}");
        Console.WriteLine(new string('-', 80));

        var allPassed = true;
        var results = new List<TestResult>();

        var documents = new (string Name, string Type)[]
        {
            ("tiny.pdf", "PDF"),
            ("lorem_ipsum.docx", "DOCX"),
            ("stanley_cups.xlsx", "XLSX"),
            ("ocr_image.jpg", "JPG Image"),
            ("test_hello_world.png", "PNG Image")
        };

        foreach (var (docName, docType) in documents)
        {
            var docPath = Path.Combine(testDocsDir, docName);

            if (!File.Exists(docPath))
            {
                Console.WriteLine($"SKIP  {docType,-15} {docName,-30} - File not found");
                continue;
            }

            Console.Write($"TEST  {docType,-15} {docName,-30} ");
            var result = TestDocument(docPath, forceOcr: false);

            if (result.Success)
            {
                Console.WriteLine($"OK   (text: {result.TextLength} chars)");
                results.Add(result);
            }
            else
            {
                Console.WriteLine("FAIL");
                Console.WriteLine($"      Error: {result.ErrorType}: {result.Error}");
                results.Add(result);
                allPassed = false;
            }
        }

        Console.WriteLine(new string('-', 80));
        Console.WriteLine("OCR Tests (force_ocr=True)");
        Console.WriteLine(new string('-', 80));

        var ocrTestFiles = new (string Name, string Type)[]
        {
            ("tiny.pdf", "PDF with OCR"),
            ("ocr_image.jpg", "JPG Image with OCR")
        };

        foreach (var (docName, docType) in ocrTestFiles)
        {
            var docPath = Path.Combine(testDocsDir, docName);

            if (!File.Exists(docPath))
            {
                Console.WriteLine($"SKIP  {docType,-25} {docName,-30} - File not found");
                continue;
            }

            Console.Write($"TEST  {docType,-25} {docName,-30} ");
            var result = TestDocument(docPath, forceOcr: true);

            if (result.Success)
            {
                Console.WriteLine($"OK   (text: {result.TextLength} chars)");
                results.Add(result);
                if (result.TextLength == 0)
                {
                    Console.WriteLine("      WARNING: OCR extracted 0 characters - PDFium may not be bundled correctly");
                }
            }
            else
            {
                Console.WriteLine("FAIL");
                Console.WriteLine($"      Error: {result.ErrorType}: {result.Error}");
                results.Add(result);
                allPassed = false;
            }
        }

        Console.WriteLine(new string('-', 80));
        Console.WriteLine("Summary");
        Console.WriteLine(new string('-', 80));

        var passed = results.Count(r => r.Success);
        var failed = results.Count(r => !r.Success);

        Console.WriteLine($"Passed: {passed}/{results.Count}");
        Console.WriteLine($"Failed: {failed}/{results.Count}");

        if (failed > 0)
        {
            Console.WriteLine("\nFailed tests:");
            foreach (var r in results.Where(r => !r.Success))
            {
                Console.WriteLine($"  - {r.File}: {r.Error}");
            }
        }

        Console.WriteLine("\nDetailed Results:");
        var options = new JsonSerializerOptions { WriteIndented = true };
        Console.WriteLine(JsonSerializer.Serialize(results, options));

        if (allPassed)
        {
            Console.WriteLine("\n✓ All tests passed!");
            return 0;
        }
        else
        {
            Console.WriteLine("\n✗ Some tests failed!");
            return 1;
        }
    }
}
