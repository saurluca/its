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
        if os.getenv("USE_OLLAMA", "False").lower() == "true" and os.getenv(
            "OLLAMA_MODEL"
        ):
            lm = dspy.LM(
                os.getenv("OLLAMA_MODEL"),
                api_base=os.getenv("OLLAMA_API_BASE"),
                api_key="",
            )
        elif os.getenv("GROK_API_KEY") and os.getenv("GROK_MODEL"):
            lm = dspy.LM(os.getenv("GROK_MODEL"), api_key=os.getenv("GROK_API_KEY"))
        elif os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_MODEL"):
            lm = dspy.LM(
                os.getenv("GEMINI_MODEL"),
                api_key=os.getenv("GEMINI_API_KEY"),
            )
        elif os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"):
            lm = dspy.LM(
                os.getenv("OPENAI_MODEL"),
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        else:
            raise ValueError("No LLM configured")

        dspy.configure(lm=lm)
        return lm


class AppConfig:
    """General application configuration"""

    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    API_VERSION = "0.1.0"
