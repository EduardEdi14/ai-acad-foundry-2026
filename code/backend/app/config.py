"""Application settings — every knob lives in .env, every field here documents one."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- server -------------------------------------------------------------
    api_port: int = 7799

    # --- vector store (Qdrant) ---------------------------------------------
    qdrant_url: str = "http://localhost:7833"
    qdrant_collection: str = "libra_rag"

    # --- chunking defaults (overridable per request) ------------------------
    chunk_strategy: str = "dynamic"        # static | dynamic | sentence | semantic
    chunk_size: int = 500                  # target chunk size, characters
    chunk_overlap: int = 80                # characters carried over between chunks
    sentences_per_chunk: int = 3           # for the 'sentence' strategy
    semantic_threshold: float = 0.75       # cosine cut-off for the 'semantic' strategy

    # --- retrieval / generation defaults ------------------------------------
    top_k: int = 4
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2500   # reasoning models spend part of this budget thinking

    # --- provider selection --------------------------------------------------
    llm_provider: str = "openai"            # lmstudio | openai | anthropic | azure
    embedding_provider: str = "openai"      # lmstudio | openai | azure  (Anthropic has no embeddings API)

    # --- agents ---------------------------------------------------------------
    agent_mode: str = "local"               # local (runs here) | foundry (hosted by Azure)
    agent_persona: str = "default"          # which app/agents/personas/<name>.json to use
    azure_ai_project_endpoint: str = ""     # Foundry portal → project → Overview
    azure_openai_endpoint: str = ""          # the OpenAI-compatible surface of the same resource
    foundry_agent_id: str = ""              # printed by scripts/deploy_agent.py

    # --- Azure AI Search (the managed alternative to the local vector store) ---
    azure_search_endpoint: str = ""          # https://<service>.search.windows.net
    azure_search_index: str = "libra-docs"
    azure_search_key: str = ""               # empty → use the Entra identity instead

    # --- Web search & fact checking --------------------------------------------
    search_provider: str = "auto"            # auto | brave | serper | duckduckgo
    search_api_key: str = ""                 # brave or serper key; empty → scraping only
    web_search_results: int = 5
    fact_check_pages: int = 3                # how many results to actually read

    # --- Azure AI Speech (falls back to the Foundry resource when unset) -------
    azure_speech_key: str = ""
    azure_speech_region: str = ""           # e.g. swedencentral
    azure_speech_voice: str = "en-US-AvaMultilingualNeural"
    azure_speech_language: str = "en-US"

    # --- environment coordinates (used by scripts/, not by the app itself) ----
    azure_resource_group: str = ""
    azure_foundry_resource: str = ""
    azure_foundry_project: str = ""
    azure_location: str = "swedencentral"

    # --- LM Studio (local, free — OpenAI-compatible server) ------------------
    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "google/gemma-3-4b"
    lmstudio_embedding_model: str = "text-embedding-nomic-embed-text-v1.5"

    # --- OpenAI --------------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-nano"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Anthropic (chat only) ----------------------------------------------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # --- Azure Foundry --------------------------------------------------------
    azure_ai_endpoint: str = ""            # https://<resource>.services.ai.azure.com/models
    azure_ai_auth: str = "identity"        # identity (az login / managed identity) | key
    azure_ai_api_key: str = ""             # only when azure_ai_auth=key
    azure_ai_chat_deployment: str = "gpt-5.1"
    azure_ai_embedding_deployment: str = "text-embedding-3-small"


settings = Settings()
