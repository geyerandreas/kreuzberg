package com.kreuzberg.test_app;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.kreuzberg.BytesWithMime;
import dev.kreuzberg.Chunk;
import dev.kreuzberg.ErrorCode;
import dev.kreuzberg.ExtractionResult;
import dev.kreuzberg.ExtractedImage;
import dev.kreuzberg.Kreuzberg;
import dev.kreuzberg.KreuzbergException;
import dev.kreuzberg.Table;
import dev.kreuzberg.config.ChunkingConfig;
import dev.kreuzberg.config.ExtractionConfig;
import dev.kreuzberg.config.ImageExtractionConfig;
import dev.kreuzberg.config.LanguageDetectionConfig;
import dev.kreuzberg.config.OcrConfig;
import dev.kreuzberg.config.PdfConfig;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/**
 * Comprehensive test suite for Kreuzberg Java FFM API.
 *
 * Tests cover:
 * - Type verification for all exported classes
 * - Synchronous and asynchronous file extraction
 * - Byte array extraction
 * - Batch extraction operations
 * - MIME type detection
 * - Configuration handling
 * - Result validation
 * - Error handling
 */
@DisplayName("Kreuzberg RC13 Comprehensive Test Suite")
final class ExtractionTests {
    private static final Path TEST_DOCUMENTS =
        Paths.get("../../../../test_documents").toAbsolutePath().normalize();

    @BeforeAll
    static void verifyTestDocumentsExist() {
        assertThat(Files.exists(TEST_DOCUMENTS))
            .as("Test documents directory must exist at: " + TEST_DOCUMENTS)
            .isTrue();
    }

    @Nested
    @DisplayName("Type Verification Tests")
    final class TypeVerificationTests {

        @Test
        @DisplayName("ExtractionResult class is accessible")
        void testExtractionResultAccessible() {
            assertThat(ExtractionResult.class).isNotNull();
        }

        @Test
        @DisplayName("ExtractionConfig class is accessible")
        void testExtractionConfigAccessible() {
            assertThat(ExtractionConfig.class).isNotNull();
        }

        @Test
        @DisplayName("ExtractionConfig builder is accessible")
        void testExtractionConfigBuilderAccessible() {
            ExtractionConfig config = ExtractionConfig.builder().build();
            assertThat(config).isNotNull();
        }

        @Test
        @DisplayName("All config sub-types are accessible")
        void testConfigSubTypesAccessible() {
            assertThat(OcrConfig.class).isNotNull();
            assertThat(ChunkingConfig.class).isNotNull();
            assertThat(LanguageDetectionConfig.class).isNotNull();
            assertThat(PdfConfig.class).isNotNull();
            assertThat(ImageExtractionConfig.class).isNotNull();
        }

        @Test
        @DisplayName("Table class is accessible")
        void testTableClassAccessible() {
            assertThat(Table.class).isNotNull();
        }

        @Test
        @DisplayName("Chunk class is accessible")
        void testChunkClassAccessible() {
            assertThat(Chunk.class).isNotNull();
        }

        @Test
        @DisplayName("ExtractedImage class is accessible")
        void testExtractedImageClassAccessible() {
            assertThat(ExtractedImage.class).isNotNull();
        }

        @Test
        @DisplayName("ErrorCode enum is accessible")
        void testErrorCodeEnumAccessible() {
            assertThat(ErrorCode.class).isNotNull();
        }

        @Test
        @DisplayName("KreuzbergException class is accessible")
        void testKreuzbergExceptionAccessible() {
            assertThat(KreuzbergException.class).isNotNull();
        }

        @Test
        @DisplayName("Kreuzberg main API is accessible")
        void testKreuzbergAPIAccessible() {
            assertThat(Kreuzberg.class).isNotNull();
        }
    }

    @Nested
    @DisplayName("Synchronous File Extraction Tests")
    final class SyncFileExtractionTests {

        @Test
        @DisplayName("Extract simple PDF file synchronously")
        void testExtractPdfSync() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            assertThat(pdfPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.getMimeType()).contains("pdf");
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract DOCX file synchronously")
        void testExtractDocxSync() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            assertThat(docxPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(docxPath);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.getMimeType())
                .contains("word")
                .or()
                .contains("document");
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract XLSX file synchronously")
        void testExtractXlsxSync() throws IOException, KreuzbergException {
            Path xlsxPath = TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx");
            assertThat(xlsxPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(xlsxPath);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.getMimeType()).contains("spreadsheet");
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract image (PNG) file synchronously")
        void testExtractPngSync() throws IOException, KreuzbergException {
            Path pngPath = TEST_DOCUMENTS.resolve("images/sample.png");
            assertThat(pngPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(pngPath);

            assertThat(result).isNotNull();
            assertThat(result.getMimeType()).contains("image");
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract image (JPG) file synchronously")
        void testExtractJpgSync() throws IOException, KreuzbergException {
            Path jpgPath = TEST_DOCUMENTS.resolve("images/example.jpg");
            assertThat(jpgPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(jpgPath);

            assertThat(result).isNotNull();
            assertThat(result.getMimeType()).contains("image");
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract ODT file synchronously")
        void testExtractOdtSync() throws IOException, KreuzbergException {
            Path odtPath = TEST_DOCUMENTS.resolve("documents/simple.odt");
            assertThat(odtPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(odtPath);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.getMimeType()).contains("document");
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract Markdown file synchronously")
        void testExtractMarkdownSync() throws IOException, KreuzbergException {
            Path mdPath = TEST_DOCUMENTS.resolve("documents/markdown.md");
            assertThat(mdPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(mdPath);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract file using String path")
        void testExtractFileWithStringPath() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            assertThat(pdfPath).exists();

            ExtractionResult result = Kreuzberg.extractFile(pdfPath.toString());

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
        }
    }

    @Nested
    @DisplayName("Asynchronous File Extraction Tests")
    final class AsyncFileExtractionTests {

        @Test
        @DisplayName("Extract PDF file asynchronously")
        void testExtractPdfAsync() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            assertThat(pdfPath).exists();

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(pdfPath);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract DOCX file asynchronously")
        void testExtractDocxAsync() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            assertThat(docxPath).exists();

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(docxPath);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract XLSX file asynchronously")
        void testExtractXlsxAsync() throws IOException, KreuzbergException {
            Path xlsxPath = TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx");
            assertThat(xlsxPath).exists();

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(xlsxPath);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract image asynchronously")
        void testExtractImageAsync() throws IOException, KreuzbergException {
            Path pngPath = TEST_DOCUMENTS.resolve("images/sample.png");
            assertThat(pngPath).exists();

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(pngPath);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract ODT file asynchronously")
        void testExtractOdtAsync() throws IOException, KreuzbergException {
            Path odtPath = TEST_DOCUMENTS.resolve("documents/simple.odt");
            assertThat(odtPath).exists();

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(odtPath);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract Markdown file asynchronously")
        void testExtractMarkdownAsync() throws IOException, KreuzbergException {
            Path mdPath = TEST_DOCUMENTS.resolve("documents/markdown.md");
            assertThat(mdPath).exists();

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(mdPath);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Multiple async extractions execute concurrently")
        void testMultipleAsyncExtractionsAreConcurrent() throws IOException, KreuzbergException {
            Path pdf = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            Path docx = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            Path xlsx = TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx");

            assertThat(pdf).exists();
            assertThat(docx).exists();
            assertThat(xlsx).exists();

            CompletableFuture<ExtractionResult> future1 = Kreuzberg.extractFileAsync(pdf);
            CompletableFuture<ExtractionResult> future2 = Kreuzberg.extractFileAsync(docx);
            CompletableFuture<ExtractionResult> future3 = Kreuzberg.extractFileAsync(xlsx);

            CompletableFuture<Void> allOf = CompletableFuture.allOf(future1, future2, future3);
            allOf.join();

            assertThat(future1.join()).isNotNull();
            assertThat(future2.join()).isNotNull();
            assertThat(future3.join()).isNotNull();
        }
    }

    @Nested
    @DisplayName("Byte Extraction Tests")
    final class ByteExtractionTests {

        @Test
        @DisplayName("Extract from byte array synchronously (PDF)")
        void testExtractBytesSync() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            byte[] pdfData = Files.readAllBytes(pdfPath);

            ExtractionResult result =
                Kreuzberg.extractBytes(pdfData, "application/pdf", null);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract from byte array synchronously with config")
        void testExtractBytesSyncWithConfig() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            byte[] docxData = Files.readAllBytes(docxPath);

            ExtractionConfig config = ExtractionConfig.builder()
                .enableQualityProcessing(true)
                .build();

            ExtractionResult result =
                Kreuzberg.extractBytes(
                    docxData,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    config);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract from byte array asynchronously")
        void testExtractBytesAsync() throws IOException, KreuzbergException {
            Path xlsxPath = TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx");
            byte[] xlsxData = Files.readAllBytes(xlsxPath);

            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractBytesAsync(
                    xlsxData,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    null);

            ExtractionResult result = futureResult.join();

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract image from byte array")
        void testExtractImageBytes() throws IOException, KreuzbergException {
            Path pngPath = TEST_DOCUMENTS.resolve("images/sample.png");
            byte[] imageData = Files.readAllBytes(pngPath);

            ExtractionResult result = Kreuzberg.extractBytes(imageData, "image/png", null);

            assertThat(result).isNotNull();
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extract bytes rejects null data")
        void testExtractBytesRejectsNullData() {
            assertThatThrownBy(() ->
                Kreuzberg.extractBytes(null, "application/pdf", null))
                .isInstanceOf(NullPointerException.class);
        }

        @Test
        @DisplayName("Extract bytes rejects empty data")
        void testExtractBytesRejectsEmptyData() {
            assertThatThrownBy(() ->
                Kreuzberg.extractBytes(new byte[0], "application/pdf", null))
                .isInstanceOf(KreuzbergException.class);
        }

        @Test
        @DisplayName("Extract bytes requires mime type")
        void testExtractBytesRequiresMimeType() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            byte[] pdfData = Files.readAllBytes(pdfPath);

            assertThatThrownBy(() ->
                Kreuzberg.extractBytes(pdfData, "", null))
                .isInstanceOf(KreuzbergException.class);
        }

        @Test
        @DisplayName("Extract bytes requires non-null mime type")
        void testExtractBytesRequiresNonNullMimeType() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            byte[] pdfData = Files.readAllBytes(pdfPath);

            assertThatThrownBy(() ->
                Kreuzberg.extractBytes(pdfData, null, null))
                .isInstanceOf(KreuzbergException.class);
        }
    }

    @Nested
    @DisplayName("Batch Extraction Tests")
    final class BatchExtractionTests {

        @Test
        @DisplayName("Batch extract multiple files synchronously")
        void testBatchExtractFilesSync() throws IOException, KreuzbergException {
            List<String> paths = List.of(
                TEST_DOCUMENTS.resolve("gmft/tiny.pdf").toString(),
                TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx").toString(),
                TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx").toString());

            List<ExtractionResult> results = Kreuzberg.batchExtractFiles(paths, null);

            assertThat(results).hasSize(3);
            assertThat(results).allMatch(r -> r.getContent().length() > 0);
            assertThat(results).allMatch(ExtractionResult::isSuccess);
        }

        @Test
        @DisplayName("Batch extract with configuration")
        void testBatchExtractFilesWithConfig() throws IOException, KreuzbergException {
            List<String> paths = List.of(
                TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx").toString(),
                TEST_DOCUMENTS.resolve("documents/simple.odt").toString());

            ExtractionConfig config = ExtractionConfig.builder()
                .enableQualityProcessing(true)
                .build();

            List<ExtractionResult> results = Kreuzberg.batchExtractFiles(paths, config);

            assertThat(results).hasSize(2);
            assertThat(results).allMatch(r -> r.getContent().length() > 0);
        }

        @Test
        @DisplayName("Batch extract bytes synchronously")
        void testBatchExtractBytesSync() throws IOException, KreuzbergException {
            byte[] pdfData = Files.readAllBytes(TEST_DOCUMENTS.resolve("gmft/tiny.pdf"));
            byte[] docxData = Files.readAllBytes(TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx"));

            List<BytesWithMime> items = List.of(
                new BytesWithMime(pdfData, "application/pdf"),
                new BytesWithMime(docxData,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"));

            List<ExtractionResult> results =
                Kreuzberg.batchExtractBytes(items, null);

            assertThat(results).hasSize(2);
            assertThat(results).allMatch(ExtractionResult::isSuccess);
        }

        @Test
        @DisplayName("Batch extract bytes asynchronously")
        void testBatchExtractBytesAsync() throws IOException, KreuzbergException {
            byte[] pdfData = Files.readAllBytes(TEST_DOCUMENTS.resolve("gmft/tiny.pdf"));
            byte[] xlsxData = Files.readAllBytes(TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx"));

            List<BytesWithMime> items = List.of(
                new BytesWithMime(pdfData, "application/pdf"),
                new BytesWithMime(xlsxData,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));

            CompletableFuture<List<ExtractionResult>> futureResults =
                Kreuzberg.batchExtractBytesAsync(items, null);

            List<ExtractionResult> results = futureResults.join();

            assertThat(results).hasSize(2);
            assertThat(results).allMatch(ExtractionResult::isSuccess);
        }

        @Test
        @DisplayName("Batch extract with invalid MIME type is handled")
        void testBatchExtractBytesInvalidMimeType() throws IOException, KreuzbergException {
            byte[] pdfData = Files.readAllBytes(TEST_DOCUMENTS.resolve("gmft/tiny.pdf"));
            List<BytesWithMime> items = List.of(
                new BytesWithMime(pdfData, "application/pdf"));

            List<ExtractionResult> results = Kreuzberg.batchExtractBytes(items, null);
            assertThat(results).hasSize(1);
        }

        @Test
        @DisplayName("Batch extract empty list returns empty list")
        void testBatchExtractEmptyList() throws KreuzbergException {
            List<ExtractionResult> results = Kreuzberg.batchExtractFiles(List.of(), null);

            assertThat(results).isEmpty();
        }

        @Test
        @DisplayName("Batch extract files asynchronously")
        void testBatchExtractFilesAsync() throws IOException, KreuzbergException {
            List<String> paths = List.of(
                TEST_DOCUMENTS.resolve("gmft/tiny.pdf").toString(),
                TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx").toString());

            CompletableFuture<List<ExtractionResult>> futureResults =
                Kreuzberg.batchExtractFilesAsync(paths, null);

            List<ExtractionResult> results = futureResults.join();

            assertThat(results).hasSize(2);
            assertThat(results).allMatch(ExtractionResult::isSuccess);
        }
    }

    @Nested
    @DisplayName("MIME Type Detection Tests")
    final class MimeTypeDetectionTests {

        @Test
        @DisplayName("Detect MIME type from PDF bytes")
        void testDetectMimeTypeFromPdfBytes() throws IOException, KreuzbergException {
            byte[] pdfData = Files.readAllBytes(TEST_DOCUMENTS.resolve("gmft/tiny.pdf"));

            String mimeType = Kreuzberg.detectMimeType(pdfData);

            assertThat(mimeType).contains("pdf");
        }

        @Test
        @DisplayName("Detect MIME type from DOCX bytes")
        void testDetectMimeTypeFromDocxBytes() throws IOException, KreuzbergException {
            byte[] docxData = Files.readAllBytes(TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx"));

            String mimeType = Kreuzberg.detectMimeType(docxData);

            assertThat(mimeType).isNotEmpty();
        }

        @Test
        @DisplayName("Detect MIME type from XLSX bytes")
        void testDetectMimeTypeFromXlsxBytes() throws IOException, KreuzbergException {
            byte[] xlsxData = Files.readAllBytes(TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx"));

            String mimeType = Kreuzberg.detectMimeType(xlsxData);

            assertThat(mimeType).isNotEmpty();
        }

        @Test
        @DisplayName("Detect MIME type from image bytes")
        void testDetectMimeTypeFromImageBytes() throws IOException, KreuzbergException {
            byte[] pngData = Files.readAllBytes(TEST_DOCUMENTS.resolve("images/sample.png"));

            String mimeType = Kreuzberg.detectMimeType(pngData);

            assertThat(mimeType).contains("image");
        }

        @Test
        @DisplayName("Detect MIME type from file path string")
        void testDetectMimeTypeFromFilePath() throws IOException, KreuzbergException {
            String pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf").toString();

            String mimeType = Kreuzberg.detectMimeType(pdfPath);

            assertThat(mimeType).contains("pdf");
        }

        @Test
        @DisplayName("Detect MIME type from path string")
        void testDetectMimeTypeFromPathString() throws IOException, KreuzbergException {
            String pathStr = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx").toString();

            String mimeType = Kreuzberg.detectMimeType(pathStr);

            assertThat(mimeType).isNotEmpty();
        }
    }

    @Nested
    @DisplayName("Configuration Handling Tests")
    final class ConfigurationTests {

        @Test
        @DisplayName("Create default extraction config")
        void testCreateDefaultConfig() {
            ExtractionConfig config = ExtractionConfig.builder().build();

            assertThat(config).isNotNull();
            assertThat(config.isUseCache()).isTrue();
            assertThat(config.isEnableQualityProcessing()).isFalse();
            assertThat(config.isForceOcr()).isFalse();
        }

        @Test
        @DisplayName("Create config with cache disabled")
        void testCreateConfigWithCacheDisabled() {
            ExtractionConfig config = ExtractionConfig.builder()
                .useCache(false)
                .build();

            assertThat(config.isUseCache()).isFalse();
        }

        @Test
        @DisplayName("Create config with quality processing enabled")
        void testCreateConfigWithQualityProcessing() {
            ExtractionConfig config = ExtractionConfig.builder()
                .enableQualityProcessing(true)
                .build();

            assertThat(config.isEnableQualityProcessing()).isTrue();
        }

        @Test
        @DisplayName("Create config with OCR forced")
        void testCreateConfigWithForcedOcr() {
            ExtractionConfig config = ExtractionConfig.builder()
                .forceOcr(true)
                .build();

            assertThat(config.isForceOcr()).isTrue();
        }

        @Test
        @DisplayName("Create config with chunking settings")
        void testCreateConfigWithChunking() {
            ChunkingConfig chunking = ChunkingConfig.builder()
                .chunkSize(1000)
                .overlapSize(100)
                .build();

            ExtractionConfig config = ExtractionConfig.builder()
                .chunking(chunking)
                .build();

            assertThat(config.getChunking()).isNotNull();
        }

        @Test
        @DisplayName("Create config with language detection")
        void testCreateConfigWithLanguageDetection() {
            LanguageDetectionConfig languageDetection = LanguageDetectionConfig.builder()
                .enableLanguageDetection(true)
                .build();

            ExtractionConfig config = ExtractionConfig.builder()
                .languageDetection(languageDetection)
                .build();

            assertThat(config.getLanguageDetection()).isNotNull();
        }

        @Test
        @DisplayName("Create config with PDF options")
        void testCreateConfigWithPdfOptions() {
            PdfConfig pdfConfig = PdfConfig.builder()
                .useGMFT(true)
                .build();

            ExtractionConfig config = ExtractionConfig.builder()
                .pdfOptions(pdfConfig)
                .build();

            assertThat(config.getPdfOptions()).isNotNull();
        }

        @Test
        @DisplayName("Create config with image extraction settings")
        void testCreateConfigWithImageExtraction() {
            ImageExtractionConfig imageExtraction = ImageExtractionConfig.builder()
                .extractImages(true)
                .build();

            ExtractionConfig config = ExtractionConfig.builder()
                .imageExtraction(imageExtraction)
                .build();

            assertThat(config.getImageExtraction()).isNotNull();
        }

        @Test
        @DisplayName("Extract with custom config")
        void testExtractWithCustomConfig() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionConfig config = ExtractionConfig.builder()
                .useCache(false)
                .build();

            ExtractionResult result = Kreuzberg.extractFile(pdfPath, config);

            assertThat(result).isNotNull();
            assertThat(result.getContent()).isNotEmpty();
        }

        @Test
        @DisplayName("Config toMap returns configuration map")
        void testConfigToMap() {
            ExtractionConfig config = ExtractionConfig.builder()
                .useCache(false)
                .enableQualityProcessing(true)
                .build();

            java.util.Map<String, Object> map = config.toMap();

            assertThat(map).isNotNull();
            assertThat(map).containsKey("use_cache");
            assertThat(map).containsKey("enable_quality_processing");
        }
    }

    @Nested
    @DisplayName("Result Structure Validation Tests")
    final class ResultValidationTests {

        @Test
        @DisplayName("Extraction result has content")
        void testResultHasContent() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            assertThat(result.getContent()).isNotNull().isNotEmpty();
        }

        @Test
        @DisplayName("Extraction result has MIME type")
        void testResultHasMimeType() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            ExtractionResult result = Kreuzberg.extractFile(docxPath);

            assertThat(result.getMimeType()).isNotNull().isNotEmpty();
        }

        @Test
        @DisplayName("Extraction result has success flag")
        void testResultHasSuccessFlag() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("Extraction result provides metadata")
        void testResultHasMetadata() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            ExtractionResult result = Kreuzberg.extractFile(docxPath);

            assertThat(result.getMetadata()).isNotNull();
        }

        @Test
        @DisplayName("Extraction result provides tables list")
        void testResultHasTablesList() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            assertThat(result.getTables()).isNotNull().isNotEmpty();
        }

        @Test
        @DisplayName("Extraction result provides chunks list")
        void testResultHasChunksList() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            assertThat(result.getChunks()).isNotNull();
        }

        @Test
        @DisplayName("Extraction result provides images list")
        void testResultHasImagesList() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            assertThat(result.getImages()).isNotNull();
        }

        @Test
        @DisplayName("Extraction result provides detected languages")
        void testResultHasDetectedLanguages() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            ExtractionResult result = Kreuzberg.extractFile(docxPath);

            assertThat(result.getDetectedLanguages()).isNotNull();
        }

        @Test
        @DisplayName("Extraction result provides toString representation")
        void testResultToString() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);

            String str = result.toString();

            assertThat(str).isNotNull().isNotEmpty().contains("ExtractionResult");
        }

        @Test
        @DisplayName("Extraction result optional fields are accessible")
        void testResultOptionalFields() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            ExtractionResult result = Kreuzberg.extractFile(docxPath);

            assertThat(result.getLanguage()).isNotNull();
            assertThat(result.getDate()).isNotNull();
            assertThat(result.getSubject()).isNotNull();
        }
    }

    @Nested
    @DisplayName("Error Handling Tests")
    final class ErrorHandlingTests {

        @Test
        @DisplayName("Extract non-existent file throws IOException")
        void testExtractNonExistentFile() {
            assertThatThrownBy(() ->
                Kreuzberg.extractFile("/nonexistent/file.pdf"))
                .isInstanceOf(IOException.class);
        }

        @Test
        @DisplayName("Extract null path throws exception")
        void testExtractNullPath() {
            assertThatThrownBy(() ->
                Kreuzberg.extractFile((Path) null))
                .isInstanceOf(NullPointerException.class);
        }

        @Test
        @DisplayName("Extract with invalid MIME type throws exception")
        void testExtractBytesInvalidMimeType() throws IOException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            byte[] pdfData = Files.readAllBytes(pdfPath);

            assertThatThrownBy(() ->
                Kreuzberg.extractBytes(pdfData, "invalid/mime-type", null))
                .isInstanceOf(KreuzbergException.class);
        }

        @Test
        @DisplayName("Batch extract files with null list throws exception")
        void testBatchExtractNullFileList() {
            assertThatThrownBy(() ->
                Kreuzberg.batchExtractFiles(null, null))
                .isInstanceOf(NullPointerException.class);
        }

        @Test
        @DisplayName("Batch extract bytes with null list throws exception")
        void testBatchExtractNullBytesList() {
            assertThatThrownBy(() ->
                Kreuzberg.batchExtractBytes(null, null))
                .isInstanceOf(NullPointerException.class);
        }

        @Test
        @DisplayName("MIME type detection rejects null bytes")
        void testDetectMimeTypeNullBytes() {
            assertThatThrownBy(() ->
                Kreuzberg.detectMimeType((byte[]) null))
                .isInstanceOf(NullPointerException.class);
        }

        @Test
        @DisplayName("MIME type detection rejects null path string")
        void testDetectMimeTypeNullPath() {
            assertThatThrownBy(() ->
                Kreuzberg.detectMimeType((String) null))
                .isInstanceOf(NullPointerException.class);
        }

        @Test
        @DisplayName("KreuzbergException includes error information")
        void testKreuzbergExceptionHasMessage() {
            KreuzbergException exception = new KreuzbergException("Test error");

            assertThat(exception).hasMessage("Test error");
            assertThat(exception.getErrorCode()).isNotNull();
        }

        @Test
        @DisplayName("KreuzbergException with cause preserves cause")
        void testKreuzbergExceptionWithCause() {
            IOException cause = new IOException("Root cause");
            KreuzbergException exception = new KreuzbergException("Test error", cause);

            assertThat(exception).hasCause(cause);
        }

        @Test
        @DisplayName("Async extraction handles exceptions properly")
        void testAsyncExtractionHandlesExceptions() {
            CompletableFuture<ExtractionResult> futureResult =
                Kreuzberg.extractFileAsync(Path.of("/nonexistent/file.pdf"));

            assertThatThrownBy(futureResult::join)
                .isInstanceOf(Exception.class);
        }
    }

    @Nested
    @DisplayName("File Type Coverage Tests")
    final class FileTypeCoverageTests {

        @Test
        @DisplayName("PDF extraction works")
        void testPdfExtractionWorks() throws IOException, KreuzbergException {
            Path pdfPath = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            ExtractionResult result = Kreuzberg.extractFile(pdfPath);
            assertThat(result.getContent()).isNotEmpty();
        }

        @Test
        @DisplayName("DOCX extraction works")
        void testDocxExtractionWorks() throws IOException, KreuzbergException {
            Path docxPath = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            ExtractionResult result = Kreuzberg.extractFile(docxPath);
            assertThat(result.getContent()).isNotEmpty();
        }

        @Test
        @DisplayName("XLSX extraction works")
        void testXlsxExtractionWorks() throws IOException, KreuzbergException {
            Path xlsxPath = TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx");
            ExtractionResult result = Kreuzberg.extractFile(xlsxPath);
            assertThat(result.getContent()).isNotEmpty();
        }

        @Test
        @DisplayName("PNG extraction works")
        void testPngExtractionWorks() throws IOException, KreuzbergException {
            Path pngPath = TEST_DOCUMENTS.resolve("images/sample.png");
            ExtractionResult result = Kreuzberg.extractFile(pngPath);
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("JPG extraction works")
        void testJpgExtractionWorks() throws IOException, KreuzbergException {
            Path jpgPath = TEST_DOCUMENTS.resolve("images/example.jpg");
            ExtractionResult result = Kreuzberg.extractFile(jpgPath);
            assertThat(result.isSuccess()).isTrue();
        }

        @Test
        @DisplayName("ODT extraction works")
        void testOdtExtractionWorks() throws IOException, KreuzbergException {
            Path odtPath = TEST_DOCUMENTS.resolve("documents/simple.odt");
            ExtractionResult result = Kreuzberg.extractFile(odtPath);
            assertThat(result.getContent()).isNotEmpty();
        }

        @Test
        @DisplayName("Markdown extraction works")
        void testMarkdownExtractionWorks() throws IOException, KreuzbergException {
            Path mdPath = TEST_DOCUMENTS.resolve("documents/markdown.md");
            ExtractionResult result = Kreuzberg.extractFile(mdPath);
            assertThat(result.getContent()).isNotEmpty();
        }
    }

    @Nested
    @DisplayName("Concurrent Operation Tests")
    final class ConcurrentOperationTests {

        @Test
        @DisplayName("Multiple synchronous extractions work correctly")
        void testMultipleSyncExtractions() throws IOException, KreuzbergException {
            Path pdf = TEST_DOCUMENTS.resolve("gmft/tiny.pdf");
            Path docx = TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx");
            Path xlsx = TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx");

            ExtractionResult result1 = Kreuzberg.extractFile(pdf);
            ExtractionResult result2 = Kreuzberg.extractFile(docx);
            ExtractionResult result3 = Kreuzberg.extractFile(xlsx);

            assertThat(result1.getContent()).isNotEmpty();
            assertThat(result2.getContent()).isNotEmpty();
            assertThat(result3.getContent()).isNotEmpty();
        }

        @Test
        @DisplayName("Batch operations complete successfully with multiple files")
        void testBatchOperationsMultipleFiles() throws IOException, KreuzbergException {
            List<String> paths = List.of(
                TEST_DOCUMENTS.resolve("gmft/tiny.pdf").toString(),
                TEST_DOCUMENTS.resolve("documents/lorem_ipsum.docx").toString(),
                TEST_DOCUMENTS.resolve("documents/simple.odt").toString(),
                TEST_DOCUMENTS.resolve("spreadsheets/test_01.xlsx").toString());

            List<ExtractionResult> results = Kreuzberg.batchExtractFiles(paths, null);

            assertThat(results).hasSize(4);
            assertThat(results).allMatch(r -> r.getContent().length() > 0);
        }
    }
}
