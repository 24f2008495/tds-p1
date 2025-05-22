from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import json
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

#### STEP 1 - load course contents and split into chunks ####
# Load all .md files
loader = DirectoryLoader("course_contents", glob="**/*.md", loader_cls=TextLoader)
documents = loader.load()

print(f"Loaded {len(documents)} course documents.")

# Add metadata to each document
base_url = 'https://tds.s-anand.net/'
for doc in documents:
    # Extract file path and name 
    file_path = doc.metadata.get('source', '')
    # Convert local path to URL path
    url_path = file_path.replace('course_contents/', '')
    full_url = base_url + url_path
    
    # Add metadata
    doc.metadata.update({
        'url': full_url,
        'title': os.path.splitext(os.path.basename(file_path))[0],
        'content_type': 'course_content',
        "author": "Course Author",
    })

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
course_md_chunks = text_splitter.split_documents(documents)

print(f"Split course documents into {len(course_md_chunks)} chunks.")

#### STEP 2 - load discourse topics and load into chunks ####
# Load discourse topics
with open('discourse_contents.json', 'r', encoding='utf-8') as f:
    threads = json.load(f)

documents = []

for thread in threads:
    thread_title = thread.get("title")
    thread_slug = thread.get("slug")
    thread_url = f"https://discourse.onlinedegree.iitm.ac.in/t/{thread_slug}/{thread['id']}"
    posts = thread.get("topic_data", {}).get("post_stream", {}).get("posts", [])

    for post in posts:
        author = post.get("name", "Unknown")
        raw_html = post.get("cooked", "")
        content = BeautifulSoup(raw_html, "html.parser").get_text().strip()
        post_url = f"{thread_url}/{post.get('post_number', 1)}"

        if content:
            doc = Document(
                page_content=f"{content}\n\n[Thread: {thread_title} | Author: {author}]\nSource: {post_url}",
                metadata={
                    "url": post_url,
                    "thread_title": thread_title,
                    "author": author,
                    "post_date": post.get("created_at"),
                    "content_type": "discourse_post",
                }
            )
            documents.append(doc)

print(f"Loaded {len(documents)} discourse posts.")

# Chunk the data
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
discourse_chunks = splitter.split_documents(documents)

print(f"Generated {len(discourse_chunks)} chunks ready for embedding.")

#### STEP 3 - load embeddings and create vectorstore ####
# Initialize OpenAI embeddings with AIPIPE configuration
embedding = OpenAIEmbeddings(
    openai_api_key=os.getenv("AIPIPE_TOKEN"),
    openai_api_base=os.getenv("AIPIPE_BASEURL"),
    model="text-embedding-3-small",
)

# Combine all chunks
all_chunks = course_md_chunks + discourse_chunks

# Store in Chroma
vectordb = Chroma.from_documents(
    documents=all_chunks,
    embedding=embedding,
    persist_directory="./chroma_store"
)

# Save to disk
vectordb.persist()