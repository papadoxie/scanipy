#!/usr/bin/env python3
"""
GitHub API clients for Scanipy.

This module provides REST and GraphQL API wrappers for interacting with GitHub,
including code search, repository metadata fetching, and keyword filtering.
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import requests

from models import Colors

from .models import (
    BATCH_QUERY_DELAY,
    CONTENT_FETCH_TIMEOUT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_PAGES,
    DEFAULT_PER_PAGE,
    DEFAULT_STAR_TIERS,
    DEFAULT_TIMEOUT,
    GITHUB_GRAPHQL_URL,
    GITHUB_REPO_SEARCH_URL,
    GITHUB_REST_SEARCH_URL,
    KEYWORD_FILTER_DELAY,
    MAX_RETRIES,
    PROGRESS_UPDATE_INTERVAL,
    RATE_LIMIT_DELAY,
    RATE_LIMIT_FALLBACK_DELAY,
    RETRY_BACKOFF,
    RETRY_DELAY,
    GitHubAPIError,
    GitHubNetworkError,
    GitHubRateLimitError,
)

# =============================================================================
# Base Client
# =============================================================================


class BaseGitHubClient(ABC):
    """Abstract base class for GitHub API clients."""

    def __init__(
        self,
        token: str | None = None,
        repositories: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the GitHub client.

        Args:
            token: GitHub personal access token. Falls back to GITHUB_TOKEN env var.
            repositories: Existing repository data to use/update.

        Raises:
            GitHubAPIError: If no token is provided or found in environment.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAPIError("GITHUB_TOKEN environment variable not set.")
        self.repositories: dict[str, Any] = repositories or defaultdict(lambda: {"files": []})

    @property
    @abstractmethod
    def _headers(self) -> dict[str, str]:
        """Return headers for API requests."""

    def _create_repo_entry(self, repo_name: str) -> dict[str, Any]:
        """Create a default repository entry structure."""
        return {
            "name": repo_name,
            "url": "",
            "stars": 0,
            "description": "",
            "files": [],
        }

    def _create_file_entry(
        self,
        path: str,
        url: str,
        raw_url: str | None = None,
    ) -> dict[str, Any]:
        """Create a default file entry structure."""
        return {
            "path": path,
            "url": url,
            "raw_url": raw_url,
            "keywords_found": [],
            "keyword_match": None,  # None = not checked, True = found, False = not found
        }

    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = MAX_RETRIES,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic for transient failures.

        Args:
            method: HTTP method ('get' or 'post').
            url: The URL to request.
            max_retries: Maximum number of retry attempts.
            **kwargs: Additional arguments passed to requests.

        Returns:
            The response object.

        Raises:
            GitHubNetworkError: If all retries fail due to network issues.
            GitHubRateLimitError: If rate limit is exceeded.
            GitHubAPIError: For other API errors.
        """
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("headers", self._headers)

        last_exception: Exception | None = None

        for attempt in range(max_retries):
            try:
                if method.lower() == "get":
                    response = requests.get(url, **kwargs)
                elif method.lower() == "post":
                    response = requests.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for rate limiting
                if response.status_code == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining", "")
                    if remaining == "0":
                        reset_time = response.headers.get("X-RateLimit-Reset", "")
                        raise GitHubRateLimitError(
                            f"GitHub API rate limit exceeded. Resets at: {reset_time}"
                        )

                # Check for secondary rate limit
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise GitHubRateLimitError(
                        f"Secondary rate limit hit. Retry after: {retry_after}s"
                    )

                return response

            except requests.exceptions.ConnectionError as e:
                last_exception = GitHubNetworkError(f"Connection error: {e}")
            except requests.exceptions.Timeout as e:
                last_exception = GitHubNetworkError(f"Request timeout: {e}")
            except requests.exceptions.RequestException as e:
                last_exception = GitHubNetworkError(f"Request failed: {e}")
            except GitHubRateLimitError:
                raise  # Don't retry rate limit errors

            # Wait before retrying with exponential backoff
            if attempt < max_retries - 1:
                delay = RETRY_DELAY * (RETRY_BACKOFF**attempt)
                print(
                    f"\n{Colors.WARNING}⚠️  Request failed, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries})...{Colors.RESET}",
                    end=" ",
                )
                time.sleep(delay)

        # All retries exhausted
        raise last_exception or GitHubNetworkError("Request failed after all retries")


# =============================================================================
# REST API Client
# =============================================================================


class RestAPI(BaseGitHubClient):
    """Client for GitHub's REST API code search endpoint."""

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        language: str | None = None,
        extension: str | None = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int = DEFAULT_MAX_PAGES,
        additional_params: str | None = None,
    ) -> None:
        """
        Search GitHub for code matching the query.

        Args:
            query: The search query string.
            language: Filter by programming language.
            extension: Filter by file extension.
            per_page: Number of results per page (max 100).
            max_pages: Maximum number of pages to fetch.
            additional_params: Additional GitHub search qualifiers.
        """
        full_query = self._build_search_query(query, language, extension, additional_params)
        params: dict[str, Any] = {"q": full_query, "per_page": per_page}

        print(f"{Colors.INFO}🔍 Searching GitHub for: {Colors.WARNING}'{full_query}'{Colors.RESET}")

        for page in range(1, max_pages + 1):
            print(f"{Colors.PROGRESS}📄 Fetching page {page}/{max_pages}...{Colors.RESET}", end=" ")
            params["page"] = page

            try:
                response, items = self._execute_search(params)
                print(f"{Colors.SUCCESS}✓ Found {len(items)} items{Colors.RESET}")
            except GitHubAPIError:
                print(f"{Colors.ERROR}✗ Failed{Colors.RESET}")
                break

            if not items:
                print(f"{Colors.WARNING}(i) No more results found.{Colors.RESET}")
                break

            self._process_search_results(items)
            self._handle_rate_limit(response)

        repo_count = len(self.repositories)
        print(f"{Colors.SUCCESS}✅ Search complete! Found {repo_count} unique repos{Colors.RESET}")
        print()

    def search_by_stars(
        self,
        query: str,
        language: str | None = None,
        extension: str | None = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int = 10,
        star_tiers: list[tuple[int, int | None]] | None = None,
        additional_params: str | None = None,
    ) -> None:
        """
        Search GitHub for code using tiered star-based searching.

        This method uses a two-step approach:
        1. Find popular repositories by star count using repository search API
        2. Search for the code pattern within those specific repositories

        This works around GitHub's inability to sort code search results by stars.
        Pages are consumed tier by tier, exhausting higher-star tiers first before
        moving to lower-star tiers. This ensures repos are truly sorted by stars.

        Args:
            query: The search query string.
            language: Filter by programming language.
            extension: Filter by file extension.
            per_page: Number of results per page (max 100).
            max_pages: Total page budget across all tiers. Higher tiers are exhausted first.
            star_tiers: List of (min_stars, max_stars) tuples. Use None for no upper limit.
                        Defaults to DEFAULT_STAR_TIERS.
            additional_params: Additional GitHub search qualifiers.
        """
        tiers = star_tiers or DEFAULT_STAR_TIERS
        pages_remaining = max_pages

        print(f"{Colors.HEADER}{'═' * 60}{Colors.RESET}")
        print(
            f"{Colors.INFO}🌟 Starting tiered star search across {len(tiers)} tiers{Colors.RESET}"
        )
        print(f"{Colors.INFO}📄 Total page budget: {max_pages} pages{Colors.RESET}")
        print(f"{Colors.HEADER}{'═' * 60}{Colors.RESET}")

        total_repos_before = len(self.repositories)

        for tier_idx, (min_stars, max_stars) in enumerate(tiers, 1):
            if pages_remaining <= 0:
                break  # Stop processing tiers when page budget is exhausted

            tier_label = self._format_tier_label(min_stars, max_stars)
            print(
                f"\n{Colors.INFO}📊 Tier {tier_idx}/{len(tiers)}: {tier_label} "
                f"({pages_remaining} pages remaining){Colors.RESET}"
            )

            # Step 1: Find repositories in this star tier (use all remaining pages)
            candidate_repos, pages_used = self._find_repos_by_stars(
                min_stars=min_stars,
                max_stars=max_stars,
                language=language,
                per_page=per_page,
                max_pages=pages_remaining,
            )
            pages_remaining -= pages_used

            if not candidate_repos:
                print(f"{Colors.WARNING}  (i) No repositories found in this tier.{Colors.RESET}")
                continue

            repo_count = len(candidate_repos)
            print(
                f"{Colors.PROGRESS}  🔍 Searching for '{query}' "
                f"in {repo_count} repos...{Colors.RESET}"
            )

            # Step 2: Search for code in these repositories
            repos_with_matches = 0
            for repo_name in candidate_repos:
                if repo_name in self.repositories:
                    continue  # Already have this repo

                matches = self._search_code_in_repo(
                    repo_name=repo_name,
                    query=query,
                    language=language,
                    extension=extension,
                    additional_params=additional_params,
                )

                if matches:
                    repos_with_matches += 1

            print(
                f"{Colors.SUCCESS}  ✅ Tier complete: "
                f"{repos_with_matches} repos with matches{Colors.RESET}"
            )

        total_new = len(self.repositories) - total_repos_before
        total_repos = len(self.repositories)
        print(f"\n{Colors.HEADER}{'═' * 60}{Colors.RESET}")
        print(
            f"{Colors.SUCCESS}🎯 Tiered search complete! "
            f"Found {total_repos} repos ({total_new} new){Colors.RESET}"
        )
        print(f"{Colors.HEADER}{'═' * 60}{Colors.RESET}")
        print()

    def _find_repos_by_stars(
        self,
        min_stars: int,
        max_stars: int | None,
        language: str | None = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int = 1,
    ) -> tuple[list[str], int]:
        """
        Find repositories within a star range using the repository search API.

        Args:
            min_stars: Minimum star count.
            max_stars: Maximum star count (None for no upper limit).
            language: Filter by programming language.
            per_page: Results per page.
            max_pages: Maximum pages to fetch.

        Returns:
            Tuple of (list of repository full names, number of pages actually used).
        """
        star_filter = self._build_star_filter(min_stars, max_stars)
        query_parts = [star_filter]
        if language:
            query_parts.append(f"language:{language}")

        params: dict[str, Any] = {
            "q": " ".join(query_parts),
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
        }

        repos: list[str] = []
        pages_used = 0

        for page in range(1, max_pages + 1):
            params["page"] = page
            print(
                f"{Colors.PROGRESS}  📄 Finding repos (page {page})...{Colors.RESET}",
                end=" ",
            )

            try:
                response = self._request_with_retry("get", GITHUB_REPO_SEARCH_URL, params=params)
                pages_used += 1

                if response.status_code != 200:
                    self._log_api_error(response)
                    print(f"{Colors.ERROR}✗ Failed (status {response.status_code}){Colors.RESET}")
                    break

                items = response.json().get("items", [])
                page_repos = [item["full_name"] for item in items if "full_name" in item]
                repos.extend(page_repos)
                print(f"{Colors.SUCCESS}✓ Found {len(page_repos)} repos{Colors.RESET}")

                # Stop if no more results (tier exhausted)
                if len(items) < per_page:
                    print(
                        f"{Colors.INFO}  (i) Tier exhausted after {pages_used} pages{Colors.RESET}"
                    )
                    break

                self._handle_rate_limit(response)

            except GitHubRateLimitError as e:
                print(f"{Colors.ERROR}✗ Rate limit exceeded: {e}{Colors.RESET}")
                break
            except GitHubNetworkError as e:
                print(f"{Colors.ERROR}✗ Network error: {e}{Colors.RESET}")
                break

        return repos, pages_used

    def _search_code_in_repo(
        self,
        repo_name: str,
        query: str,
        language: str | None = None,
        extension: str | None = None,
        additional_params: str | None = None,
    ) -> bool:
        """
        Search for code pattern in a specific repository.

        Args:
            repo_name: Full repository name (owner/repo).
            query: Code pattern to search for.
            language: Filter by programming language.
            extension: Filter by file extension.
            additional_params: Additional search qualifiers.

        Returns:
            True if matches were found, False otherwise.
        """
        # Build query with repo filter
        full_query = self._build_search_query(query, language, extension, additional_params)
        full_query = f"{full_query} repo:{repo_name}"

        params: dict[str, Any] = {"q": full_query, "per_page": 10}  # Just get first few matches

        try:
            response = self._request_with_retry("get", GITHUB_REST_SEARCH_URL, params=params)

            if response.status_code != 200:
                return False

            items = response.json().get("items", [])
            if items:
                self._process_search_results(items)
                self._handle_rate_limit(response)
                return True

        except (GitHubNetworkError, GitHubRateLimitError):
            pass

        return False

    def _format_tier_label(self, min_stars: int, max_stars: int | None) -> str:
        """Format a human-readable label for a star tier."""
        if max_stars is None:
            return f"⭐ {min_stars:,}+ stars"
        if min_stars == 0:
            return f"⭐ <{max_stars + 1:,} stars"
        return f"⭐ {min_stars:,}-{max_stars:,} stars"

    def _build_star_filter(self, min_stars: int, max_stars: int | None) -> str:
        """Build a GitHub search star filter string."""
        if max_stars is None:
            return f"stars:>={min_stars}"
        if min_stars == 0:
            return f"stars:<={max_stars}"
        return f"stars:{min_stars}..{max_stars}"

    def _count_new_repos(self, items: list[dict[str, Any]]) -> int:
        """Count how many items are from repositories not yet seen."""
        new_count = 0
        for item in items:
            repo_name = item.get("repository", {}).get("full_name")
            if repo_name and repo_name not in self.repositories:
                new_count += 1
        return new_count

    def filter_by_keywords(self, keywords: Iterable[str]) -> None:
        """
        Filter repository files by checking if they contain specified keywords.

        Args:
            keywords: Keywords to search for in file contents.
        """
        keywords_list = list(keywords)
        if not keywords_list:
            return

        kw_str = ", ".join(keywords_list)
        print(
            f"{Colors.INFO}🔍 Filtering files by keywords: {Colors.WARNING}{kw_str}{Colors.RESET}"
        )

        total_files = sum(len(repo["files"]) for repo in self.repositories.values())
        processed = 0

        for _repo_name, repo_data in list(self.repositories.items()):
            filtered_files = []

            for file_info in repo_data["files"]:
                processed += 1
                self._print_progress(processed, total_files)

                if self._process_file_for_keywords(file_info, keywords_list):
                    filtered_files.append(file_info)

                time.sleep(KEYWORD_FILTER_DELAY)

            repo_data["files"] = filtered_files

        self._remove_empty_repositories()

        print(
            f"\n{Colors.SUCCESS}✅ Keyword filtering complete! "
            f"{len(self.repositories)} repositories have files with matching keywords{Colors.RESET}"
        )
        print()

    # -------------------------------------------------------------------------
    # Private Methods - Search
    # -------------------------------------------------------------------------

    def _build_search_query(
        self,
        query: str,
        language: str | None,
        extension: str | None,
        additional_params: str | None,
    ) -> str:
        """Build the complete GitHub search query string."""
        parts = [query]
        if language:
            parts.append(f"language:{language}")
        if extension:
            parts.append(f"extension:{extension}")
        if additional_params:
            parts.append(additional_params)
        return " ".join(parts)

    def _execute_search(
        self,
        params: dict[str, Any],
    ) -> tuple[requests.Response, list[dict[str, Any]]]:
        """Execute a search API request and return response with items."""
        response = self._request_with_retry("get", GITHUB_REST_SEARCH_URL, params=params)

        if response.status_code != 200:
            self._log_api_error(response)
            raise GitHubAPIError(
                f"GitHub REST API request failed with status {response.status_code}"
            )

        return response, response.json().get("items", [])

    def _process_search_results(self, items: list[dict[str, Any]]) -> None:
        """Process search result items and add to repositories."""
        for item in items:
            repo_name = item.get("repository", {}).get("full_name")
            if repo_name:
                self._add_file_to_repo(
                    repo_name,
                    item.get("path", ""),
                    item.get("html_url", ""),
                )

    def _add_file_to_repo(
        self,
        repo_name: str,
        file_path: str,
        file_url: str,
    ) -> None:
        """Add a file entry to a repository."""
        if repo_name not in self.repositories:
            self.repositories[repo_name] = self._create_repo_entry(repo_name)

        self.repositories[repo_name]["files"].append(self._create_file_entry(file_path, file_url))

    # -------------------------------------------------------------------------
    # Private Methods - Keyword Filtering
    # -------------------------------------------------------------------------

    def _process_file_for_keywords(
        self,
        file_info: dict[str, Any],
        keywords: list[str],
    ) -> bool:
        """
        Check a file for keywords and update its info.

        Returns:
            True if the file should be kept, False otherwise.
        """
        url = file_info.get("url")
        if not url:
            return True

        raw_url = self._convert_to_raw_url(url)
        content = self._fetch_file_content(raw_url)

        if content is None:
            file_info["keywords_found"] = []
            file_info["keyword_match"] = None
            return True  # Keep files we couldn't fetch

        found_keywords = self._find_keywords_in_content(content, keywords)
        file_info["keywords_found"] = found_keywords
        file_info["keyword_match"] = bool(found_keywords)

        return bool(found_keywords)

    def _convert_to_raw_url(self, github_url: str) -> str:
        """Convert a GitHub file URL to a raw content URL."""
        return github_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    def _fetch_file_content(self, raw_url: str) -> str | None:
        """Fetch the content of a file from its raw URL."""
        try:
            response = requests.get(
                raw_url,
                headers=self._headers,
                timeout=CONTENT_FETCH_TIMEOUT,
            )
            if response.status_code == 200:
                return str(response.text)
            return None
        except requests.RequestException as exc:
            print(f"{Colors.WARNING}⚠️  Could not fetch content: {exc}{Colors.RESET}")
            return None

    def _find_keywords_in_content(
        self,
        content: str,
        keywords: list[str],
    ) -> list[str]:
        """Find which keywords appear in the content."""
        content_lower = content.lower()
        return [kw for kw in keywords if re.search(re.escape(kw.lower()), content_lower)]

    def _remove_empty_repositories(self) -> None:
        """Remove repositories that have no files."""
        empty_repos = [name for name, data in self.repositories.items() if not data["files"]]
        for repo_name in empty_repos:
            del self.repositories[repo_name]

    # -------------------------------------------------------------------------
    # Private Methods - Rate Limiting & Utilities
    # -------------------------------------------------------------------------

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle GitHub API rate limiting based on response headers."""
        remaining = response.headers.get("X-RateLimit-Remaining")

        if remaining is None:
            time.sleep(RATE_LIMIT_FALLBACK_DELAY)
            return

        if int(remaining) < 1:
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            wait_time = max(reset_time - time.time(), 0) + 1
            print(
                f"{Colors.WARNING}⏳ Rate limit reached. "
                f"Waiting {wait_time:.1f} seconds...{Colors.RESET}"
            )
            time.sleep(wait_time)
        else:
            time.sleep(RATE_LIMIT_DELAY)

    def _log_api_error(self, response: requests.Response) -> None:
        """Log details about a failed API response."""
        print(f"{Colors.ERROR}❌ Error: {response.status_code}{Colors.RESET}")
        try:
            print(response.json())
        except ValueError:
            print(response.text)

    def _print_progress(self, current: int, total: int) -> None:
        """Print progress update if at interval or complete."""
        if current % PROGRESS_UPDATE_INTERVAL == 0 or current == total:
            print(
                f"{Colors.PROGRESS}📄 Processing file {current}/{total}...{Colors.RESET}",
                end="\r",
            )


# =============================================================================
# GraphQL API Client
# =============================================================================


class GraphQLAPI(BaseGitHubClient):
    """Client for GitHub's GraphQL API to fetch repository metadata."""

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def batch_query(self, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        """
        Fetch metadata for all repositories in batches.

        Args:
            batch_size: Number of repositories to query per batch.
        """
        repo_names = list(self.repositories.keys())
        if not repo_names:
            return

        total_batches = (len(repo_names) + batch_size - 1) // batch_size
        batch_label = "batch" if total_batches == 1 else "batches"

        print(
            f"{Colors.INFO}📊 Fetching repository details "
            f"in {total_batches} {batch_label}...{Colors.RESET}"
        )

        for batch_idx in range(total_batches):
            batch_repos = self._get_batch(repo_names, batch_idx, batch_size)
            self._process_batch(batch_repos, batch_idx + 1, total_batches)
            time.sleep(BATCH_QUERY_DELAY)

        print(f"{Colors.SUCCESS}✅ Repository details fetched successfully!{Colors.RESET}")
        print()

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _get_batch(
        self,
        repo_names: list[str],
        batch_idx: int,
        batch_size: int,
    ) -> list[str]:
        """Get a slice of repository names for the given batch index."""
        start = batch_idx * batch_size
        end = min(start + batch_size, len(repo_names))
        return repo_names[start:end]

    def _process_batch(
        self,
        batch_repos: list[str],
        batch_num: int,
        total_batches: int,
    ) -> None:
        """Process a single batch of repositories."""
        print(
            f"{Colors.PROGRESS}⚡ Processing batch {batch_num}/{total_batches} "
            f"({len(batch_repos)} repositories){Colors.RESET}",
            end=" ",
        )

        try:
            data = self._fetch_batch_data(batch_repos)
            print(f"{Colors.SUCCESS}✓{Colors.RESET}")
            self._update_repositories_from_response(data, batch_repos)
        except GitHubNetworkError as exc:
            print(f"{Colors.ERROR}✗ Network error: {exc}{Colors.RESET}")
        except GitHubRateLimitError as exc:
            print(f"{Colors.ERROR}✗ Rate limit: {exc}{Colors.RESET}")
        except GitHubAPIError as exc:
            print(f"{Colors.ERROR}✗ Error: {exc}{Colors.RESET}")

    def _fetch_batch_data(self, repo_names: list[str]) -> dict[str, Any]:
        """Fetch repository data for a batch using GraphQL."""
        query = self._build_graphql_query(repo_names)

        response = self._request_with_retry(
            "post",
            GITHUB_GRAPHQL_URL,
            json={"query": query},
        )

        if response.status_code != 200:
            raise GitHubAPIError(f"GraphQL API request failed with status {response.status_code}")

        result: dict[str, Any] = response.json()
        return result

    def _build_graphql_query(self, repo_names: list[str]) -> str:
        """Build a GraphQL query for multiple repositories."""
        repo_queries = []

        for i, full_name in enumerate(repo_names):
            owner, name = full_name.split("/", 1)
            repo_queries.append(f'''
                repo{i}: repository(owner: "{owner}", name: "{name}") {{
                    nameWithOwner
                    stargazerCount
                    description
                    url
                    updatedAt
                }}
            ''')

        return "query {\n" + "\n".join(repo_queries) + "\n}"

    def _update_repositories_from_response(
        self,
        response_data: dict[str, Any],
        batch_repos: list[str],
    ) -> None:
        """Update repository data from GraphQL response."""
        if "errors" in response_data:
            print(f"{Colors.ERROR}⚠️  GraphQL Errors:{Colors.RESET}")
            print(json.dumps(response_data["errors"], indent=2))

        data = response_data.get("data", {})
        for i, repo_name in enumerate(batch_repos):
            repo_data = data.get(f"repo{i}")
            if repo_data:
                self.repositories[repo_name].update(
                    {
                        "stars": repo_data.get("stargazerCount", 0),
                        "description": repo_data.get("description") or "",
                        "url": repo_data.get("url", ""),
                        "updated_at": repo_data.get("updatedAt", ""),
                    }
                )
