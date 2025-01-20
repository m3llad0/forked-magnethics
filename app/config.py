import os
from dotenv import load_dotenv

load_dotenv()

class DevelopmentConfig():
    FLASK_ENV = os.getenv("FLASK_ENV")
    MONGO_URI = os.getenv("DEV_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "ssl": {
            "ca": os.getenv("DEV_SSLA_CA")
        }
    }
}
    
class TestConfig():
    FLASK_ENV = os.getenv("FLASK_ENV")
    MONGO_URI = os.getenv("TEST_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "ssl": {
            "ca": os.getenv("TEST_SSLA_CA")
        }
    }
}
    
class StageConfig():
    FLASK_ENV = os.getenv("FLASK_ENV")
    MONGO_URI = os.getenv("STAGE_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("STAGE_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "ssl": {
            "ca": os.getenv("STAGE_SSLA_CA")
        }
    }
}
    
class ProdConfig():
    FLASK_ENV = os.getenv("FLASK_ENV")
    MONGO_URI = os.getenv("PROD_MONGODB_URI")
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "ssl": {
            "ca": os.getenv("PROD_SSLA_CA")
        }
    }
}


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestConfig,
    "staging": StageConfig,
    "production": ProdConfig
}

def get_config(env_name):
    """Retrieve the config class based on the environment."""
    return config_by_name.get(env_name, ProdConfig)  # Default to production