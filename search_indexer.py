import os
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)
from openai import AzureOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        openai_endpoint = get_required_env_var("AZURE_OPENAI_ENDPOINT")
        openai_key = get_required_env_var("AZURE_OPENAI_API_KEY")
        # Embedding deployment name (e.g., text-embedding-ada-002)
        embedding_deployment = get_required_env_var("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        
        search_endpoint = get_required_env_var("AZURE_SEARCH_ENDPOINT")
        search_key = get_required_env_var("AZURE_SEARCH_API_KEY")
        index_name = get_required_env_var("AZURE_SEARCH_INDEX_NAME")

        # Initialize Azure OpenAI Client
        openai_client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-02-01" 
        )

        # Initialize Azure Search Clients
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=AzureKeyCredential(search_key))
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=AzureKeyCredential(search_key))

        # 1. Re-create Index to ensure schema matches
        logger.info(f"Checking if index '{index_name}' exists...")
        if index_name in [name for name in index_client.list_index_names()]:
            logger.info(f"Index '{index_name}' exists. Deleting to ensure schema match...")
            index_client.delete_index(index_name)
        
        logger.info(f"Creating index '{index_name}'...")
            
        # Define Vector Search Configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="myHnsw"
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw",
                    vectorizer_name="myOpenAIVectorizer"
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name="myOpenAIVectorizer",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=openai_endpoint,
                        deployment_name=embedding_deployment,
                        model_name=embedding_deployment, # Required by 2024 preview+ and 2025 versions
                        api_key=openai_key
                    )
                )
            ]
        )

        # Define Schema
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
            # Vector field
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536, # Open AI Ada-002 dimensions
                vector_search_profile_name="myHnswProfile"
            )
        ]

        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        index_client.create_index(index)
        logger.info(f"Index '{index_name}' created successfully.")

        # 2. Process Files
        processed_dir = "processed_data"
        if not os.path.exists(processed_dir):
            logger.error(f"Directory '{processed_dir}' not found.")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        files = [f for f in os.listdir(processed_dir) if f.lower().endswith(".txt")]
        logger.info(f"Found {len(files)} text files in '{processed_dir}'.")

        for filename in files:
            file_path = os.path.join(processed_dir, filename)
            logger.info(f"Processing '{filename}'...")
            
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            # Chunking
            chunks = text_splitter.split_text(text_content)
            logger.info(f"  Split into {len(chunks)} chunks.")

            documents_to_upload = []
            
            for i, chunk in enumerate(chunks):
                # Unique ID for each chunk
                # Using filename (sanitized) + chunk index
                # Ensure ID is safe for Azure Search (letters, numbers, dashes, underscores, =, etc)
                # We'll use a simple hash or safe string.
                # Let's base64 encode or just safe replacements.
                
                # Make a safe ID
                safe_id = f"{filename}_{i}".replace(".", "_").replace(" ", "").replace("-", "_")
                # Alternatively verify regex: ^[a-zA-Z0-9_\-=]+$
                # clean unsafe chars
                import re
                safe_id = re.sub(r'[^a-zA-Z0-9_\-=]', '', safe_id)

                try:
                    # Generate Embedding
                    response = openai_client.embeddings.create(
                        input=chunk,
                        model=embedding_deployment
                    )
                    embedding = response.data[0].embedding

                    # Create Document
                    doc = {
                        "id": safe_id,
                        "content": chunk,
                        "source_file": filename,
                        "embedding": embedding
                    }
                    documents_to_upload.append(doc)
                    
                except Exception as e:
                    logger.error(f"  Error embedding chunk {i}: {e}")
                    continue

            # Upload Batch
            if documents_to_upload:
                try:
                    result = search_client.upload_documents(documents=documents_to_upload)
                    logger.info(f"  Uploaded {len(documents_to_upload)} chunks from '{filename}'.")
                except Exception as e:
                    logger.error(f"  Error uploading documents for '{filename}': {e}")

        logger.info("Indexing complete.")

    except Exception as e:
        logger.critical(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
