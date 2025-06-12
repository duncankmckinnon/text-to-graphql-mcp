"""
Schema management tool for the Text-to-GraphQL MCP Server.
"""
import os
import json
from typing import Dict, Any, Optional, List
from ..types import AgentState
from ..logger import logger
from ..config import settings
from graphql import build_client_schema
from graphql.utilities import IntrospectionQuery
from gql.transport.httpx import HTTPXTransport
from gql import Client as GQLClient, gql
from .graphql_helpers import execute_graphql_query


async def schema_management(state: AgentState) -> AgentState:
    """
    Manages GraphQL schema and identifies relevant types.
    
    Given the results from intent_recognition:
    - Identifies relevant types and fields from the schema for the user's intent
    - Determines type relationships that are needed to fulfill the request
    - Provides guidance for schema exploration when needed
    - Extracts documentation for relevant fields to support understanding
    """
    state["current_step"] = "schema_management"
    logger.json("INFO", "Schema management tool called", {
        "state": state
    })
    
    try:
        # Get the intent from the state
        intent = state.get("intent")
        if not intent:
            logger.json("WARNING", "No intent provided for schema management", {
                "tool": "schema_management",
                "error": "missing_intent"
            })
            state["tool_error"] = "No intent provided for schema management"
            return state
            
        logger.json("INFO", "Managing schema based on intent", {
            "tool": "schema_management",
            "intent": intent
        })
        
        # Mock implementation - in a real implementation, this would fetch the schema from the GraphQL API
        schema = load_graphql_schema(endpoint_url=settings.GRAPHQL_ENDPOINT)
        
        # Store the schema in the state
        state["schema"] = schema
        logger.json("INFO", "Schema management completed successfully", {
            "tool": "schema_management",
            "schema_loaded": bool(schema),
            "schema_type": type(schema).__name__
        })
        
        return state
    except Exception as e:
        error_info = {
            "tool": "schema_management",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        logger.json("ERROR", "Error in schema management", error_info)
        state["tool_error"] = f"Schema management failed: {str(e)}"
        return state 
    
def load_graphql_schema(file_path: Optional[str] = None, endpoint_url: Optional[str] = None, 
                        headers: Optional[Dict[str, str]] = None) -> str:
    """
    Load a GraphQL schema from either a file or via introspection.
    If schema is loaded via introspection, it will be saved to the specified file path.
    Falls back to a default schema if both methods fail.
    
    Args:
        file_path: Path to schema file (optional)
        endpoint_url: GraphQL endpoint for introspection (optional)
        headers: Optional request headers for introspection
        
    Returns:
        The schema as a string
    """
    import time
    import datetime
    
    schema = None
    
    logger.json("DEBUG", "Starting schema loading process", {
        "function": "load_graphql_schema",
        "file_path_provided": bool(file_path),
        "endpoint_provided": bool(endpoint_url)
    })
    
    # Use configured endpoint if not provided
    if not endpoint_url:
        endpoint_url = settings.GRAPHQL_ENDPOINT
        logger.json("INFO", "Using configured GraphQL endpoint", {
            "function": "load_graphql_schema",
            "endpoint": endpoint_url
        })
    
    # Use configured headers if none provided
    if headers is None and endpoint_url:
        headers = settings.get_graphql_headers()
        logger.json("INFO", "Using configured authentication headers", {
            "function": "load_graphql_schema"
        })
    
    # Default schema file path if not provided
    if not file_path:
        # Use the name of the endpoint in the filename if available
        if endpoint_url:
            from urllib.parse import urlparse
            parsed_url = urlparse(endpoint_url)
            domain = parsed_url.netloc.replace(".", "_")
            file_path = f"src/schema/{domain}_schema.graphql"
        else:
            file_path = "src/schema/cached_schema.graphql"
    
    logger.json("INFO", "Attempting to load schema from cache", {
        "function": "load_graphql_schema",
        "cache_file": file_path
    })
    
    # Try loading from file first
    schema = load_schema_from_file(file_path)
    if schema:
        logger.json("INFO", "Successfully loaded schema from cache", {
            "function": "load_graphql_schema",
            "source": "file",
            "file_path": file_path,
            "schema_size": len(json.dumps(schema))
        })
        schema = get_graphql_schema_from_introspection(schema)
        return schema
            
    # If file loading failed or no schema was found, try introspection if endpoint is provided
    if endpoint_url:
        logger.json("INFO", "No cached schema found, attempting introspection", {
            "function": "load_graphql_schema",
            "endpoint": endpoint_url,
            "headers_provided": bool(headers)
        })
        schema = load_schema_via_introspection(endpoint_url, headers)
        
        if schema:
            # Save the schema to file
            try:
                logger.json("INFO", "Saving schema from introspection to file", {
                    "function": "load_graphql_schema",
                    "destination_file": file_path
                })
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                with open(file_path, "w") as f:
                    f.write(json.dumps(schema))
                    
                logger.json("INFO", "Schema successfully saved to file", {
                    "function": "load_graphql_schema",
                    "file_path": file_path,
                    "schema_size": len(json.dumps(schema))
                })
                
                logger.json("DEBUG", "Converting introspection data to GraphQLSchema", {
                    "function": "load_graphql_schema"
                })
                
                schema = get_graphql_schema_from_introspection(schema)
                return schema
            except Exception as e:
                logger.json("ERROR", "Error saving schema to file", {
                    "function": "load_graphql_schema",
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "file_path": file_path
                })
                schema = get_graphql_schema_from_introspection(schema)
                return schema
    
    # If both methods failed, try loading the default schema
    default_schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schema", "default_schema.graphql")
    logger.json("WARNING", "Failed to load schema from file or introspection, trying default schema", {
        "function": "load_graphql_schema",
        "default_schema_path": default_schema_path
    })
    
    default_schema = load_schema_from_file(default_schema_path)
    if default_schema:
        logger.json("INFO", "Successfully loaded default schema as fallback", {
            "function": "load_graphql_schema",
            "source": "default_file",
            "file_path": default_schema_path
        })
        return default_schema
    
    # If all methods failed, return a default message
    logger.json("WARNING", "Failed to load GraphQL schema from any source", {
        "function": "load_graphql_schema",
        "attempts": ["cache", "introspection", "default"]
    })
    return "# No schema available. Please provide a valid schema file or GraphQL endpoint."

def load_schema_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a GraphQL schema from a file.
    
    Args:
        file_path: Path to the schema file (.graphql, .gql)
        
    Returns:
        The schema as a string or None if file not found
    """
    try:
        if os.path.exists(file_path):
            logger.json("INFO", "Loading schema from file", {
                "function": "load_schema_from_file",
                "file_path": file_path
            })
            with open(file_path, "r") as f:
                schema_data = json.loads(f.read())
                logger.json("DEBUG", "Schema file loaded successfully", {
                    "function": "load_schema_from_file",
                    "file_path": file_path,
                    "schema_size": len(json.dumps(schema_data))
                })
                return schema_data
        else:
            logger.json("WARNING", "Schema file not found", {
                "function": "load_schema_from_file",
                "file_path": file_path
            })
            return None
    except Exception as e:
        logger.json("ERROR", "Error loading schema from file", {
            "function": "load_schema_from_file",
            "error_type": type(e).__name__,
            "error": str(e),
            "file_path": file_path
        })
        return None
    
def load_schema_via_introspection(endpoint_url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Load a GraphQL schema via introspection query.
    
    Args:
        endpoint_url: GraphQL API endpoint
        headers: Optional headers for the request (e.g., authentication)
        
    Returns:
        The schema as a string or None if introspection fails
    """
    
    try:
        logger.json("INFO", "Loading schema via introspection", {
            "function": "load_schema_via_introspection",
            "endpoint": endpoint_url,
            "headers_provided": bool(headers)
        })

        # Use configured headers if none provided
        if headers is None:
            headers = settings.get_graphql_headers()
            logger.json("INFO", "Using configured authentication headers for introspection", {
                "function": "load_schema_via_introspection"
            })

        result = execute_graphql_query(endpoint_url, introspection_query, headers)
        
        if result:
            logger.json("DEBUG", "Introspection query successful", {
                "function": "load_schema_via_introspection",
                "response_size": len(json.dumps(result)),
                "has_data": "__schema" in result.get("data", {})
            })
        
        return result
    except Exception as e:
        logger.json("ERROR", "Error loading schema via introspection", {
            "function": "load_schema_via_introspection",
            "error_type": type(e).__name__,
            "error": str(e),
            "endpoint": endpoint_url
        })
        return None
    
def get_graphql_schema_from_introspection(introspection_data: Dict[str, Any]) -> str:
    """
    Convert introspection data to a GraphQLSchema object.
    
    Args:
        introspection_data: The introspection query result
    """
    try:
        logger.json("DEBUG", "Converting introspection data to GraphQLSchema", {
            "function": "get_graphql_schema_from_introspection",
            "data_size": len(json.dumps(introspection_data))
        })

        introspection = IntrospectionQuery(introspection_data["data"])
        schema = build_client_schema(introspection)
        
        logger.json("DEBUG", "Successfully built GraphQLSchema from introspection data", {
            "function": "get_graphql_schema_from_introspection",
            "schema_type": type(schema).__name__,
            "query_type": schema.query_type.name if schema.query_type else None,
            "mutation_type": schema.mutation_type.name if schema.mutation_type else None
        })
        
        return schema
    except Exception as e:
        logger.json("ERROR", "Error building GraphQLSchema from introspection data", {
            "function": "get_graphql_schema_from_introspection",
            "error_type": type(e).__name__,
            "error": str(e)
        })
        # Return original data if conversion fails
        return introspection_data
    
introspection_query = """
    query IntrospectionQuery {
        __schema {

            queryType { name }
            mutationType { name }
            subscriptionType { name }
            types {
            ...FullType
            }
            directives {
            name
            description

            locations
            args {
                ...InputValue
            }
            }
        }
        }

        fragment FullType on __Type {
        kind
        name
        description

        fields(includeDeprecated: true) {
            name
            description
            args {
            ...InputValue
            }
            type {
            ...TypeRef
            }
            isDeprecated
            deprecationReason
        }
        inputFields {
            ...InputValue
        }
        interfaces {
            ...TypeRef
        }
        enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
        }
        possibleTypes {
            ...TypeRef
        }
        }

        fragment InputValue on __InputValue {
        name
        description
        type { ...TypeRef }
        defaultValue


        }

        fragment TypeRef on __Type {
        kind
        name
        ofType {
            kind
            name
            ofType {
            kind
            name
            ofType {
                kind
                name
                ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                        }
                        }
                    }
                    }
                }
                }
            }
            }
        }
        }
"""