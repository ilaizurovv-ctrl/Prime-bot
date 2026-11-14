from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    webhook_secret: str | None = None
    bot_username: str = "PrimeGarantBft_bot"
    bot_display_name: str = "Prime Bot"
    ton_network: str = "testnet"
    escrow_fee_bps: int = 150
    admin_ids: str = "8717928428"
    manager_username: str = "korhoul"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}


settings = Settings()
