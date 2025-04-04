import base64
from backend.settings import app_settings

import os
import asyncio
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions, ContentSettings
from datetime import datetime, timedelta, timezone


async def upload_url_to_blob(base64_image, blob_identifier):
    """
    Uploads a URL to Azure Blob Storage and generates a SAS URL for the blob.

    :param url: The URL to be uploaded as blob content.
    :param conversation_id: The name of the blob to be created.
    :return: A SAS URL for the created blob.
    """
    try:
        # Get account details from environment variables
        connection_string = app_settings.image_file.upload_blob_storage_connection_string
        container_name = app_settings.image_file.upload_blob_storage_container_name

        if not connection_string or not container_name:
            raise ValueError("Missing Azure Storage configuration in environment variables.")

        # Connect to the Blob Service Client
        async with AsyncBlobServiceClient.from_connection_string(connection_string) as blob_service_client:

            # Get the container client
            container_client = blob_service_client.get_container_client(container_name)

            # Upload the URL as blob content with the correct content type
            blob_name = f"{blob_identifier}.png"
            
            blob_client = container_client.get_blob_client(blob_name)

            image_data = base64.b64decode(base64_image)
            await blob_client.upload_blob(image_data, blob_type="BlockBlob", overwrite=True)

            # Generate a SAS URL for the blob
            sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=app_settings.image_file.sas_url_timeout_hours),
            )

            sas_url = f"{blob_client.url}?{sas_token}"
            print (f"Generated SAS URL: {sas_url}")
            return sas_url

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


async def delete_blobs_by_conversation_id(conversation_id):
    """
    Deletes all blobs in Azure Blob Storage whose names start with the given conversation ID.

    :param conversation_id: The conversation ID to filter blobs by.
    """
    try:
        # Get account details from environment variables
        connection_string = app_settings.image_file.upload_blob_storage_connection_string
        container_name = app_settings.image_file.upload_blob_storage_container_name

        if not connection_string or not container_name:
            raise ValueError("Missing Azure Storage configuration in environment variables.")

        # Connect to the Blob Service Client
        async with AsyncBlobServiceClient.from_connection_string(connection_string) as blob_service_client:

            # Get the container client
            container_client = blob_service_client.get_container_client(container_name)

            # List blobs whose names start with the conversation ID
            async for blob in container_client.list_blobs(name_starts_with=conversation_id):
                # Delete each blob
                await container_client.delete_blob(blob.name)
                print(f"Deleted blob: {blob.name}")

    except Exception as e:
        print(f"An error occurred while deleting blobs: {e}")



