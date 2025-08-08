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
            ollama_model = os.getenv("OLLAMA_MODEL")
            if ollama_model:
                lm = dspy.LM(
                    ollama_model,
                    api_base=os.getenv("OLLAMA_API_BASE") or "",
                    api_key="",
                )
            else:
                raise ValueError("OLLAMA_MODEL is required when USE_OLLAMA is true")
        elif os.getenv("GROK_API_KEY") and os.getenv("GROK_MODEL"):
            grok_model = os.getenv("GROK_MODEL")
            grok_api_key = os.getenv("GROK_API_KEY")
            if grok_model and grok_api_key:
                lm = dspy.LM(grok_model, api_key=grok_api_key)
            else:
                raise ValueError("GROK_MODEL and GROK_API_KEY must be set together")
        elif os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_MODEL"):
            gemini_model = os.getenv("GEMINI_MODEL")
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if gemini_model and gemini_api_key:
                lm = dspy.LM(gemini_model, api_key=gemini_api_key)
            else:
                raise ValueError("GEMINI_MODEL and GEMINI_API_KEY must be set together")
        elif os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"):
            openai_model = os.getenv("OPENAI_MODEL")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_model and openai_api_key:
                lm = dspy.LM(openai_model, api_key=openai_api_key)
            else:
                raise ValueError("OPENAI_MODEL and OPENAI_API_KEY must be set together")
        else:
            raise ValueError("No LLM configured")

        dspy.configure(lm=lm)
        return lm


class AppConfig:
    """General application configuration"""

    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    API_VERSION = "0.1.0"
