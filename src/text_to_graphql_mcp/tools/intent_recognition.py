"""
Intent recognition tool for the Text-to-GraphQL MCP Server.
"""

from typing import Dict, Any, Optional, List
from ..logger import logger
from langchain_core.prompts import ChatPromptTemplate
import json
from ..types import AgentState

def get_intent_recognition_prompt() -> ChatPromptTemplate:
    """
    Returns the prompt template for the Intent Recognition tool.
    
    This tool is responsible for converting natural language requests into 
    structured intents that can be used to build GraphQL queries.
    """
    template = """You are an expert Intent Recognition Engine for a GraphQL API assistant.
    
Your task is to analyze the user's natural language request and extract the following elements:
1. Primary intent (query vs. mutation)
2. Target entities or types from the GraphQL schema
3. Requested fields or properties
4. Filtering criteria or conditions
5. Relationships between entities that need to be traversed
6. Any sorting, pagination, or limiting requirements

Remember to:
- Map domain-specific terminology to GraphQL schema elements
- Handle ambiguity by identifying multiple possible interpretations
- Recognize entity relationships and how they should be connected
- Identify multi-query requests that might need to be separated
- Consider the context of the conversation when interpreting the request

Given the user's message and the conversation history, identify the structured intent that represents what the user is trying to accomplish.

### User Query:
{query}

### Conversation History:
{history}

Please respond with only a single word, that word being the primary intent from the user request, either "query" or "mutation"
"""

    return ChatPromptTemplate.from_template(template) 

async def intent_recognition(state: AgentState) -> AgentState:
    """
    Analyzes natural language queries to identify GraphQL intent.
    
    This tool extracts the following from a natural language query:
    - Primary intent (query vs. mutation)
    - Target entities or types from the GraphQL schema
    - Requested fields or properties
    - Filtering criteria or conditions
    - Relationships between entities that need to be traversed
    - Any sorting, pagination, or limiting requirements
    """
    state["current_step"] = "intent_recognition"
    logger.json("INFO", "Intent recognition tool started", {
        "state": state
    })
    
    try:
        # Get the natural language query from the state
        query = state.get("natural_language_query", "")
        if not query:
            logger.json("WARNING", "No natural language query provided", {
                "tool": "intent_recognition",
                "error": "missing_query"
            })
            state["tool_error"] = "No natural language query provided"
            return state
            
        # Log the start of analysis
        logger.json("INFO", "Analyzing intent for query", {
            "state": state
        })
        
        # Get prompt template and format it
        prompt_template = get_intent_recognition_prompt()
        prompt = prompt_template.format(query=query, history=state.get("messages", []))
        
        # Log the LLM interaction
        logger.llm("Intent recognition prompt", prompt=prompt)
        
        # Call the LLM
        response = await state.get("default_llm").ainvoke(prompt)
        
        # Log the response
        logger.llm("Intent recognition LLM response", 
                prompt=query, 
                response=response.content)
    
        # Store the intent in the state
        if "query" in response.content.lower():
            intent = "query"
        elif "mutation" in response.content.lower():
            intent = "mutation"
        else:
            intent = "unknown"
        
        state["intent"] = intent
        
        logger.json("INFO", "Intent recognition completed", {
            "tool": "intent_recognition",
            "intent": intent,
            "confidence": "high" if intent in ["query", "mutation"] else "low"
        })
        
        return state
    except Exception as e:
        error_info = {
            "tool": "intent_recognition",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        logger.json("ERROR", "Error in intent recognition", error_info)
        state["tool_error"] = f"Intent recognition failed: {str(e)}"
        return state 