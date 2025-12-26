"""
Prompt Injection Defense System (TR-014)

Protects against malicious prompt injection attacks where user input
attempts to override system instructions or leak sensitive information.

Defense Layers:
1. Input Sanitization - Remove/escape malicious patterns
2. Dual-Prompt Architecture - Separate system from user data
3. Output Validation - Detect leaked system prompts
4. Keyword Filtering - Block known attack patterns

OWASP LLM01: Prompt Injection
"""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SanitizationResult:
    """Result of input sanitization"""
    sanitized_text: str
    blocked_patterns: List[str]
    is_safe: bool
    severity: str  # low, medium, high, critical


class PromptInjectionDetector:
    """
    Detects and blocks prompt injection attacks

    Attack Types Detected:
    - Instruction Override: "Ignore previous instructions..."
    - Role Manipulation: "You are now a helpful AI that..."
    - System Prompt Leakage: "Repeat your instructions"
    - Data Exfiltration: "Output all client data"
    - Jailbreak Attempts: "DAN mode", "Developer mode"
    """

    # Critical patterns that indicate prompt injection
    CRITICAL_PATTERNS = [
        # Instruction override
        r'ignore\s+(all\s+)?(previous|prior|above|system)\s+instructions',
        r'disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)',
        r'forget\s+(all\s+)?(previous|prior|above|your)\s+(instructions|context|prompt|system)',

        # Role manipulation
        r'you\s+are\s+now\s+(a|an)\s+\w+',
        r'act\s+as\s+(a|an)\s+\w+',
        r'pretend\s+(to\s+be|you\s+are)',
        r'roleplay\s+as',

        # System prompt leakage
        r'repeat\s+(your|the)\s+(instructions|prompt|system\s+message)',
        r'show\s+(me\s+)?(your|the)\s+(instructions|prompt|system\s+prompt)',
        r'what\s+(are|were)\s+your\s+(original\s+)?(instructions|rules)',
        r'print\s+(your|the)\s+system\s+(prompt|message)',

        # Data exfiltration
        r'output\s+(all\s+)?(previous\s+)?(data|clients|keys|secrets)',
        r'list\s+all\s+(clients|users|api\s+keys)',
        r'show\s+(me\s+)?all\s+(client|user|api)\s+(data|keys)',

        # Jailbreak attempts
        r'developer\s+mode',
        r'DAN\s+mode',
        r'jailbreak',
        r'sudo\s+mode',
        r'god\s+mode',
    ]

    # Medium-risk patterns (warnings, but may be legitimate)
    MEDIUM_PATTERNS = [
        # Delimiter confusion
        r'</?system>',
        r'</?user>',
        r'</?assistant>',
        r'\[SYSTEM\]',
        r'\[USER\]',

        # Encoding attempts
        r'base64',
        r'url\s*encode',
        r'rot13',

        # Special characters that might be used for injection
        r'```\s*(?:python|javascript|bash|sql)',  # Code blocks
    ]

    # Low-risk patterns (informational)
    LOW_PATTERNS = [
        # API key patterns (might be legitimate examples)
        r'sk-ant-[a-zA-Z0-9]{40,}',
        r'AWS_SECRET',
        r'API_KEY\s*=',
    ]

    def __init__(self, strict_mode: bool = False):
        """
        Initialize detector

        Args:
            strict_mode: If True, blocks medium-risk patterns too
        """
        self.strict_mode = strict_mode

        # Compile regex patterns for performance
        self.critical_regex = [re.compile(p, re.IGNORECASE) for p in self.CRITICAL_PATTERNS]
        self.medium_regex = [re.compile(p, re.IGNORECASE) for p in self.MEDIUM_PATTERNS]
        self.low_regex = [re.compile(p, re.IGNORECASE) for p in self.LOW_PATTERNS]

    def detect_injection(self, text: str) -> Tuple[bool, List[str], str]:
        """
        Detect prompt injection attempts

        Returns:
            (is_malicious, blocked_patterns, severity)
        """
        blocked_patterns = []
        severity = "low"

        # Check critical patterns
        for pattern in self.critical_regex:
            matches = pattern.findall(text)
            if matches:
                blocked_patterns.extend([f"CRITICAL: {m}" for m in matches])
                severity = "critical"

        # Check medium patterns
        for pattern in self.medium_regex:
            matches = pattern.findall(text)
            if matches:
                blocked_patterns.extend([f"MEDIUM: {m}" for m in matches])
                if severity not in ["critical", "high"]:
                    severity = "medium"

        # Check low patterns
        for pattern in self.low_regex:
            matches = pattern.findall(text)
            if matches:
                blocked_patterns.extend([f"LOW: {m}" for m in matches])
                if severity == "low":
                    severity = "low"

        # Determine if malicious
        is_malicious = severity in ["critical", "high"]
        if self.strict_mode and severity == "medium":
            is_malicious = True

        return is_malicious, blocked_patterns, severity

    def sanitize_input(self, text: str, remove_patterns: bool = True) -> SanitizationResult:
        """
        Sanitize user input to remove/escape malicious patterns

        Args:
            text: User input text
            remove_patterns: If True, removes malicious patterns. If False, escapes them.

        Returns:
            SanitizationResult with sanitized text and metadata
        """
        is_malicious, blocked_patterns, severity = self.detect_injection(text)

        if not is_malicious:
            return SanitizationResult(
                sanitized_text=text,
                blocked_patterns=[],
                is_safe=True,
                severity="safe"
            )

        # Log security event
        logger.warning(
            f"Prompt injection detected (severity={severity}). "
            f"Blocked patterns: {len(blocked_patterns)}"
        )

        # Sanitize by removing or escaping patterns
        sanitized = text

        if remove_patterns:
            # Remove critical patterns entirely
            for pattern in self.critical_regex:
                sanitized = pattern.sub("[REDACTED]", sanitized)

            # Escape medium patterns
            for pattern in self.medium_regex:
                sanitized = pattern.sub(lambda m: f"\\{m.group(0)}", sanitized)
        else:
            # Escape all patterns
            for pattern in self.critical_regex + self.medium_regex:
                sanitized = pattern.sub(lambda m: f"\\{m.group(0)}", sanitized)

        return SanitizationResult(
            sanitized_text=sanitized,
            blocked_patterns=blocked_patterns,
            is_safe=False,  # Original input was malicious
            severity=severity
        )


class OutputValidator:
    """
    Validates LLM outputs to detect leaked system prompts or sensitive data
    """

    # Patterns that indicate system prompt leakage
    LEAKAGE_PATTERNS = [
        r'<system>.*?</system>',
        r'You are an expert content strategist',  # Our system prompt
        r'ANTHROPIC_API_KEY',
        r'sk-ant-[a-zA-Z0-9]{40,}',
        r'Template Structure:',  # Our prompt structure
        r'Client Brief:.*?"company_name"',  # JSON leak
    ]

    # Sensitive data patterns
    SENSITIVE_PATTERNS = [
        r'password\s*[:=]\s*\S+',
        r'secret\s*[:=]\s*\S+',
        r'token\s*[:=]\s*\S+',
    ]

    def __init__(self):
        self.leakage_regex = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.LEAKAGE_PATTERNS]
        self.sensitive_regex = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]

    def validate_output(self, output: str) -> Tuple[bool, List[str]]:
        """
        Validate LLM output for prompt leakage or sensitive data

        Returns:
            (is_safe, violations)
        """
        violations = []

        # Check for system prompt leakage
        for pattern in self.leakage_regex:
            matches = pattern.findall(output)
            if matches:
                violations.extend([f"LEAK: {m[:50]}..." for m in matches])

        # Check for sensitive data
        for pattern in self.sensitive_regex:
            matches = pattern.findall(output)
            if matches:
                violations.extend([f"SENSITIVE: {m}" for m in matches])

        is_safe = len(violations) == 0

        if not is_safe:
            logger.error(
                f"Output validation failed. Violations: {len(violations)}. "
                f"This may indicate prompt injection or data leakage."
            )

        return is_safe, violations


# Convenience functions

_detector = PromptInjectionDetector()
_validator = OutputValidator()


def sanitize_prompt_input(text: str, strict: bool = False) -> str:
    """
    Sanitize user input before including in prompts

    Args:
        text: User input
        strict: If True, blocks medium-risk patterns too

    Returns:
        Sanitized text safe for use in prompts

    Raises:
        ValueError: If critical prompt injection is detected and removal fails
    """
    detector = PromptInjectionDetector(strict_mode=strict)
    result = detector.sanitize_input(text, remove_patterns=True)

    # Re-check if sanitized text still contains critical patterns
    is_still_malicious, _, severity_after = detector.detect_injection(result.sanitized_text)

    if is_still_malicious and severity_after == "critical":
        raise ValueError(
            f"Input contains critical prompt injection patterns that could not be fully sanitized. "
            f"Blocked: {', '.join(result.blocked_patterns[:3])}"
        )

    return result.sanitized_text


def detect_prompt_leakage(output: str) -> bool:
    """
    Check if LLM output contains leaked system prompts or sensitive data

    Args:
        output: LLM-generated text

    Returns:
        True if leakage detected
    """
    is_safe, violations = _validator.validate_output(output)
    return not is_safe


def validate_safe_output(output: str) -> str:
    """
    Validate output and raise error if unsafe

    Args:
        output: LLM-generated text

    Returns:
        Original output if safe

    Raises:
        SecurityError: If prompt leakage detected
    """
    is_safe, violations = _validator.validate_output(output)

    if not is_safe:
        raise SecurityError(
            f"Output validation failed. Detected {len(violations)} security violations. "
            f"First violation: {violations[0] if violations else 'Unknown'}"
        )

    return output


class SecurityError(Exception):
    """Raised when security validation fails"""
    pass
