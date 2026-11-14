from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    database_url: str
    bot_username: str = "YourBotUsername"
    bot_display_name: str = "Prime Bot"
    ton_network: str = "testnet"
    escrow_fee_bps: int = 150
    admin_ids: str = ""
    manager_username: str = "korhoul"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

settings = Settings()
