from __future__ import annotations

from kreuzberg import FontConfig, PdfConfig


def test_font_config_default_initialization() -> None:
    config = FontConfig()
    assert config.enabled is True
    assert config.custom_font_dirs is None


def test_font_config_with_enabled_flag() -> None:
    config = FontConfig(enabled=False)
    assert config.enabled is False
    assert config.custom_font_dirs is None


def test_font_config_with_custom_dirs() -> None:
    dirs = ["/usr/share/fonts/custom", "~/my-fonts"]
    config = FontConfig(custom_font_dirs=dirs)
    assert config.enabled is True
    assert config.custom_font_dirs == dirs


def test_font_config_with_all_parameters() -> None:
    dirs = ["/path/to/fonts"]
    config = FontConfig(enabled=True, custom_font_dirs=dirs)
    assert config.enabled is True
    assert config.custom_font_dirs == dirs


def test_font_config_setter_enabled() -> None:
    config = FontConfig()
    config.enabled = False
    assert config.enabled is False


def test_font_config_setter_custom_dirs() -> None:
    config = FontConfig()
    dirs = ["/new/path"]
    config.custom_font_dirs = dirs
    assert config.custom_font_dirs == dirs


def test_font_config_setter_clear_dirs() -> None:
    dirs = ["/path1", "/path2"]
    config = FontConfig(custom_font_dirs=dirs)
    config.custom_font_dirs = None
    assert config.custom_font_dirs is None


def test_font_config_repr() -> None:
    config = FontConfig(enabled=True, custom_font_dirs=["/path1", "/path2"])
    repr_str = repr(config)
    assert "FontConfig" in repr_str
    assert "enabled=True" in repr_str


def test_font_config_repr_no_dirs() -> None:
    config = FontConfig(enabled=False)
    repr_str = repr(config)
    assert "FontConfig" in repr_str
    assert "enabled=False" in repr_str
    assert "None" in repr_str


def test_pdf_config_with_font_config() -> None:
    font_config = FontConfig(enabled=True, custom_font_dirs=["/fonts"])
    pdf_config = PdfConfig(font_config=font_config)
    assert pdf_config.font_config is not None
    assert pdf_config.font_config.enabled is True
    assert pdf_config.font_config.custom_font_dirs == ["/fonts"]


def test_pdf_config_font_config_setter() -> None:
    pdf_config = PdfConfig()
    assert pdf_config.font_config is None

    font_config = FontConfig(enabled=False, custom_font_dirs=["/custom"])
    pdf_config.font_config = font_config
    assert pdf_config.font_config is not None
    assert pdf_config.font_config.enabled is False
    assert pdf_config.font_config.custom_font_dirs == ["/custom"]


def test_pdf_config_font_config_getter() -> None:
    font_config = FontConfig(enabled=True, custom_font_dirs=["/path"])
    pdf_config = PdfConfig(font_config=font_config)
    retrieved = pdf_config.font_config
    assert retrieved is not None
    assert retrieved.enabled is True
    assert retrieved.custom_font_dirs == ["/path"]


def test_pdf_config_clear_font_config() -> None:
    font_config = FontConfig(custom_font_dirs=["/fonts"])
    pdf_config = PdfConfig(font_config=font_config)
    assert pdf_config.font_config is not None

    pdf_config.font_config = None
    assert pdf_config.font_config is None


def test_font_config_multiple_dirs() -> None:
    dirs = ["/path1", "/path2", "/path3", "~/fonts"]
    config = FontConfig(custom_font_dirs=dirs)
    assert config.custom_font_dirs == dirs
    assert len(config.custom_font_dirs) == 4


def test_pdf_config_all_parameters_with_font_config() -> None:
    font_config = FontConfig(enabled=True, custom_font_dirs=["/fonts"])
    pdf_config = PdfConfig(
        extract_images=True,
        passwords=["pass1"],
        extract_metadata=True,
        font_config=font_config,
    )
    assert pdf_config.extract_images is True
    assert pdf_config.passwords == ["pass1"]
    assert pdf_config.extract_metadata is True
    assert pdf_config.font_config is not None
    assert pdf_config.font_config.custom_font_dirs == ["/fonts"]
