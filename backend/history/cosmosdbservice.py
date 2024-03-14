import logging
import os
import uuid
from datetime import datetime
from flask import Flask, request
from azure.identity import DefaultAzureCredential  
from azure.cosmos import CosmosClient, PartitionKey  
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

class CosmosConversationClient():
    
    def __init__(self, cosmosdb_endpoint: str, credential: any, database_name: str, container_name: str, enable_message_feedback: bool = False):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.credential = credential
        self.database_name = database_name
        self.container_name = container_name
        self.cosmosdb_client = CosmosClient(self.cosmosdb_endpoint, credential=credential)
        self.database_client = self.cosmosdb_client.get_database_client(database_name)
        self.container_client = self.database_client.get_container_client(container_name)
        self.enable_message_feedback = enable_message_feedback

    def ensure(self):
        try:
            if not self.cosmosdb_client or not self.database_client or not self.container_client:
                return False
            
            container_info = self.container_client.read()
            if not container_info:
                return False
            
            return True
        except Exception as e:
            logger.exception(f"Exception occurred in cosmosdbservice.py ", e)
            return False

    def create_conversation(self, user_id, title = ''):
        conversation = {
            'id': str(uuid.uuid4()),  
            'type': 'conversation',
            'createdAt': datetime.utcnow().isoformat(),  
            'updatedAt': datetime.utcnow().isoformat(),  
            'userId': user_id,
            'title': title
        }
        ## TODO: add some error handling based on the output of the upsert_item call
        resp = self.container_client.upsert_item(conversation)  
        if resp:
            logger.debug(f"create_conversation response: {resp}")
            return resp
        else:
            logger.debug("No response object returned during create_conversation call")
            return False
    
    def upsert_conversation(self, conversation):
        resp = self.container_client.upsert_item(conversation)
        if resp:
            logger.debug(f"upsert_conversation response: {resp}")
            return resp
        else:
            logger.debug("No response object returned during upsert_conversation call")
            return False

    def delete_conversation(self, user_id, conversation_id):
        conversation = self.container_client.read_item(item=conversation_id, partition_key=user_id)        
        if conversation:
            resp = self.container_client.delete_item(item=conversation_id, partition_key=user_id)
            logger.debug(f"delete_conversation response: {resp}")
            return resp
        else:
            logger.debug("No response object returned during delete_conversation call")
            return True
        
    def delete_messages(self, conversation_id, user_id):
        ## get a list of all the messages in the conversation
        messages = self.get_messages(user_id, conversation_id)
        response_list = []
        if messages:
            for message in messages:
                resp = self.container_client.delete_item(item=message['id'], partition_key=user_id)
                response_list.append(resp)
            return response_list

    def get_conversations(self, user_id, limit, sort_order = 'DESC', offset = 0):
        parameters = [
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c where c.userId = @userId and c.type='conversation' order by c.updatedAt {sort_order}"
        if limit is not None:
            query += f" offset {offset} limit {limit}" 
            
        conversations = list(self.container_client.query_items(query=query, parameters=parameters,
                                                                               enable_cross_partition_query =True))
        ## if no conversations are found, return None
        if len(conversations) == 0:
            logger.debug("No conversations were found.")
            return []
        else:
            logger.debug(f"Conversations found: {conversations}")
            return conversations

    def get_conversation(self, user_id, conversation_id):
        parameters = [
            {
                'name': '@conversationId',
                'value': conversation_id
            },
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c where c.id = @conversationId and c.type='conversation' and c.userId = @userId"
        conversation = list(self.container_client.query_items(query=query, parameters=parameters,
                                                                               enable_cross_partition_query =True))
        ## if no conversations are found, return None
        if len(conversation) == 0:
            logger.debug("No conversation was found.")
            return None
        else:
            logger.debug(f"Conversations found: {conversation[0]}")
            return conversation[0]
 
    def create_message(self, uuid, conversation_id, user_id, input_message: dict):
        message = {
            'id': uuid,
            'type': 'message',
            'userId' : user_id,
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'conversationId' : conversation_id,
            'role': input_message['role'],
            'content': input_message['content']
        }

        if self.enable_message_feedback:
            message['feedback'] = ''
        
        resp = self.container_client.upsert_item(message)  
        if resp:
            logger.debug(f"create_message response: {resp}")
            ## update the parent conversations's updatedAt field with the current message's createdAt datetime value
            conversation = self.get_conversation(user_id, conversation_id)
            conversation['updatedAt'] = message['createdAt']
            self.upsert_conversation(conversation)
            return resp
        else:
            logger.debug("No response returned in create_message")
            return False
    
    def update_message_feedback(self, user_id, message_id, feedback):
        message = self.container_client.read_item(item=message_id, partition_key=user_id)
        if message:
            message['feedback'] = feedback
            resp = self.container_client.upsert_item(message)
            logger.debug(f"update_message_feedback response {resp}")
            return resp
        else:
            logger.debug("No response returned in update_message_feedback")
            return False

    def get_messages(self, user_id, conversation_id):
        parameters = [
            {
                'name': '@conversationId',
                'value': conversation_id
            },
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c WHERE c.conversationId = @conversationId AND c.type='message' AND c.userId = @userId ORDER BY c.timestamp ASC"
        messages = list(self.container_client.query_items(query=query, parameters=parameters,
                                                                     enable_cross_partition_query =True))
        ## if no messages are found, return false
        if len(messages) == 0:
            logger.debug("No messages were found.")
            return []
        else:
            logger.debug(f"Messages found: {messages}")
            return messages

