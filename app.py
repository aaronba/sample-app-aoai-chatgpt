import json
import os
import logging
import requests
from openai import AzureOpenAI
import copy
import uuid
from azure.identity import DefaultAzureCredential
from base64 import b64encode
from flask import Flask, Response, request, jsonify, send_from_directory
from dotenv import load_dotenv
from opencensus.ext.azure.log_exporter import AzureLogHandler

from backend.auth.auth_utils import get_authenticated_user_details
from backend.history.cosmosdbservice import CosmosConversationClient
from backend.usersettings.cosmosdbserviceUserSettings import CosmosUserSettingsClient

load_dotenv()


# UI configuration (optional)
UI_TITLE = os.environ.get("UI_TITLE") or "Contoso"
UI_LOGO = os.environ.get("UI_LOGO")
UI_CHAT_LOGO = os.environ.get("UI_CHAT_LOGO")
UI_CHAT_TITLE = os.environ.get("UI_CHAT_TITLE") or "Start chatting"
UI_CHAT_DESCRIPTION = (
    os.environ.get("UI_CHAT_DESCRIPTION")
    or "This chatbot is configured to answer your questions"
)
UI_FAVICON = os.environ.get("UI_FAVICON") or "/favicon.ico"
UI_SHOW_SHARE_BUTTON = os.environ.get("UI_SHOW_SHARE_BUTTON", "true").lower() == "true"
UI_FOOTER_DISCLAIMER = os.environ.get("UI_FOOTER_DISCLAIMER")
UI_QUESTION_PLACEHOLDER = os.environ.get("UI_QUESTION_PLACEHOLDER") or "Ask a question"   

# Beta Settings
BETA_ENABLED=os.environ.get("BETA_ENABLED", "false").lower() == "true"
BETA_HEADER=os.environ.get("BETA_HEADER", "Beta")



app = Flask(__name__, static_folder="static")

# Static Files
@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/favicon.ico")
def favicon():
    return app.send_static_file('favicon.ico')

@app.route("/assets/<path:path>")
def assets(path):
    return send_from_directory("static/assets", path)

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
    logger.info("Loaded Azure App Insights")
except Exception as e:
    raise Exception(f"Exception initializing Azure App Insights logger: {e}")


# On Your Data Settings
DATASOURCE_TYPE = os.environ.get("DATASOURCE_TYPE", "AzureCognitiveSearch")
SEARCH_TOP_K = os.environ.get("SEARCH_TOP_K", 5)
SEARCH_STRICTNESS = os.environ.get("SEARCH_STRICTNESS", 3)
SEARCH_ENABLE_IN_DOMAIN = os.environ.get("SEARCH_ENABLE_IN_DOMAIN", "true")

# ACS Integration Settings
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX")
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY")
AZURE_SEARCH_USE_SEMANTIC_SEARCH = os.environ.get("AZURE_SEARCH_USE_SEMANTIC_SEARCH", "false")
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG = os.environ.get("AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG", "default")
AZURE_SEARCH_TOP_K = os.environ.get("AZURE_SEARCH_TOP_K", SEARCH_TOP_K)
AZURE_SEARCH_ENABLE_IN_DOMAIN = os.environ.get("AZURE_SEARCH_ENABLE_IN_DOMAIN", SEARCH_ENABLE_IN_DOMAIN)
AZURE_SEARCH_CONTENT_COLUMNS = os.environ.get("AZURE_SEARCH_CONTENT_COLUMNS")
AZURE_SEARCH_FILENAME_COLUMN = os.environ.get("AZURE_SEARCH_FILENAME_COLUMN")
AZURE_SEARCH_TITLE_COLUMN = os.environ.get("AZURE_SEARCH_TITLE_COLUMN")
AZURE_SEARCH_URL_COLUMN = os.environ.get("AZURE_SEARCH_URL_COLUMN")
AZURE_SEARCH_VECTOR_COLUMNS = os.environ.get("AZURE_SEARCH_VECTOR_COLUMNS")
AZURE_SEARCH_QUERY_TYPE = os.environ.get("AZURE_SEARCH_QUERY_TYPE")
AZURE_SEARCH_PERMITTED_GROUPS_COLUMN = os.environ.get("AZURE_SEARCH_PERMITTED_GROUPS_COLUMN")
AZURE_SEARCH_STRICTNESS = os.environ.get("AZURE_SEARCH_STRICTNESS", SEARCH_STRICTNESS)

# AOAI Integration Settings
AZURE_OPENAI_RESOURCE = os.environ.get("AZURE_OPENAI_RESOURCE")
AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_MODEL")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_TEMPERATURE = os.environ.get("AZURE_OPENAI_TEMPERATURE", 0)
AZURE_OPENAI_TOP_P = os.environ.get("AZURE_OPENAI_TOP_P", 1.0)
AZURE_OPENAI_MAX_TOKENS = os.environ.get("AZURE_OPENAI_MAX_TOKENS", 1000)
AZURE_OPENAI_STOP_SEQUENCE = os.environ.get("AZURE_OPENAI_STOP_SEQUENCE")
AZURE_OPENAI_SYSTEM_MESSAGE = os.environ.get("AZURE_OPENAI_SYSTEM_MESSAGE", "You are an AI assistant that helps people find information.")
AZURE_OPENAI_PREVIEW_API_VERSION = os.environ.get("AZURE_OPENAI_PREVIEW_API_VERSION", "2023-08-01-preview")
AZURE_OPENAI_STREAM = os.environ.get("AZURE_OPENAI_STREAM", "true")
AZURE_OPENAI_MODEL_NAME = os.environ.get("AZURE_OPENAI_MODEL_NAME", "gpt-35-turbo-16k") # Name of the model, e.g. 'gpt-35-turbo-16k' or 'gpt-4'
AZURE_OPENAI_EMBEDDING_ENDPOINT = os.environ.get("AZURE_OPENAI_EMBEDDING_ENDPOINT")
AZURE_OPENAI_EMBEDDING_KEY = os.environ.get("AZURE_OPENAI_EMBEDDING_KEY")
AZURE_OPENAI_EMBEDDING_NAME = os.environ.get("AZURE_OPENAI_EMBEDDING_NAME", "")

# CosmosDB Mongo vcore vector db Settings
AZURE_COSMOSDB_MONGO_VCORE_CONNECTION_STRING = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_CONNECTION_STRING")  #This has to be secure string
AZURE_COSMOSDB_MONGO_VCORE_DATABASE = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_DATABASE")
AZURE_COSMOSDB_MONGO_VCORE_CONTAINER = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_CONTAINER")
AZURE_COSMOSDB_MONGO_VCORE_INDEX = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_INDEX")
AZURE_COSMOSDB_MONGO_VCORE_TOP_K = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_TOP_K", AZURE_SEARCH_TOP_K)
AZURE_COSMOSDB_MONGO_VCORE_STRICTNESS = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_STRICTNESS", AZURE_SEARCH_STRICTNESS)  
AZURE_COSMOSDB_MONGO_VCORE_ENABLE_IN_DOMAIN = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_ENABLE_IN_DOMAIN", AZURE_SEARCH_ENABLE_IN_DOMAIN)
AZURE_COSMOSDB_MONGO_VCORE_CONTENT_COLUMNS = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_CONTENT_COLUMNS", "")
AZURE_COSMOSDB_MONGO_VCORE_FILENAME_COLUMN = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_FILENAME_COLUMN")
AZURE_COSMOSDB_MONGO_VCORE_TITLE_COLUMN = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_TITLE_COLUMN")
AZURE_COSMOSDB_MONGO_VCORE_URL_COLUMN = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_URL_COLUMN")
AZURE_COSMOSDB_MONGO_VCORE_VECTOR_COLUMNS = os.environ.get("AZURE_COSMOSDB_MONGO_VCORE_VECTOR_COLUMNS")

SHOULD_STREAM = True if AZURE_OPENAI_STREAM.lower() == "true" else False

# Chat History CosmosDB Integration Settings
AZURE_COSMOSDB_DATABASE = os.environ.get("AZURE_COSMOSDB_DATABASE")
AZURE_COSMOSDB_ACCOUNT = os.environ.get("AZURE_COSMOSDB_ACCOUNT")
AZURE_COSMOSDB_CONVERSATIONS_CONTAINER = os.environ.get("AZURE_COSMOSDB_CONVERSATIONS_CONTAINER")
AZURE_COSMOSDB_USERSETTINGS_CONTAINER = os.environ.get("AZURE_COSMOSDB_USERSETTINGS_CONTAINER")
AZURE_COSMOSDB_ACCOUNT_KEY = os.environ.get("AZURE_COSMOSDB_ACCOUNT_KEY")
AZURE_COSMOSDB_ENABLE_FEEDBACK = os.environ.get("AZURE_COSMOSDB_ENABLE_FEEDBACK", "false").lower() == "true"
AZURE_COSMOSDB_SUFFIX = os.environ.get("AZURE_COSMOSDB_SUFFIX", ".us")

# Elasticsearch Integration Settings
ELASTICSEARCH_ENDPOINT = os.environ.get("ELASTICSEARCH_ENDPOINT")
ELASTICSEARCH_ENCODED_API_KEY = os.environ.get("ELASTICSEARCH_ENCODED_API_KEY")
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX")
ELASTICSEARCH_QUERY_TYPE = os.environ.get("ELASTICSEARCH_QUERY_TYPE", "simple")
ELASTICSEARCH_TOP_K = os.environ.get("ELASTICSEARCH_TOP_K", SEARCH_TOP_K)
ELASTICSEARCH_ENABLE_IN_DOMAIN = os.environ.get("ELASTICSEARCH_ENABLE_IN_DOMAIN", SEARCH_ENABLE_IN_DOMAIN)
ELASTICSEARCH_CONTENT_COLUMNS = os.environ.get("ELASTICSEARCH_CONTENT_COLUMNS")
ELASTICSEARCH_FILENAME_COLUMN = os.environ.get("ELASTICSEARCH_FILENAME_COLUMN")
ELASTICSEARCH_TITLE_COLUMN = os.environ.get("ELASTICSEARCH_TITLE_COLUMN")
ELASTICSEARCH_URL_COLUMN = os.environ.get("ELASTICSEARCH_URL_COLUMN")
ELASTICSEARCH_VECTOR_COLUMNS = os.environ.get("ELASTICSEARCH_VECTOR_COLUMNS")
ELASTICSEARCH_STRICTNESS = os.environ.get("ELASTICSEARCH_STRICTNESS", SEARCH_STRICTNESS)
ELASTICSEARCH_EMBEDDING_MODEL_ID = os.environ.get("ELASTICSEARCH_EMBEDDING_MODEL_ID")

message_uuid = ""

# Initialize a CosmosDB client with AAD auth and containers for Chat History and User Settings
cosmos_conversation_client = None
cosmos_usersettings_client = None

if AZURE_COSMOSDB_DATABASE and AZURE_COSMOSDB_ACCOUNT and AZURE_COSMOSDB_CONVERSATIONS_CONTAINER and AZURE_COSMOSDB_USERSETTINGS_CONTAINER:
    try :
        cosmos_endpoint = f'https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure{AZURE_COSMOSDB_SUFFIX}:443/'
        logger.debug(f"CosmosDB endpoint: {cosmos_endpoint}")

        if not AZURE_COSMOSDB_ACCOUNT_KEY:
            credential = DefaultAzureCredential()
        else:
            credential = AZURE_COSMOSDB_ACCOUNT_KEY

        cosmos_conversation_client = CosmosConversationClient(
            cosmosdb_endpoint=cosmos_endpoint, 
            credential=credential, 
            database_name=AZURE_COSMOSDB_DATABASE,
            container_name=AZURE_COSMOSDB_CONVERSATIONS_CONTAINER,
            enable_message_feedback = AZURE_COSMOSDB_ENABLE_FEEDBACK
        )

        cosmos_usersettings_client = CosmosUserSettingsClient(
            cosmosdb_endpoint=cosmos_endpoint, 
            credential=credential, 
            database_name=AZURE_COSMOSDB_DATABASE,
            container_name=AZURE_COSMOSDB_USERSETTINGS_CONTAINER
        )
    except Exception as e:
        logger.exception("Exception in CosmosDB initialization", e)
        cosmos_conversation_client = None
        cosmos_usersettings_client = None

def is_chat_model():
    if 'gpt-4' in AZURE_OPENAI_MODEL_NAME.lower() or AZURE_OPENAI_MODEL_NAME.lower() in ['gpt-35-turbo-4k', 'gpt-35-turbo-16k']:
        return True
    return False

def should_use_data():
    if AZURE_SEARCH_SERVICE and AZURE_SEARCH_INDEX and AZURE_SEARCH_KEY:
        if DEBUG_LOGGING:
            logger.debug("Using Azure Cognitive Search")
        return True
    
    if AZURE_COSMOSDB_MONGO_VCORE_DATABASE and AZURE_COSMOSDB_MONGO_VCORE_CONTAINER and AZURE_COSMOSDB_MONGO_VCORE_INDEX and AZURE_COSMOSDB_MONGO_VCORE_CONNECTION_STRING:
        if DEBUG_LOGGING:
            logger.debug("Using Azure CosmosDB Mongo vcore")
        return True
    
    return False

def format_as_ndjson(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"

def parse_multi_columns(columns: str) -> list:
    if "|" in columns:
        return columns.split("|")
    else:
        return columns.split(",")

def fetchUserGroups(userToken, nextLink=None):
    # Recursively fetch group membership
    if nextLink:
        endpoint = nextLink
    else:
        endpoint = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf?$select=id"
    
    headers = {
        'Authorization': "bearer " + userToken
    }
    try :
        r = requests.get(endpoint, headers=headers)
        if r.status_code != 200:
            if DEBUG_LOGGING:
                logger.error(f"Error fetching user groups: {r.status_code} {r.text}")
            return []
        
        r = r.json()
        if "@odata.nextLink" in r:
            nextLinkData = fetchUserGroups(userToken, r["@odata.nextLink"])
            r['value'].extend(nextLinkData)
        
        return r['value']
    except Exception as e:
        logger.error(f"Exception in fetchUserGroups: {e}")
        return []


def generateFilterString(userToken):
    # Get list of groups user is a member of
    userGroups = fetchUserGroups(userToken)

    # Construct filter string
    if not userGroups:
        logger.debug("No user groups found")

    group_ids = ", ".join([obj['id'] for obj in userGroups])
    return f"{AZURE_SEARCH_PERMITTED_GROUPS_COLUMN}/any(g:search.in(g, '{group_ids}'))"



def prepare_body_headers_with_data(request):
    request_messages = request.json["messages"]

    body = {
        "messages": request_messages,
        "temperature": float(AZURE_OPENAI_TEMPERATURE),
        "max_tokens": int(AZURE_OPENAI_MAX_TOKENS),
        "top_p": float(AZURE_OPENAI_TOP_P),
        "stop": AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else None,
        "stream": SHOULD_STREAM,
        "dataSources": []
    }

    if DATASOURCE_TYPE == "AzureCognitiveSearch":
        # Set query type
        query_type = "simple"
        if AZURE_SEARCH_QUERY_TYPE:
            query_type = AZURE_SEARCH_QUERY_TYPE
        elif AZURE_SEARCH_USE_SEMANTIC_SEARCH.lower() == "true" and AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG:
            query_type = "semantic"

        # Set filter
        filter = None
        userToken = None
        if AZURE_SEARCH_PERMITTED_GROUPS_COLUMN:
            userToken = request.headers.get('X-MS-TOKEN-AAD-ACCESS-TOKEN', "")
            if DEBUG_LOGGING:
                logger.debug(f"USER TOKEN is {'present' if userToken else 'not present'}")

            filter = generateFilterString(userToken)
            if DEBUG_LOGGING:
                logger.debug(f"FILTER: {filter}")

        body["dataSources"].append(
            {
                "type": "AzureCognitiveSearch",
                "parameters": {
                    "endpoint": f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
                    "key": AZURE_SEARCH_KEY,
                    "indexName": AZURE_SEARCH_INDEX,
                    "fieldsMapping": {
                        "contentFields": parse_multi_columns(AZURE_SEARCH_CONTENT_COLUMNS) if AZURE_SEARCH_CONTENT_COLUMNS else [],
                        "titleField": AZURE_SEARCH_TITLE_COLUMN if AZURE_SEARCH_TITLE_COLUMN else None,
                        "urlField": AZURE_SEARCH_URL_COLUMN if AZURE_SEARCH_URL_COLUMN else None,
                        "filepathField": AZURE_SEARCH_FILENAME_COLUMN if AZURE_SEARCH_FILENAME_COLUMN else None,
                        "vectorFields": parse_multi_columns(AZURE_SEARCH_VECTOR_COLUMNS) if AZURE_SEARCH_VECTOR_COLUMNS else []
                    },
                    "inScope": True if AZURE_SEARCH_ENABLE_IN_DOMAIN.lower() == "true" else False,
                    "topNDocuments": int(AZURE_SEARCH_TOP_K),
                    "queryType": query_type,
                    "semanticConfiguration": AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG if AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG else "",
                    "roleInformation": AZURE_OPENAI_SYSTEM_MESSAGE,
                    "filter": filter,
                    "strictness": int(AZURE_SEARCH_STRICTNESS)
                }
            })
    elif DATASOURCE_TYPE == "AzureCosmosDB":
        # Set query type
        query_type = "vector"

        body["dataSources"].append(
            {
                "type": "AzureCosmosDB",
                "parameters": {
                    "connectionString": AZURE_COSMOSDB_MONGO_VCORE_CONNECTION_STRING,
                    "indexName": AZURE_COSMOSDB_MONGO_VCORE_INDEX,
                    "databaseName": AZURE_COSMOSDB_MONGO_VCORE_DATABASE,
                    "containerName": AZURE_COSMOSDB_MONGO_VCORE_CONTAINER,                    
                    "fieldsMapping": {
                        "contentFields": parse_multi_columns(AZURE_COSMOSDB_MONGO_VCORE_CONTENT_COLUMNS) if AZURE_COSMOSDB_MONGO_VCORE_CONTENT_COLUMNS else [],
                        "titleField": AZURE_COSMOSDB_MONGO_VCORE_TITLE_COLUMN if AZURE_COSMOSDB_MONGO_VCORE_TITLE_COLUMN else None,
                        "urlField": AZURE_COSMOSDB_MONGO_VCORE_URL_COLUMN if AZURE_COSMOSDB_MONGO_VCORE_URL_COLUMN else None,
                        "filepathField": AZURE_COSMOSDB_MONGO_VCORE_FILENAME_COLUMN if AZURE_COSMOSDB_MONGO_VCORE_FILENAME_COLUMN else None,
                        "vectorFields": parse_multi_columns(AZURE_COSMOSDB_MONGO_VCORE_VECTOR_COLUMNS) if AZURE_COSMOSDB_MONGO_VCORE_VECTOR_COLUMNS else []
                    },
                    "inScope": True if AZURE_COSMOSDB_MONGO_VCORE_ENABLE_IN_DOMAIN.lower() == "true" else False,
                    "topNDocuments": int(AZURE_COSMOSDB_MONGO_VCORE_TOP_K),
                    "strictness": int(AZURE_COSMOSDB_MONGO_VCORE_STRICTNESS),
                    "queryType": query_type,
                    "roleInformation": AZURE_OPENAI_SYSTEM_MESSAGE
                }
            }
        )

    elif DATASOURCE_TYPE == "Elasticsearch":
        body["dataSources"].append(
            {
                "messages": request_messages,
                "temperature": float(AZURE_OPENAI_TEMPERATURE),
                "max_tokens": int(AZURE_OPENAI_MAX_TOKENS),
                "top_p": float(AZURE_OPENAI_TOP_P),
                "stop": AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else None,
                "stream": SHOULD_STREAM,
                "dataSources": [
                    {
                        "type": "AzureCognitiveSearch",
                        "parameters": {
                            "endpoint": ELASTICSEARCH_ENDPOINT,
                            "encodedApiKey": ELASTICSEARCH_ENCODED_API_KEY,
                            "indexName": ELASTICSEARCH_INDEX,
                            "fieldsMapping": {
                                "contentFields": parse_multi_columns(ELASTICSEARCH_CONTENT_COLUMNS) if ELASTICSEARCH_CONTENT_COLUMNS else [],
                                "titleField": ELASTICSEARCH_TITLE_COLUMN if ELASTICSEARCH_TITLE_COLUMN else None,
                                "urlField": ELASTICSEARCH_URL_COLUMN if ELASTICSEARCH_URL_COLUMN else None,
                                "filepathField": ELASTICSEARCH_FILENAME_COLUMN if ELASTICSEARCH_FILENAME_COLUMN else None,
                                "vectorFields": parse_multi_columns(ELASTICSEARCH_VECTOR_COLUMNS) if ELASTICSEARCH_VECTOR_COLUMNS else []
                            },
                            "inScope": True if ELASTICSEARCH_ENABLE_IN_DOMAIN.lower() == "true" else False,
                            "topNDocuments": int(ELASTICSEARCH_TOP_K),
                            "queryType": ELASTICSEARCH_QUERY_TYPE,
                            "roleInformation": AZURE_OPENAI_SYSTEM_MESSAGE,
                            "embeddingEndpoint": AZURE_OPENAI_EMBEDDING_ENDPOINT,
                            "embeddingKey": AZURE_OPENAI_EMBEDDING_KEY,
                            "embeddingModelId": ELASTICSEARCH_EMBEDDING_MODEL_ID,
                            "strictness": int(ELASTICSEARCH_STRICTNESS)
                        }
                    }
                ]
            }
        )
    else:
        raise Exception(f"DATASOURCE_TYPE is not configured or unknown: {DATASOURCE_TYPE}")

    if "vector" in query_type.lower():
        if AZURE_OPENAI_EMBEDDING_NAME:
            body["dataSources"][0]["parameters"]["embeddingDeploymentName"] = AZURE_OPENAI_EMBEDDING_NAME
        else:
            body["dataSources"][0]["parameters"]["embeddingEndpoint"] = AZURE_OPENAI_EMBEDDING_ENDPOINT
            body["dataSources"][0]["parameters"]["embeddingKey"] = AZURE_OPENAI_EMBEDDING_KEY

    if DEBUG_LOGGING:
        body_clean = copy.deepcopy(body)
        if body_clean["dataSources"][0]["parameters"].get("key"):
            body_clean["dataSources"][0]["parameters"]["key"] = "*****"
        if body_clean["dataSources"][0]["parameters"].get("connectionString"):
            body_clean["dataSources"][0]["parameters"]["connectionString"] = "*****"
        if body_clean["dataSources"][0]["parameters"].get("embeddingKey"):
            body_clean["dataSources"][0]["parameters"]["embeddingKey"] = "*****"
            
        logger.debug(f"REQUEST BODY: {json.dumps(body_clean, indent=4)}")

    headers = {
        'Content-Type': 'application/json',
        'api-key': AZURE_OPENAI_KEY,
        "x-ms-useragent": "GitHubSampleWebApp/PublicAPI/3.0.0"
    }

    return body, headers


def stream_with_data(body, headers, endpoint, history_metadata={}):
    s = requests.Session()
    try:
        with s.post(endpoint, json=body, headers=headers, stream=True) as r:
            for line in r.iter_lines(chunk_size=10):
                response = {
                    "id": "",
                    "model": "",
                    "created": 0,
                    "object": "",
                    "choices": [{
                        "messages": []
                    }],
                    "apim-request-id": "",
                    'history_metadata': history_metadata
                }
                if line:
                    if AZURE_OPENAI_PREVIEW_API_VERSION == '2023-06-01-preview':
                        lineJson = json.loads(line.lstrip(b'data:').decode('utf-8'))
                    else:
                        try:
                            rawResponse = json.loads(line.lstrip(b'data:').decode('utf-8'))
                            lineJson = formatApiResponseStreaming(rawResponse)
                        except json.decoder.JSONDecodeError:
                            continue

                    if 'error' in lineJson:
                        yield format_as_ndjson(lineJson)
                    response.id = message_uuid
                    response.model = lineJson["model"]
                    response.created = lineJson["created"]
                    response.object = lineJson["object"]
                ## response.apim-request-id = r.headers.get('apim-request-id')

                    role = lineJson["choices"][0]["messages"][0]["delta"].get("role")

                    if role == "tool":
                        response.choices[0].messages.append(lineJson["choices"][0]["messages"][0]["delta"])
                        yield format_as_ndjson(response)
                    elif role == "assistant": 
                        if response.apim-request-id and DEBUG_LOGGING: 
                            logger.debug(f"RESPONSE apim-request-id: {response.apim-request-id}")
                        response.choices[0].messages.append({
                            "role": "assistant",
                            "content": ""
                        })
                        yield format_as_ndjson(response)
                    else:
                        deltaText = lineJson["choices"][0]["messages"][0]["delta"]["content"]
                        if deltaText != "[DONE]":
                            response.choices[0].messages.append({
                                "role": "assistant",
                                "content": deltaText
                            })
                            yield format_as_ndjson(response)
    except Exception as e:
        yield format_as_ndjson({"error" + str(e)})

def formatApiResponseNoStreaming(rawResponse):
    if 'error' in rawResponse:
        return {"error": rawResponse["error"]}
    response = {
        "id": rawResponse["id"],
        "model": rawResponse["model"],
        "created": rawResponse["created"],
        "object": rawResponse["object"],
        "choices": [{
            "messages": []
        }],
    }
    toolMessage = {
        "role": "tool",
        "content": rawResponse["choices"][0]["message"]["context"]["messages"][0]["content"]
    }
    assistantMessage = {
        "role": "assistant",
        "content": rawResponse["choices"][0]["message"]["content"]
    }
    response.choices[0].messages.append(toolMessage)
    response.choices[0].messages.append(assistantMessage)

    return response

def formatApiResponseStreaming(rawResponse):
    if 'error' in rawResponse:
        return {"error": rawResponse["error"]}
    response = {
        "id": rawResponse["id"],
        "model": rawResponse["model"],
        "created": rawResponse["created"],
        "object": rawResponse["object"],
        "choices": [{
            "messages": []
        }],
    }

    if rawResponse["choices"][0]["delta"].get("context"):
        messageObj = {
            "delta": {
                "role": "tool",
                "content": rawResponse["choices"][0]["delta"]["context"]["messages"][0]["content"]
            }
        }
        response.choices[0].messages.append(messageObj)
    elif rawResponse["choices"][0]["delta"].get("role"):
        messageObj = {
            "delta": {
                "role": "assistant",
            }
        }
        response.choices[0].messages.append(messageObj)
    else:
        if rawResponse["choices"][0]["end_turn"]:
            messageObj = {
                "delta": {
                    "content": "[DONE]",
                }
            }
            response.choices[0].messages.append(messageObj)
        else:
            messageObj = {
                "delta": {
                    "content": rawResponse["choices"][0]["delta"]["content"],
                }
            }
            response.choices[0].messages.append(messageObj)

    return response

def conversation_with_data(request_body, model):
    body, headers = prepare_body_headers_with_data(request)
    base_url = AZURE_OPENAI_ENDPOINT if AZURE_OPENAI_ENDPOINT else f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/"
    endpoint = f"{base_url}openai/deployments/{model}/extensions/chat/completions?api-version={AZURE_OPENAI_PREVIEW_API_VERSION}"
    history_metadata = request_body.get("history_metadata", {})

    if not SHOULD_STREAM:
        r = requests.post(endpoint, headers=headers, json=body)
        status_code = r.status_code
        r = r.json()
        if AZURE_OPENAI_PREVIEW_API_VERSION == "2023-06-01-preview":
            r['history_metadata'] = history_metadata
            return Response(format_as_ndjson(r), status=status_code)
        else:
            result = formatApiResponseNoStreaming(r)
            result['history_metadata'] = history_metadata
            return Response(format_as_ndjson(result), status=status_code)

    else:
        return Response(stream_with_data(body, headers, endpoint, history_metadata), mimetype='text/event-stream')

def stream_without_data(response, history_metadata={}):
    for line in response:
        if line.choices:
            deltaText = line.choices[0].delta.content
        else:
            deltaText = ""
        if deltaText and deltaText != "[DONE]":
            responseText = deltaText

            response_obj = {
                "id": message_uuid,
                "model": line.model,
                "created": line.created,
                "object": line.object,
                "choices": [{
                    "messages": [{
                        "role": "assistant",
                        "content": responseText
                    }]
                }],
                "history_metadata": history_metadata
            }
            yield format_as_ndjson(response_obj)

def conversation_without_data(request_body, model):
    client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT if AZURE_OPENAI_ENDPOINT else f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/",
                         azure_deployment=model,
                         api_version=AZURE_OPENAI_PREVIEW_API_VERSION,
                         api_key=AZURE_OPENAI_KEY)

    request_messages = request_body["messages"]
    messages = [
        {
            "role": "system",
            "content": AZURE_OPENAI_SYSTEM_MESSAGE
        }
    ]

    for message in request_messages:
        if message:
            messages.append({
                "role": message["role"] ,
                "content": message["content"]
            })

    response = client.chat.completions.create(model=model, ## user selected in frontend settings
    messages = messages,
    temperature=float(AZURE_OPENAI_TEMPERATURE),
    max_tokens=int(AZURE_OPENAI_MAX_TOKENS),
    top_p=float(AZURE_OPENAI_TOP_P),
    stop=AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else None,
    stream=SHOULD_STREAM)

    history_metadata = request_body.get("history_metadata", {})

    if not SHOULD_STREAM:
        response_obj = {
            "id": message_uuid,
            "model": response.model,
            "created": response.created,
            "object": response.object,
            "choices": [{
                "messages": [{
                    "role": "assistant",
                    "content": response.choices[0].message.content
                }]
            }],
            "history_metadata": history_metadata
        }

        return jsonify(response_obj), 200
    else:
        return Response(stream_without_data(response, history_metadata), mimetype='text/event-stream')

@app.route("/conversation", methods=["GET", "POST"])
def conversation():
    request_body = request.json
    model = request.json.get("model", None);
    return conversation_internal(request_body, model)

def conversation_internal(request_body, model):
    try:
        use_data = should_use_data()
        if use_data:
            return conversation_with_data(request_body, model)
        else:
            return conversation_without_data(request_body, model)
    except Exception as e:
        logger.exception("Exception in /conversation")
        return jsonify({"error": str(e)}), 500

## Conversation History API ## 
@app.route("/history/generate", methods=["POST"])
def add_conversation():
    global message_uuid
    message_uuid = str(uuid.uuid4())
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for conversation_id and Azure OpenAI Model
    conversation_id = request.json.get("conversation_id", None)
    model = request.json.get("model", None);

    try:
        # make sure cosmos is configured
        if not cosmos_conversation_client:
            raise Exception("CosmosDB is not configured")

        # check for the conversation_id, if the conversation is not set, we will create a new one
        history_metadata = {}
        if not conversation_id:
            title = generate_title(request.json["messages"], model)
            conversation_dict = cosmos_conversation_client.create_conversation(user_id=user_id, title=title)
            conversation_id = conversation_dict['id']
            history_metadata['title'] = title
            history_metadata['date'] = conversation_dict['createdAt']
            
        ## Format the incoming message object in the "chat/completions" messages format
        ## then write it to the conversation history in cosmos
        messages = request.json["messages"]
        if len(messages) > 0 and messages[-1]['role'] == "user":
            cosmos_conversation_client.create_message(
                uuid=str(uuid.uuid4()),
                conversation_id=conversation_id,
                user_id=user_id,
                input_message=messages[-1]
            )
        else:
            raise Exception("No user message found")
        
        # Submit request to Chat Completions for response
        request_body = request.json
        history_metadata['conversation_id'] = conversation_id
        request_body['history_metadata'] = history_metadata
        return conversation_internal(request_body, model)
       
    except Exception as e:
        logger.exception("Exception in /history/generate")
        return jsonify({"error": str(e)}), 500


@app.route("/history/update", methods=["POST"])
def update_conversation():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)

    try:
        # make sure cosmos is configured
        if not cosmos_conversation_client:
            raise Exception("CosmosDB is not configured")

        # check for the conversation_id, if the conversation is not set, we will create a new one
        if not conversation_id:
            raise Exception("No conversation_id found")
            
        ## Format the incoming message object in the "chat/completions" messages format
        ## then write it to the conversation history in cosmos
        messages = request.json["messages"]
        if len(messages) > 0 and messages[-1]['role'] == "assistant":
            if len(messages) > 1 and messages[-2].get('role', None) == "tool":
                # write the tool message first
                cosmos_conversation_client.create_message(
                    uuid=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    user_id=user_id,
                    input_message=messages[-2]
                )
            # write the assistant message
            cosmos_conversation_client.create_message(
                uuid=message_uuid,
                conversation_id=conversation_id,
                user_id=user_id,
                input_message=messages[-1]
            )
        else:
            raise Exception("No bot messages found")
        
        # Submit request to Chat Completions for response
        response = {'success': True}
        return jsonify(response), 200
       
    except Exception as e:
        logger.exception("Exception in /history/update")
        return jsonify({"error": str(e)}), 500

@app.route("/history/message_feedback", methods=["POST"])
def update_message():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for message_id
    message_id = request.json.get("message_id", None)
    message_feedback = request.json.get("message_feedback", None)
    try:
        if not message_id:
            return jsonify({"error": "message_id is required"}), 400
        
        if not message_feedback:
            return jsonify({"error": "message_feedback is required"}), 400
        
        ## update the message in cosmos
        updated_message = cosmos_conversation_client.update_message_feedback(user_id, message_id, message_feedback)
        if updated_message:
            return jsonify({"message": f"Successfully updated message with feedback {message_feedback}", "message_id": message_id}), 200
        else:
            return jsonify({"error": f"Unable to update message {message_id}. It either does not exist or the user does not have access to it."}), 404
        
    except Exception as e:
        logger.exception("Exception in /history/message_feedback")
        return jsonify({"error": str(e)}), 500


@app.route("/history/delete", methods=["DELETE"])
def delete_conversation():
    ## get the user id from the request headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']
    
    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    logger.debug(f"{authenticated_user['user_name']} is deleting conversation {conversation_id}")
    try: 
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400
        
        ## delete the conversation messages from cosmos first
        deleted_messages = cosmos_conversation_client.delete_messages(conversation_id, user_id)

        ## Now delete the conversation 
        deleted_conversation = cosmos_conversation_client.delete_conversation(user_id, conversation_id)

        return jsonify({"message": "Successfully deleted conversation and messages", "conversation_id": conversation_id}), 200
    except Exception as e:
        logger.exception("Exception in /history/delete")
        return jsonify({"error": str(e)}), 500

@app.route("/history/list", methods=["GET"])
def list_conversations():
    offset = request.args.get("offset", 0)
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## get the conversations from cosmos
    conversations = cosmos_conversation_client.get_conversations(user_id, offset=offset, limit=25)
    logger.debug(f"{authenticated_user['user_name']} is listing conversations {conversations}")
    if not isinstance(conversations, list):
        return jsonify({"error": f"No conversations for {user_id} were found"}), 404

    ## return the conversation ids

    return jsonify(conversations), 200

@app.route("/history/read", methods=["POST"])
def get_conversation():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    
    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    ## get the conversation object and the related messages from cosmos
    conversation = cosmos_conversation_client.get_conversation(user_id, conversation_id)
    logger.debug(f"{authenticated_user['user_name']} is getting conversation {conversation}")
    ## return the conversation id and the messages in the bot frontend format
    if not conversation:
        return jsonify({"error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."}), 404
    
    # get the messages for the conversation from cosmos
    conversation_messages = cosmos_conversation_client.get_messages(user_id, conversation_id)

    ## format the messages in the bot frontend format
    messages = [{'id': msg['id'], 'role': msg['role'], 'content': msg['content'], 'createdAt': msg['createdAt'], 'feedback': msg.get('feedback')} for msg in conversation_messages]

    return jsonify({"conversation_id": conversation_id, "messages": messages}), 200

@app.route("/history/rename", methods=["POST"])
def rename_conversation():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    
    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400
    
    ## get the conversation from cosmos
    conversation = cosmos_conversation_client.get_conversation(user_id, conversation_id)
    logger.debug(f"{authenticated_user['user_name']} is renaming conversation {conversation}")
    if not conversation:
        return jsonify({"error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."}), 404

    ## update the title
    title = request.json.get("title", None)
    if not title:
        return jsonify({"error": "title is required"}), 400
    conversation['title'] = title
    updated_conversation = cosmos_conversation_client.upsert_conversation(conversation)

    return jsonify(updated_conversation), 200

@app.route("/history/delete_all", methods=["DELETE"])
def delete_all_conversations():
    ## get the user id from the request headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    # get conversations for user
    try:
        conversations = cosmos_conversation_client.get_conversations(user_id, offset=0, limit=None)
        logger.debug(f"{authenticated_user['user_name']} is deleting all conversations {conversations}")
        if not conversations:
            return jsonify({"error": f"No conversations for {user_id} were found"}), 404
        
        # delete each conversation
        for conversation in conversations:
            ## delete the conversation messages from cosmos first
            deleted_messages = cosmos_conversation_client.delete_messages(conversation['id'], user_id)

            ## Now delete the conversation 
            deleted_conversation = cosmos_conversation_client.delete_conversation(user_id, conversation['id'])

        return jsonify({"message": f"Successfully deleted conversation and messages for user {user_id}"}), 200
    
    except Exception as e:
        logger.exception("Exception in /history/delete_all")
        return jsonify({"error": str(e)}), 500
    

@app.route("/history/clear", methods=["POST"])
def clear_messages():
    ## get the user id from the request headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']
    
    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    try: 
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400
        
        logger.debug(f"{authenticated_user['user_name']} is deleting conversation {conversation_id}")
        ## delete the conversation messages from cosmos
        deleted_messages = cosmos_conversation_client.delete_messages(conversation_id, user_id)

        return jsonify({"message": "Successfully deleted messages in conversation", "conversation_id": conversation_id}), 200
    except Exception as e:
        logger.exception("Exception in /history/clear_messages")
        return jsonify({"error": str(e)}), 500

@app.route("/history/ensure", methods=["GET"])
def ensure_cosmos():
    if not AZURE_COSMOSDB_ACCOUNT:
        return jsonify({"error": "CosmosDB is not configured"}), 404
    
    if not cosmos_conversation_client or not cosmos_conversation_client.ensure():
        return jsonify({"error": "CosmosDB is not working"}), 500

    return jsonify({"message": "CosmosDB is configured and working"}), 200

@app.route("/frontend_settings/read", methods=["GET"])  
def read_frontend_settings():
    try:       
        # Default Frontend Settings via Environment Variables
        AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "True") == "True"
        FEEDBACK_ENABLED = AZURE_COSMOSDB_ENABLE_FEEDBACK and AZURE_COSMOSDB_DATABASE not in [None, ""]
        HEADER_TITLE = os.environ.get("HEADER_TITLE", "TryOpenAI")
        PAGE_TAB_TITLE = os.environ.get("PAGE_TAB_TITLE", "TryOpenAI Chat Room")
        AZURE_OPENAI_DEPLOYMENTS = os.environ.get("AZURE_OPENAI_DEPLOYMENTS", "gpt-35-turbo,gpt-4") ## These are available Deployments, not Models in Azure
        AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_MODEL", "gpt-35-turbo")

        if AUTH_ENABLED:
            ## Check if there are any user specific values
            authenticated_user = get_authenticated_user_details(request_headers=request.headers)
            user_id = authenticated_user['user_principal_id']
            logger.debug(f"Retrieving any user settings for {authenticated_user['user_name']}")

            # Retrieve any user settings for this user from cosmos
            user_settings = cosmos_usersettings_client.get_user_settings(user_id)

            if user_settings:
                for setting in user_settings:
                    key = setting['key']
                    match key:
                        case 'AUTH_ENABLED':
                            AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "True") == "True" ## User cannot override
                        case 'FEEDBACK_ENABLED':
                            FEEDBACK_ENABLED = AZURE_COSMOSDB_ENABLE_FEEDBACK and AZURE_COSMOSDB_DATABASE not in [None, ""] ## User cannot override
                        case 'HEADER_TITLE':
                            HEADER_TITLE = os.environ.get("HEADER_TITLE", "TryOpenAI") ## User cannot override
                        case 'PAGE_TAB_TITLE':
                            PAGE_TAB_TITLE = os.environ.get("PAGE_TAB_TITLE", "TryOpenAI Chat Room") ## User cannot override
                        case 'AZURE_OPENAI_MODEL':
                            AZURE_OPENAI_MODEL = setting['value']
        else:
            logger.debug("NOTE!! Authentication is disabled so the user accessing chat is unknown.")

        frontend_settings = { 
            "auth_enabled": AUTH_ENABLED, 
            "feedback_enabled": FEEDBACK_ENABLED,
            "header_title": HEADER_TITLE,
            "page_tab_title": PAGE_TAB_TITLE,
            "azure_openai_deployments": AZURE_OPENAI_DEPLOYMENTS, ## available options for selection by user
            "azure_openai_model": AZURE_OPENAI_MODEL,
            "ui": {
                    "title": UI_TITLE,
                    "logo": UI_LOGO,
                    "chat_logo": UI_CHAT_LOGO or UI_LOGO,
                    "chat_title": UI_CHAT_TITLE,
                    "chat_description": UI_CHAT_DESCRIPTION,
                    "show_share_button": UI_SHOW_SHARE_BUTTON,
                    "show_beta_title": BETA_ENABLED,
                    "beta_title": BETA_HEADER,
                    "footer_disclaimer": UI_FOOTER_DISCLAIMER,
                    "question_input_placeholder": UI_QUESTION_PLACEHOLDER        
                }
            
        }

        return jsonify(frontend_settings), 200
    except Exception as e:
        logger.exception("Exception in /frontend_settings")
        return jsonify({"error": str(e)}), 500  

@app.route("/frontend_settings/write", methods=["POST"]) 
def write_frontend_settings():
    try:
        logger.debug("Handling request to save frontend settings...")

        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user['user_principal_id']

        # Create(upsert) user settings for this user in Cosmos DB
        cosmos_usersettings_client.create_user_setting(user_id, "AUTH_ENABLED", "True" if request.json["AUTH_ENABLED"] else "False")
        cosmos_usersettings_client.create_user_setting(user_id, "FEEDBACK_ENABLED", "True" if request.json["FEEDBACK_ENABLED"] else "False")
        cosmos_usersettings_client.create_user_setting(user_id, "HEADER_TITLE", request.json["HEADER_TITLE"])
        cosmos_usersettings_client.create_user_setting(user_id, "PAGE_TAB_TITLE", request.json["PAGE_TAB_TITLE"])
        cosmos_usersettings_client.create_user_setting(user_id, "AZURE_OPENAI_MODEL", request.json["AZURE_OPENAI_MODEL"])

        logger.debug(f"Frontend settings have been saved by {authenticated_user['user_name']}")

        return jsonify(request.json), 200
    except Exception as e:
        logger.exception("Exception in /frontend_settings_save")
        return jsonify({"error": str(e)}), 500  
    
def generate_title(conversation_messages, model):
    client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT if AZURE_OPENAI_ENDPOINT else f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/",
                        azure_deployment=model,
                        api_version=AZURE_OPENAI_PREVIEW_API_VERSION,
                        api_key=AZURE_OPENAI_KEY)
        
    ## make sure the messages are sorted by _ts descending
    title_prompt = 'Summarize the conversation so far into a 4-word or less title. Do not use any quotation marks or punctuation. Respond with a json object in the format {{"title": string}}. Do not include any other commentary or description.'

    messages = [{'role': msg['role'], 'content': msg['content']} for msg in conversation_messages]
    messages.append({'role': 'user', 'content': title_prompt})

    try:
        ## Submit prompt to Chat Completions for response
        base_url = AZURE_OPENAI_ENDPOINT if AZURE_OPENAI_ENDPOINT else f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/"
        completion = client.chat.completions.create(model=model, ## user selected in frontend settings
        messages=messages,
        temperature=1,
        max_tokens=64)
        title = json.loads(completion.choices[0].message.content).title
        return title
    except Exception as e:
        return messages[-2]['content']

if __name__ == "__main__":
    app.run()
