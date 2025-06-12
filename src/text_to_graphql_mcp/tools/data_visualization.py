"""
Data visualization tool for the Text-to-GraphQL MCP Server.
"""

import json
import re
from typing import Dict, Any, Optional, List
from collections import Counter
from ..types import AgentState  
from ..logger import logger
from langchain.prompts import ChatPromptTemplate

def get_data_visualization_prompt() -> ChatPromptTemplate:
    """
    Returns the prompt template for the Data Visualization tool.
    
    This tool is responsible for generating appropriate visualizations based on query results,
    considering data structure and user needs.
    """
    template = """You are a Data Visualization expert for GraphQL query results.

Your task is to analyze GraphQL response data and determine the most appropriate visualizations.

Given the query results and context, you need to:
1. Identify the data structure and relationships
2. Determine appropriate visualization types (charts, tables, etc.)
3. Configure visualization settings for clarity and insight
4. Consider user preferences and previous interactions
5. Enable interactive elements where appropriate
6. Support exporting visualizations for reports

Remember to:
- Match visualization types to data structure (e.g., time series data in line charts)
- Consider data volume when choosing visualizations
- Use colors, labels, and annotations effectively
- Enable appropriate interactivity (sorting, filtering, etc.)
- Support comparison between related data sets
- Ensure visualizations answer the user's original question

### Query Results:
{results}

### Original Query:
{query}

### User Intent:
{intent}

### Visualization Context:
{context}

Please respond with visualization specifications in JSON format. Each visualization should be a JSON object with the following structure:

```json
{{
  "type": "line_chart", // One of: line_chart, bar_chart, pie_chart, radar_chart, data_grid, map, json_viewer
  "title": "Chart Title",
  "description": "Short description of what this visualization shows",
  "data": {{
    // Specific data structure based on the chart type
    "labels": ["Label1", "Label2", "..."],
    "datasets": [
      {{
        "label": "Dataset 1",
        "data": [value1, value2, ...]
      }}
    ]
  }}
}}
```

You can include multiple visualizations by putting them in a JSON array. You MUST respond with valid JSON that can be parsed directly. Do not include explanatory text outside the JSON structure.

The available visualization types are:
1. line_chart - For time series or trend data
2. bar_chart - For comparing values across categories
3. pie_chart - For showing composition or portions of a whole
4. radar_chart - For comparing multiple variables
5. data_grid - For displaying tabular data
6. map - For geographical data
7. json_viewer - For raw data when other visualizations aren't appropriate

Each type requires specific data structures as shown in the example above.
"""

    return ChatPromptTemplate.from_template(template) 


async def data_visualization(state: AgentState) -> AgentState:
    """
    Generates visualizations for query results data using LLM.
    
    Based on the data structure:
    - Determines appropriate visualization types
    - Creates charts, tables, or other visual components
    - Extracts key metrics and insights
    - Formats the data for the frontend renderer
    """
    state["current_step"] = "data_visualization"
    
    # Log minimal state information instead of entire state
    logger.json("INFO", "Data visualization tool called", {
        "tool": "data_visualization",
        "has_execution_result": bool(state.get("execution_result")),
        "has_intent": bool(state.get("intent")),
        "has_query": bool(state.get("query")),
        "current_step": state.get("current_step")
    })
    
    try:
        # Get the execution result from the state
        execution_result = state.get("execution_result", {})
        intent = state.get("intent", {})
        query = state.get("query", "")
        
        # Extract the data to visualize
        data = execution_result.get("data", {})
        
        if not data:
            logger.warning("No execution result data for visualization")
            state["tool_error"] = "No execution result data for visualization"
            return state
            
        logger.info(f"Analyzing data for visualization: {str(data)[:100]}...")
        
        # Check if default_llm is available
        llm = state.get("default_llm")
        if not llm:
            logger.error("No default LLM provided for data visualization")
            state["tool_error"] = "No default LLM provided for data visualization"
            return state
        
        # Get the data visualization prompt template
        prompt_template = get_data_visualization_prompt()
        
        # Create the prompt with relevant data and context
        context = {
            "data_type": detect_data_type(data),
            "available_viz_types": ["line_chart", "bar_chart", "pie_chart", "radar_chart", "data_grid", "map", "json_viewer"],
            "user_preferences": state.get("visualization_preferences", {})
        }
        
        # Format the prompt with our data
        prompt = prompt_template.format(
            results=json.dumps(data, default=str),
            query=query,
            intent=json.dumps(intent, default=str),
            context=json.dumps(context, default=str)
        )
        
        # Log the prompt for debugging
        logger.llm("Data visualization prompt", prompt=prompt)

        
        # Call LLM to get visualization recommendations
        response = await llm.ainvoke(prompt)
        
        # Log the LLM response
        logger.llm("Data visualization LLM response", response=response.content)
        
        # Parse LLM response and generate visualizations
        visualizations = parse_llm_visualization_response(response.content, data)
        
        # If LLM-based visualization failed, fall back to a simple fallback
        if not visualizations:
            logger.info("LLM visualization failed, creating fallback visualization")
            visualizations = [{
                "type": "json_viewer",
                "title": "Query Result Data",
                "description": "Raw JSON data from the GraphQL query",
                "data": data
            }]
        
        # Generate recommendations based on visualization types
        recommendations = generate_recommendations(visualizations)
        
        # Store the visualization result in the state
        state["visualization_result"] = {
            "visualizations": visualizations,
            "recommendations": recommendations
        }
        
        logger.info(f"Data visualization completed successfully with {len(visualizations)} visualizations")
    
        return state
    except Exception as e:
        logger.error(f"Error in data visualization: {str(e)}", exc_info=True)
        state["tool_error"] = f"Data visualization failed: {str(e)}"
        
        return state

def detect_data_type(data: Dict[str, Any]) -> str:
    """
    Detect the general type of data structure, including nested GraphQL response patterns.
    
    Args:
        data: The data structure to analyze
        
    Returns:
        String describing the detected data type
    """
    if not data:
        return "empty"
    
    # Flatten nested data for analysis (common in GraphQL responses)
    flattened_data = flatten_graphql_data(data)
    all_keys = list(flattened_data.keys())
    all_values = list(flattened_data.values())
    
    # Check for time series patterns (dates and numeric values)
    date_patterns = ['date', 'time', 'timestamp', 'created', 'updated', 'at']
    has_date = any(any(pattern in key.lower() for pattern in date_patterns) for key in all_keys)
    has_numeric = any(isinstance(val, (int, float)) and not isinstance(val, bool) for val in all_values)
    
    if has_date and has_numeric:
        return "time_series"
    
    # Check for categorical data
    categorical_patterns = ['status', 'category', 'type', 'state', 'level', 'priority']
    if any(any(pattern in key.lower() for pattern in categorical_patterns) for key in all_keys):
        return "categorical"
    
    # Check for geographical data
    geo_patterns = ['location', 'latitude', 'longitude', 'geo', 'country', 'city', 'address', 'coordinate']
    if any(any(pattern in key.lower() for pattern in geo_patterns) for key in all_keys):
        return "geographical"
    
    # Check for comparable metrics
    metric_patterns = ['score', 'ratio', 'rate', 'count', 'total', 'average', 'accuracy', 'precision', 'recall']
    metric_count = sum(1 for key in all_keys if any(pattern in key.lower() for pattern in metric_patterns))
    
    if metric_count >= 2:
        return "metrics"
    
    # Check for GraphQL-specific patterns
    if any(key in data for key in ['edges', 'nodes', 'pageInfo']):
        return "paginated_list"
    
    if isinstance(data, dict) and len(data) == 1 and isinstance(list(data.values())[0], list):
        return "single_list"
    
    # Default to generic structured data
    return "structured"

def flatten_graphql_data(data: Any, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten nested GraphQL data structures for better analysis.
    
    Args:
        data: The data to flatten
        parent_key: The parent key for nested structures
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            # Handle GraphQL pagination structures
            if k in ['edges', 'nodes'] and isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        # For edges, look in 'node' if it exists
                        if k == 'edges' and 'node' in item:
                            items.extend(flatten_graphql_data(item['node'], f"{new_key}[{i}].node", sep).items())
                        else:
                            items.extend(flatten_graphql_data(item, f"{new_key}[{i}]", sep).items())
            elif isinstance(v, dict):
                items.extend(flatten_graphql_data(v, new_key, sep).items())
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # Handle arrays of objects
                for i, item in enumerate(v[:5]):  # Limit to first 5 items for performance
                    items.extend(flatten_graphql_data(item, f"{new_key}[{i}]", sep).items())
            else:
                items.append((new_key, v))
    elif isinstance(data, list):
        for i, item in enumerate(data[:5]):  # Limit to first 5 items for performance
            if isinstance(item, (dict, list)):
                items.extend(flatten_graphql_data(item, f"{parent_key}[{i}]" if parent_key else f"item_{i}", sep).items())
            else:
                items.append((f"{parent_key}[{i}]" if parent_key else f"item_{i}", item))
    else:
        items.append((parent_key, data))
    
    return dict(items)

def parse_llm_visualization_response(response_content: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse the LLM response into visualization specifications
    
    Args:
        response_content: Raw text response from the LLM
        data: The original data being visualized
        
    Returns:
        List of visualization specifications
    """
    visualizations = []
    
    try:
        # Clean the response - remove markdown formatting if needed
        cleaned_response = response_content.strip()
        
        # First try: Check if the entire response is valid JSON
        try:
            json_data = json.loads(cleaned_response)
            
            # If it's an array, assume it's a list of visualizations
            if isinstance(json_data, list):
                visualizations = json_data
            # If it's a dict, assume it's a single visualization
            elif isinstance(json_data, dict):
                visualizations = [json_data]
            
            logger.info("Successfully parsed LLM response as direct JSON")
            
        except json.JSONDecodeError:
            logger.info("Response is not direct JSON, trying to extract JSON blocks")
            
            # Second try: Extract JSON code blocks (format: ```json {...} ```)
            json_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            json_matches = re.findall(json_block_pattern, cleaned_response)
            
            if json_matches:
                for json_str in json_matches:
                    try:
                        json_data = json.loads(json_str.strip())
                        if isinstance(json_data, list):
                            visualizations.extend(json_data)
                        elif isinstance(json_data, dict):
                            visualizations.append(json_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON block: {str(e)[:100]}")
            
            # Third try: Look for JSON objects/arrays without code blocks
            if not visualizations:
                # Try to find JSON objects/arrays within the text
                object_pattern = r'(\{[\s\S]*?\})'
                array_pattern = r'(\[[\s\S]*?\])'
                
                # Try to extract arrays first (for multiple visualizations)
                array_matches = re.findall(array_pattern, cleaned_response)
                for array_str in array_matches:
                    try:
                        json_data = json.loads(array_str)
                        if isinstance(json_data, list):
                            visualizations.extend(json_data)
                            break  # If we found a valid array, stop looking
                    except:
                        continue
                
                # If we still don't have visualizations, try objects
                if not visualizations:
                    object_matches = re.findall(object_pattern, cleaned_response)
                    for object_str in object_matches:
                        try:
                            json_data = json.loads(object_str)
                            if isinstance(json_data, dict):
                                visualizations.append(json_data)
                        except:
                            continue
        
        # Validate and normalize the visualization specs
        validated_visualizations = []
        for viz in visualizations:
            if not isinstance(viz, dict):
                logger.warning(f"Invalid visualization spec (not a dict): {type(viz)}")
                continue
                
            # Check for required fields
            if 'type' not in viz:
                logger.warning("Visualization spec missing 'type' field")
                continue
                
            # Ensure we have a data field (create empty one if missing)
            if 'data' not in viz:
                viz['data'] = {}
                
            # Ensure we have title and description (add defaults if missing)
            if 'title' not in viz:
                viz['title'] = f"{viz['type'].replace('_', ' ').title()} Visualization"
                
            if 'description' not in viz:
                viz['description'] = f"Visualization of data using {viz['type'].replace('_', ' ')}"
                
            # Normalize type names
            valid_types = ["line_chart", "bar_chart", "pie_chart", "radar_chart", "data_grid", "map", "json_viewer"]
            if viz['type'] not in valid_types:
                # Try to map to a valid type
                type_mapping = {
                    "line": "line_chart",
                    "bar": "bar_chart",
                    "pie": "pie_chart",
                    "radar": "radar_chart",
                    "table": "data_grid",
                    "grid": "data_grid",
                    "map": "map",
                    "geo": "map",
                    "json": "json_viewer"
                }
                viz_type = viz['type'].lower()
                for key, value in type_mapping.items():
                    if key in viz_type:
                        viz['type'] = value
                        break
                else:
                    # If no match, default to json_viewer
                    viz['type'] = "json_viewer"
            
            validated_visualizations.append(viz)
        
        # If we couldn't parse any visualizations, create a fallback
        if not validated_visualizations:
            logger.warning("Could not parse any valid visualizations, creating fallback")
            validated_visualizations = [{
                "type": "json_viewer",
                "title": "Raw Query Result Data",
                "description": "Showing raw data from the GraphQL query",
                "data": data
            }]
            
        logger.info(f"Successfully parsed {len(validated_visualizations)} visualization specs")
        return validated_visualizations
        
    except Exception as e:
        logger.error(f"Error parsing LLM visualization response: {str(e)}", exc_info=True)
        # Return fallback visualization
        return [{
            "type": "json_viewer",
            "title": "Raw Query Result Data",
            "description": "Showing raw data from the GraphQL query as fallback due to parsing error",
            "data": data
        }]

def generate_recommendations(visualizations: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations for improving visualizations"""
    recommendations = []
    
    if not visualizations:
        recommendations.append("No visualizations could be generated. Consider querying more structured data.")
        return recommendations
    
    # Check for visualization types and provide appropriate recommendations
    has_time_series = any(v.get("type") == "line_chart" for v in visualizations)
    has_comparison = any(v.get("type") in ["bar_chart", "radar_chart"] for v in visualizations)
    has_categorical = any(v.get("type") in ["pie_chart", "bar_chart"] and "Distribution" in v.get("title", "") for v in visualizations)
    has_geo = any(v.get("type") == "map" for v in visualizations)
    has_table = any(v.get("type") == "data_grid" for v in visualizations)
    has_json = any(v.get("type") == "json_viewer" for v in visualizations)
    
    # Add specific recommendations based on visualization types
    if has_time_series:
        recommendations.append("Consider adding date filters to your query to focus on specific time periods.")
    
    if has_comparison:
        recommendations.append("Include additional metrics in your query to enhance comparison visualizations.")
    
    if has_categorical:
        recommendations.append("Query additional categorical fields to explore different distributions.")
    
    if has_geo:
        recommendations.append("Include location data with coordinates for more precise geographical visualization.")
    
    if has_table and len(visualizations) == 1:
        recommendations.append("Your data appears to be tabular. Consider adding specific fields to visualize trends or patterns.")
    
    if has_json and len(visualizations) == 1:
        recommendations.append("Your query returned complex data. Try querying specific fields to create more targeted visualizations.")
    
    # General recommendations
    if len(visualizations) <= 2:
        recommendations.append("Query more diverse data types to generate additional visualization options.")
    
    # Add fallback recommendation if none were generated
    if not recommendations:
        recommendations.append("The visualizations provide a good overview of your data. Consider drilling down into specific areas of interest.")
    
    return recommendations 