mport json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "inventorydb"
    groq_api_key: str = ""
    groq_model: str = "mixtral-8x7b-32768"
    cors_origins_json: str = Field(default='["*"]', validation_alias="CORS_ORIGINS")

    @field_validator("mongo_uri")
    def validate_mongo_uri(cls, value: str) -> str:
        if "<" in value or ">" in value:
            raise ValueError(
                "MONGO_URI contains placeholder characters. "
                "Set backend/.env to a valid MongoDB URI, e.g. mongodb://localhost:27017."
            )
        return value

    @property
    def cors_origins(self) -> list[str]:
        try:
            return json.loads(self.cors_origins_json)
        except Exception:
            return ["*"]


settings = Settings()
