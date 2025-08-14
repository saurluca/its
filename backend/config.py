import os
from dotenv import load_dotenv
import dspy

load_dotenv()


class DatabaseConfig:
    """Database configuration settings"""

    @staticmethod
    def get_database_url():
        return f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"


class LLMConfig:
    """Language model configuration"""

    # TODO add test if llm conection works

    @staticmethod
    def configure_dspy():
        if os.getenv("USE_OLLAMA", "False").lower() == "true":
            print("configuring ollama")
            ollama_model = os.getenv("OLLAMA_MODEL")
            if ollama_model:
                lm = dspy.LM(
                    ollama_model,
                    api_base=os.getenv("OLLAMA_API_BASE") or "",
                    api_key="",
                )
            else:
                raise ValueError("OLLAMA_MODEL is required when USE_OLLAMA is true")
        elif os.getenv("USE_AZURE", "False").lower() == "true":
            print("configuring azure")
            azure_model = os.getenv("AZURE_MODEL")
            azure_api_key = os.getenv("AZURE_API_KEY")
            azure_api_base = os.getenv("AZURE_API_BASE")
            if azure_model and azure_api_key and azure_api_base:
                lm = dspy.LM(
                    azure_model,
                    api_base=azure_api_base,
                    api_key=azure_api_key,
                    api_version="2024-12-01-preview",
                )
            else:
                raise ValueError(
                    "AZURE_MODEL, AZURE_API_KEY, and AZURE_API_BASE are required when USE_AZURE is true"
                )
        elif os.getenv("GROK_API_KEY") and os.getenv("GROK_MODEL"):
            print("configuring grok")
            grok_model = os.getenv("GROK_MODEL")
            grok_api_key = os.getenv("GROK_API_KEY")
            if grok_model and grok_api_key:
                lm = dspy.LM(grok_model, api_key=grok_api_key)
            else:
                raise ValueError("GROK_MODEL and GROK_API_KEY must be set together")
        else:
            raise ValueError("No LLM configured")

        dspy.configure(lm=lm)
        return lm


class AppConfig:
    """General application configuration"""

    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    API_VERSION = "0.1.0"
