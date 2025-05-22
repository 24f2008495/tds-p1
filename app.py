from fastapi import FastAPI, UploadFile, Request
from pydantic import BaseModel
from typing import Optional, List
import base64
import openai
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Initialize OpenAI embeddings with AIPIPE configuration
embedding = OpenAIEmbeddings(
    openai_api_key=os.getenv("AIPIPE_TOKEN"),
    openai_api_base=os.getenv("AIPIPE_BASEURL"),
    model="text-embedding-3-small",
)

# Load the persisted Chroma DB
vectordb = Chroma(persist_directory="./chroma_store", embedding_function=embedding)
retriever = vectordb.as_retriever(search_kwargs={"k": 5})

# Prompt template (optional)
prompt_template = """
Answer the following question based on the provided context. If the context is not enough, say "I don't know."

Question: {question}

Context:
{context}

Answer:
"""

prompt = PromptTemplate.from_template(prompt_template)

# Initialize ChatOpenAI with AIPIPE configuration
llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,
    openai_api_key=os.getenv("AIPIPE_TOKEN"),
    openai_api_base=os.getenv("AIPIPE_BASEURL")
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    chain_type_kwargs={"prompt": prompt},
    return_source_documents=True
)

# Input request format
class QuestionRequest(BaseModel):
    question: str
    image: Optional[str] = None  # base64-encoded image string

@app.post("/api/")
async def answer_question(request: QuestionRequest):
    full_query = request.question

    # Step 1: If image is provided, use GPT-4o-vision to extract text
    if request.image:
        try:
            image_bytes = base64.b64decode(request.image)
            # Configure OpenAI client with AIPIPE
            openai.api_key = os.getenv("AIPIPE_TOKEN")
            openai.api_base = os.getenv("AIPIPE_BASEURL")
            
            vision_response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this image."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{request.image}"}}
                        ]
                    }
                ],
                max_tokens=500
            )
            extracted_text = vision_response.choices[0].message.content.strip()
            full_query += "\n\nAdditional info from image:\n" + extracted_text
        except Exception as e:
            return {"answer": "Failed to process image.", "error": str(e), "links": []}

    # Step 2: Run RAG pipeline
    result = qa_chain.invoke({"query": full_query})
    answer = result["result"]
    source_docs: List[Document] = result.get("source_documents", [])

    # Step 3: Extract links from metadata
    links = []
    for doc in source_docs:
        if "url" in doc.metadata:
            links.append({
                "url": doc.metadata["url"],
                "text": doc.page_content[:200].replace("\n", " ") + "..."
            })

    return {
        "answer": answer,
        "links": links
    }
