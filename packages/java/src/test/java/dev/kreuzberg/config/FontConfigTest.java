package dev.kreuzberg.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Nested;

import static org.junit.jupiter.api.Assertions.*;
import static org.assertj.core.api.Assertions.*;

/**
 * Comprehensive FontConfig tests.
 *
 * Tests for FontConfig feature that allows users to enable/disable custom
 * font provider and add custom font directories.
 */
class FontConfigTest {

	@Test
	void testFontConfigDefaults() {
		FontConfig config = FontConfig.builder().build();

		assertNotNull(config, "FontConfig should not be null");
		assertTrue(config.isEnabled(), "enabled should default to true");
		assertNull(config.getCustomFontDirs(), "customFontDirs should default to null");
	}

	@Test
	void testFontConfigBuilderWithEnabledTrue() {
		FontConfig config = FontConfig.builder()
				.enabled(true)
				.build();

		assertTrue(config.isEnabled(), "enabled should be true");
		assertNull(config.getCustomFontDirs(), "customFontDirs should be null");
	}

	@Test
	void testFontConfigBuilderWithEnabledFalse() {
		FontConfig config = FontConfig.builder()
				.enabled(false)
				.build();

		assertFalse(config.isEnabled(), "enabled should be false");
		assertNull(config.getCustomFontDirs(), "customFontDirs should be null");
	}

	@Test
	void testFontConfigBuilderWithCustomDirs() {
		java.util.List<String> dirs = java.util.Arrays.asList(
				"/usr/share/fonts/custom",
				"~/my-fonts"
		);

		FontConfig config = FontConfig.builder()
				.customFontDirs(dirs)
				.build();

		assertTrue(config.isEnabled(), "enabled should default to true");
		assertNotNull(config.getCustomFontDirs(), "customFontDirs should not be null");
		assertThat(config.getCustomFontDirs())
				.hasSize(2)
				.containsExactly("/usr/share/fonts/custom", "~/my-fonts");
	}

	@Test
	void testFontConfigBuilderWithAllParameters() {
		java.util.List<String> dirs = java.util.Arrays.asList("/path/to/fonts", "/another/path");

		FontConfig config = FontConfig.builder()
				.enabled(true)
				.customFontDirs(dirs)
				.build();

		assertTrue(config.isEnabled(), "enabled should be true");
		assertNotNull(config.getCustomFontDirs(), "customFontDirs should not be null");
		assertThat(config.getCustomFontDirs())
				.hasSize(2)
				.containsExactlyElementsOf(dirs);
	}

	@Test
	void testFontConfigBuilderChaining() {
		FontConfig config = FontConfig.builder()
				.enabled(false)
				.customFontDirs(java.util.Arrays.asList("/fonts"))
				.build();

		assertFalse(config.isEnabled(), "Method chaining should work");
		assertNotNull(config.getCustomFontDirs());
	}

	@Test
	void testFontConfigEmptyCustomDirs() {
		FontConfig config = FontConfig.builder()
				.enabled(true)
				.customFontDirs(new java.util.ArrayList<>())
				.build();

		assertTrue(config.isEnabled());
		assertNotNull(config.getCustomFontDirs());
		assertThat(config.getCustomFontDirs()).isEmpty();
	}

	@Test
	void testFontConfigMultipleCustomDirs() {
		java.util.List<String> dirs = java.util.Arrays.asList(
				"/path1",
				"/path2",
				"/path3",
				"~/fonts",
				"./relative-fonts"
		);

		FontConfig config = FontConfig.builder()
				.customFontDirs(dirs)
				.build();

		assertThat(config.getCustomFontDirs())
				.hasSize(5)
				.containsExactlyElementsOf(dirs);
	}

	@Test
	void testFontConfigEqualsAndHashCode() {
		java.util.List<String> dirs = java.util.Arrays.asList("/fonts");

		FontConfig config1 = FontConfig.builder()
				.enabled(true)
				.customFontDirs(dirs)
				.build();

		FontConfig config2 = FontConfig.builder()
				.enabled(true)
				.customFontDirs(dirs)
				.build();

		assertEquals(config1, config2, "Equal configs should be equal");
		assertEquals(config1.hashCode(), config2.hashCode(), "Equal configs should have same hash");
	}

	@Test
	void testFontConfigToString() {
		FontConfig config = FontConfig.builder()
				.enabled(true)
				.customFontDirs(java.util.Arrays.asList("/fonts"))
				.build();

		String str = config.toString();

		assertNotNull(str);
		assertThat(str).contains("FontConfig");
	}

	@Nested
	class PdfConfigIntegration {

		@Test
		void testPdfConfigWithFontConfig() {
			FontConfig fontConfig = FontConfig.builder()
					.enabled(true)
					.customFontDirs(java.util.Arrays.asList("/fonts"))
					.build();

			PdfConfig pdfConfig = PdfConfig.builder()
					.extractImages(true)
					.fontConfig(fontConfig)
					.build();

			assertNotNull(pdfConfig.getFontConfig());
			assertTrue(pdfConfig.getFontConfig().isEnabled());
			assertThat(pdfConfig.getFontConfig().getCustomFontDirs())
					.contains("/fonts");
		}

		@Test
		void testPdfConfigWithFontConfigDisabled() {
			FontConfig fontConfig = FontConfig.builder()
					.enabled(false)
					.customFontDirs(java.util.Arrays.asList("/custom"))
					.build();

			PdfConfig pdfConfig = PdfConfig.builder()
					.fontConfig(fontConfig)
					.build();

			assertNotNull(pdfConfig.getFontConfig());
			assertFalse(pdfConfig.getFontConfig().isEnabled());
			assertThat(pdfConfig.getFontConfig().getCustomFontDirs())
					.contains("/custom");
		}

		@Test
		void testPdfConfigWithFontConfigAllParameters() {
			FontConfig fontConfig = FontConfig.builder()
					.enabled(true)
					.customFontDirs(java.util.Arrays.asList("/custom-fonts"))
					.build();

			PdfConfig pdfConfig = PdfConfig.builder()
					.extractImages(true)
					.passwords(java.util.Arrays.asList("pass1"))
					.extractMetadata(true)
					.fontConfig(fontConfig)
					.build();

			assertTrue(pdfConfig.isExtractImages());
			assertThat(pdfConfig.getPasswords()).contains("pass1");
			assertTrue(pdfConfig.isExtractMetadata());
			assertTrue(pdfConfig.getFontConfig().isEnabled());
		}

		@Test
		void testPdfConfigWithoutFontConfig() {
			PdfConfig pdfConfig = PdfConfig.builder()
					.extractImages(true)
					.build();

			assertNull(pdfConfig.getFontConfig(), "FontConfig should be null when not set");
		}

		@Test
		void testPdfConfigFontConfigNull() {
			PdfConfig pdfConfig = PdfConfig.builder()
					.fontConfig(null)
					.build();

			assertNull(pdfConfig.getFontConfig());
		}
	}
}
