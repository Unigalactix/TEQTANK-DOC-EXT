import os
import json
import logging
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_required_env_var(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

def main():
    try:
        # Configuration
        di_key = get_required_env_var("AZURE_DI_KEY")
        di_endpoint = get_required_env_var("AZURE_DI_ENDPOINT")
        storage_conn_str = get_required_env_var("AZ_STORAGE_STRING")
        container_name = get_required_env_var("AZ_STORAGE_CONTAINER")
        prefix = os.getenv("AZ_STORAGE_PREFIX", "")

        # Initialize clients
        blob_service_client = BlobServiceClient.from_connection_string(storage_conn_str)
        di_client = DocumentIntelligenceClient(endpoint=di_endpoint, credential=AzureKeyCredential(di_key))
        
        container_client = blob_service_client.get_container_client(container_name)

        # Create output directory
        output_dir = "processed_data"
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Connected to container '{container_name}'. Searching for blobs with prefix '{prefix}'...")

        # Iterate through blobs
        blobs = container_client.list_blobs(name_starts_with=prefix)
        for blob in blobs:
            try:
                logger.info(f"Processing: {blob.name}")
                
                # Filter out directories if any (though usually blobs are files)
                if blob.size == 0: 
                     logger.info(f"Skipping empty/directory blob: {blob.name}")
                     continue

                # Download blob content
                blob_client = container_client.get_blob_client(blob)
                blob_data = blob_client.download_blob().readall()

                # Analyze with Document Intelligence
                # Polling logic is handled by the SDK's begin_analyze_document
                # Using 'prebuilt-layout' as requested
                poller = di_client.begin_analyze_document(
                    "prebuilt-layout", 
                    analyze_request=blob_data,
                    content_type="application/octet-stream"
                )
                result = poller.result()

                # Save result to JSON
                # Create a filename safe version of the blob name (replacing / with _)
                safe_filename = blob.name.replace("/", "_") + ".json"
                output_path = os.path.join(output_dir, safe_filename)

                # Serialize the result to JSON
                # The result object is not directly JSON serializable, we need to convert it or use its as_dict method if available
                # Azure SDK models usually have an as_dict method
                result_dict = result.as_dict()
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result_dict, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Saved extracted data to: {output_path}")

            except Exception as e:
                logger.error(f"Failed to process {blob.name}: {e}")
                continue

        logger.info("Ingestion complete.")

    except Exception as e:
        logger.critical(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
