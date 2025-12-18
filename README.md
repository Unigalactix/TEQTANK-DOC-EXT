# Data Ingestion & Extraction Layer

This project implements a Data Ingestion & Extraction layer for a RAG pipeline. It ingests documents (PDFs) from an Azure Blob Storage container, extracts text using Azure Document Intelligence, and saves the results locally.

## Features

*   **Azure Blob Integration**: Connects to a specified container and processes files recursively (or by prefix).
*   **Document Intelligence**: Uses the `prebuilt-layout` model to extract text.
*   **Local Staging**: Saves extracted text as `.txt` files in a local `processed_data` directory.
*   **Resilience**: Handles individual file failures gracefully without stopping the entire batch.

## Prerequisites

*   Python 3.10+
*   Azure Storage Account
*   Azure Document Intelligence Resource

## Setup

1.  **Clone the repository** (if applicable) or navigate to the project directory.

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    Create a `.env` file in the root directory (you can copy `.env.example`).
    ```bash
    cp .env.example .env
    ```
    Fill in your Azure credentials:
    *   `AZURE_DI_KEY`: Your Document Intelligence API key.
    *   `AZURE_DI_ENDPOINT`: Your Document Intelligence endpoint URL.
    *   `AZ_STORAGE_STRING`: Your Azure Storage Connection String.
    *   `AZ_STORAGE_CONTAINER`: The name of the container to process (e.g., `$web`).
    *   `AZ_STORAGE_PREFIX`: (Optional) Prefix to filter blobs (e.g., `420/BackOffice`).

## Usage

Run the ingestion script:

```bash
python ingest.py
```

### Output

Processed files will be saved in the `processed_data` directory.
*   Format: Raw text (.txt) extracted from the document.
*   Naming: Original filename with special characters replaced, ending in `.txt`.
