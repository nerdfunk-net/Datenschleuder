#!/usr/bin/env python3
"""
Test script to verify OIDC backend configuration loading
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.settings_manager import settings_manager


def test_oidc_backend_config():
    """Test OIDC backend configuration loading"""
    
    print("=" * 70)
    print("OIDC Backend Configuration Test")
    print("=" * 70)
    print()
    
    # Test 1: Check OIDC_BACKEND_PROVIDER setting
    print("1. Environment Configuration:")
    print(f"   OIDC_BACKEND_PROVIDER: '{settings.OIDC_BACKEND_PROVIDER}'")
    print()
    
    # Test 2: Load all providers
    print("2. All OIDC Providers:")
    all_providers = settings_manager.get_oidc_providers()
    if not all_providers:
        print("   ⚠️  No providers found in oidc_providers.yaml")
    else:
        for provider in all_providers:
            provider_id = provider.get("provider_id")
            enabled = provider.get("enabled", False)
            backend = provider.get("backend", False)
            name = provider.get("name", provider_id)
            print(f"   - {provider_id}:")
            print(f"     Name: {name}")
            print(f"     Enabled: {enabled}")
            print(f"     Backend-only: {backend}")
    print()
    
    # Test 3: User-facing providers (should exclude backend=true)
    print("3. User-Facing Providers (shown on login page):")
    user_providers = settings_manager.get_enabled_user_providers()
    if not user_providers:
        print("   ℹ️  No user-facing providers enabled")
    else:
        for provider in user_providers:
            provider_id = provider.get("provider_id")
            name = provider.get("name", provider_id)
            print(f"   - {provider_id}: {name}")
    print()
    
    # Test 4: Backend provider lookup
    print("4. Backend Provider Configuration:")
    if settings.OIDC_BACKEND_PROVIDER:
        backend_provider = settings_manager.get_backend_provider(
            settings.OIDC_BACKEND_PROVIDER
        )
        if backend_provider:
            print(f"   ✅ Found backend provider: {settings.OIDC_BACKEND_PROVIDER}")
            print(f"   Provider name: {backend_provider.get('name')}")
            print(f"   Discovery URL: {backend_provider.get('discovery_url')}")
            print(f"   Client ID: {backend_provider.get('client_id')}")
            print(f"   Client Secret: {'***' if backend_provider.get('client_secret') else 'NOT SET'}")
        else:
            print(f"   ❌ Backend provider '{settings.OIDC_BACKEND_PROVIDER}' not found or not enabled")
    else:
        print("   ℹ️  No backend provider configured (using certificate/username auth)")
    print()
    
    # Test 5: Validation
    print("5. Configuration Validation:")
    errors = []
    warnings = []
    
    # Check if OIDC_BACKEND_PROVIDER is set but provider doesn't exist
    if settings.OIDC_BACKEND_PROVIDER:
        backend_provider = settings_manager.get_backend_provider(
            settings.OIDC_BACKEND_PROVIDER
        )
        if not backend_provider:
            errors.append(
                f"OIDC_BACKEND_PROVIDER is set to '{settings.OIDC_BACKEND_PROVIDER}' "
                "but provider not found or not enabled in oidc_providers.yaml"
            )
        else:
            # Validate required fields
            if not backend_provider.get("discovery_url"):
                errors.append(f"Provider '{settings.OIDC_BACKEND_PROVIDER}' missing discovery_url")
            if not backend_provider.get("client_id"):
                errors.append(f"Provider '{settings.OIDC_BACKEND_PROVIDER}' missing client_id")
            if not backend_provider.get("client_secret"):
                errors.append(f"Provider '{settings.OIDC_BACKEND_PROVIDER}' missing client_secret")
    
    # Check for providers marked as backend but also shown to users
    for provider in all_providers:
        if provider.get("enabled") and provider.get("backend"):
            if provider in user_providers:
                warnings.append(
                    f"Provider '{provider.get('provider_id')}' is marked as backend=true "
                    "but still appears in user-facing providers"
                )
    
    if errors:
        print("   ❌ Errors found:")
        for error in errors:
            print(f"      - {error}")
    
    if warnings:
        print("   ⚠️  Warnings:")
        for warning in warnings:
            print(f"      - {warning}")
    
    if not errors and not warnings:
        print("   ✅ Configuration is valid")
    
    print()
    print("=" * 70)
    
    return len(errors) == 0


if __name__ == "__main__":
    success = test_oidc_backend_config()
    sys.exit(0 if success else 1)
