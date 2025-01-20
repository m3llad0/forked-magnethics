from pymongo import MongoClient


class Database:
    """
    A class that provides a convenient interface for interacting with a MongoDB database.

    Args:
        url (str): The URL of the MongoDB server.
        databaseName (str): The name of the selected database.

    Attributes:
        url (str): The URL of the MongoDB server.
        databaseName (str): The name of the selected database.
        client (pymongo.MongoClient): An instance of the `MongoClient` class from the `pymongo` library, representing the connection to the MongoDB server.
        db (pymongo.database.Database): An instance of the `Database` class from the `pymongo` library, representing the selected database.
    """

    def __init__(self, url, databaseName):
        self.url = url
        self.databaseName = databaseName
        self.client = None
        self.db = None

    def connect(self):
        """
        Establishes a connection to the MongoDB server.
        """
        try:

            self.client = MongoClient(self.url)
            self.db = self.client[self.databaseName]
            print("Connected to database!")
        except Exception as e:
            print(f"Error connecting to database: {e}") 

    def get_collection(self, collectionName):
        """
        Retrieves a collection from the selected database with the specified name.

        Args:
            collectionName (str): The name of the collection to retrieve.

        Returns:
            pymongo.collection.Collection: The retrieved collection.
        """
        try:
            if self.db is None:
                self.connect()
            return self.db[collectionName]
        except Exception as e:
            print(f"Error retrieving collection: {e}")
            return None

    def close_collection(self):
        """
        Closes the connection to the MongoDB server.
        """
        if self.client is not None:
            self.client.close()
        