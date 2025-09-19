#!/usr/bin/env python3

# Helpers for interacting with GitHub's API
import requests
import json
import time
import os
import sys
import re
from collections import defaultdict
from colorama import init, Fore, Back, Style
import base64

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Color utilities for consistent styling
class Colors:
    SUCCESS = Fore.GREEN + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.BLUE + Style.BRIGHT
    PROGRESS = Fore.CYAN
    RESET = Style.RESET_ALL

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    def __init__(self, message):
        super().__init__(message)

class RestAPI:
    def __init__(self, token=None, repositories=None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAPIError("GITHUB_TOKEN environment variable not set.")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.search_url = "https://api.github.com/search/code"
        self.repositories = repositories or defaultdict(lambda: {"files": []})
        
    def __query_api(self, params):
        response = requests.get(self.search_url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"{Colors.ERROR}❌ Error: {response.status_code}{Colors.RESET}")
            print(response.json())
            raise GitHubAPIError(f"GitHub REST API request failed with status {response.status_code}: {response.text}")
        return (response, response.json().get("items", []))
    
    def __update_repo(self, repo_name, file_path, file_url, raw_url=None):
        if repo_name not in self.repositories:
            self.repositories[repo_name] = {
                "name": repo_name,
                "url": "",
                "stars": 0,     # Too expensive to fetch using REST API, we can use GraphQL later
                "description": "",
                "files": []
            } 
        self.repositories[repo_name]["files"].append({
            "path": file_path,
            "url": file_url,
            "raw_url": raw_url,
            "keywords_found": [],
            "keyword_match": False
        })

    def __fetch_file_content(self, raw_url):
        """Fetch the raw content of a file from GitHub"""
        try:
            response = requests.get(raw_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                # Try to decode as text, fallback to raw if it fails
                try:
                    return response.text
                except UnicodeDecodeError:
                    return response.content.decode('utf-8', errors='ignore')
            else:
                return None
        except Exception as e:
            print(f"{Colors.WARNING}⚠️  Could not fetch content from {raw_url}: {e}{Colors.RESET}")
            return None

    def __check_keywords_in_content(self, content, keywords):
        """Check if any of the keywords are present in the file content"""
        if not content or not keywords:
            return [], False
        
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in keywords:
            # Use regex for more flexible matching
            if re.search(re.escape(keyword.lower()), content_lower):
                found_keywords.append(keyword)
        
        return found_keywords, len(found_keywords) > 0

    def filter_by_keywords(self, keywords):
        """Filter repositories and files based on keyword presence in file content"""
        if not keywords:
            return
        
        print(f"{Colors.INFO}🔍 Filtering files by keywords: {Colors.WARNING}{', '.join(keywords)}{Colors.RESET}")
        
        total_files = sum(len(repo['files']) for repo in self.repositories.values())
        processed_files = 0
        
        for repo_name, repo_data in self.repositories.items():
            files_to_keep = []
            
            for file_info in repo_data['files']:
                processed_files += 1
                if processed_files % 10 == 0 or processed_files == total_files:
                    print(f"{Colors.PROGRESS}📄 Processing file {processed_files}/{total_files}...{Colors.RESET}", end="\r")
                
                # Build raw URL from the GitHub URL
                if file_info.get('url'):
                    # Convert GitHub URL to raw URL
                    raw_url = file_info['url'].replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
                    
                    content = self.__fetch_file_content(raw_url)
                    if content:
                        found_keywords, has_keywords = self.__check_keywords_in_content(content, keywords)
                        file_info['keywords_found'] = found_keywords
                        file_info['keyword_match'] = has_keywords
                        
                        if has_keywords:
                            files_to_keep.append(file_info)
                    else:
                        # If we can't fetch content, keep the file but mark as unknown
                        file_info['keywords_found'] = []
                        file_info['keyword_match'] = None
                        files_to_keep.append(file_info)
                    
                    # Rate limiting
                    time.sleep(0.2)
                else:
                    files_to_keep.append(file_info)
            
            repo_data['files'] = files_to_keep
        
        # Remove repositories with no matching files
        empty_repos = [repo_name for repo_name, repo_data in self.repositories.items() if not repo_data['files']]
        for repo_name in empty_repos:
            del self.repositories[repo_name]
        
        print(f"\n{Colors.SUCCESS}✅ Keyword filtering complete! {len(self.repositories)} repositories have files with matching keywords{Colors.RESET}")
        print()

    def __rate_limit(self, response):
        if "X-RateLimit-Remaining" in response.headers:
            remaining = int(response.headers["X-RateLimit-Remaining"])
            # Only wait if we have very few requests left (0)
            if remaining < 1:
                reset_time = int(response.headers["X-RateLimit-Reset"])
                wait_time = max(reset_time - time.time(), 0) + 1
                print(f"{Colors.WARNING}⏳ Rate limit reached. Waiting {wait_time:.1f} seconds...{Colors.RESET}")
                time.sleep(wait_time)
            else:
                # Small delay to be respectful to the API
                time.sleep(0.5)
        else:
            # Fallback delay if headers are missing
            time.sleep(1)
                
    def search(self, query, language=None, extension=None, per_page=100, max_pages=10, additional_params=None):
        q = query
        if language:
            q += f" language:{language}"
        if extension:
            q += f" extension:{extension}"
        if additional_params:
            q += f" {additional_params}"
        params = {
            "q": q,
            "per_page": per_page
        }
        
        page = 1
        total_pages = max_pages
        print(f"{Colors.INFO}🔍 Searching GitHub for: {Colors.WARNING}'{q}'{Colors.RESET}")

        while page <= total_pages:
            print(f"{Colors.PROGRESS}📄 Fetching page {page}/{total_pages}...{Colors.RESET}", end=" ")
            params["page"] = page
            try:
                response, items = self.__query_api(params)
                print(f"{Colors.SUCCESS}✓ Found {len(items)} items{Colors.RESET}")
            except GitHubAPIError as e:
                print(f"{Colors.ERROR}✗ Failed{Colors.RESET}")
                break
            
            if not items:
                print(f"{Colors.WARNING}ℹ️  No more results found.{Colors.RESET}")
                break
            
            for item in items:
                repo_name = item.get("repository", {}).get("full_name")
                if repo_name:
                    self.__update_repo(repo_name, item.get("path"), item.get("html_url"))
                    
            page += 1
            self.__rate_limit(response)

        print(f"{Colors.SUCCESS}✅ Search complete! Found {len(self.repositories)} unique repositories{Colors.RESET}")
        print()


class GraphQLAPI:
    def __init__(self, token=None, repositories=None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAPIError("GITHUB_TOKEN environment variable not set.")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.graphql_url = "https://api.github.com/graphql"
        
        self.repositories = repositories or defaultdict(lambda: {"files": []})
    
    def __fetch_repo_data(self, repo_names):
        query_parts = []
        variables = {}
        
        for i, full_name in enumerate(repo_names):
            owner, name = full_name.split("/")
            query_parts.append(f"""
            repo{i}: repository(owner: "{owner}", name: "{name}") {{
                nameWithOwner
                stargazerCount
                description
                url
            }}
            """)
        
        graphql_query = """
        query {
            """ + "\n".join(query_parts) + """
        }
        """
        
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": graphql_query}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise GitHubAPIError(f"GraphQL API request failed with status {response.status_code}: {response.text}")
        
    def __update_repo(self, repo_name, stars, description, url):
        self.repositories[repo_name].update({
            "stars": stars,
            "description": description,
            "url": url
        })
        
    def batch_query(self, batch_size=25):
        """
        Fetch star counts and other details for a list of repositories.
        :return: None, updates the repositories in place.
        """
        repo_names = list(self.repositories.keys())
        total_batches = (len(repo_names) + batch_size - 1) // batch_size
        
        print(f"{Colors.INFO}📊 Fetching repository details in {total_batches} batch{'es' if total_batches != 1 else ''}...{Colors.RESET}")
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(repo_names))
            batch_repos = repo_names[start_idx:end_idx]
            
            print(f"{Colors.PROGRESS}⚡ Processing batch {batch_idx + 1}/{total_batches} ({len(batch_repos)} repositories){Colors.RESET}", end=" ")
            try:
                graphql_data = self.__fetch_repo_data(batch_repos)
                print(f"{Colors.SUCCESS}✓{Colors.RESET}")
            except GitHubAPIError as e:
                print(f"{Colors.ERROR}✗ Error: {e}{Colors.RESET}")
                continue
            
            if "errors" in graphql_data:
                print(f"{Colors.ERROR}⚠️  GraphQL Errors:{Colors.RESET}")
                print(json.dumps(graphql_data["errors"], indent=2))
                
            if "data" in graphql_data:
                for i, full_name in enumerate(batch_repos):
                    repo_data = graphql_data["data"].get(f"repo{i}")
                    if repo_data:
                        self.__update_repo(repo_name=full_name,
                                      stars=repo_data.get("stargazerCount", 0),
                                      description=repo_data.get("description", ""),
                                      url=repo_data.get("url")
                                      )
            time.sleep(2)
        
        print(f"{Colors.SUCCESS}✅ Repository details fetched successfully!{Colors.RESET}")
        print()
