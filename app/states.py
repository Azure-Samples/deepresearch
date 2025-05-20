import operator
from dataclasses import field, dataclass
from typing_extensions import Annotated

# Define the states 
@dataclass(kw_only=True)
class SummaryState:
    research_topic: str = field(default=None) # Report topic     
    search_query: str = field(default=None) # Search query
    rationale: str = field(default=None) # rationale for the search query
    web_research_results: Annotated[list, operator.add] = field(default_factory=list) 
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list) 
    research_loop_count: int = field(default=0) # Research loop count
    running_summary: str = field(default=None) # Final report
    knowledge_gap: str = field(default=None) # Knowledge gap
    websocket_id: str = field(default=None) # Websocket ID
    thoughts: str = field(default=None) # model thoughts

@dataclass(kw_only=True)
class SummaryStateInput:
    research_topic: str = field(default=None) # Report topic  
    websocket_id: str = field(default=None) # Websocket ID   

@dataclass(kw_only=True)
class SummaryStateOutput:
    running_summary: str = field(default=None) # Final report