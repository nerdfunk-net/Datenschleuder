"""
Settings Manager for OIDC Configuration
Loads and manages OIDC provider configurations from YAML file.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages OIDC provider configuration from YAML file."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize settings manager.

        Args:
            config_path: Path to oidc_providers.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default: config/oidc_providers.yaml (root workspace folder)
            backend_dir = Path(__file__).parent.parent.parent
            workspace_root = backend_dir.parent  # Go up one more level from backend/
            config_path = workspace_root / "config" / "oidc_providers.yaml"

        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load OIDC configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"OIDC config file not found: {self.config_path}")
            self._config = {"providers": {}, "global": {}}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            
            # Ensure required keys exist
            if "providers" not in self._config:
                self._config["providers"] = {}
            if "global" not in self._config:
                self._config["global"] = {}
            
            logger.info(f"Loaded OIDC configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load OIDC configuration: {e}")
            self._config = {"providers": {}, "global": {}}

    def reload_config(self) -> None:
        """Reload configuration from file (useful for runtime updates)."""
        self._load_config()

    def get_oidc_providers(self) -> List[Dict[str, Any]]:
        """
        Get all OIDC providers (enabled and disabled).
        
        Returns:
            List of provider configurations with provider_id included
        """
        if not self._config:
            return []
        
        providers = []
        for provider_id, config in self._config.get("providers", {}).items():
            provider_config = config.copy()
            provider_config["provider_id"] = provider_id
            providers.append(provider_config)
        
        # Sort by display_order
        return sorted(providers, key=lambda p: p.get("display_order", 999))

    def get_enabled_oidc_providers(self) -> List[Dict[str, Any]]:
        """
        Get only enabled OIDC providers.
        
        Returns:
            List of enabled provider configurations sorted by display_order
        """
        if not self._config:
            return []
        
        enabled_providers = []
        for provider_id, config in self._config.get("providers", {}).items():
            if config.get("enabled", False):
                provider_config = config.copy()
                provider_config["provider_id"] = provider_id
                enabled_providers.append(provider_config)
        
        # Sort by display_order
        return sorted(enabled_providers, key=lambda p: p.get("display_order", 999))

    def get_enabled_user_providers(self) -> List[Dict[str, Any]]:
        """
        Get enabled OIDC providers for user login (excludes backend-only providers).
        
        Returns:
            List of enabled user-facing provider configurations sorted by display_order
        """
        if not self._config:
            return []
        
        user_providers = []
        for provider_id, config in self._config.get("providers", {}).items():
            if config.get("enabled", False) and not config.get("backend", False):
                provider_config = config.copy()
                provider_config["provider_id"] = provider_id
                user_providers.append(provider_config)
        
        # Sort by display_order
        return sorted(user_providers, key=lambda p: p.get("display_order", 999))

    def get_backend_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a backend OIDC provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider configuration dict or None if not found or not enabled
        """
        provider_config = self.get_oidc_provider(provider_id)
        if provider_config and provider_config.get("enabled", False):
            return provider_config
        return None

    def get_oidc_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific OIDC provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider configuration dict or None if not found
        """
        if not self._config:
            return None
        
        provider_config = self._config.get("providers", {}).get(provider_id)
        if provider_config:
            config = provider_config.copy()
            config["provider_id"] = provider_id
            return config
        
        return None

    def is_oidc_enabled(self) -> bool:
        """
        Check if OIDC authentication is enabled (at least one provider is enabled).
        
        Returns:
            True if any provider is enabled
        """
        if not self._config:
            return False
        
        providers = self._config.get("providers", {})
        return any(p.get("enabled", False) for p in providers.values())

    def get_oidc_global_settings(self) -> Dict[str, Any]:
        """
        Get global OIDC settings.
        
        Returns:
            Dictionary with global settings (allow_traditional_login, etc.)
        """
        if not self._config:
            return {
                "allow_traditional_login": True,
                "session_timeout": 480,
                "auto_redirect_single_provider": False,
            }
        
        return self._config.get("global", {})


# Singleton instance
settings_manager = SettingsManager()
