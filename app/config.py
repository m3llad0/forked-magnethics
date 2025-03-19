import os
from dotenv import load_dotenv
from clerk_backend_api import Clerk
from app.utils import logger
load_dotenv()

def format_pem_key(key_str: str):
    return key_str.replace('\\n', '\n')


class BaseConfig:
    FLASK_ENV = os.getenv("FLASK_ENV")
    MONGO_URI = os.getenv("MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "ssl": {
                "ca": os.getenv("SSL_CA")
            }
        }
    }
    API_DOMAIN = os.getenv("API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN")
    CLERK_PEM_PUBLIC_KEY = format_pem_key(os.getenv("CLERK_PEM_PUBLIC_KEY", ""))
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")

class DevelopmentConfig(BaseConfig):
    FLASK_ENV = "development"
    MONGO_URI = os.getenv("DEV_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URI")
    API_DOMAIN = os.getenv("DEV_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("DEV_WEBSITE_DOMAIN")
    CLERK_PEM_PUBLIC_KEY = format_pem_key(os.getenv("DEV_CLERK_PEM_PUBLIC_KEY", ""))
    CLERK_SECRET_KEY = os.getenv("DEV_CLERK_SECRET_KEY")

class TestConfig(BaseConfig):
    FLASK_ENV = "testing"
    MONGO_URI = os.getenv("TEST_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URI")
    API_DOMAIN = os.getenv("TEST_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("TEST_WEBSITE_DOMAIN")
    CLERK_PEM_PUBLIC_KEY = format_pem_key(os.getenv("TEST_CLERK_PEM_PUBLIC_KEY", ""))
    CLERK_SECRET_KEY = os.getenv("TEST_CLERK_SECRET_KEY")
    CLERK_FRONTEND_API = os.getenv("TEST_CLERK_FRONTEND_API")

class StageConfig(BaseConfig):
    FLASK_ENV = "staging"
    MONGO_URI = os.getenv("STAGE_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("STAGE_DATABASE_URI")
    API_DOMAIN = os.getenv("STAGE_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("STAGE_WEBSITE_DOMAIN")
    CLERK_PEM_PUBLIC_KEY = format_pem_key(os.getenv("STAGE_CLERK_PEM_PUBLIC_KEY", ""))
    CLERK_SECRET_KEY = os.getenv("STAGE_CLERK_SECRET_KEY")
    CLERK_FRONTEND_API = os.getenv("STAGE_CLERK_FRONTEND_API")

class ProdConfig(BaseConfig):
    FLASK_ENV = "production"
    MONGO_URI = os.getenv("PROD_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DATABASE_URI")
    API_DOMAIN = os.getenv("PROD_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("PROD_WEBSITE_DOMAIN")
    CLERK_PEM_PUBLIC_KEY = format_pem_key(os.getenv("PROD_CLERK_PEM_PUBLIC_KEY", ""))
    CLERK_SECRET_KEY = os.getenv("PROD_CLERK_SECRET_KEY")
    CLERK_FRONTEND_API = os.getenv("PROD_CLERK_FRONTEND_API")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestConfig,
    "staging": StageConfig,
    "production": ProdConfig,
}

def get_config(env_name):
    """Retrieve the config class based on the environment."""
    return config_by_name.get(env_name, ProdConfig)

# Create a global Clerk client using the environment-specific configuration.
def get_clerk_client()-> Clerk:
    """Create a Clerk client using the environment-specific configuration."""
    try:
        config = get_config(os.getenv("FLASK_ENV"))
        clerk_client = Clerk(
        config.CLERK_SECRET_KEY
    )
        logger.info("Clerk client created successfully.")
        return clerk_client
        
    except Exception as e:
        logger.error(f"Error creating Clerk client: {e}")


# Global instance of the Clerk client
CLERK_CLIENT = get_clerk_client()

