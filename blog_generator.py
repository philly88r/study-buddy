import os
import json
import time
import openai
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
import markdown
import re
from slugify import slugify

class BlogGenerator:
    def __init__(self, openai_api_key: str, fal_api_key: str):
        self.openai_api_key = openai_api_key
        self.fal_api_key = fal_api_key
        openai.api_key = openai_api_key

    def generate_seo_title(self, keyword: str) -> str:
        """Generate an SEO-optimized title from a keyword."""
        prompt = f"""Generate an SEO-optimized blog title for the keyword: {keyword}
        The title should:
        - Be compelling and click-worthy
        - Include the main keyword naturally
        - Be between 50-60 characters
        - Address search intent
        - Use power words when appropriate
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip('"')

    def generate_table_of_contents(self, keyword: str, title: str) -> List[str]:
        """Generate a detailed table of contents based on the keyword and title."""
        prompt = f"""Create a detailed table of contents for a blog post about: {keyword}
        Title: {title}
        
        Requirements:
        - Include 8-12 H2 headings that answer "People Also Ask" questions
        - Each H2 should be followed by 2-3 H3 subheadings
        - Focus on search intent and user value
        - Make headings descriptive and informative
        - Include numbers and specific details when relevant
        
        Format each heading as:
        H2: [heading]
        - H3: [subheading]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content.split('\n')

    def generate_introduction(self, keyword: str, title: str) -> str:
        """Generate an engaging introduction based on search intent."""
        prompt = f"""Write an engaging introduction for a blog post:
        Title: {title}
        Keyword: {keyword}
        
        Requirements:
        - Hook the reader in the first sentence
        - Address the search intent clearly
        - Include what the reader will learn
        - Be between 150-200 words
        - End with a transition to the main content
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    def generate_section_content(self, title: str, heading: str, subheadings: List[str]) -> str:
        """Generate content for a specific section."""
        prompt = f"""Write a detailed section for a blog post:
        Article Title: {title}
        Section Heading: {heading}
        Subheadings: {', '.join(subheadings)}
        
        Requirements:
        - Write 300-400 words
        - Include all subheadings
        - Use examples and specific details
        - Make content actionable and valuable
        - Include transition sentences
        - Use proper formatting with markdown
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    def generate_image(self, prompt: str) -> str:
        """Generate an image using fal.ai API."""
        headers = {
            "Authorization": f"Key {self.fal_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "prompt": prompt,
            "image_size": "768x768"  # Adjust size as needed
        }
        
        response = requests.post(
            "https://api.fal.ai/text-to-image",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["image_url"]
        else:
            raise Exception(f"Image generation failed: {response.text}")

    def create_blog_post(self, keyword: str) -> Dict:
        """Create a complete blog post with images."""
        # Generate title
        title = self.generate_seo_title(keyword)
        
        # Generate table of contents
        toc_items = self.generate_table_of_contents(keyword, title)
        
        # Generate introduction
        introduction = self.generate_introduction(keyword, title)
        
        # Process TOC and generate content
        content = ""
        current_h2 = None
        h3_list = []
        
        for item in toc_items:
            if item.strip():
                if item.startswith('H2:'):
                    # Generate content for previous section
                    if current_h2 and h3_list:
                        section_content = self.generate_section_content(title, current_h2, h3_list)
                        # Generate image for H2
                        image_url = self.generate_image(current_h2)
                        content += f"\n## {current_h2}\n\n![{current_h2}]({image_url})\n\n{section_content}\n\n"
                    
                    current_h2 = item.replace('H2:', '').strip()
                    h3_list = []
                elif item.startswith('- H3:'):
                    h3_list.append(item.replace('- H3:', '').strip())
        
        # Generate content for the last section
        if current_h2 and h3_list:
            section_content = self.generate_section_content(title, current_h2, h3_list)
            image_url = self.generate_image(current_h2)
            content += f"\n## {current_h2}\n\n![{current_h2}]({image_url})\n\n{section_content}\n\n"
        
        # Convert markdown to HTML
        html_content = markdown.markdown(content)
        html_introduction = markdown.markdown(introduction)
        
        # Generate TOC HTML
        toc_html = self.generate_toc_html(toc_items)
        
        return {
            'title': title,
            'introduction': html_introduction,
            'content': html_content,
            'toc': toc_html,
            'slug': slugify(title)
        }

    def generate_toc_html(self, toc_items: List[str]) -> str:
        """Generate HTML for table of contents with proper linking."""
        html = '<ul class="toc">'
        for item in toc_items:
            if item.strip():
                if item.startswith('H2:'):
                    heading = item.replace('H2:', '').strip()
                    slug = slugify(heading)
                    html += f'<li><a href="#{slug}">{heading}</a>'
                    html += '<ul>'
                elif item.startswith('- H3:'):
                    heading = item.replace('- H3:', '').strip()
                    slug = slugify(heading)
                    html += f'<li><a href="#{slug}">{heading}</a></li>'
                elif item.startswith('</ul>'):
                    html += '</ul></li>'
        html += '</ul>'
        return html

    def bulk_generate(self, keywords: List[str]) -> List[Dict]:
        """Generate multiple blog posts from a list of keywords."""
        blog_posts = []
        for keyword in keywords:
            try:
                blog_post = self.create_blog_post(keyword)
                blog_posts.append(blog_post)
                # Sleep to avoid rate limits
                time.sleep(2)
            except Exception as e:
                print(f"Error generating blog for keyword '{keyword}': {str(e)}")
        return blog_posts
