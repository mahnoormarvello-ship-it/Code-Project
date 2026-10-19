
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone


# =====================================================
# 1. CONFIGURATION
# =====================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

NAMESPACE = "rag-document"

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSION = 1536

# Use a model ID available to your Gemini API project.
CHAT_MODEL = "gemini-3.8-flash"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 5

DOCUMENT_PATH = Path(__file__).parent / "rag_document.txt"

MAX_RETRIES = 3


# =====================================================
# 2. VALIDATE CONFIGURATION
# =====================================================

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is missing from .env")

if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME is missing from .env")


# =====================================================
# 3. INITIALIZE CLIENTS
# =====================================================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)

pinecone_client = Pinecone(
    api_key=PINECONE_API_KEY
)

index = pinecone_client.Index(
    PINECONE_INDEX_NAME
)


# =====================================================
# 4. LOAD DOCUMENT
# =====================================================

def load_document():

    if not DOCUMENT_PATH.exists():
        raise FileNotFoundError(
            f"Document not found: {DOCUMENT_PATH}"
        )

    text = DOCUMENT_PATH.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise ValueError("The document is empty.")

    print(f"Document loaded: {DOCUMENT_PATH.name}")
    print(f"Total characters: {len(text)}")

    return text


# =====================================================
# 5. SPLIT DOCUMENT INTO CHUNKS
# =====================================================

def split_into_chunks(text):

    chunks = []
    start = 0

    while start < len(text):

        end = min(
            start + CHUNK_SIZE,
            len(text)
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    print(f"Total chunks created: {len(chunks)}")

    return chunks


# =====================================================
# 6. CREATE GEMINI EMBEDDINGS WITH RETRIES
# =====================================================

def create_embeddings(texts, task_type):

    all_embeddings = []

    for text_index, text in enumerate(texts, start=1):

        for attempt in range(MAX_RETRIES):

            try:
                response = gemini_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=EMBEDDING_DIMENSION,
                        task_type=task_type
                    )
                )

                if not response.embeddings:
                    raise ValueError(
                        "Gemini returned no embeddings."
                    )

                embedding = response.embeddings[0].values

                if len(embedding) != EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Expected {EMBEDDING_DIMENSION} dimensions, "
                        f"received {len(embedding)}."
                    )

                all_embeddings.append(embedding)
                break

            except Exception as error:

                error_message = str(error)

                temporary_error = any(
                    code in error_message
                    for code in (
                        "429", "500", "502", "503", "504"
                    )
                )

                if not temporary_error:
                    raise RuntimeError(
                        f"Embedding failed for item "
                        f"{text_index}: {error}"
                    ) from error

                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"Embedding failed after "
                        f"{MAX_RETRIES} attempts: {error}"
                    ) from error

                wait_seconds = 2 ** (attempt + 1)

                print(
                    f"Embedding temporarily unavailable. "
                    f"Retrying in {wait_seconds}s..."
                )

                time.sleep(wait_seconds)

    return all_embeddings


# =====================================================
# 7. STORE DOCUMENT IN PINECONE
# =====================================================

def store_in_pinecone(chunks):

    print("\nChecking Pinecone namespace...")

    stats = index.describe_index_stats()
    namespaces = stats.namespaces or {}

    if NAMESPACE in namespaces:
        print(f"Namespace '{NAMESPACE}' already exists.")
    else:
        print(
            f"Namespace '{NAMESPACE}' will be created "
            "on the first successful upsert."
        )

    batch_size = 20
    total_chunks = len(chunks)

    for start in range(0, total_chunks, batch_size):

        batch = chunks[start:start + batch_size]

        embeddings = create_embeddings(
            batch,
            task_type="RETRIEVAL_DOCUMENT"
        )

        vectors = []

        for i, (chunk, embedding) in enumerate(
            zip(batch, embeddings)
        ):

            chunk_number = start + i

            vectors.append({
                "id": f"rag-document-{chunk_number}",
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "source": DOCUMENT_PATH.name,
                    "chunk_number": chunk_number
                }
            })

        index.upsert(
            vectors=vectors,
            namespace=NAMESPACE
        )

        print(
            f"Stored {min(start + len(batch), total_chunks)}"
            f"/{total_chunks} chunks"
        )

    print("\nKnowledge base stored successfully.")


# =====================================================
# 8. RETRIEVE RELEVANT CONTEXT
# =====================================================

def retrieve_context(user_query):

    query_embedding = create_embeddings(
        [user_query],
        task_type="RETRIEVAL_QUERY"
    )[0]

    results = index.query(
        vector=query_embedding,
        top_k=TOP_K,
        namespace=NAMESPACE,
        include_metadata=True
    )

    matches = results.matches or []

    context_parts = []

    for match in matches:

        metadata = match.metadata or {}
        chunk_text = metadata.get("text", "")

        if chunk_text:
            context_parts.append(chunk_text)

    print(
        f"Retrieved {len(context_parts)} relevant chunks."
    )

    return "\n\n".join(context_parts)


# =====================================================
# 9. GENERATE ANSWER WITH RETRIES
# =====================================================

def generate_answer(prompt):

    for attempt in range(MAX_RETRIES):

        try:
            response = gemini_client.models.generate_content(
                model=CHAT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2
                )
            )

            if response.text:
                return response.text

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        except Exception as error:

            error_message = str(error)

            temporary_error = any(
                code in error_message
                for code in (
                    "429", "500", "502", "503", "504"
                )
            )

            if not temporary_error:
                print(f"Gemini API error: {error}")
                return (
                    "I could not generate an answer. "
                    "Please check the model name and API access."
                )

            if attempt == MAX_RETRIES - 1:
                print(
                    f"Gemini failed after {MAX_RETRIES} attempts: "
                    f"{error}"
                )

                return (
                    "The Gemini service is temporarily unavailable. "
                    "Please try your question again shortly."
                )

            wait_seconds = 2 ** (attempt + 1)

            print(
                f"Gemini returned a temporary error. "
                f"Retrying in {wait_seconds}s "
                f"(attempt {attempt + 2}/{MAX_RETRIES})..."
            )

            time.sleep(wait_seconds)


# =====================================================
# 10. RAG CHAT FUNCTION
# =====================================================

def chat(user_query):

    context = retrieve_context(user_query)

    if not context:
        return (
            "I could not find relevant information "
            "in the knowledge base."
        )

    prompt = f"""
You are a helpful Retrieval-Augmented Generation chatbot.

Rules:
1. Answer using only the provided knowledge-base context.
2. Do not invent facts or unsupported information.
3. If the answer is missing from the context, say that
   the information is not available in the knowledge base.
4. Give a clear and concise answer.

KNOWLEDGE-BASE CONTEXT:
{context}

USER QUESTION:
{user_query}

ANSWER:
"""

    return generate_answer(prompt)


# =====================================================
# 11. MAIN PROGRAM
# =====================================================

def main():

    print("\n================================")
    print("       GEMINI RAG CHATBOT")
    print("================================\n")

    try:

        document = load_document()
        chunks = split_into_chunks(document)

        store_in_pinecone(chunks)

        print("\nKnowledge base is ready!")
        print("You can now ask questions.")
        print("Type 'exit' to stop.\n")

        while True:

            user_query = input("You: ").strip()

            if user_query.lower() in {
                "exit", "quit", "bye"
            }:
                print("Chatbot: Goodbye!")
                break

            if not user_query:
                continue

            try:
                answer = chat(user_query)
                print(f"\nChatbot: {answer}\n")

            except Exception as error:
                print(f"\nChatbot error: {error}\n")

    except Exception as error:
        print(f"\nSystem error: {error}")


if __name__ == "__main__":
    main()
