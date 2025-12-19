# Kreuzberg Java Test Suite - Quick Start Guide

## Setup (5 minutes)

### 1. Install Java 21+
```bash
java -version  # Verify Java 21+
javac -version # Verify javac 21+
```

### 2. Verify Maven
```bash
mvn --version  # Verify Maven 3.9.0+
```

### 3. Build Main Library (requires Java 25)
```bash
cd packages/java
mvn clean install -DskipTests
```

### 4. Navigate to Test App
```bash
cd test_apps/java
```

## Running Tests

### Quick Run (All Tests)
```bash
mvn clean test
```

### Run Specific Test Category
```bash
# Type verification
mvn test -Dtest=ExtractionTests#TypeVerificationTests

# Synchronous extraction
mvn test -Dtest=ExtractionTests#SyncFileExtractionTests

# Asynchronous extraction
mvn test -Dtest=ExtractionTests#AsyncFileExtractionTests

# Byte extraction
mvn test -Dtest=ExtractionTests#ByteExtractionTests

# Batch operations
mvn test -Dtest=ExtractionTests#BatchExtractionTests

# MIME detection
mvn test -Dtest=ExtractionTests#MimeTypeDetectionTests

# Configuration
mvn test -Dtest=ExtractionTests#ConfigurationTests

# Result validation
mvn test -Dtest=ExtractionTests#ResultValidationTests

# Error handling
mvn test -Dtest=ExtractionTests#ErrorHandlingTests

# File coverage
mvn test -Dtest=ExtractionTests#FileTypeCoverageTests

# Concurrent ops
mvn test -Dtest=ExtractionTests#ConcurrentOperationTests
```

### Verbose Output
```bash
mvn clean test -X
```

### Skip Tests
```bash
mvn clean install -DskipTests
```

## Understanding Test Output

### Success
```
[INFO] Tests run: 85, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

### Failure
```
[ERROR] Tests run: 85, Failures: 1, Errors: 0, Skipped: 0
[ERROR] FAILURE
[ERROR] testExtractPdfSync(ExtractionTests$SyncFileExtractionTests) AssertionError
```

## Test Structure

```
com.kreuzberg.test_app.ExtractionTests
├── TypeVerificationTests (10 tests)
├── SyncFileExtractionTests (8 tests)
├── AsyncFileExtractionTests (7 tests)
├── ByteExtractionTests (7 tests)
├── BatchExtractionTests (8 tests)
├── MimeTypeDetectionTests (6 tests)
├── ConfigurationTests (9 tests)
├── ResultValidationTests (9 tests)
├── ErrorHandlingTests (8 tests)
├── FileTypeCoverageTests (7 tests)
└── ConcurrentOperationTests (2 tests)

Total: 11 test classes, 85 test methods
```

## Test Document Files

The tests use these files from `test_documents/`:

| Format | File | Used In |
|--------|------|---------|
| PDF | gmft/tiny.pdf | Sync/async/batch/MIME tests |
| DOCX | documents/lorem_ipsum.docx | Sync/async/batch tests |
| XLSX | spreadsheets/test_01.xlsx | Sync/async/batch tests |
| PNG | images/sample.png | Image/MIME tests |
| JPG | images/example.jpg | Image tests |
| ODT | documents/simple.odt | Format coverage tests |
| Markdown | documents/markdown.md | Format coverage tests |

## File Locations

```
test_apps/java/
├── src/test/java/com/kreuzberg/test_app/
│   └── ExtractionTests.java          (40 KB, 1,060 lines)
├── pom.xml                            (2.7 KB)
├── README.md                          (7.5 KB, detailed guide)
├── TEST_SUMMARY.md                    (11 KB, detailed breakdown)
├── IMPLEMENTATION.md                  (detailed technical info)
└── QUICK_START.md                     (this file)
```

## Common Commands

### Compile Only
```bash
mvn clean compile
```

### Run Tests with Coverage
```bash
mvn clean test jacoco:report
```

### Run Tests in Parallel
```bash
mvn clean test -T 1C
```

### Run with Specific Java Version
```bash
export JAVA_HOME=/path/to/java21
mvn clean test
```

### Generate Test Report
```bash
mvn clean test
cat target/surefire-reports/ExtractionTests.txt
```

## Test Features at a Glance

### Types Tested
✓ ExtractionResult
✓ ExtractionConfig
✓ OcrConfig, ChunkingConfig, LanguageDetectionConfig, PdfConfig
✓ Table, Chunk, ExtractedImage
✓ ErrorCode, KreuzbergException
✓ BytesWithMime record

### Methods Tested
✓ extractFile (sync & async)
✓ extractBytes (sync & async)
✓ batchExtractFiles (sync & async)
✓ batchExtractBytes (sync & async)
✓ detectMimeType (bytes & path)

### File Formats
✓ PDF
✓ DOCX
✓ XLSX
✓ PNG
✓ JPG
✓ ODT
✓ Markdown

### Features
✓ Synchronous extraction
✓ Asynchronous/concurrent extraction
✓ In-memory byte processing
✓ Batch operations
✓ Configuration handling
✓ MIME type detection
✓ Error handling
✓ Result validation

## Troubleshooting

### "Java version not supported"
```bash
# Solution: Update Java to 21+
java -version
# Or set JAVA_HOME to Java 21+
export JAVA_HOME=/path/to/java21
```

### "Cannot find test documents"
```bash
# Solution: Ensure test documents exist at ../../../../test_documents/
ls ../../../../test_documents/gmft/tiny.pdf
```

### "Native library not found"
```bash
# Solution: Build the main package first
cd packages/java
mvn clean install
```

### "Compilation error: symbol not found"
```bash
# Solution: Make sure Kreuzberg library is installed
mvn -f packages/java/pom.xml install -DskipTests
```

### "Tests timeout"
```bash
# Solution: Increase timeout
mvn test -DargLine="-Dfile.encoding=UTF-8" -Dorg.slf4j.simpleLogger.defaultLogLevel=debug
```

## Quick Test Matrix

| Scenario | Command |
|----------|---------|
| Test everything | `mvn clean test` |
| Test PDF only | `mvn test -Dtest=ExtractionTests#SyncFileExtractionTests#testExtractPdfSync` |
| Test async only | `mvn test -Dtest=ExtractionTests#AsyncFileExtractionTests` |
| Test config | `mvn test -Dtest=ExtractionTests#ConfigurationTests` |
| Test errors | `mvn test -Dtest=ExtractionTests#ErrorHandlingTests` |
| Test all formats | `mvn test -Dtest=ExtractionTests#FileTypeCoverageTests` |

## Test Statistics

- **Total Tests**: 85
- **Test Classes**: 11 (nested)
- **Assertions**: 200+
- **File Types**: 7
- **API Methods**: 15+
- **Configuration Options**: 13+
- **Expected Duration**: 2-5 minutes

## Success Criteria

All tests pass when:
```
[INFO] Tests run: 85, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Next Steps

1. Read **README.md** for comprehensive guide
2. Read **TEST_SUMMARY.md** for detailed test breakdown
3. Read **IMPLEMENTATION.md** for technical details
4. Review **ExtractionTests.java** for test implementation

## Support

- Check test names with `@DisplayName` annotations
- Review test categories with `@Nested` classes
- Use fluent assertions from AssertJ
- Look at test documents used in each category

---

**Ready to run**: `mvn clean test`
