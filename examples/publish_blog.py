import requests
import json

def publish_blog_post(title, content, introduction='', toc=''):
    """
    Publish a blog post to the StudyBuddy website.
    
    Args:
        title (str): The title of the blog post
        content (str): The main content of the blog post
        introduction (str, optional): A brief introduction to the blog post
        toc (str, optional): Table of contents in HTML format
        
    Returns:
        dict: Response from the API containing the published blog post details
    """
    
    # API endpoint
    url = 'http://localhost:5000/api/blog/publish'
    
    # Prepare the blog post data
    data = {
        'title': title,
        'content': content,
        'introduction': introduction,
        'toc': toc
    }
    
    # Send POST request to the API
    response = requests.post(
        url,
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    
    # Check if request was successful
    if response.status_code == 201:
        result = response.json()
        print(f"Blog post published successfully!")
        print(f"Title: {result['blog']['title']}")
        print(f"URL: {result['blog']['url']}")
        return result
    else:
        print(f"Error publishing blog post: {response.text}")
        return None

# Example usage
if __name__ == '__main__':
    # Example blog post
    title = "5 Effective Study Techniques for Better Learning"
    content = """
    <h2>Introduction</h2>
    <p>Studying effectively is crucial for academic success. Here are five proven techniques that can help you learn better and retain information longer.</p>
    
    <h2>1. The Pomodoro Technique</h2>
    <p>The Pomodoro Technique involves studying in focused 25-minute intervals, followed by short breaks. This helps maintain concentration and prevents mental fatigue.</p>
    
    <h2>2. Active Recall</h2>
    <p>Instead of passively reading, test yourself on the material. This strengthens memory and helps identify areas that need more review.</p>
    
    <h2>3. Spaced Repetition</h2>
    <p>Review material at increasing intervals over time. This method helps move information from short-term to long-term memory.</p>
    
    <h2>4. Mind Mapping</h2>
    <p>Create visual representations of concepts and their relationships. This helps understand complex topics and see the bigger picture.</p>
    
    <h2>5. Teaching Others</h2>
    <p>Explaining concepts to others helps solidify your understanding and reveals gaps in your knowledge.</p>
    """
    
    introduction = "Discover five scientifically-proven study techniques that can help you learn more effectively and retain information longer."
    
    toc = """
    <ul>
        <li><a href="#introduction">Introduction</a></li>
        <li><a href="#pomodoro">The Pomodoro Technique</a></li>
        <li><a href="#active-recall">Active Recall</a></li>
        <li><a href="#spaced-repetition">Spaced Repetition</a></li>
        <li><a href="#mind-mapping">Mind Mapping</a></li>
        <li><a href="#teaching">Teaching Others</a></li>
    </ul>
    """
    
    # Publish the blog post
    result = publish_blog_post(title, content, introduction, toc)
