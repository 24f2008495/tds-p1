import json
import os
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import re

def parse_markdown_list(content):
    """Parse markdown list into nested structure"""
    lines = content.strip().split('\n')
    result = []
    current_level = 0
    stack = [result]
    
    for line in lines:
        if not line.strip():
            continue
            
        # Count leading spaces to determine level
        level = len(line) - len(line.lstrip())
        level = level // 2  # Convert spaces to level (2 spaces per level)
        
        # Extract text and link
        text = line.strip()
        link_match = re.search(r'\[(.*?)\]\((.*?)\)', text)
        if link_match:
            text = link_match.group(1)
            link = link_match.group(2)
        else:
            link = None
            
        # Adjust stack based on level
        while level < current_level:
            stack.pop()
            current_level -= 1
            
        if level > current_level:
            stack.append(stack[-1][-1]['children'])
            current_level = level
            
        # Add new item
        item = {
            'text': text,
            'link': link,
            'children': []
        }
        stack[-1].append(item)
        
    return result

def download_markdown(url, output_path):
    """Download markdown file from URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Downloaded: {output_path}")
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")

def main():
    # # Read sidebar.md
    # with open('sidebar.md', 'r', encoding='utf-8') as f:
    #     content = f.read()
    
    # # Parse into JSON structure
    # structure = parse_markdown_list(content)
    
    # # Save JSON structure
    # with open('course_structure.json', 'w', encoding='utf-8') as f:
    #     json.dump(structure, f, indent=2)
    
    # Read course_structure.json into variable structure
    with open('course_structure.json', 'r', encoding='utf-8') as f:
        structure = json.load(f)

    # Create output directory
    output_dir = Path('course_contents')
    output_dir.mkdir(exist_ok=True)
    
    # Download all markdown files
    base_url = 'https://tds.s-anand.net/'
    
    def process_item(item):
        if item['link'] and item['link'].endswith('.md'):
            url = base_url + item['link']
            output_path = output_dir / item['link']
            download_markdown(url, output_path)
        
        for child in item['children']:
            process_item(child)
    
    # Process all items
    for item in structure:
        process_item(item)

if __name__ == '__main__':
    main() 