"""Text preprocessing and PII redaction service."""

import re
from typing import List, Tuple

import phonenumbers


class TextPreprocessor:
    """Service for preprocessing text and redacting PII."""

    def __init__(self, enabled: bool = True) -> None:
        """Initialize preprocessor.
        
        Args:
            enabled: Whether PII redaction is enabled
        """
        self.enabled = enabled
        self._email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self._phone_pattern = re.compile(
            r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        )
        # Simple Russian passport/ID patterns
        self._passport_pattern = re.compile(
            r'\b\d{4}\s?\d{6}\b'
        )
        # Credit card pattern
        self._card_pattern = re.compile(
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        )
        # Russian INN (taxpayer identification number)
        self._inn_pattern = re.compile(
            r'\b\d{10,12}\b'
        )

    def preprocess(self, text: str) -> str:
        """Preprocess text with cleaning and PII redaction.
        
        Args:
            text: Raw text input
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""

        # Basic cleaning
        text = self._clean_text(text)
        
        # PII redaction
        if self.enabled:
            text = self._redact_pii(text)
        
        return text

    def _clean_text(self, text: str) -> str:
        """Clean text by normalizing whitespace and special characters.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive punctuation (more than 3 in a row)
        text = re.sub(r'([!?.,]){4,}', r'\1\1\1', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text

    def _redact_pii(self, text: str) -> str:
        """Redact personally identifiable information.
        
        Args:
            text: Input text
            
        Returns:
            Text with PII redacted
        """
        # Redact emails
        text = self._email_pattern.sub('<EMAIL>', text)
        
        # Redact phone numbers
        text = self._redact_phone_numbers(text)
        
        # Redact passport numbers
        text = self._passport_pattern.sub('<PASSPORT>', text)
        
        # Redact credit card numbers
        text = self._card_pattern.sub('<CARD>', text)
        
        # Redact INN (but be careful not to redact normal numbers)
        # Only redact if it's standalone
        text = re.sub(r'\bИНН:?\s*\d{10,12}\b', '<INN>', text, flags=re.IGNORECASE)
        
        return text

    def _redact_phone_numbers(self, text: str) -> str:
        """Redact phone numbers using phonenumbers library.
        
        Args:
            text: Input text
            
        Returns:
            Text with phone numbers redacted
        """
        # Try to parse Russian phone numbers
        try:
            for match in phonenumbers.PhoneNumberMatcher(text, "RU"):
                phone_str = text[match.start:match.end]
                text = text.replace(phone_str, '<PHONE>')
        except Exception:
            # Fallback to regex if phonenumbers fails
            text = self._phone_pattern.sub('<PHONE>', text)
        
        return text

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting for Russian text
        # Split on period, exclamation, question mark followed by space and capital letter
        sentences = re.split(r'[.!?]+\s+(?=[А-ЯA-Z])', text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison/matching.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        # Lowercase
        text = text.lower()
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip
        text = text.strip()
        
        return text
