#!/usr/bin/env python3
"""
Secrets Validation Script for AI Gatekeeper
Validates that all required secrets and environment variables are properly configured
"""

import os
import sys
import re
from typing import List, Tuple

class SecretsValidator:
    """Validate environment secrets and configuration."""

    # Required secrets for all environments
    REQUIRED_SECRETS = [
        'OPENAI_API_KEY',
        'JWT_SECRET_KEY',
    ]

    # Required secrets for production only
    PRODUCTION_SECRETS = [
        'DATABASE_URL',
    ]

    # Minimum lengths for secrets
    MIN_SECRET_LENGTHS = {
        'JWT_SECRET_KEY': 32,
        'OPENAI_API_KEY': 20,
        'ADMIN_API_KEY': 32,
    }

    # Secret format validators
    SECRET_PATTERNS = {
        'OPENAI_API_KEY': r'^sk-[A-Za-z0-9\-_]+$',
        'DATABASE_URL': r'^postgresql:\/\/',
    }

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.environment = os.getenv('ENVIRONMENT', 'development')

    def validate_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists."""
        value = os.getenv(secret_name)
        if not value or value.strip() == '':
            self.errors.append(f"❌ Missing required secret: {secret_name}")
            return False
        return True

    def validate_secret_length(self, secret_name: str, value: str) -> bool:
        """Check if secret meets minimum length requirement."""
        if secret_name in self.MIN_SECRET_LENGTHS:
            min_length = self.MIN_SECRET_LENGTHS[secret_name]
            if len(value) < min_length:
                self.errors.append(
                    f"❌ Secret {secret_name} is too short "
                    f"(min {min_length} chars, got {len(value)})"
                )
                return False
        return True

    def validate_secret_format(self, secret_name: str, value: str) -> bool:
        """Check if secret matches expected format."""
        if secret_name in self.SECRET_PATTERNS:
            pattern = self.SECRET_PATTERNS[secret_name]
            if not re.match(pattern, value):
                self.errors.append(
                    f"❌ Secret {secret_name} has invalid format "
                    f"(expected pattern: {pattern})"
                )
                return False
        return True

    def check_weak_secrets(self, secret_name: str, value: str):
        """Check for common weak secrets."""
        weak_patterns = [
            'password', 'secret', 'default', 'test', '123',
            'admin', 'gatekeeper', 'changeme'
        ]

        value_lower = value.lower()
        for pattern in weak_patterns:
            if pattern in value_lower:
                self.warnings.append(
                    f"⚠️  Secret {secret_name} may be weak (contains '{pattern}')"
                )
                break

    def validate_api_keys(self):
        """Validate API key configuration."""
        api_key_count = 0
        for key, value in os.environ.items():
            if key.startswith('API_KEY_'):
                api_key_count += 1
                if ':' not in value:
                    self.errors.append(
                        f"❌ API key {key} has invalid format "
                        "(expected format: <key>:<role>)"
                    )
                else:
                    api_key, role = value.split(':', 1)
                    allowed_roles = ['admin', 'operator', 'viewer', 'api_user']
                    if role not in allowed_roles:
                        self.errors.append(
                            f"❌ API key {key} has invalid role '{role}' "
                            f"(allowed: {allowed_roles})"
                        )
                    if len(api_key) < 16:
                        self.errors.append(
                            f"❌ API key {key} is too short (min 16 chars)"
                        )

        if self.environment == 'production' and api_key_count == 0:
            self.errors.append(
                "❌ No API keys configured in production "
                "(set API_KEY_* environment variables)"
            )

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations."""
        print(f"🔍 Validating secrets for environment: {self.environment}")
        print("=" * 60)

        # Check required secrets
        secrets_to_check = self.REQUIRED_SECRETS.copy()
        if self.environment == 'production':
            secrets_to_check.extend(self.PRODUCTION_SECRETS)

        for secret_name in secrets_to_check:
            if self.validate_secret_exists(secret_name):
                value = os.getenv(secret_name)
                self.validate_secret_length(secret_name, value)
                self.validate_secret_format(secret_name, value)
                self.check_weak_secrets(secret_name, value)

        # Validate API keys
        self.validate_api_keys()

        # Check for deprecated/dangerous defaults
        self.check_dangerous_defaults()

        return len(self.errors) == 0, self.errors, self.warnings

    def check_dangerous_defaults(self):
        """Check for dangerous default values that should never be used."""
        dangerous_defaults = {
            'JWT_SECRET_KEY': ['ai-gatekeeper-secret', 'secret', 'your-secret-key'],
            'DEFAULT_API_KEY': ['ai-gatekeeper-default-key'],
            'ADMIN_API_KEY': ['ai-gatekeeper-admin-key', 'admin', 'admin-key'],
        }

        for secret_name, bad_values in dangerous_defaults.items():
            value = os.getenv(secret_name, '')
            if value.lower() in [v.lower() for v in bad_values]:
                self.errors.append(
                    f"❌ CRITICAL: {secret_name} is using a dangerous default value! "
                    "This must be changed immediately."
                )

def validate_secrets() -> bool:
    """Main validation function."""
    validator = SecretsValidator()
    success, errors, warnings = validator.validate_all()

    # Print errors
    if errors:
        print("\n🚨 VALIDATION ERRORS:")
        for error in errors:
            print(f"  {error}")

    # Print warnings
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")

    # Print success
    if success and not warnings:
        print("\n✅ All secrets validated successfully!")
    elif success and warnings:
        print("\n⚠️  Secrets validated with warnings (review recommended)")
    else:
        print("\n❌ Secret validation FAILED!")
        print("\nPlease fix the errors above before proceeding.")
        return False

    print("=" * 60)
    return True

def main():
    """Main entry point."""
    success = validate_secrets()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
