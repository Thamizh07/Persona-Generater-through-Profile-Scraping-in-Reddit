#!/usr/bin/env python3
"""
Reddit User Persona Generator
A script that scrapes Reddit user profiles and generates detailed user personas
using AI analysis of their posts and comments.
"""
import requests
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import argparse
import os
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RedditPost:
    """Data class for Reddit posts/comments"""
    title: str
    content: str
    subreddit: str
    score: int
    created_utc: float
    post_type: str  # 'post' or 'comment'
    url: str
    permalink: str

class RedditScraper:
    """Scrapes Reddit user data using the public JSON API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PersonaGenerator/1.0 (by /u/research_bot)'
        })
        self.rate_limit_delay = 2  # seconds between requests
    
    def extract_username(self, profile_url: str) -> str:
        """Extract username from Reddit profile URL"""
        parsed_url = urlparse(profile_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) >= 2 and path_parts[0] == 'user':
            return path_parts[1]
        else:
            raise ValueError(f"Invalid Reddit profile URL: {profile_url}")
    
    def scrape_user_data(self, username: str, limit: int = 100) -> List[RedditPost]:
        """Scrape posts and comments from a Reddit user"""
        posts = []
        
        # Get user's posts
        posts.extend(self._get_user_posts(username, limit))
        
        # Get user's comments
        posts.extend(self._get_user_comments(username, limit))
        
        # Sort by creation time (newest first)
        posts.sort(key=lambda x: x.created_utc, reverse=True)
        
        return posts
    
    def _get_user_posts(self, username: str, limit: int) -> List[RedditPost]:
        """Get user's submitted posts"""
        url = f"https://www.reddit.com/user/{username}/submitted.json?limit={limit}"
        return self._fetch_reddit_data(url, 'post')
    
    def _get_user_comments(self, username: str, limit: int) -> List[RedditPost]:
        """Get user's comments"""
        url = f"https://www.reddit.com/user/{username}/comments.json?limit={limit}"
        return self._fetch_reddit_data(url, 'comment')
    
    def _fetch_reddit_data(self, url: str, post_type: str) -> List[RedditPost]:
        """Fetch and parse Reddit JSON data"""
        try:
            logger.info(f"Fetching {post_type}s from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = []
            
            if 'data' in data and 'children' in data['data']:
                for item in data['data']['children']:
                    post_data = item['data']
                    
                    # Extract relevant information
                    if post_type == 'post':
                        title = post_data.get('title', '')
                        content = post_data.get('selftext', '')
                    else:  # comment
                        title = f"Comment on: {post_data.get('link_title', 'Unknown')}"
                        content = post_data.get('body', '')
                    
                    # Skip deleted/removed content
                    if content in ['[deleted]', '[removed]', '']:
                        continue
                    
                    post = RedditPost(
                        title=title,
                        content=content,
                        subreddit=post_data.get('subreddit', ''),
                        score=post_data.get('score', 0),
                        created_utc=post_data.get('created_utc', 0),
                        post_type=post_type,
                        url=post_data.get('url', ''),
                        permalink=f"https://www.reddit.com{post_data.get('permalink', '')}"
                    )
                    posts.append(post)
            
            time.sleep(self.rate_limit_delay)  # Rate limiting
            return posts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {url}: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {url}: {e}")
            return []

class PersonaGenerator:
    """Generates user personas using AI analysis"""
    
    def __init__(self):
        self.persona_template = {
            "Basic Information": {
                "Age Range": "",
                "Gender": "",
                "Location": "",
                "Occupation": ""
            },
            "Interests and Hobbies": [],
            "Personality Traits": [],
            "Communication Style": "",
            "Values and Beliefs": [],
            "Technology Usage": "",
            "Social Behavior": "",
            "Goals and Aspirations": [],
            "Challenges and Pain Points": [],
            "Lifestyle": ""
        }
    
    def generate_persona(self, posts: List[RedditPost], username: str) -> Dict:
        """Generate a user persona from Reddit posts"""
        if not posts:
            return {"error": "No posts found for analysis"}
        
        # Analyze posts to extract persona characteristics
        persona = self._analyze_posts(posts)
        persona["username"] = username
        persona["analysis_date"] = datetime.now().isoformat()
        persona["total_posts_analyzed"] = len(posts)
        
        return persona
    
    def _analyze_posts(self, posts: List[RedditPost]) -> Dict:
        """Analyze posts to extract persona characteristics"""
        persona = {}
        citations = {}
        
        # Extract basic information
        persona["Basic Information"] = self._extract_basic_info(posts, citations)
        
        # Extract interests from subreddits and content
        persona["Interests and Hobbies"] = self._extract_interests(posts, citations)
        
        # Analyze personality traits
        persona["Personality Traits"] = self._extract_personality_traits(posts, citations)
        
        # Analyze communication style
        persona["Communication Style"] = self._analyze_communication_style(posts, citations)
        
        # Extract values and beliefs
        persona["Values and Beliefs"] = self._extract_values_beliefs(posts, citations)
        
        # Analyze technology usage
        persona["Technology Usage"] = self._analyze_tech_usage(posts, citations)
        
        # Analyze social behavior
        persona["Social Behavior"] = self._analyze_social_behavior(posts, citations)
        
        # Extract goals and aspirations
        persona["Goals and Aspirations"] = self._extract_goals(posts, citations)
        
        # Extract challenges and pain points
        persona["Challenges and Pain Points"] = self._extract_challenges(posts, citations)
        
        # Analyze lifestyle
        persona["Lifestyle"] = self._analyze_lifestyle(posts, citations)
        
        # Add citations
        persona["Citations"] = citations
        
        return persona
    
    def _extract_basic_info(self, posts: List[RedditPost], citations: Dict) -> Dict:
        """Extract basic demographic information"""
        basic_info = {
            "Age Range": "Unknown",
            "Gender": "Unknown",
            "Location": "Unknown",
            "Occupation": "Unknown"
        }
        
        citations["Basic Information"] = []
        
        # Age indicators
        age_keywords = {
            "teen": "13-19",
            "college": "18-25",
            "university": "18-25",
            "student": "18-25",
            "graduated": "22-30",
            "career": "25-40",
            "retirement": "60+",
            "kids": "25-45",
            "children": "25-45"
        }
        
        # Gender indicators
        gender_keywords = {
            "boyfriend": "female",
            "girlfriend": "male",
            "husband": "female",
            "wife": "male",
            "m/": "male",
            "f/": "female"
        }
        
        # Location indicators
        location_keywords = ["live in", "from", "in my city", "my state", "my country"]
        
        # Occupation indicators
        occupation_keywords = ["work as", "job", "profession", "career", "employed", "developer", "teacher", "nurse", "engineer"]
        
        for post in posts:
            content = (post.title + " " + post.content).lower()
            
            # Check for age indicators
            for keyword, age_range in age_keywords.items():
                if keyword in content and basic_info["Age Range"] == "Unknown":
                    basic_info["Age Range"] = age_range
                    citations["Basic Information"].append({
                        "characteristic": "Age Range",
                        "value": age_range,
                        "source": post.permalink,
                        "context": content[:200] + "..."
                    })
            
            # Check for gender indicators
            for keyword, gender in gender_keywords.items():
                if keyword in content and basic_info["Gender"] == "Unknown":
                    basic_info["Gender"] = gender
                    citations["Basic Information"].append({
                        "characteristic": "Gender",
                        "value": gender,
                        "source": post.permalink,
                        "context": content[:200] + "..."
                    })
            
            # Check for location
            for keyword in location_keywords:
                if keyword in content and basic_info["Location"] == "Unknown":
                    # Extract location context
                    location_match = re.search(f"{keyword}\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)", content)
                    if location_match:
                        basic_info["Location"] = location_match.group(1)
                        citations["Basic Information"].append({
                            "characteristic": "Location",
                            "value": location_match.group(1),
                            "source": post.permalink,
                            "context": content[:200] + "..."
                        })
            
            # Check for occupation
            for keyword in occupation_keywords:
                if keyword in content and basic_info["Occupation"] == "Unknown":
                    basic_info["Occupation"] = "Professional/Working"
                    citations["Basic Information"].append({
                        "characteristic": "Occupation",
                        "value": "Professional/Working",
                        "source": post.permalink,
                        "context": content[:200] + "..."
                    })
        
        return basic_info
    
    def _extract_interests(self, posts: List[RedditPost], citations: Dict) -> List[str]:
        """Extract interests from subreddits and content"""
        interests = set()
        citations["Interests and Hobbies"] = []
        
        # Count subreddit participation
        subreddit_counts = {}
        for post in posts:
            if post.subreddit:
                subreddit_counts[post.subreddit] = subreddit_counts.get(post.subreddit, 0) + 1
        
        # Top subreddits indicate interests
        top_subreddits = sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for subreddit, count in top_subreddits:
            if count >= 2:  # Only include subreddits with multiple posts
                interests.add(subreddit)
                citations["Interests and Hobbies"].append({
                    "characteristic": "Interest",
                    "value": subreddit,
                    "source": f"Multiple posts in r/{subreddit}",
                    "context": f"Posted {count} times in r/{subreddit}"
                })
        
        # Look for hobby-related keywords
        hobby_keywords = [
            "hobby", "love", "enjoy", "passionate", "interested", "collect",
            "gaming", "reading", "music", "sports", "cooking", "art", "travel",
            "fitness", "photography", "programming", "writing", "movies"
        ]
        
        for post in posts:
            content = (post.title + " " + post.content).lower()
            for keyword in hobby_keywords:
                if keyword in content:
                    interests.add(keyword.title())
                    citations["Interests and Hobbies"].append({
                        "characteristic": "Interest",
                        "value": keyword.title(),
                        "source": post.permalink,
                        "context": content[:200] + "..."
                    })
        
        return list(interests)
    
    def _extract_personality_traits(self, posts: List[RedditPost], citations: Dict) -> List[str]:
        """Extract personality traits from writing style and content"""
        traits = []
        citations["Personality Traits"] = []
        
        # Analyze writing patterns
        total_posts = len(posts)
        long_posts = sum(1 for post in posts if len(post.content) > 200)
        question_posts = sum(1 for post in posts if '?' in post.title or '?' in post.content)
        help_posts = sum(1 for post in posts if any(word in (post.title + post.content).lower() 
                                                   for word in ['help', 'advice', 'question', 'how to']))
        
        # Determine traits based on patterns
        if long_posts / total_posts > 0.3:
            traits.append("Detailed/Thorough")
            citations["Personality Traits"].append({
                "characteristic": "Detailed/Thorough",
                "value": "True",
                "source": "Writing pattern analysis",
                "context": f"{long_posts}/{total_posts} posts are detailed (>200 chars)"
            })
        
        if question_posts / total_posts > 0.4:
            traits.append("Curious/Inquisitive")
            citations["Personality Traits"].append({
                "characteristic": "Curious/Inquisitive",
                "value": "True",
                "source": "Content analysis",
                "context": f"{question_posts}/{total_posts} posts contain questions"
            })
        
        if help_posts / total_posts > 0.3:
            traits.append("Help-seeking")
            citations["Personality Traits"].append({
                "characteristic": "Help-seeking",
                "value": "True",
                "source": "Content analysis",
                "context": f"{help_posts}/{total_posts} posts seek help or advice"
            })
        
        # Look for emotional indicators
        positive_words = ['great', 'awesome', 'love', 'amazing', 'excellent', 'fantastic']
        negative_words = ['hate', 'terrible', 'awful', 'worst', 'horrible', 'annoying']
        
        positive_count = sum(1 for post in posts for word in positive_words 
                           if word in (post.title + post.content).lower())
        negative_count = sum(1 for post in posts for word in negative_words 
                           if word in (post.title + post.content).lower())
        
        if positive_count > negative_count * 2:
            traits.append("Optimistic")
            citations["Personality Traits"].append({
                "characteristic": "Optimistic",
                "value": "True",
                "source": "Language analysis",
                "context": f"Uses positive language more frequently ({positive_count} vs {negative_count})"
            })
        
        return traits
    
    def _analyze_communication_style(self, posts: List[RedditPost], citations: Dict) -> str:
        """Analyze communication style"""
        citations["Communication Style"] = []
        
        if not posts:
            return "Unknown"
        
        # Calculate average post length
        avg_length = sum(len(post.content) for post in posts) / len(posts)
        
        # Count formal vs informal indicators
        formal_indicators = ['however', 'therefore', 'furthermore', 'moreover', 'consequently']
        informal_indicators = ['lol', 'omg', 'wtf', 'tbh', 'imo', 'btw', 'basically', 'like']
        
        formal_count = sum(1 for post in posts for word in formal_indicators 
                          if word in (post.title + post.content).lower())
        informal_count = sum(1 for post in posts for word in informal_indicators 
                           if word in (post.title + post.content).lower())
        
        if avg_length > 150:
            if formal_count > informal_count:
                style = "Formal and detailed"
            else:
                style = "Conversational and detailed"
        else:
            if informal_count > formal_count:
                style = "Casual and concise"
            else:
                style = "Direct and concise"
        
        citations["Communication Style"].append({
            "characteristic": "Communication Style",
            "value": style,
            "source": "Language pattern analysis",
            "context": f"Average post length: {avg_length:.0f} chars, Formal: {formal_count}, Informal: {informal_count}"
        })
        
        return style
    
    def _extract_values_beliefs(self, posts: List[RedditPost], citations: Dict) -> List[str]:
        """Extract values and beliefs from content"""
        values = []
        citations["Values and Beliefs"] = []
        
        # Value indicators
        value_keywords = {
            "family": ["family", "parents", "siblings", "relatives"],
            "education": ["learning", "education", "school", "knowledge"],
            "health": ["health", "fitness", "exercise", "wellness"],
            "career": ["career", "job", "profession", "work"],
            "relationships": ["friends", "friendship", "dating", "relationship"],
            "creativity": ["art", "creative", "music", "writing"],
            "technology": ["tech", "programming", "coding", "innovation"],
            "environment": ["environment", "climate", "sustainability", "green"],
            "social justice": ["justice", "equality", "rights", "fair"]
        }
        
        for post in posts:
            content = (post.title + " " + post.content).lower()
            for value, keywords in value_keywords.items():
                for keyword in keywords:
                    if keyword in content and value not in values:
                        values.append(value)
                        citations["Values and Beliefs"].append({
                            "characteristic": "Value",
                            "value": value,
                            "source": post.permalink,
                            "context": content[:200] + "..."
                        })
                        break
        
        return values
    
    def _analyze_tech_usage(self, posts: List[RedditPost], citations: Dict) -> str:
        """Analyze technology usage patterns"""
        citations["Technology Usage"] = []
        
        tech_subreddits = ['technology', 'programming', 'coding', 'apple', 'android', 'windows', 'linux']
        tech_keywords = ['app', 'software', 'computer', 'phone', 'device', 'tech', 'digital']
        
        tech_posts = [post for post in posts if post.subreddit.lower() in tech_subreddits or 
                     any(keyword in (post.title + post.content).lower() for keyword in tech_keywords)]
        
        if len(tech_posts) / len(posts) > 0.3:
            usage = "Tech-savvy and engaged"
        elif len(tech_posts) / len(posts) > 0.1:
            usage = "Moderate technology user"
        else:
            usage = "Basic technology user"
        
        citations["Technology Usage"].append({
            "characteristic": "Technology Usage",
            "value": usage,
            "source": "Content analysis",
            "context": f"{len(tech_posts)}/{len(posts)} posts are tech-related"
        })
        
        return usage
    
    def _analyze_social_behavior(self, posts: List[RedditPost], citations: Dict) -> str:
        """Analyze social behavior patterns"""
        citations["Social Behavior"] = []
        
        # Count different types of social interactions
        question_posts = sum(1 for post in posts if '?' in post.title or '?' in post.content)
        help_posts = sum(1 for post in posts if any(word in (post.title + post.content).lower() 
                                                   for word in ['help', 'advice', 'support']))
        discussion_posts = sum(1 for post in posts if any(word in (post.title + post.content).lower() 
                                                          for word in ['discuss', 'opinion', 'think', 'thoughts']))
        
        total_posts = len(posts)
        
        if help_posts / total_posts > 0.3:
            behavior = "Help-seeking and community-oriented"
        elif discussion_posts / total_posts > 0.3:
            behavior = "Discussion-focused and opinionated"
        elif question_posts / total_posts > 0.4:
            behavior = "Curious and inquisitive"
        else:
            behavior = "Selective participant"
        
        citations["Social Behavior"].append({
            "characteristic": "Social Behavior",
            "value": behavior,
            "source": "Interaction pattern analysis",
            "context": f"Help: {help_posts}, Discussion: {discussion_posts}, Questions: {question_posts} out of {total_posts}"
        })
        
        return behavior
    
    def _extract_goals(self, posts: List[RedditPost], citations: Dict) -> List[str]:
        """Extract goals and aspirations"""
        goals = []
        citations["Goals and Aspirations"] = []
        
        goal_keywords = {
            "career advancement": ["promotion", "career", "job", "professional", "advance"],
            "education": ["degree", "study", "learn", "education", "course"],
            "health and fitness": ["lose weight", "fitness", "healthy", "exercise", "gym"],
            "relationships": ["relationship", "dating", "marriage", "family"],
            "financial": ["money", "save", "invest", "financial", "budget"],
            "personal growth": ["improve", "better", "growth", "develop", "skills"],
            "travel": ["travel", "trip", "vacation", "visit", "explore"],
            "hobbies": ["hobby", "passion", "interest", "enjoy", "fun"]
        }
        
        for post in posts:
            content = (post.title + " " + post.content).lower()
            for goal, keywords in goal_keywords.items():
                if any(keyword in content for keyword in keywords) and goal not in goals:
                    goals.append(goal)
                    citations["Goals and Aspirations"].append({
                        "characteristic": "Goal",
                        "value": goal,
                        "source": post.permalink,
                        "context": content[:200] + "..."
                    })
        
        return goals
    
    def _extract_challenges(self, posts: List[RedditPost], citations: Dict) -> List[str]:
        """Extract challenges and pain points"""
        challenges = []
        citations["Challenges and Pain Points"] = []
        
        challenge_keywords = {
            "work stress": ["stress", "work", "job", "pressure", "overwhelmed"],
            "financial concerns": ["money", "expensive", "afford", "budget", "financial"],
            "health issues": ["pain", "sick", "health", "doctor", "medical"],
            "relationship problems": ["relationship", "breakup", "argument", "conflict"],
            "time management": ["time", "busy", "schedule", "rushed", "deadline"],
            "social anxiety": ["anxiety", "social", "nervous", "awkward", "uncomfortable"],
            "decision making": ["decision", "choice", "confused", "unsure", "help"]
        }
        
        for post in posts:
            content = (post.title + " " + post.content).lower()
            for challenge, keywords in challenge_keywords.items():
                if any(keyword in content for keyword in keywords) and challenge not in challenges:
                    challenges.append(challenge)
                    citations["Challenges and Pain Points"].append({
                        "characteristic": "Challenge",
                        "value": challenge,
                        "source": post.permalink,
                        "context": content[:200] + "..."
                    })
        
        return challenges
    
    def _analyze_lifestyle(self, posts: List[RedditPost], citations: Dict) -> str:
        """Analyze lifestyle patterns"""
        citations["Lifestyle"] = []
        
        # Analyze posting patterns and content
        activity_level = "moderate"
        work_life_balance = "balanced"
        
        # Check for lifestyle indicators
        lifestyle_keywords = {
            "active": ["gym", "exercise", "run", "sport", "active", "fitness"],
            "social": ["friends", "party", "social", "hangout", "meet"],
            "homebody": ["home", "indoor", "staying in", "cozy", "quiet"],
            "busy": ["busy", "schedule", "time", "rushed", "deadline"],
            "relaxed": ["relax", "chill", "calm", "peaceful", "easy"]
        }
        
        lifestyle_scores = {}
        for post in posts:
            content = (post.title + " " + post.content).lower()
            for lifestyle, keywords in lifestyle_keywords.items():
                score = sum(1 for keyword in keywords if keyword in content)
                lifestyle_scores[lifestyle] = lifestyle_scores.get(lifestyle, 0) + score
        
        if lifestyle_scores:
            dominant_lifestyle = max(lifestyle_scores, key=lifestyle_scores.get)
            lifestyle = f"{dominant_lifestyle.title()} lifestyle"
        else:
            lifestyle = "Balanced lifestyle"
        
        citations["Lifestyle"].append({
            "characteristic": "Lifestyle",
            "value": lifestyle,
            "source": "Content analysis",
            "context": f"Lifestyle indicators: {lifestyle_scores}"
        })
        
        return lifestyle

def save_persona_to_file(persona: Dict, username: str, output_dir: str = "output"):
    """Save persona to a text file"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = f"{output_dir}/{username}_persona.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"USER PERSONA: {username}\n")
        f.write("=" * 50 + "\n\n")
        
        # Write analysis metadata
        f.write(f"Analysis Date: {persona.get('analysis_date', 'Unknown')}\n")
        f.write(f"Total Posts Analyzed: {persona.get('total_posts_analyzed', 'Unknown')}\n\n")
        
        # Write persona characteristics
        for category, data in persona.items():
            if category in ['username', 'analysis_date', 'total_posts_analyzed', 'Citations']:
                continue
            
            f.write(f"{category.upper()}:\n")
            f.write("-" * 30 + "\n")
            
            if isinstance(data, dict):
                for key, value in data.items():
                    f.write(f"  {key}: {value}\n")
            elif isinstance(data, list):
                for item in data:
                    f.write(f"  • {item}\n")
            else:
                f.write(f"  {data}\n")
            
            f.write("\n")
        
        # Write citations
        if 'Citations' in persona:
            f.write("CITATIONS:\n")
            f.write("=" * 50 + "\n\n")
            
            for category, citations in persona['Citations'].items():
                if citations:
                    f.write(f"{category}:\n")
                    f.write("-" * 30 + "\n")
                    
                    for citation in citations:
                        f.write(f"  Characteristic: {citation['characteristic']}\n")
                        f.write(f"  Value: {citation['value']}\n")
                        f.write(f"  Source: {citation['source']}\n")
                        f.write(f"  Context: {citation['context']}\n")
                        f.write("\n")
    
    logger.info(f"Persona saved to {filename}")
    return filename

def main():
    """Main function to run the Reddit persona generator"""
    parser = argparse.ArgumentParser(description='Generate user personas from Reddit profiles')
    parser.add_argument('profile_url', nargs='?', help='Reddit profile URL (e.g., https://www.reddit.com/user/username/)')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of posts/comments to analyze')
    parser.add_argument('--output', default='output', help='Output directory for persona files')
    
    args = parser.parse_args()
    
    # If no URL provided as argument, ask for it interactively
    if not args.profile_url:
        print("Reddit User Persona Generator")
        print("=" * 40)
        print("Please provide a Reddit profile URL.")
        print("Examples:")
        print("  https://www.reddit.com/user/kojied/")
        print("  https://www.reddit.com/user/Hungry-Move-6603/")
        print()
        
        profile_url = input("Enter Reddit profile URL: ").strip()
        if not profile_url:
            print("Error: No profile URL provided.")
            return 1
        args.profile_url = profile_url
    
    try:
        # Initialize scraper and generator
        scraper = RedditScraper()
        generator = PersonaGenerator()
        
        # Extract username from URL
        username = scraper.extract_username(args.profile_url)
        logger.info(f"Analyzing Reddit user: {username}")
        
        print(f"\nStarting analysis of Reddit user: u/{username}")
        print("This may take a few minutes...")
        
        # Scrape user data
        posts = scraper.scrape_user_data(username, args.limit)
        logger.info(f"Scraped {len(posts)} posts/comments")
        
        if not posts:
            logger.error("No posts found for this user. The profile might be private or empty.")
            print("Error: No posts found for this user. The profile might be private, empty, or the username might be incorrect.")
            return 1
        
        print(f"Found {len(posts)} posts/comments to analyze...")
        
        # Generate persona
        persona = generator.generate_persona(posts, username)
        
        # Save to file
        output_file = save_persona_to_file(persona, username, args.output)
        
        print(f"\n✓ Persona generation complete!")
        print(f"✓ Results saved to: {output_file}")
        print(f"✓ Analyzed {len(posts)} posts/comments from u/{username}")
        
    except ValueError as e:
        logger.error(f"Invalid URL: {e}")
        print(f"Error: {e}")
        print("Please provide a valid Reddit profile URL like: https://www.reddit.com/user/username/")
        return 1
    except Exception as e:
        logger.error(f"Error generating persona: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    main()