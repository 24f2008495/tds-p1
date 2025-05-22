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

    # First get RAG results
    result = qa_chain.invoke({"query": full_query})
    context = result["result"]
    source_docs: List[Document] = result.get("source_documents", [])

    # Extract links from metadata
    links = []
    for doc in source_docs:
        if "url" in doc.metadata:
            links.append({
                "url": doc.metadata["url"],
                "text": doc.page_content[:200].replace("\n", " ") + "..."
            })

    try:
        # Configure OpenAI client with AIPIPE
        client = openai.OpenAI(
            api_key=os.getenv("AIPIPE_TOKEN"),
            base_url=os.getenv("AIPIPE_BASEURL"),
        )
        
        # Create a prompt that includes both the RAG context and the original query
        prompt = f"""Based on the following context and question, please provide a comprehensive answer. 
        Consider both the text information and the attached image(if present) in your response.

        Context from knowledge base:
        {context}

        Original question:
        {full_query}
        """
        
        # Prepare the message content
        message_content = [{"type": "text", "text": prompt}]
        
        # Add image if provided
        if request.image:
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{request.image}"}
            })
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            max_tokens=500
        )
        return {
            "answer": response.choices[0].message.content.strip(),
            "links": links
        }
    except Exception as e:
        return {"answer": "Failed to process request.", "error": str(e), "links": links}
