#!/usr/bin/env python3
import os
import sys
import argparse
from colorama import init, Fore, Back, Style

from tools.semgrep.semgrep_runner import analyze_repositories_with_semgrep

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Color and styling utilities
class Colors:
    HEADER = Fore.CYAN + Style.BRIGHT
    SUCCESS = Fore.GREEN + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.BLUE + Style.BRIGHT
    PROGRESS = Fore.CYAN
    REPO_NAME = Fore.MAGENTA + Style.BRIGHT
    STARS = Fore.YELLOW + Style.BRIGHT
    FILES = Fore.GREEN
    URL = Fore.BLUE + Style.DIM
    DESCRIPTION = Fore.WHITE + Style.DIM
    RESET = Style.RESET_ALL

def print_banner():
    """Print a colorful banner for the tool"""
    banner = f"""
{Colors.HEADER}╔══════════════════════════════════════════════════════════════╗
║                          📡 SCANIPY                          ║
║              Code Pattern Scanner for GitHub                 ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)

def print_search_info(query, language, extension, pages, keywords=None):
    """Print search parameters in a formatted way"""
    print(f"{Colors.INFO}🔍 Search Parameters:{Colors.RESET}")
    print(f"   {Colors.INFO}•{Colors.RESET} Query: {Colors.WARNING}'{query}'{Colors.RESET}")
    if language:
        print(f"   {Colors.INFO}•{Colors.RESET} Language: {Colors.SUCCESS}{language}{Colors.RESET}")
    if extension:
        print(f"   {Colors.INFO}•{Colors.RESET} Extension: {Colors.SUCCESS}{extension}{Colors.RESET}")
    if keywords:
        print(f"   {Colors.INFO}•{Colors.RESET} Keywords: {Colors.WARNING}{', '.join(keywords)}{Colors.RESET}")
    print(f"   {Colors.INFO}•{Colors.RESET} Max Pages: {Colors.WARNING}{pages}{Colors.RESET}")
    print()

def format_star_count(stars):
    """Format star count with appropriate color and formatting"""
    if stars == 'N/A':
        return f"{Colors.WARNING}N/A{Colors.RESET}"
    elif stars >= 10000:
        return f"{Colors.SUCCESS}⭐ {stars:,}{Colors.RESET}"
    elif stars >= 1000:
        return f"{Colors.STARS}⭐ {stars:,}{Colors.RESET}"
    else:
        return f"{Colors.WARNING}⭐ {stars}{Colors.RESET}"

def print_repository(index, repo, query):
    """Print a single repository with colorful formatting"""
    # Repository header
    print(f"{Colors.HEADER}{'─' * 80}{Colors.RESET}")
    print(f"{Colors.INFO}{index:2d}.{Colors.RESET} {Colors.REPO_NAME}{repo['name']}{Colors.RESET} {format_star_count(repo.get('stars', 'N/A'))}")
    
    # Description
    if repo.get('description'):
        desc = repo['description']
        if len(desc) > 100:
            desc = desc[:97] + "..."
        print(f"    {Colors.DESCRIPTION}📝 {desc}{Colors.RESET}")
    
    # File count
    file_count = len(repo['files'])
    if file_count > 0:
        print(f"    {Colors.FILES}📁 {file_count} file{'s' if file_count != 1 else ''} containing '{query}'{Colors.RESET}")
        
        # Show files with keyword information
        for i, file in enumerate(repo['files'][:3]):
            file_line = f"    {Colors.FILES}├─{Colors.RESET} {file['path']}"
            
            # Add keyword match information
            if file.get('keyword_match') is True:
                keywords_str = ', '.join(file.get('keywords_found', []))
                file_line += f" {Colors.SUCCESS}[Keywords: {keywords_str}]{Colors.RESET}"
            elif file.get('keyword_match') is False:
                file_line += f" {Colors.WARNING}[No keywords found]{Colors.RESET}"
            elif file.get('keyword_match') is None:
                file_line += f" {Colors.WARNING}[Content unavailable]{Colors.RESET}"
            
            print(file_line)
        
        if len(repo['files']) > 3:
            remaining = len(repo['files']) - 3
            print(f"    {Colors.FILES}└─{Colors.RESET} {Colors.WARNING}... and {remaining} more file{'s' if remaining != 1 else ''}{Colors.RESET}")
    
    # URL
    if repo.get('url'):
        print(f"    {Colors.URL}🔗 {repo['url']}{Colors.RESET}")
    
    print()

def setup_argparser():
    parser = argparse.ArgumentParser(
    description='Search for open source repositories containing specific code patterns and sort by stars.',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog='''
Examples:

    # Search for a pattern
    scanipy --query "extractall"
    
    # Search for a specific language
    scanipy --query "pickle.loads" --language python
  
    # Search with keyword filtering
    scanipy --query "extractall" --keywords "path,directory,zip" --language python
  
    # Search with a higher page limit 
    scanipy --query "pickle.loads" --pages 10
  
    # Search in specific file types
    scanipy --query "os.system" --language python --extension ".py"
  
    # Search with additional filters
    scanipy --query "subprocess.call" --additional-params "stars:>100"
    
    # Run semrep on top repositories
    scanipy --query "extractall" --run-semrep
    '''
    )

    # Search query parameters
    parser.add_argument(
        '--query', '-q',
        required=True,
        help='Code pattern to search for (e.g., "extractall")'
    )
    parser.add_argument(
        '--language', '-l',
        default='',
        help='Programming language to search in (e.g., python)'
    )
    parser.add_argument(
        '--extension', '-e',
        default='',
        help='File extension to search in (e.g., ".py", ".ipynb")'
    )
    parser.add_argument(
        '--keywords', '-k',
        default='',
        help='Comma-separated keywords to look for in files containing the main pattern (e.g., "path,directory,zip")'
    )
    parser.add_argument(
        '--additional-params',
        default='',
        help='Additional search parameters (e.g., "stars:>100 -org:microsoft")'
    )
    # Pagination and limits
    parser.add_argument(
        '--pages', '-p',
        type=int,
        default=5,
        help='Maximum number of pages to retrieve (default: 5, max 10 pages = 1000 results)'
    )
    # GitHub API authentication
    parser.add_argument(
        '--github-token',
        help='GitHub personal access token (also can be set via GITHUB_TOKEN env variable)'
    )
    # Output options
    parser.add_argument(
        '--output', '-o',
        default='repos.json',
        help='Output JSON file path (default: repos.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    # New semrep options
    parser.add_argument(
        '--run-semrep',
        action='store_true',
        help='Run semrep analysis on the top 10 repositories'
    )
    parser.add_argument(
        '--semrep-args',
        default='',
        help='Additional arguments to pass to semrep (e.g., "--json --verbose"). Quote the arguments as a single string.'
    )
    parser.add_argument(
        '--pro',
        action='store_true',
        help='Use semgrep with the --pro flag'
    )
    parser.add_argument(
        '--rules',
        default=None,
        help='Path to custom semgrep rules file or directory (YAML format)'
    )
    parser.add_argument(
        '--clone-dir',
        default=None,
        help='Directory to clone repositories into (default: temporary directory)'
    )
    parser.add_argument(
        '--keep-cloned',
        action='store_true',
        help='Keep cloned repositories after analysis (only applicable with --clone-dir)'
    )
    
    args = parser.parse_args()
    
    # Parse keywords
    if args.keywords:
        args.keywords_list = [kw.strip() for kw in args.keywords.split(',') if kw.strip()]
    else:
        args.keywords_list = []
    
    # Build the complete search query
    query_parts = []
    if args.query:
        query_parts.append(args.query)
    if args.language:
        query_parts.append(f"language:{args.language}")
    if args.extension:
        query_parts.append(f"extension:{args.extension}")
    if args.additional_params:
        query_parts.append(args.additional_params)
    args.full_query = " ".join(query_parts)
    
    return args


if __name__ == "__main__":
    args = setup_argparser()
    
    # Check if GITHUB_TOKEN is set in environment variables
    if not args.github_token:
        args.github_token = os.getenv("GITHUB_TOKEN")
    
    if not args.github_token:
        print(f"{Colors.ERROR}❌ Error: GITHUB_TOKEN environment variable or --github-token argument must be set.{Colors.RESET}")
        sys.exit(1)
    
    print_banner()
    
    # Print search information
    print_search_info(args.query, args.language, args.extension, args.pages, args.keywords_list)
    
    # Initialize GitHub API client
    from integrations.github.github import RestAPI as GHRest
    from integrations.github.github import GraphQLAPI as GHGraphQL
    ghrest = GHRest(token=args.github_token)
    ghrest.search(args.query, language=args.language, extension=args.extension, per_page=100, max_pages=args.pages, additional_params=args.additional_params)
    repos = ghrest.repositories
    
    # Apply keyword filtering if keywords are provided
    if args.keywords_list:
        ghrest.filter_by_keywords(args.keywords_list)
        repos = ghrest.repositories
    
    ghgraphql = GHGraphQL(token=args.github_token, repositories=repos)
    ghgraphql.batch_query()
    
    repos = ghgraphql.repositories
    
    repo_list = list(repos.values())
    repo_list.sort(key=lambda x: x.get("stars", 0), reverse=True)
    
    # Print top repositories
    if repo_list:
        print(f"{Colors.SUCCESS}🎯 TOP REPOSITORIES BY STARS:{Colors.RESET}")
        for i, repo in enumerate(repo_list[:20], 1):
            print_repository(i, repo, args.query)
        
        # Run semrep on top repositories if requested
        if args.run_semrep:
            analyze_repositories_with_semrep(
                repo_list,
                Colors,
                semgrep_args=args.semrep_args,
                clone_dir=args.clone_dir,
                keep_cloned=args.keep_cloned,
                rules_path=args.rules,
                use_pro=args.pro,
            )
    else:
        print(f"{Colors.WARNING}📭 No repositories found matching your criteria.{Colors.RESET}")
        if args.keywords_list:
            print(f"{Colors.INFO}💡 Try with fewer or different keywords, or search without keyword filtering.{Colors.RESET}")

