# Standard library imports
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
import uvicorn
from typing import List, Dict
import json
from fastapi.middleware.cors import CORSMiddleware

# Third-party imports for OpenAI and LangChain
import openai
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from helper import get_full_content_from_url

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("uvicorn.error")

# Get API configuration from environment variables
apikey = os.getenv("OPENAI_KEY")
baseurl = os.getenv("OPENAI_BASE_URL")
# Initialize FastAPI application
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize OpenAI embeddings with custom configuration
# Using text-embedding-3-small model for efficient text embeddings
embedding = OpenAIEmbeddings(
    openai_api_key=apikey,
    openai_api_base=baseurl,
    model="text-embedding-3-small",
)

# Load the persisted Chroma vector database
# This database stores document embeddings for semantic search
vectordb = Chroma(persist_directory="./chroma_store", embedding_function=embedding)
retriever = vectordb.as_retriever(
    search_kwargs={"k": 5}
)  # Retrieve top 5 most relevant documents

# Define the prompt template for the QA chain
# This template structures how the context and question are presented to the model
prompt_template = """
Answer the following question based on the provided context. If the context is not enough, say "I don't know."

Question: {question}

Context:
{context}

Answer:
"""

rag_prompt = PromptTemplate.from_template(prompt_template)

# Initialize ChatOpenAI with custom configuration
# Using GPT-3.5 Turbo for efficient text generation
llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,  # Set to 0 for deterministic responses
    openai_api_key=apikey,
    openai_api_base=baseurl,
)

# Create a RetrievalQA chain that combines:
# 1. Document retrieval from vector store
# 2. Context-aware question answering
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # Simple stuffing of retrieved documents
    retriever=retriever,
    chain_type_kwargs={"prompt": rag_prompt},
    return_source_documents=True,  # Return source documents for reference
)

# Define the request model for the API endpoint
class QuestionRequest(BaseModel):
    question: str  # The user's question
    image: Optional[str] = None  # Optional base64-encoded image string

logger.info("API is ready to accept requests at /api/ endpoint")

@app.post("/api")
async def answer_question(request: QuestionRequest):
    """
    Main API endpoint that handles question answering with optional image analysis.
    Combines RAG (Retrieval Augmented Generation) with vision capabilities.
    """
    # print received query
    logger.info(f"Received question: {request.question}")
    full_query = request.question

    # First get RAG results using the QA chain
    result = qa_chain.invoke({"query": full_query})
    # context = result["result"]
    source_docs: List[Document] = result.get("source_documents", [])

    # Extract and format source links from document metadata
    rag_links = []
    for doc in source_docs:
        if "url" in doc.metadata:
            rag_links.append(
                {
                    "url": doc.metadata["url"],
                    "text": doc.page_content[:200].replace("\n", " ")
                    + "...",  # Truncate and clean text
                }
            )

    # Fetch full content from the URLs using helper function, ensuring no duplicates
    full_links = []
    unique_urls = set()
    for link in rag_links:
        url = link["url"]
        if url not in unique_urls:
            unique_urls.add(url)
            # Get full content from the URL if it's a discourse or TDS link
            true_url, content = get_full_content_from_url(url)
            if content is not None:
                logger.info(f"Fetched content from {url}")
                # logger.info(f"Content: {content[:100]}...")
                full_links.append({"url": true_url, "text": content})

    context = "\n\n".join(
        [
            f"Context No. {i+1}: {link['text']}\nLink: {link['url']}"
            for i, link in enumerate(full_links)
            if link["text"]
        ]
    )

    logger.info(f"{len(full_links)} source links found for the question.")

    try:
        # Initialize OpenAI client with custom configuration
        client = openai.OpenAI(
            api_key=apikey,
            base_url=baseurl,
        )

        # System prompt
        system_prompt = """
        You are an AI Teaching Assistant for the 'Tools in Data Science' course. Your responses should be based solely on the knowledge present in the knowldege base. Consider the question and any attached images (if applicable) by the user. Always reply only in the following JSON format.

        ### JSON Output Format:
        {
            "answer": string,          // This should be your answer to the question based on your knowledge base and reasoning.
            "links": [                 // This is a list of references that support your answer.
                {
                    "url": string,         // The exact URL of the reference being cited.
                    "text": string         // A brief explanation of what this link supports or why it is relevant to the answer.
                }
            ]
        }

        All fields are mandatory. Your response **must** be a valid JSON object that adheres exactly to this structure. Do not include anything outside the JSON block.

        ### One-shot Example:

        {
        "answer": "You must use `gpt-3.5-turbo-0125`, even if the AI Proxy only supports `gpt-4o-mini`. Use the OpenAI API directly for this question.",
        "links": [
                {
                "url": "https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/4",
                "text": "Use the model that's mentioned in the question."
                },
                {
                "url": "https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/3",
                "text": "My understanding is that you just have to use a tokenizer, similar to what Prof. Anand used, to get the number of tokens and multiply that by the given rate."
                }
            ]
        }
        """

        # Create a comprehensive prompt combining RAG context and original query
        user_prompt = f"""
        Original question:
        {full_query}

        KNOWLEDGE_BASE:
        The knowledge base relevant to this question (This may contain full discourse threads or links from the professors GitHub repository):
        {context}

        Original question(repeated again for clarity):
        {full_query}

        RULES
        1. Every factual statement in "answer" must be traceable to the supplied KNOWLEDGE_BASE.  
        2. Cite with links[]. Each link object must correspond to a source actually present in KNOWLEDGE_BASE.  
        3. If the KNOWLEDGE_BASE clearly answers the question, write a **detailed** explanation (>100 words) that weaves in evidence from the sources.  
        4. If the answer is only partially covered, begin the answer with “I may not be completely certain, but based on the available context..." and still cite what you found.  
        5. If no part of the KNOWLEDGE_BASE is relevant, respond exactly with:
        {{
            "answer": "I am not sure about the answer to this question with my current knowledge base",
            "links": []
        }}
        """

        # Prepare message content for the model
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}],
            },
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]

        # if image provided, add that in
        if request.image:
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{request.image}"
                            },
                        },
                    ],
                },
            ]

        logger.info("Sending request to OpenAI API")

        # Generate response using our chunky smart boi
        completion = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            response_format={"type": "json_object"}
        )

        logger.warning("Answer generated successfully.")
        answer = json.loads(completion.choices[0].message.content)

        return answer
    except Exception as e:
        # Handle any errors during processing
        logger.error(f"Error processing request: {str(e)}")
        return {
            "answer": f"I encountered an error while processing your request. {str(e)}",
            "links": [],
        }


if __name__ == "__main__":
    # Start the FastAPI application using uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")
