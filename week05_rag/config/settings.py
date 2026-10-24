"""Application settings loader resolving .env and config.yaml."""

from pathlib import Path
from typing import Any, Dict
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Hierarchical configuration model with environment fallback."""

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys & Tracing (sourced from .env / environment)
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    langchain_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langchain_tracing_v2: str = Field(default="true", alias="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field(default="week5-mft-edi-rag", alias="LANGCHAIN_PROJECT")

    # Ingestion & Retrieval configs (sourced from config.yaml defaults)
    chunk_size: int = 512
    chunk_overlap: int = 64
    k_retrieval: int = 3
    mmr_lambda: float = 0.4
    chroma_db_dir: str = "./chroma_db"
    collection_name: str = "mft_edi_knowledge_base"
    data_dir: str = "./data"

    # LLM Settings
    model_id: str = "claude-sonnet-5-5"
    max_tokens: int = 4096
    thinking_budget_tokens: int = 1024

    @classmethod
    def load_from_yaml(cls, yaml_path: str = "config.yaml") -> "AppConfig":
        """Factory method populating settings from YAML prior to env overlays."""
        config_data: Dict[str, Any] = {}
        path = Path(yaml_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as file:
                raw_yaml = yaml.safe_load(file)
                if raw_yaml:
                    rag_cfg = raw_yaml.get("rag", {})
                    llm_cfg = raw_yaml.get("llm", {})
                    config_data.update(rag_cfg)
                    config_data.update(llm_cfg)
        return cls(**config_data)


# Global singleton instance
settings = AppConfig.load_from_yaml()