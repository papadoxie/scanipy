"""
GitHub search functionality for Scanipy.

This module provides a high-level interface for searching GitHub repositories
using both REST and GraphQL APIs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from models import SearchConfig

from .github import GraphQLAPI, RestAPI


class SearchStrategy(Enum):
    """Search strategy for GitHub code search."""

    GREEDY = "greedy"  # Fast but may miss high-star repos
    TIERED_STARS = "tiered"  # Searches by star tiers (highest first)


class SortOrder(Enum):
    """Sort order for search results."""

    STARS = "stars"  # Sort by star count (default)
    UPDATED = "updated"  # Sort by most recently updated


def search_repositories(
    config: SearchConfig,
    token: str,
    strategy: SearchStrategy = SearchStrategy.TIERED_STARS,
    sort_order: SortOrder = SortOrder.STARS,
) -> list[dict[str, Any]]:
    """
    Search GitHub for repositories matching the search configuration.

    This function combines REST API code search with GraphQL metadata
    enrichment to provide comprehensive repository information.

    Args:
        config: Search parameters including query, language, extension, etc.
        token: GitHub API token for authentication
        strategy: Search strategy to use:
            - GREEDY: Fast search, may miss high-star repos due to API limits
            - TIERED_STARS: Searches by star tiers (10k+, 1k-10k, etc.) to
              ensure popular repositories are included first
        sort_order: How to sort results:
            - STARS: Sort by star count (highest first)
            - UPDATED: Sort by most recently updated

    Returns:
        List of repository dictionaries sorted according to sort_order
    """
    rest_client = RestAPI(token=token)

    # Execute search based on strategy
    if strategy == SearchStrategy.TIERED_STARS:
        rest_client.search_by_stars(
            query=config.query,
            language=config.language,
            extension=config.extension,
            per_page=config.per_page,
            max_pages=config.max_pages,  # Total page budget, exhausts higher tiers first
            additional_params=config.additional_params,
        )
    else:
        # Greedy search (original behavior)
        rest_client.search(
            query=config.query,
            language=config.language,
            extension=config.extension,
            per_page=config.per_page,
            max_pages=config.max_pages,
            additional_params=config.additional_params,
        )

    # Apply keyword filtering if specified
    if config.keywords:
        rest_client.filter_by_keywords(config.keywords)

    # Enrich with repository metadata using GraphQL API
    graphql_client = GraphQLAPI(token=token, repositories=rest_client.repositories)
    graphql_client.batch_query()

    # Sort results based on sort_order
    repo_list = list(graphql_client.repositories.values())
    if sort_order == SortOrder.UPDATED:
        repo_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    else:
        repo_list.sort(key=lambda x: x.get("stars", 0), reverse=True)

    return repo_list
