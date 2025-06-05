from urllib.parse import urlparse
import json
from bs4 import BeautifulSoup

def clean_html_content(html_content):
    """
    Uses BeautifulSoup to extract clean text from HTML content.
    """
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    # Get text and clean up whitespace
    text = soup.get_text(separator='\n', strip=True)
    # Remove extra newlines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return '\n'.join(lines)

def format_thread_to_string(thread):
    """
    Takes a thread (list of posts) and formats it into a readable string
    where each post shows who said what and when.
    """
    if not thread:
        return "No thread data available"
    
    formatted_thread = []
    for post in thread:
        # Skip empty posts or system posts
        if not post.get('cooked') or post.get('post_type') == 3:
            continue
            
        author = post.get('display_username', 'Unknown')
        content = clean_html_content(post.get('cooked', ''))
        timestamp = post.get('created_at', '')
        
        # Format the post
        post_text = f"{author} ({timestamp}):\n{content}\n"
        formatted_thread.append(post_text)
    
    return "\n".join(formatted_thread)

def get_full_content_from_url(url):
    # Takes input a URLL:str which could either be a discourse link or a TDS GH page link
    # Discourse link: https://discourse.onlinedegree.iitm.ac.in/t/ga4-data-sourcing-discussion-thread-tds-jan-2025/165959/16
    # GH Page Link: https://tds.s-anand.net/docker.md
    # This function will return the full content of the page as a string
    if( "discourse.onlinedegree.iitm.ac.in" in url):
        # get the topic slug
        parsed_url = urlparse(url)
        topic_slug = parsed_url.path.split('/')[2]
        thread = None
        with open('discourse_contents.json', 'r', encoding='utf-8') as f:
            discourse_contents = json.load(f)
        for content in discourse_contents:
            if content['slug'] == topic_slug:
                thread = content['topic_data']['post_stream']['posts']
        # Format the thread into a readable string
        formatted_thread = format_thread_to_string(thread)
        return url, formatted_thread
    elif("tds.s-anand.net" in url):
        # Handle TDS GH links
        slug = urlparse(url).path.split('/')[-1]
        with open(f'course_contents/{slug}', 'r', encoding='utf-8') as f:
            content = f.read()
        parsed_url = urlparse(url)
        if parsed_url.netloc == "tds.s-anand.net":
            url = f"{parsed_url.scheme}://{parsed_url.netloc}/#{parsed_url.path[:-3]}"
        return url, content
    else:
        return url, None
    
# if __name__ == "__main__":
#     url = "https://tds.s-anand.net/crawling-cli.md"
#     print(get_full_content_from_url(url)[0])

