from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
from langchain.embeddings.openai import OpenAIEmbeddings
from openai import OpenAI


class MongoInterface:
    def __init__(self, uri=None, db_name="SISCO"):
        mongo_uri = uri or os.environ["MONGO_URI"]
        openai_key = os.environ["OPENAI_API_KEY"]
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.embedder = OpenAIEmbeddings(
            model="text-embedding-3-large", openai_api_key=openai_key
        )
        self.openai_client = OpenAI(api_key=openai_key)

    # --------- PressRelease Collection ----------
    def create_press_release(
        self,
        url: str,
        title: str,
        subtitle: str,
        text: str,
        collection_id: str,
        client_id: str,
        template_html: str = None,
        extracted_fields: dict = None,
    ) -> ObjectId:
        """Insert a new press release document."""
        doc = {
            "Name": title,
            "Subtitle": subtitle,
            "Filename": url.split("/")[-1],
            "Url": url,
            "ClientID": client_id,
            "CollectionID": collection_id,
            "TemplateHTML": template_html,
            "ExtractedFields": extracted_fields or {},
            "AttachedDocs": [],  # will be filled with Document IDs of PDFs
            "CreatedAt": datetime.utcnow(),
        }
        result = self.db.PressRelease.insert_one(doc)
        return result.inserted_id

    def get_press_release(self, pr_id: str) -> dict:
        return self.db.PressRelease.find_one({"_id": ObjectId(pr_id)})

    def list_press_releases(self, client_id: str, collection_id: str) -> list[dict]:
        return list(
            self.db.PressRelease.find(
                {"ClientID": client_id, "CollectionID": collection_id}
            )
        )

    # --------- Document Collection (Attached PDFs, etc.) ----------
    def create_attached_document(
        self,
        parent_pr_id: ObjectId,
        url: str,
        filename: str,
        client_id: str,
        collection_id: str,
    ) -> ObjectId:
        """Insert an attached document (e.g., PDF) and link it to its press release."""
        doc = {
            "Name": filename,
            "Filename": filename,
            "Url": url,
            "ClientID": client_id,
            "CollectionID": collection_id,
            "PressReleaseId": parent_pr_id,
            "CreatedAt": datetime.utcnow(),
        }
        result = self.db.Document.insert_one(doc)

        # update parent press release with reference
        self.db.PressRelease.update_one(
            {"_id": parent_pr_id},
            {"$addToSet": {"AttachedDocs": result.inserted_id}},
        )
        return result.inserted_id

    def get_document(self, doc_id: str) -> dict:
        return self.db.Document.find_one({"_id": ObjectId(doc_id)})

    def list_documents(self, client_id: str, collection_id: str) -> list[dict]:
        return list(
            self.db.Document.find(
                {"ClientID": client_id, "CollectionID": collection_id}
            )
        )

    # --------- ProcessedContent Collection ----------
    def add_processed_chunks(
        self, document_id: ObjectId, text_chunks: list[str]
    ) -> list[str]:
        """Embed and store processed text chunks for a given document (press release or PDF)."""
        vectors = self.embedder.embed_documents(text_chunks)
        chunk_docs = [
            {
                "DocumentId": document_id,
                "Vector": vector,
                "Content": chunk,
                "CreatedAt": datetime.utcnow(),
            }
            for chunk, vector in zip(text_chunks, vectors)
        ]
        result = self.db.ProcessedContent.insert_many(chunk_docs)
        return [str(doc_id) for doc_id in result.inserted_ids]

    def get_chunks_for_document(self, document_id: str) -> list[dict]:
        return list(self.db.ProcessedContent.find({"DocumentId": ObjectId(document_id)}))

    def similarity_search(self, query: str, limit: int = 5) -> list[dict]:
        """Vector similarity search across all processed content."""
        embedding = self.embedder.embed_query(query)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "Vector",
                    "queryVector": embedding,
                    "numCandidates": 100,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "Content": 1,
                    "score": {"$meta": "vectorSearchScore"},
                    "DocumentId": 1,
                }
            },
        ]
        return list(self.db.ProcessedContent.aggregate(pipeline))

    # --------- Companies Collection ----------
    def create_company(
        self, parent: str, child: str, percent: float, notes: str = None
    ) -> ObjectId:
        """Insert ownership relation between companies."""
        company_doc = {
            "Parent": parent,
            "Child": child,
            "Percent": percent,
            "Notes": notes,
            "CreatedAt": datetime.utcnow(),
        }
        result = self.db.Companies.insert_one(company_doc)
        return result.inserted_id

    def list_companies(self) -> list[dict]:
        return list(self.db.Companies.find({}))

    def find_company_relations(self, name: str) -> list[dict]:
        return list(
            self.db.Companies.find({"$or": [{"Parent": name}, {"Child": name}]})
        )

    def fetch_company_tree(self) -> dict:
        """Return parent → [(child, percent)] structure for all companies."""
        graph = {}
        for c in self.db.Companies.find({}, {"Parent": 1, "Child": 1, "Percent": 1}):
            graph.setdefault(c["Parent"], []).append((c["Child"], c["Percent"]))
        return graph

    # --------- Convenience ----------
    def fetch_press_releases_with_chunks(
        self, client_id: str, collection_id: str
    ) -> list[dict]:
        """Return press releases with their chunks."""
        prs = self.list_press_releases(client_id, collection_id)
        enriched = []
        for pr in prs:
            chunks = self.get_chunks_for_document(pr["_id"])
            enriched.append({"press_release": pr, "chunks": chunks})
        return enriched
