"""
Query construction tool for the Text-to-GraphQL MCP Server.
"""

from typing import Dict, Any, Optional, List
from ..types import AgentState
from ..logger import logger
import json
from .graphql_helpers import construct_query_context, construct_mutation_context
from langchain_core.prompts import ChatPromptTemplate


def get_query_construction_prompt():
    """Get the prompt template for the query construction tool."""
    
    # Use default examples
    examples = ""
    
    prompt_template = """You are an AI assistant that helps convert natural language intents into GraphQL queries.

Given a user's intent, schema guidance, and context, construct a suitable GraphQL query.

Input:
intent: {intent}
schema_guidance: {schema_guidance}
context: {context}

Output a GraphQL query that satisfies the intent. Format your response as follows:

1. A brief explanation of what the query does (1-2 sentences).
2. The GraphQL query in a code block with ```graphql and ``` tags.
3. A "Required Arguments" section listing any placeholders that need to be filled in.

When writing GraphQL queries:
- Use proper GraphQL syntax
- Include only fields mentioned in the schema guidance
- Use fragments for complex repeated structures
- Include necessary comments for clarity
- Keep queries concise but complete for the intent
- ALWAYS add pagination parameters to fields that require them:
  - For collection fields (like 'models', 'runs', etc.), include 'first: 10' by default
  - When a field has parameters like (after, first, before, last), ALWAYS include either (first: 10) or (last: 10)
  - If the specific field requires pagination but doesn't fit the pattern above, reference the schema guidance
- ALWAYS inject specific IDs mentioned in the user's query directly into the GraphQL query:
  - If the user mentions model ID "abc123", use that exact ID in the query instead of a placeholder
  - If the user provides project ID "proj-567", use that literal value in your query
  - Only use placeholders when the user hasn't specified an exact ID value

For placeholder values in queries, use these formats:
- For IDs: $id or variables like $modelId
- For strings: $string or specific variables like $name
- For numbers: $number or specific variables like $limit
- For booleans: $boolean or specific variables like $includeDisabled

Required Arguments section should list each placeholder with:
- The variable name (e.g., $modelId)
- Required data type (e.g., String, ID, Int)
- Brief description of what it represents

If you include a type from the schema guidance, make sure to include any arguments that are required for that type. For example,
if annotationQueues( after: String first: Int before: String last: Int ) is included in the schema guidance, and you decide to include annotationQueues as one of the fields in your query,
you must include the arguments after, first, before, and last in the query.

{examples}

Remember to focus on translating the intent into a properly formatted GraphQL query that follows schema constraints.
"""
    return ChatPromptTemplate.from_template(prompt_template), examples


async def query_construction(state: AgentState) -> AgentState:
    """
    Builds executable GraphQL queries from intent.
    
    When writing GraphQL queries:
    - Uses proper GraphQL syntax
    - Includes only fields mentioned in the schema guidance
    - Uses fragments for complex repeated structures
    - Includes necessary comments for clarity
    - Keeps queries concise but complete for the intent
    """
    state["current_step"] = "query_construction"
    logger.json("INFO", "Query construction tool called", {
        "state": state
    })

    try:
        # Get the intent and schema from the state
        intent = state.get("intent")
        schema = state.get("schema")
        selected_option = state.get("selected_option")
        natural_language_query = state.get("natural_language_query")
        if not intent or not schema or not selected_option:
            logger.warning("Missing intent or schema for query construction or the llm did not select an option")
            state["tool_error"] = "Missing intent or schema for query construction or the llm did not select an option"
            return state
            
        logger.info("Constructing query based on intent and schema")
        
        if intent == "query":
            query_context = construct_query_context(schema, selected_option)
        else:
            query_context = construct_mutation_context(schema, selected_option)

        # logger.info(f"Query context: {query_context}")
        state["query_context"] = query_context

        llm = state.get("default_llm")
        if not llm:
            logger.warning("No default LLM provided")
            state["tool_error"] = "No default LLM provided"
            return state
        
        prompt_template, examples = get_query_construction_prompt()
        prompt = prompt_template.format(intent=intent, schema_guidance=query_context, context=natural_language_query, examples=examples)
        
        response = llm.invoke(prompt).content
        state["llm_response"] = response
        
        # Extract the query from the response
        query = extract_graphql_query(response)
        if query:
            state["query"] = query
            logger.json("INFO", "Query constructed successfully", {
                "query": query
            })
        else:
            logger.warning("Failed to extract GraphQL query from response")
            state["tool_error"] = "Failed to extract GraphQL query from response"
        
        return state
    except Exception as e:
        logger.error(f"Error in query construction: {str(e)}", exc_info=True)
        logger.exception(e)
        state["tool_error"] = f"Query construction failed: {str(e)}"
        return state
    
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

