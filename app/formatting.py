from typing import Dict, Any, List, Union, Optional
from markdownify import markdownify

def deduplicate_and_format_sources(
    search_response: Union[Dict[str, Any], List[Dict[str, Any]]], 
    max_tokens_per_source: int, 
    fetch_full_page: bool = False
) -> str:
    """
    Format and deduplicate search responses from various search APIs.
    
    Takes either a single search response or list of responses from search APIs,
    deduplicates them by URL, and formats them into a structured string.
    
    Args:
        search_response (Union[Dict[str, Any], List[Dict[str, Any]]]): Either:
            - A dict with a 'results' key containing a list of search results
            - A list of dicts, each containing search results
        max_tokens_per_source (int): Maximum number of tokens to include for each source's content
        fetch_full_page (bool, optional): Whether to include the full page content. Defaults to False.
            
    Returns:
        str: Formatted string with deduplicated sources
        
    Raises:
        ValueError: If input is neither a dict with 'results' key nor a list of search results
    """
    # Convert input to list of results
    if isinstance(search_response, dict):
        sources_list = search_response['results']
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and 'results' in response:
                sources_list.extend(response['results'])
            else:
                sources_list.extend(response)
    else:
        raise ValueError("Input must be either a dict with 'results' or a list of search results")
    
    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source['url'] not in unique_sources:
            unique_sources[source['url']] = source
    
    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source: {source['title']}\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += f"Most relevant content from source: {source['content']}\n===\n"
        if fetch_full_page:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get('raw_content', '')
            if raw_content is None:
                raw_content = ''
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
                
    return formatted_text.strip()

def format_sources(search_results: Dict[str, Any]) -> str:
    """
    Format search results into a bullet-point list of sources with URLs.
    
    Creates a simple bulleted list of search results with title and URL for each source.
    
    Args:
        search_results (Dict[str, Any]): Search response containing a 'results' key with
                                        a list of search result objects
        
    Returns:
        str: Formatted string with sources as bullet points in the format "* title : url"
    """
    return '\n'.join(
        f"* {source['title']} : {source['url']}"
        for source in search_results['results']
    )