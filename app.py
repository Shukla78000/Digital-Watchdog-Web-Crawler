from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app

# Function to scrape data from a given URL with a specific selector
def scrape_news(url, selector, content_selector=None, image_selector=None, limit=5):
    try:
        response = requests.get(url, timeout=10)  # Added timeout to prevent hanging
        response.raise_for_status()  # Raise an error for failed requests
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select(selector)
        news_items = []

        for article in articles[:limit]:  # Limit the number of articles
            title = article.get_text(strip=True)
            link = article.get('href')

            # Try to extract a small content snippet (first paragraph or similar)
            snippet = ''
            if content_selector:
                content = article.find_next(content_selector)
                if content:
                    snippet = content.get_text(strip=True)

            # Extract the image URL
            image_url = ''
            if image_selector:
                image_tag = article.select_one(image_selector)  # Use CSS selector for the image
                if image_tag and image_tag.get('src'):
                    image_url = image_tag.get('src')

            # Handle relative URLs
            if link and link.startswith('/'):
                link = url + link

            # Handle relative image URLs
            if image_url and image_url.startswith('/'):
                image_url = url + image_url

            news_items.append({
                'title': title,
                'link': link,
                'snippet': snippet,  # Add the snippet to the response
                'image': image_url  # Add the image URL to the response
            })

        return news_items
    except requests.exceptions.RequestException as e:  # Catch network-related errors
        return {'error': f"Failed to retrieve data from {url}: {str(e)}"}

# Route to render the HTML page
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    return render_template('index.html')  # Render the HTML file

# API endpoint to scrape news
@app.route('/api/scrape', methods=['GET'])
def scrape_news_api():
    try:
        # Get limit from query parameters (default is 5)
        limit = int(request.args.get('limit', 5))
        filter_type = request.args.get('type')  # News source filter
        category = request.args.get('category')  # News category filter (e.g., 'tech', 'malware')
        sort_order = request.args.get('sort', 'asc')  # Sort order (default is ascending)

        # Define keywords for each category
        category_keywords = {
            'tech': ['tech', 'technology', 'cybersecurity', 'software', 'AI', 'machine learning'],
            'malware': ['malware', 'virus', 'trojan', 'spyware', 'worm'],
            'ransomware': ['ransomware', 'ransom', 'cyber extortion', 'data breach', 'crypto'],
        }

        # URL configurations for different news sources
        urls = {
            'Krebs on Security': {
                'url': 'https://krebsonsecurity.com/', 
                'selector': '.entry-title a',
                'content_selector': 'p',  
                'image_selector': 'img'  
            },
            'The Hacker News': {
                'url': 'https://thehackernews.com/', 
                'selector': 'a.story-link',
                'content_selector': 'p',  
                'image_selector': 'img'  
            },
            'Ars Technica': {
                'url': 'https://arstechnica.com/', 
                'selector': 'h2 a',
                'content_selector': 'p',  
                'image_selector': 'img'  
            },
            'TechRadar': {
                'url': 'https://www.techradar.com/news', 
                'selector': 'a.article-link',
                'content_selector': 'p',  
                'image_selector': 'img'  
            }
        }

        all_news = {}
        for site, details in urls.items():
            news_items = scrape_news(details['url'], details['selector'], 
                                     details.get('content_selector'), 
                                     details.get('image_selector'), 
                                     limit)
            if 'error' in news_items:  
                all_news[site] = {'error': news_items['error']}
            else:
                all_news[site] = news_items

        # Filter news if a specific source type is requested
        if filter_type:
            all_news = {k: v for k, v in all_news.items() if k == filter_type}

        # Flatten the news items for further processing
        flat_news = []
        for site, articles in all_news.items():
            if 'error' not in articles:
                for article in articles:
                    flat_news.append({
                        'source': site,
                        'title': article['title'],
                        'link': article['link'],
                        'snippet': article['snippet'],
                        'image': article['image']
                    })

        # Apply category filtering if a category is specified
        if category and category in category_keywords:
            keywords = category_keywords[category]
            flat_news = [article for article in flat_news 
                         if any(keyword.lower() in article['title'].lower() or 
                                keyword.lower() in article['snippet'].lower() 
                                for keyword in keywords)]

        # Sort news based on the specified order
        flat_news.sort(key=lambda x: x['title'], reverse=(sort_order == 'desc'))

        # Group back the sorted news into sections by source
        sorted_news = {}
        for item in flat_news:
            source = item['source']
            if source not in sorted_news:
                sorted_news[source] = []
            sorted_news[source].append(item)

        return jsonify(sorted_news)

    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == "__main__":
    app.run(debug=True)
