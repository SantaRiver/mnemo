"""Tests for preprocessor service."""

import pytest

from nlp_service.services.preprocessor import TextPreprocessor


class TestTextPreprocessor:
    """Tests for TextPreprocessor."""

    def test_basic_cleaning(self, preprocessor: TextPreprocessor) -> None:
        """Test basic text cleaning."""
        text = "  Multiple   spaces   here  "
        result = preprocessor.preprocess(text)
        assert result == "Multiple spaces here"

    def test_pii_redaction_email(self, preprocessor: TextPreprocessor) -> None:
        """Test email redaction."""
        text = "Contact me at user@example.com for details"
        result = preprocessor.preprocess(text)
        assert "user@example.com" not in result
        assert "<EMAIL>" in result

    def test_pii_redaction_phone(self, preprocessor: TextPreprocessor) -> None:
        """Test phone number redaction."""
        text = "Call me at +7 999 123-45-67"
        result = preprocessor.preprocess(text)
        assert "+7 999 123-45-67" not in result
        assert "<PHONE>" in result

    def test_pii_redaction_disabled(self) -> None:
        """Test with PII redaction disabled."""
        preprocessor = TextPreprocessor(enabled=False)
        text = "Email: user@example.com Phone: +7 999 123-45-67"
        result = preprocessor.preprocess(text)
        assert "user@example.com" in result
        assert "+7 999 123-45-67" in result

    def test_normalize_text(self, preprocessor: TextPreprocessor) -> None:
        """Test text normalization."""
        text = "Hello, World! How are you?"
        result = preprocessor.normalize_text(text)
        assert result == "hello world how are you"

    def test_split_sentences(self, preprocessor: TextPreprocessor) -> None:
        """Test sentence splitting."""
        text = "Первое предложение. Второе предложение! Третье предложение?"
        sentences = preprocessor.split_sentences(text)
        assert len(sentences) == 3
        assert "Первое предложение" in sentences[0]

    def test_empty_text(self, preprocessor: TextPreprocessor) -> None:
        """Test handling of empty text."""
        result = preprocessor.preprocess("")
        assert result == ""

    def test_excessive_punctuation(self, preprocessor: TextPreprocessor) -> None:
        """Test removal of excessive punctuation."""
        text = "Amazing!!!!! Really?????"
        result = preprocessor.preprocess(text)
        assert result.count("!") <= 3
        assert result.count("?") <= 3
