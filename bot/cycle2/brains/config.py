from mem0.configs.base import MemoryConfig, LlmConfig, EmbedderConfig, VectorStoreConfig


from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_URL: str = "http://127.0.0.1:7071/bot"
    DB_URI: SecretStr
    DB_URIP: SecretStr
    DB_NAME: str = "postgres"
    DB_USER: str = "possu"
    DB_PASSWORD: SecretStr
    DB_HOST: str = "127.0.0.1"
    DB_PORT: str = "5432"
    REDIS_URI: str = "redis://127.0.0.1:6379/0"
    MASTER_KEY: SecretStr
    DJANGO_SECRET_KEY: SecretStr
    LANGSMITH_API_KEY: SecretStr
    OPENAI_API_KEY: SecretStr
    TAVILY_API_KEY: SecretStr
    LANGCHAIN_TRACING_V2: bool = True

settings = Settings()

MEM0CONF = MemoryConfig(
    llm=LlmConfig(
        provider="openai",
        config={
            "model": "gpt-4.1-nano",
            "temperature": 0.2,
            "max_tokens": 2000,
        }
    ),
    vector_store=VectorStoreConfig(
        provider="pgvector",
        config={
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD.get_secret_value(),
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
        }
    ),
    embedder=EmbedderConfig(
        provider="openai",
        config={
            "model": "text-embedding-3-small"
        }
    ),
)