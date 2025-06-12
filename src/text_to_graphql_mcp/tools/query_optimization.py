"""
Query optimization tool for the Text-to-GraphQL MCP Server.
"""

from typing import Dict, Any
import json
from ..types import AgentState
from ..logger import logger

from langchain_core.prompts import ChatPromptTemplate

def get_query_optimization_prompt():
    """Get the prompt template for the query optimization tool."""
    
    prompt_template = """You are a GraphQL expert tasked with fixing a query that failed validation.

## Original User Request
{user_request}

## Failed GraphQL Query
```graphql
{query}
```

## Validation Errors
{errors}

## Schema Information (relevant parts)
{schema_context}

## Your Task
1. Analyze the validation errors carefully
2. Understand what the query is trying to accomplish
3. Fix the issues mentioned in the validation errors
4. Return a corrected query that should pass validation

## Guidelines:
- Fix syntax errors, field names, and argument issues
- Ensure the query follows GraphQL syntax rules
- Make sure all fields exist in the schema
- Add required arguments that were missing
- Fix type issues in arguments or variables
- Keep the original intent and functionality of the query
- Only make changes necessary to fix the validation errors
- Maintain the same basic structure unless a structural change is required to fix an error

Respond with a corrected GraphQL query in a code block with ```graphql and ``` tags. Do not add any explanations or comments outside the code block.
"""
    return ChatPromptTemplate.from_template(prompt_template)


async def query_optimization(state: AgentState) -> AgentState:
    """
    Optimizes GraphQL queries based on validation errors.
    
    Given a GraphQL query that failed validation:
    - Analyzes the validation errors
    - Understands the query's intent
    - Applies fixes to address the validation issues
    - Produces an improved, valid GraphQL query
    - Tracks optimization attempts to prevent infinite loops
    """
    state["current_step"] = "query_optimization"
    
    logger.json("INFO", "Query Optimization started", {
        "state": state
    })

    try:
        # Get the failed query, validation errors, and original context
        query = state.get("query", "")
        validation_result = state.get("query_validation_result", {})
        errors = validation_result.get("errors", [])
        natural_language_query = state.get("natural_language_query", "")
        schema_context = state.get("query_context", "")

        
        # Track optimization attempts
        optimization_attempts = state.get("optimization_attempts", 0)
        state["optimization_attempts"] = optimization_attempts + 1
        
        if not query or not errors:
            logger.json("WARNING", "Missing query or validation errors for optimization", {
                "tool": "query_optimization",
                "error": "missing_prerequisites"
            })
            state["tool_error"] = "Missing query or validation errors for optimization"
            return state
        
        # Log the optimization attempt
        logger.json("INFO", "Optimizing GraphQL query", {
            "tool": "query_optimization",
            "attempt": optimization_attempts + 1,
            "error_count": len(errors),
            "query_preview": query[:100] + ("..." if len(query) > 100 else "")
        })
        
        # Get the LLM
        llm = state.get("default_llm")
        if not llm:
            logger.warning("No default LLM provided for query optimization")
            state["tool_error"] = "No LLM available for query optimization"
            return state
        
        # Format errors for the prompt
        formatted_errors = "\n".join([f"- {error}" for error in errors])
        
        # Get the optimization prompt template
        prompt_template = get_query_optimization_prompt()
        
        # Format the prompt
        prompt = prompt_template.format(
            user_request=natural_language_query,
            query=query,
            errors=formatted_errors,
            schema_context=schema_context
        )
        
        # Get the optimized query from the LLM
        response = await llm.ainvoke(prompt)
        response_content = response.content
        
        # Extract the query from the response
        optimized_query = extract_graphql_query(response_content)
        if optimized_query:
            state["query"] = optimized_query
            state["llm_response"] = response_content
            
            logger.json("INFO", "Query optimized successfully", {
                "tool": "query_optimization",
                "attempt": optimization_attempts + 1,
                "optimized_query": optimized_query[:100] + ("..." if len(optimized_query) > 100 else "")
            })
        else:
            logger.warning("Failed to extract optimized GraphQL query from response")
            state["tool_error"] = "Failed to extract optimized GraphQL query from response"
        
        return state
    except Exception as e:
        logger.error(f"Error in query optimization: {str(e)}", exc_info=True)
        state["tool_error"] = f"Query optimization failed: {str(e)}"
        return state

#TODO - I think this is a duplicate of the extract_graphql_query function in query_construction.py, we should refactor to graphql_helpers.py
def extract_graphql_query(response: str) -> str:
    """
    Extract a GraphQL query from an LLM response
    
    Args:
        response (str): The LLM response text
        
    Returns:
        str: The extracted GraphQL query or empty string if not found
    """
    try:
        if "```graphql" in response:
            # Extract between ```graphql and ``` tags
            final_query = response.split("```graphql")[1].split("```")[0].strip()
        elif "```" in response and response.count("```") >= 2:
            # Extract between ``` and ``` tags
            final_query = response.split("```")[1].strip()
        else:
            # Assume the whole response is a query
            final_query = response
            
        return final_query
    except Exception as e:
        logger.error(f"Error extracting GraphQL query: {str(e)}")
        return "" 