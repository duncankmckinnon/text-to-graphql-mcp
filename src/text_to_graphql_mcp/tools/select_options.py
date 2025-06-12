from ..types import AgentState
from ..logger import logger
from ..config import settings

from langchain_core.prompts import ChatPromptTemplate
import json
async def select_options(state: AgentState) -> AgentState:
    """Select the appropriate GraphQL {intent} based on a user request."""
    state["current_step"] = "select_options"
    logger.json("INFO", "Select Options tool called", {
        "state": state
    })
    
    prompt_template = get_select_options_prompt()
    prompt = prompt_template.format(intent=state.get("intent"), options=state.get("options"), request=state.get("natural_language_query"))
    llm = state.get("default_llm")
    if not llm:
        raise ValueError("No default LLM provided")
    
    # Log the prompt for debugging
    logger.json("DEBUG", "Select options prompt", {
        "prompt": prompt,
        "intent": state.get("intent"),
        "options": state.get("options")
    })
    
    response = await llm.ainvoke(prompt)
    selected_option = response.content.strip()
    
    logger.json("INFO", "Select options response", {
        "response": response.content,
        "selected_option": selected_option
    })
    
    state["selected_option"] = selected_option
    logger.info(f"Selected Option: {selected_option}")
    return state

def get_select_options_prompt():
    """Get the prompt template for the select options tool."""
    prompt_template = """
        You are an assistant that selects the appropriate GraphQL {intent} based on a user request.
        Choose ONE {intent} from the following options that best matches the user's request:

        User's request: {request}

        ================================
                OPTIONS
        ================================
        {options}

        Respond with ONLY the name of the {intent} you've selected.

        Examples:
        If the user's request is "Find all of the models in the space with ID space_id", you should select "Space" as the query.
        If the user's request is "Update the drift monitor with ID drift_monitor_id" to have a manual threshold of 0.5, you should select "patchDriftMonitor" as the mutation.
        For queries, pay careful attention to what the source object that you will be querying is. A request of "Find all dashboards connected to a model" should select "Model" as the query, which will then have the dashboards as a field.
        """
    
    return ChatPromptTemplate.from_template(prompt_template)