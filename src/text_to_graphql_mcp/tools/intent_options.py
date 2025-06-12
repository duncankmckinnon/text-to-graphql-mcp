from typing import TypedDict, Dict, Any, Optional
from ..types import AgentState
from ..logger import logger
import json

def get_query_options(state: AgentState) -> AgentState:
    """
    Get the query options for the user's intent.
    """
    schema = state.get("schema")
    if not schema:
        logger.warning("No schema provided for query options")
        state["tool_error"] = "No schema provided for query options"
        return state
    
    query_options = ""
    for obj in schema.get_implementations(schema.get_type('Node')).objects:
        query_options += obj.name + "\n"
    
    # state["options"] = query_options

    return query_options

def get_mutation_options(state: AgentState) -> AgentState:
    """
    Get the mutation options for the user's intent.
    """
    schema = state.get("schema")
    if not schema:
        logger.warning("No schema provided for mutation options")
        state["tool_error"] = "No schema provided for mutation options"
        return state
    
    mutation_options = ""
    for key in schema.get_type('Mutation').fields.keys():
        mutation_options += key + "\n"
    
    # state["options"] = mutation_options
    return mutation_options

async def intent_options(state: AgentState) -> AgentState:
    """
    Get the options for the user's intent.
    """
    # Update current step
    state["current_step"] = "intent_options"
    logger.json("INFO", "Intent Options tool called", {
        "state": state
    })

    intent = state.get("intent")
    logger.info(f"Intent: {intent}")
    if intent == "query":
        state["options"] = get_query_options(state) 
        return state
    if intent == "mutation":
        state["options"] = get_mutation_options(state)
        return state
    