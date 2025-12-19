import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

# 1. Load Environment Variables
load_dotenv()

def get_required_env_var(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

# Azure AI Search Configuration
SEARCH_ENDPOINT = get_required_env_var("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = get_required_env_var("AZURE_SEARCH_API_KEY")
INDEX_NAME = get_required_env_var("AZURE_SEARCH_INDEX_NAME")

# Azure OpenAI Configuration (for Embeddings)
AZURE_OPENAI_ENDPOINT = get_required_env_var("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = get_required_env_var("AZURE_OPENAI_API_KEY")
EMBEDDING_DEPLOYMENT = get_required_env_var("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = "2024-02-01" 

def get_embedding(text):
    """Generates a vector embedding for the query text."""
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )
    
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_DEPLOYMENT
    )
    return response.data[0].embedding

def search_index(query_text):
    """Searches the index using Vector Search."""
    print(f"\n--- Searching for: '{query_text}' ---")
    
    # 1. Generate Vector for the query
    try:
        query_vector = get_embedding(query_text)
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return

    # 2. Initialize Search Client
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    # 3. Execute Vector Search
    # We ask for the top 3 nearest neighbors (k=3)
    vector_query = VectorizedQuery(
        vector=query_vector, 
        k_nearest_neighbors=3, 
        fields="embedding"  # MATCHED: Field name in search_indexer.py is "embedding"
    )

    try:
        results = search_client.search(
            search_text=None,  # No keyword search, purely vector
            vector_queries=[vector_query],
            select=["id", "content", "source_file"] # MATCHED: Field name in search_indexer.py is "source_file"
        )

        # 4. Print Results
        count = 0
        for result in results:
            count += 1
            score = result['@search.score']
            source = result.get('source_file', 'Unknown File')
            content_preview = result.get('content', '')[:200].replace('\n', ' ')
            
            print(f"\n[Result {count} | Score: {score:.4f}] File: {source}")
            print(f"Preview: {content_preview}...")
        
        if count == 0:
            print("\nNo results found.")

    except Exception as e:
        print(f"Error executing search: {e}")

if __name__ == "__main__":
    # Test queries based on your file names
    print("Vector Search Tester")
    print("--------------------")
    while True:
        user_query = input("\nEnter a search query (or 'q' to quit): ")
        if user_query.lower() in ['q', 'quit', 'exit']:
            break
        if user_query:
            search_index(user_query)
