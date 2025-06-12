#!/usr/bin/env python3
"""
Logging configuration for the Text-to-GraphQL MCP Server using loguru.
"""

import os
import sys
from datetime import datetime
from loguru import logger as loguru_logger
import json

# Remove default logger
loguru_logger.remove()

# Setup logs directory
os.makedirs("logs", exist_ok=True)

def pretty_json(value):
    """Format JSON nicely for logs with proper indentation and colors."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)
    return str(value)

def setup_logger(name="app", log_level="INFO"):
    """
    Configure and return a logger with the given name and log level
    
    Args:
        name: Name of the logger
        log_level: Logging level to use
        
    Returns:
        A configured logger instance
    """
    # Create current date for log file naming
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs/{name}_{current_date}.log"
    
    # Console handler with colorful formatting
    loguru_logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <blue>{function}:{line}</blue> | <level>{message}</level>",
        filter=lambda record: record["extra"].get("name", "") == name or not record["extra"].get("name"),
        colorize=True,
        enqueue=True,  # Thread-safe logging
    )
    
    # File handler with rotation
    loguru_logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} | {function}:{line} | {message}",
        filter=lambda record: record["extra"].get("name", "") == name or not record["extra"].get("name"),
        rotation="10 MB",
        compression="zip",
        retention="1 week",
        enqueue=True,  # Thread-safe logging
    )
    
    # Create a contextualized logger
    contextualized_logger = loguru_logger.bind(name=name)
    
    # Add a special method for JSON logging
    def log_json(level, message, data, **kwargs):
        pretty = pretty_json(data)
        contextualized_logger.opt(colors=True).log(
            level, 
            f"{message}\n<magenta>{pretty}</magenta>", 
            **kwargs
        )
    
    # Add a method for logging LLM prompts
    def log_llm(message, prompt=None, response=None, **kwargs):
        log_message = f"{message}"
        
        if prompt:
            prompt_str = prompt if isinstance(prompt, str) else pretty_json(prompt)
            log_message += f"\n<yellow>Prompt:</yellow>\n<yellow>{prompt_str}</yellow>"
            
        if response:
            response_str = response if isinstance(response, str) else pretty_json(response)
            log_message += f"\n<green>Response:</green>\n<green>{response_str}</green>"
            
        contextualized_logger.opt(colors=True).info(log_message, **kwargs)
    
    # Add a method for logging GraphQL queries
    def log_graphql(message, query=None, variables=None, result=None, error=None, **kwargs):
        log_message = f"{message}"
        
        if query:
            query_str = query.strip() if isinstance(query, str) else pretty_json(query)
            log_message += f"\n<cyan>Query:</cyan>\n<cyan>{query_str}</cyan>"
        
        if variables:
            variables_str = pretty_json(variables)
            log_message += f"\n<blue>Variables:</blue>\n<blue>{variables_str}</blue>"
        
        if result:
            result_str = pretty_json(result)
            log_message += f"\n<green>Result:</green>\n<green>{result_str}</green>"
            
        if error:
            error_str = error if isinstance(error, str) else pretty_json(error)
            log_message += f"\n<red>Error:</red>\n<red>{error_str}</red>"
            
        level = "ERROR" if error else "INFO"
        contextualized_logger.opt(colors=True).log(level, log_message, **kwargs)
    
    # Add methods to the logger
    contextualized_logger.json = log_json
    contextualized_logger.llm = log_llm
    contextualized_logger.graphql = log_graphql
    
    return contextualized_logger

# Create a default application logger
logger = setup_logger() 