from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    NOC_DATABASE: str = "localhost"
    NOC_USERNAME: str = "postgres"
    NOC_PASSWORD: str = "postgres"
    NOC_DATABASE_PORT: int = 5432
    NOC_DATABASE_NAME: str = "noc"
    NOC_DATABASE_SSL: bool = False

    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Default Admin Credentials
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin"

    # OIDC Backend Provider
    # If set, use this OIDC provider from oidc_providers.yaml for backend-to-NiFi authentication
    # Leave empty to use certificate-based authentication
    OIDC_BACKEND_PROVIDER: str = ""

    @property
    def database_url(self) -> str:
        """Construct database URL from configuration"""
        ssl_mode = "require" if self.NOC_DATABASE_SSL else "disable"
        return (
            f"postgresql://{self.NOC_USERNAME}:{self.NOC_PASSWORD}"
            f"@{self.NOC_DATABASE}:{self.NOC_DATABASE_PORT}"
            f"/{self.NOC_DATABASE_NAME}?sslmode={ssl_mode}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
