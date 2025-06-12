#!/usr/bin/env python3
"""
FastMCP Server for Text-to-GraphQL MCP Server.
Exposes GraphQL agent functionality as MCP tools for LLM clients using FastMCP.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastmcp import FastMCP

try:
    from .agent import GraphQLAgent
    from .config import settings
    from .logger import logger
    from .error_handlers import validated
except ImportError:
    # Handle imports when running as main module
    from agent import GraphQLAgent
    from config import settings
    from logger import logger
    from error_handlers import validated


# Initialize FastMCP server
mcp = FastMCP("Text-to-GraphQL MCP Server")

# Initialize the agent and storage
agent = GraphQLAgent()
query_history: Dict[str, Dict[str, Any]] = {}
session_id_map: Dict[str, str] = {}


@mcp.tool()
@validated({
    "query": {"type": "string", "required": True, "min_length": 1, "max_length": 10000},
    "history_id": {"type": "history_id", "required": False}
})
async def generate_graphql_query(
    query: str,
    history_id: Optional[str] = None
) -> str:
    """Generate a GraphQL query from natural language description
    
    Args:
        query: Natural language description of the desired GraphQL query
        history_id: Optional history ID to associate with this query
    
    Returns:
        JSON string containing the generated query, validation result, and history ID
    """
    logger.info(f"MCP: Generating query for: {query}")
    
    # Handle history ID
    if not history_id:
        history_id = str(len(query_history) + 1)
    
    if history_id not in session_id_map:
        session_id_map[history_id] = str(uuid4())
    
    result = await agent.generate_query(query, session_id_map[history_id])
    
    # Store in history
    query_history[history_id] = {
        "id": history_id,
        "natural_language_query": query,
        "graphql_query": result.get("graphql_query"),
        "validation_result": result.get("validation_result")
    }
    
    response = {
        "history_id": history_id,
        "natural_language_query": query,
        "graphql_query": result.get("graphql_query"),
        "validation_result": result.get("validation_result")
    }
    
    return json.dumps(response, indent=2)


@mcp.tool()
@validated({
    "graphql_query": {"type": "graphql_query", "required": True},
    "natural_language_query": {"type": "string", "required": False, "max_length": 10000},
    "history_id": {"type": "history_id", "required": False}
})
async def validate_graphql_query(
    graphql_query: str,
    natural_language_query: Optional[str] = None,
    history_id: Optional[str] = None
) -> str:
    """Validate and update a GraphQL query
    
    Args:
        graphql_query: The GraphQL query to validate
        natural_language_query: The original natural language query for context
        history_id: Optional history ID to update
    
    Returns:
        JSON string containing the validation result and history ID
    """
    logger.info(f"MCP: Validating query: {graphql_query[:50]}...")
    
    result = await agent.validate_query(graphql_query, natural_language_query or "")
    
    # Update history
    if history_id and history_id in query_history:
        query_history[history_id]["graphql_query"] = graphql_query
        query_history[history_id]["validation_result"] = result
    else:
        # Create new history entry
        history_id = str(len(query_history) + 1) if not history_id else history_id
        query_history[history_id] = {
            "id": history_id,
            "natural_language_query": natural_language_query or "",
            "graphql_query": graphql_query,
            "validation_result": result
        }
    
    response = {
        "history_id": history_id,
        "validation_result": result
    }
    
    return json.dumps(response, indent=2)


@mcp.tool()
@validated({
    "graphql_query": {"type": "graphql_query", "required": True},
    "natural_language_query": {"type": "string", "required": False, "max_length": 10000},
    "history_id": {"type": "history_id", "required": False},
    "variables": {"type": "dict", "required": False}
})
async def execute_graphql_query(
    graphql_query: str,
    natural_language_query: Optional[str] = None,
    history_id: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None
) -> str:
    """Execute a GraphQL query and optionally visualize the results
    
    Args:
        graphql_query: The GraphQL query to execute
        natural_language_query: The original natural language query for context
        history_id: Optional history ID to update
        variables: Optional variables for the GraphQL query
    
    Returns:
        JSON string containing execution results, visualization, and history ID
    """
    logger.info(f"MCP: Executing query: {graphql_query[:50]}...")
    
    # Execute the query
    execution_result = await agent.execute_query(graphql_query, variables=variables or {})
    
    # Format execution result
    formatted_execution_result = {
        "status": "SUCCESS" if execution_result.get("success") == True else "ERROR",
        "response_data": execution_result.get("data", {}),
        "error": execution_result.get("message", "") if execution_result.get("success") == False else None,
        "execution_time": execution_result.get("execution_time", 0)
    }
    
    # Generate visualization if execution was successful
    visualization_result = None
    if execution_result.get("success") == True:
        visualization_result = await agent.visualize_data(
            execution_result.get("data", {}),
            natural_language_query or ""
        )
    
    # Update history
    if history_id and history_id in query_history:
        query_history[history_id]["execution_result"] = formatted_execution_result
        query_history[history_id]["visualization_result"] = visualization_result
    else:
        # Create new history entry
        history_id = str(len(query_history) + 1) if not history_id else history_id
        query_history[history_id] = {
            "id": history_id,
            "natural_language_query": natural_language_query or "",
            "graphql_query": graphql_query,
            "execution_result": formatted_execution_result,
            "visualization_result": visualization_result
        }
    
    response = {
        "history_id": history_id,
        "execution_result": formatted_execution_result,
        "visualization_result": visualization_result
    }
    
    return json.dumps(response, indent=2)


@mcp.tool()
@validated()
async def get_query_history() -> str:
    """Retrieve the history of all queries
    
    Returns:
        JSON string containing all query history
    """
    history = list(query_history.values())
    response = {"history": history}
    
    return json.dumps(response, indent=2)


@mcp.tool()
@validated()
async def get_query_examples() -> str:
    """Get example queries to help users understand what they can ask for
    
    Returns:
        JSON string containing example queries
    """
    # Provide default examples
    examples = [
        {"query": "Get all users with their names and emails"},
        {"query": "Find posts by author ID 123"},
        {"query": "List all products with prices above $50"},
        {"query": "Get user profile including posts and comments"},
        {"query": "Search for posts containing 'GraphQL'"}
    ]
    
    response = {"examples": examples}
    
    return json.dumps(response, indent=2)


def main():
    """Main entry point for the MCP server."""
    logger.info("=== Text-to-GraphQL MCP Server Starting ===")
    mcp.run()


if __name__ == "__main__":
    main() 