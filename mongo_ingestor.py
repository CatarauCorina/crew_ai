import os
from datetime import datetime
from bson.objectid import ObjectId
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

from mongo_interface import CustomerServiceMongoInterface
from pdf_reader import PDFReader


class Ingestor:
    def __init__(self, mongo_uri: str, chunk_size=500, chunk_overlap=50):
        self.mongo = CustomerServiceMongoInterface(mongo_uri)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        use_core42_client = os.getenv('USE_CORE_42_CLIENT', "False") == "True"
        if use_core42_client:
            self.client = OpenAI(
                base_url="https://api.core42.ai/v1",
                api_key=os.getenv("CORE42_KEY"),
                default_headers={"api-key": os.getenv("CORE42_KEY")},
                default_query={"api-version": "2024-11-01-preview"}
            )
        else:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed_chunks(self, chunks: list[str], model: str = "text-embedding-3-large") -> list[list[float]]:
        response = self.client.embeddings.create(
            input=chunks,
            model=model
        )
        return [item.embedding for item in response.data]

    def ingest_pdf(self, pdf_path: str, name: str, collection_id: ObjectId, client_id: str):
        reader = PDFReader(pdf_path)
        reader.read_all()

        full_text = "\n\n".join([page["text"] for page in reader.text_content if page["text"]])
        if not full_text.strip():
            print(f"[Warning] No text found in PDF: {pdf_path}")
            return None

        filename = os.path.basename(pdf_path)

        # Insert into Document collection
        document_id = self.mongo.create_document(
            name=name,
            filename=filename,
            collection_id=collection_id,
            client_id=client_id
        )

        # Chunk and embed using the OpenAI client directly
        chunks = self.splitter.split_text(full_text)
        vectors = self.embed_chunks(chunks)

        # Insert into ProcessedContent collection
        processed_docs = [
            {
                "DocumentId": document_id,
                "Vector": vector,
                "Content": chunk,
                "CreatedAt": datetime.utcnow()
            }
            for chunk, vector in zip(chunks, vectors)
        ]

        self.mongo.db.ProcessedContent.insert_many(processed_docs)
        print(f"[Success] Inserted {len(processed_docs)} chunks for document '{name}'.")

        return document_id
