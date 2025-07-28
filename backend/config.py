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

    @staticmethod
    def configure_dspy():
        # lm = dspy.LM(
        #     "groq/deepseek-r1-distill-llama-70b", api_key=os.getenv("GROQ_API_KEY")
        # )
        lm = dspy.LM(
            "ollama_chat/llama3.2", api_base="http://localhost:11434", api_key="test"
        )
        dspy.configure(lm=lm)
        return lm


class AppConfig:
    """General application configuration"""

    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    API_VERSION = "0.1.0"
