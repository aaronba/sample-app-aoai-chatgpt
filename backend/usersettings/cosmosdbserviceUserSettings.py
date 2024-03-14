import logging
import os
import uuid
from datetime import datetime
from azure.cosmos import CosmosClient
from opencensus.ext.azure.log_exporter import AzureLogHandler

# Debug settings
DEBUG = os.environ.get("DEBUG", "false")
DEBUG_LOGGING = DEBUG.lower() == "true"
if DEBUG_LOGGING:
    logging.basicConfig(level=logging.DEBUG)

# Set up Azure App Insights logger
try:
    app_insights_conn_str = os.environ.get("AZURE_APP_INSIGHTS_CONNECTION_STRING", "")
    logger = logging.getLogger(__name__)
    handler = AzureLogHandler(connection_string=app_insights_conn_str)
    logger.addHandler(handler)
    if DEBUG_LOGGING:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.info("Loaded Azure App Insights for CosmosDB service")
except Exception as e:
    raise Exception(f"Exception initializing Azure App Insights logger: {e}")

class CosmosUserSettingsClient():
    
    def __init__(self, cosmosdb_endpoint: str, credential: any, database_name: str, container_name: str):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.credential = credential
        self.database_name = database_name
        self.container_name = container_name
        self.cosmosdb_client = CosmosClient(self.cosmosdb_endpoint, credential=credential)
        self.database_client = self.cosmosdb_client.get_database_client(database_name)
        self.container_client = self.database_client.get_container_client(container_name)

    def ensure(self):
        try:
            if not self.cosmosdb_client or not self.database_client or not self.container_client:
                return False
            
            container_info = self.container_client.read()
            if not container_info:
                return False
            
            return True
        except:
            return False

    def create_user_setting(self, user_id, key, value):
        userSetting = {
            'id': str(uuid.uuid4()),  
            'type': 'usersetting',
            'createdAt': datetime.utcnow().isoformat(),  
            'updatedAt': datetime.utcnow().isoformat(),  
            'userId': user_id,
            'key': key,
            'value': value
        }

        resp = self.container_client.upsert_item(userSetting)  
        if resp:
            logger.debug(f"Response object in create_user_setting: {resp}")
            return resp
        else:
            logger.debug("No response returned in create_user_setting")
            return False
    
    def upsert_user_setting(self, userSetting):
        resp = self.container_client.upsert_item(userSetting)
        if resp:
            logger.debug(f"Response object in upsert_user_setting: {resp}")
            return resp
        else:
            logger.debug("No response returned in upsert_user_setting")
            return False

    def get_user_settings(self, user_id):
        try:
            parameters = [
                {
                    'name': '@userId',
                    'value': user_id
                }
            ]
            query = f"SELECT * FROM c where c.userId = @userId"
            userSettings = list(self.container_client.query_items(query=query, parameters=parameters,
                                                                enable_cross_partition_query =True))
            ## if no settings are found, return None
            if len(userSettings) == 0:
                logger.debug("No user frontend settings found.")
                return None
            else:
                logger.debug(f"Frontend user settings found: {userSettings}")

            return userSettings
        except:
            return None
 
    def delete_user_setting(self, user_id, usersetting_id):
        userSetting = self.container_client.read_item(item=usersetting_id, partition_key=user_id)        
        if userSetting:
            resp = self.container_client.delete_item(item=usersetting_id, partition_key=user_id)
            logger.debug(f"Response object from deleting user setting: {resp}")
            return resp
        else:
            logger.debug("No response object returned on delete user setting attempt.")
            return True


