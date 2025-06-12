"""
Query execution tool for the Text-to-GraphQL MCP Server.
"""

from typing import Dict, Any, Optional, List
import requests
import time
from ..config import settings
from ..types import AgentState
from ..logger import logger
from .graphql_helpers import execute_graphql_query
import json

async def query_execution(state: AgentState, variables: Dict[str, Any]=None) -> AgentState:
    """
    Executes GraphQL queries against the API endpoint.
    
    Given a validated GraphQL query and execution context:
    - Prepares any necessary authentication credentials
    - Submits the query to the appropriate endpoint
    - Handles any errors or exceptions that occur during execution
    - Processes the response data into a usable format
    - Implements retry logic if needed
    - Considers rate limiting and API constraints
    """
    state["current_step"] = "query_execution"

    logger.json("INFO", "Query Execution tool called", {
        "state": state
    })

    # Get the query from the state
    query = state.get("query", "")
    
    if not query:
        logger.json("WARNING", "No query provided for execution", {
            "tool": "query_execution",
            "error": "missing_query"
        })
        state["tool_error"] = "No query provided for execution"
        return state
        
    # Log the query with proper formatting
    logger.json("INFO", "Executing GraphQL query", {
        "tool": "query_execution",
        "query_preview": query[:100] + ("..." if len(query) > 100 else ""),
        "endpoint": settings.GRAPHQL_ENDPOINT
    })
    

    
    execution_result = execute_graphql_query(settings.GRAPHQL_ENDPOINT, query, variables=variables)
    
    # Store the execution result in the state
    state["execution_result"] = execution_result
            # Log the result summary
    response_data = execution_result.get("data", {})
    result_summary = {
        "tool": "query_execution",
        "success": execution_result["success"],
        "data_size": len(str(response_data)),
    }
    
    logger.json("INFO", "Query execution completed successfully", result_summary)
    
    return state