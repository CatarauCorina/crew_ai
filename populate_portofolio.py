import os
from pymongo import MongoClient
from datetime import datetime

def seed(mongo_uri="mongodb://localhost:27017", db_name="SISCO"):
    mongo_uri = os.environ['MONGO_URI']
    openai_key = os.environ['OPENAI_API_KEY']
    client = MongoClient(mongo_uri)
    col = client[db_name].Companies

    # clear old data
    col.delete_many({})

    # ownership edges from the chart
    edges = [
        {"Parent": "SISCO", "Child": "Tusdeer", "Percent": 76.0},
        {"Parent": "Tusdeer", "Child": "Xenmet", "Percent": 19.0},

        {"Parent": "SISCO", "Child": "Isnad", "Percent": 99.28},
        {"Parent": "Isnad", "Child": "IWD/Tawzea", "Percent": 50.0},
        {"Parent": "Isnad", "Child": "SA Talke", "Percent": 33.33},

        {"Parent": "SISCO", "Child": "Kindasa", "Percent": 65.0},
        {"Parent": "Kindasa", "Child": "Green Dome-UAE", "Percent": 31.67},

        {"Parent": "SISCO", "Child": "RSPD", "Percent": 60.6},
        {"Parent": "RSPD", "Child": "RSGT", "Percent": 60.0},
        {"Parent": "RSPD", "Child": "BALC", "Percent": 100.0, "Notes": "Incorporated 10 Jan 2024"},

        {"Parent": "SISCO", "Child": "RSPDI-UK", "Percent": 60.6},
        {"Parent": "RSPDI-UK", "Child": "RSGTI-UK", "Percent": 60.0},
        {"Parent": "RSGTI-UK", "Child": "RSGTI-Bangladesh", "Percent": 100.0},
    ]

    # insert
    for e in edges:
        e["CreatedAt"] = datetime.utcnow()
        col.insert_one(e)

    print(f"✅ Inserted {len(edges)} ownership links into {db_name}.Companies")

if __name__ == "__main__":
    seed()
