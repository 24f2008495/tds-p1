import requests
from datetime import datetime, timezone
from vars import cookies, headers
import json

base_url = "https://discourse.onlinedegree.iitm.ac.in"

def fetch_discourse(pageno):
    url = base_url + "/c/courses/tds-kb/34/l/latest.json"
    params = {
        "filter": "latest",
        "page": pageno,
    }
    response = requests.get(url, params=params, headers=headers, cookies=cookies)
    return extract_topics(response.json())


def extract_topics(data):
    """Extract specific fields from topics and convert created_at to datetime object."""
    topics = []
    for topic in data['topic_list']['topics']:
        # Convert ISO format string to datetime object with UTC timezone
        created_at = datetime.fromisoformat(topic['created_at'].replace('Z', '+00:00'))
        
        topic_info = {
            'id': topic['id'],
            'title': topic['title'],
            'slug': topic['slug'],
            'created_at': created_at
        }
        topics.append(topic_info)
    return topics

def get_topic_details(slug:str, topic_id:int):
    """Fetch detailed information about a specific topic using its slug and ID."""
    url = base_url + f"/t/{slug}/{topic_id}.json"
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching topic details: {e}")
        return None

if __name__ == "__main__":
    try:
        ##### PART 1 - Knowning till which page no to scrape #####
        # # i = 0
        # # data = []
        # # # with by checking this, just checked last date of last post in the page which came to be page 5 as it contains 26 Dec 2024 data but we only need 1 Jan 2025 - 14 Apr 2025 - this could change in the future
        # # while True:
        # #     topics = fetch_discourse(pageno=i)
        # #     print(f"Page {i}: {topics[-1]['title'][:5]} | {topics[-1]['created_at'].strftime("%d %b %Y")}")
        # #     data.extend(topics)
        # #     i += 1
        
        ##### PART 2 - Scraping till that page no. #####
        # data = []
        # final_page = 6 # 0,1,2,3,4,5,6
        # for i in range(final_page+1):
        #     topics = fetch_discourse(pageno=i)
        #     data.extend(topics)
        
        # # Create timezone-aware datetime objects for comparison
        # start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        # end_date = datetime(2025, 4, 14, tzinfo=timezone.utc)
        # filtered_topics = [
        #     topic for topic in data
        #     if start_date <= topic['created_at'] <= end_date
        # ]
        # print(len(filtered_topics))

        # # sort them by created_at
        # filtered_topics.sort(key=lambda x: x['created_at'])
        # print("Total filtered topics: ", len(filtered_topics))

        # final_list = []
        # # get the details of each topic(it will be a json), copy it into a subvariable within the topic variable, call it topic_data  
        # for topic in filtered_topics:
        #     print(f"Fetching details for topic: {topic['title']}")
        #     topic_data = get_topic_details(topic['slug'], topic['id'])
        #     if topic_data:
        #         topic['topic_data'] = topic_data
        #         final_list.append(topic)
        
        # # write the final_list to a json file
        # with open('discourse_contents.json', 'w', encoding='utf-8') as f:
        #     json.dump(final_list, f, indent=2, default=str)

        # ##### PART 3 - process the images within (avoiding for not #TODO) #####
        # # load the json file
        # with open('discourse_contents.json', 'r', encoding='utf-8') as f:
        #     data = json.load(f)

        # # do a regex match accross whole json(all the data and subdata and data within that like a fts) and look for links that end with .png .jpg etc all images basicall
        # from urllib.parse import urlparse
        # import re
        # import requests
        # # regex pattern to match image links
        # image_pattern = re.compile(r'http[s]?://.*?\.(?:png|jpg|jpeg|gif|bmp|webp|svg)', re.IGNORECASE)
        # # iterate through the data and subdata
        # links = []
        # for topic in data:
        #     for post in topic['topic_data']['post_stream']['posts']:
        #             image_links = image_pattern.findall(post['cooked'])
        #             for link in image_links:
        #                  links.append(link)
        
        # print(len(links))
        # # remove duplicates
        # links = list(set(links))
        # print(len(links))

        # # count all that have the word europe in them
        # europe_count = 0
        # for link in links:
        #     if 'europe1.discourse-cdn.com' in link:
        #         europe_count += 1
        # print(f"Total links containing 'europe': {europe_count}")
        
        print("Yay! Scraping completed successfully!")

            
    except Exception as e:
        print(f"An error occurred: {e}")
