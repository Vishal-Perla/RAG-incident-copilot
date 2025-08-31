# db_setup.py
import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

load_dotenv()

# Load API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1-aws")
INDEX_NAME = "incident-response-index"

# Init clients
pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# Create index if not exists
if INDEX_NAME not in [i["name"] for i in pc.list_indexes()]:
    print(f"Creating index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536,  # embedding size for OpenAI text-embedding-3-small
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
else:
    print(f"Index {INDEX_NAME} already exists")

index = pc.Index(INDEX_NAME)

# Sample cybersecurity docs (mock data)
docs = [
    {
        "id": "nist-incident",
        "text": "According to NIST SP 800-61, incident handling should include preparation, detection, containment, eradication, and recovery.",
        "metadata": {"source": "NIST SP 800-61", "url": "https://csrc.nist.gov/publications/sp/800-61"},
    },
    {
        "id": "mitre-bruteforce",
        "text": "MITRE ATT&CK T1110 describes brute force: adversaries may repeatedly attempt passwords to gain unauthorized access.",
        "metadata": {"source": "MITRE ATT&CK", "url": "https://attack.mitre.org/techniques/T1110/"},
    },
    {
        "id": "mfa-guidance",
        "text": "Enabling multi-factor authentication (MFA) is a recommended security control to mitigate account compromise risks.",
        "metadata": {"source": "CIS Controls", "url": "https://www.cisecurity.org/controls"},
    },
]

# Embed and upsert
vectors = []
for doc in docs:
    embedding = client.embeddings.create(
        input=doc["text"], model="text-embedding-3-small"
    ).data[0].embedding

    vectors.append(
        {
            "id": doc["id"],
            "values": embedding,
            "metadata": doc["metadata"] | {"text": doc["text"]},
        }
    )

index.upsert(vectors)
print("✅ Uploaded sample cybersecurity docs to Pinecone.")
