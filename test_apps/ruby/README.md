# Kreuzberg Ruby Test Application

Comprehensive test suite for the Kreuzberg Ruby bindings (Magnus FFI).

## Structure

- `spec/spec_helper.rb` - RSpec configuration and helper methods
- `spec/extraction_spec.rb` - Comprehensive extraction tests (40+ tests)
- `Gemfile` - Ruby gem dependencies
- `Rakefile` - Rake build configuration
- `.rspec` - RSpec configuration file

## Test Categories

The test suite includes 40+ comprehensive tests covering:

### 1. Type Verification Tests (8 tests)
- Verify all exported types from kreuzberg gem are accessible
- Kreuzberg module, Result, Config, Extraction, OCR
- Errors module and CLI

### 2. Sync Extraction Tests (4 tests)
- Extract from DOCX files
- Extract from ODT files
- Result structure validation
- Explicit MIME type handling

### 3. Async Extraction Tests (2 tests)
- Asynchronous file extraction
- Async result structure and content

### 4. Sync Byte Extraction Tests (3 tests)
- Extract from binary DOCX data
- Extract from binary ODT data
- MIME type requirement validation

### 5. Async Byte Extraction Tests (2 tests)
- Asynchronous extraction from binary data
- Async byte extraction from ODT

### 6. Batch Sync Extraction Tests (4 tests)
- Multiple files in batch
- Result order maintenance
- Single file batch extraction
- Content validation

### 7. Batch Async Extraction Tests (2 tests)
- Asynchronous batch file extraction
- Async batch with configuration

### 8. Batch Byte Extraction Tests (3 tests)
- Batch extract multiple documents (sync)
- Batch extract multiple documents (async)
- Order maintenance in batch byte extraction

### 9. MIME Type Detection Tests (3 tests)
- Detect MIME type from file path
- ODT file MIME detection
- MIME type in extraction result

### 10. File Type Coverage Tests (5 tests)
- DOCX extraction
- ODT extraction
- Markdown extraction
- PNG image extraction
- JPG image extraction

### 11. Configuration and Result Structure Tests (9 tests)
- Create extraction config objects
- Create OCR config objects
- Extract with custom config
- Extract with hash config
- Content attribute
- MIME type attribute
- Metadata attribute
- Tables attribute
- Chunks attribute
- Detected languages attribute
- Pages attribute
- Images attribute

### 12. Integration Tests (4 tests)
- Consistent results on repeated calls
- Sync and async extraction parity
- File and bytes extraction parity
- Batch and individual extraction parity

### 13. CLI Tests (3 tests)
- CLI extract functionality
- CLI MIME type detection
- CLI version string

## Test Files

The test suite uses documents from `/Users/naamanhirschfeld/workspace/kreuzberg-dev/kreuzberg/test_documents/`:

- `documents/fake.docx` - Word document sample
- `documents/simple.odt` - OpenDocument text sample
- `images/sample.png` - PNG image sample
- `images/example.jpg` - JPEG image sample
- `extraction_test.md` - Markdown sample

## Running Tests

```bash
# Install dependencies
bundle install

# Run all tests
bundle exec rspec

# Run specific test file
bundle exec rspec spec/extraction_spec.rb

# Run with detailed output
bundle exec rspec spec/extraction_spec.rb --format documentation

# Run specific test by name
bundle exec rspec spec/extraction_spec.rb -e "extracts content from DOCX file"
```

## Build Requirements

The test app requires the kreuzberg gem to be built from source with native extensions. To build:

```bash
cd ../../packages/ruby
bash ../../scripts/ci/ruby/vendor-kreuzberg-core.sh
bundle install
bundle exec rake compile
```

The native extension must be compiled before running tests.

## Test Documentation

All tests use RSpec conventions with:
- `describe` blocks for grouping related tests
- `context` blocks for test scenarios
- `it` blocks for individual test cases
- Proper setup/teardown via RSpec hooks
- Helper methods for document access

### Helper Methods

- `test_document_path(relative_path)` - Get absolute path to test document
- `read_test_document(relative_path)` - Read binary test document
- `create_test_file(content, filename)` - Create temporary test file

## Expected Test Results

With 40+ comprehensive tests, expected results:
- All type verification tests pass
- All extraction tests pass (sync and async)
- All batch extraction tests pass
- All file type coverage tests pass (with skips for unavailable formats)
- All configuration and result structure tests pass
- All integration tests pass
- All CLI tests pass

## Notes

- Tests use real test documents from the main test_documents directory
- Tests validate both synchronous and asynchronous APIs
- Tests check consistency between different extraction methods
- Tests verify configuration is properly applied
- Tests validate result structure and attributes
- Some tests may skip if optional test files are unavailable
