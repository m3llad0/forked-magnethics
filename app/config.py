import os
from dotenv import load_dotenv
# from supertokens_python import init
# from supertokens_python.recipe import session, passwordless
# from supertokens_python.supertokens import InputAppInfo, SupertokensConfig

load_dotenv()

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
    SUPERTOKENS_URI = os.getenv("SUPERTOKENS_URI")
    API_DOMAIN = os.getenv("API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN")

class DevelopmentConfig(BaseConfig):
    FLASK_ENV = "development"
    MONGO_URI = os.getenv("DEV_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URI")
    SUPERTOKENS_URI = os.getenv("DEV_SUPERTOKENS_URI")
    API_DOMAIN = os.getenv("DEV_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("DEV_WEBSITE_DOMAIN")

class TestConfig(BaseConfig):
    FLASK_ENV = "testing"
    MONGO_URI = os.getenv("TEST_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URI")
    SUPERTOKENS_URI = os.getenv("TEST_SUPERTOKENS_URI")
    API_DOMAIN = os.getenv("TEST_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("TEST_WEBSITE_DOMAIN")

class StageConfig(BaseConfig):
    FLASK_ENV = "staging"
    MONGO_URI = os.getenv("STAGE_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("STAGE_DATABASE_URI")
    SUPERTOKENS_URI = os.getenv("STAGE_SUPERTOKENS_URI")
    API_DOMAIN = os.getenv("STAGE_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("STAGE_WEBSITE_DOMAIN")

class ProdConfig(BaseConfig):
    FLASK_ENV = "production"
    MONGO_URI = os.getenv("PROD_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DATABASE_URI")
    SUPERTOKENS_URI = os.getenv("PROD_SUPERTOKENS_URI")
    API_DOMAIN = os.getenv("PROD_API_DOMAIN")
    WEBSITE_DOMAIN = os.getenv("PROD_WEBSITE_DOMAIN")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestConfig,
    "staging": StageConfig,
    "production": ProdConfig
}

def get_config(env_name):
    """Retrieve the config class based on the environment."""
    return config_by_name.get(env_name, ProdConfig)  # Default to production

# SuperTokens Initialization
# config = get_config(os.getenv("FLASK_ENV", "production"))

# init(
#     app_info=InputAppInfo(
#         app_name="My SaaS App",
#         api_domain=config.API_DOMAIN,
#         website_domain=config.WEBSITE_DOMAIN,
#     ),
#     supertokens_config=SupertokensConfig(
#         connection_uri=config.SUPERTOKENS_URI,
#     ),
#     recipe_list=[
#         session.init(),
#         passwordless.init(contact_method="EMAIL_OTP"),  # OTP via email
#     ],
# )
