# TDS Virtual TA - Scraper and RAG System

This system scrapes course content and discourse posts, creates embeddings, and provides a RAG-based question answering system.

> **Bonus Feature**: The system includes a date-range based Discourse scraper (`discourse_scraper.py`) that can scrape posts from any Discourse course page within a specified date range. This feature was implemented for bonus marks in the project. Please modify start_date and end_date variables in this file to achieve outcome

## Prerequisites

- Python 3.8 or higher
- Git
- AIPIPE API access (for embeddings and LLM)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd scraper
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory with:
   ```
   OPENAI_KEY=your_aipipe_token
   OPENAI_BASE_URL=your_aipipe_baseurl
   ```

## Data Collection and Processing

1. **Scrape Course Content**
   ```bash
   python course_scrape.py
   ```
   This will create `course_structure.json` with the course content.

2. **Scrape Discourse Posts**
   ```bash
   python discourse_scraper.py
   ```
   This will create `discourse_contents.json` with the forum posts.

3. **Generate Embeddings and Create Vector Store**
   ```bash
   python chunk_and_embed.py
   ```
   This will:
   - Process the course content and discourse posts
   - Create chunks of text
   - Generate embeddings using OpenAI's text-embedding-3-small model
   - Store them in the `chroma_store` directory

## Running the System

1. **Start the FastAPI server**
   ```bash
   python app.py
   ```
   The server will start at `http://localhost:8000`

2. **Using the API**
   Send POST requests to `/api/` with the following JSON structure:
   ```json
   {
     "question": "Your question here",
     "image": "base64_encoded_image_string" // optional
   }
   ```

   The response will include:
   - `answer`: The generated answer
   - `links`: Relevant source links with snippets

3. **Evaluate**
   ```cd promptfoo & promptfoo eval --config project-tds-virtual-ta-promptfoo.yaml --no-cache```

## Project Structure

- `app.py`: FastAPI server and RAG implementation
- `course_scrape.py`: Course content scraper
- `discourse_scraper.py`: Discourse forum scraper
- `chunk_and_embed.py`: Text processing and embedding generation
- `vars.py`: Configuration variables
- `requirements.txt`: Python dependencies
- `chroma_store/`: Vector database (generated)
- `course_contents/`: Scraped course content
- `discourse_contents.json`: Scraped forum posts
- `course_structure.json`: Course structure data

## Notes

- The `chroma_store` directory is git-ignored as it can be regenerated
- Large data files (`discourse_contents.json` and `course_structure.json`) are included in the repository
- The system uses AIPIPE for embeddings and LLM access
- Final answer processing is supported through GPT-4.1

## Troubleshooting

1. If the vector store is missing:
   - Ensure all data files exist
   - Run `chunk_and_embed.py` to regenerate the store

2. If API calls fail:
   - Check your AIPIPE credentials in `.env`
   - Verify the server is running
   - Check the API endpoint URL

3. If scraping fails:
   - Verify internet connection
   - Check if the source URLs are accessible
   - Ensure you have necessary permissions 