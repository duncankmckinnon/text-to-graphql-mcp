# Text-to-GraphQL MCP Server

Transform natural language queries into GraphQL queries using an MCP (Model Context Protocol) server that integrates seamlessly with AI assistants like Claude Desktop and Cursor.

## 🚀 Overview

The Text-to-GraphQL MCP Server converts natural language descriptions into valid GraphQL queries using advanced AI agents built with LangGraph. It provides a bridge between human language and GraphQL APIs, making database and API interactions more intuitive for developers and non-technical users alike.

## ✨ Features

- **Natural Language to GraphQL**: Convert plain English queries to valid GraphQL
- **Schema Management**: Load and introspect GraphQL schemas automatically
- **Query Validation**: Validate generated queries against loaded schemas
- **Query Execution**: Execute queries against GraphQL endpoints with authentication
- **Query History**: Track and manage query history across sessions
- **MCP Protocol**: Full compatibility with Claude Desktop, Cursor, and other MCP clients
- **Error Handling**: Graceful error handling with detailed debugging information
- **Caching**: Built-in caching for schemas and frequently used queries

## 🛠 Installation

### Prerequisites: Install UV (Recommended)

UV is a fast Python package installer and resolver. Install it first:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Setup for MCP Usage

```bash
# Install dependencies (UV automatically creates virtual environment)
uv sync

# Test the installation
uv run text-to-graphql-mcp --help
```

> **Note**: The `uv run` pattern automatically handles virtual environments, making MCP configuration cleaner and more reliable than traditional pip installations.

### Alternative Installation Methods

**From PyPI (when published):**
```bash
pip install text-to-graphql-mcp
```

**Development Setup:**
```bash
# For contributing to the project
uv sync --dev
```

## 🏃‍♂️ Quick Start

### 1. Configure with Cursor (Recommended)

Add to your `.cursor/mcp.json`:

```json
{
  "text-to-graphql": {
    "command": "uv",
    "args": [
      "--directory",
      "/path/to/text-to-graphql-mcp",
      "run",
      "text-to-graphql-mcp"
    ],
    "env": {
      "OPENAI_API_KEY": "your_openai_api_key_here",
      "GRAPHQL_ENDPOINT": "https://your-graphql-api.com/graphql",
      "GRAPHQL_API_KEY": "your_api_key_here",
      "GRAPHQL_AUTH_TYPE": "bearer"
    }
  }
}
```

> Replace `/path/to/text-to-graphql-mcp` with the actual path to your cloned repository.

### 2. Configure with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "text-to-graphql": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/text-to-graphql-mcp",
        "run",
        "text-to-graphql-mcp"
      ],
      "env": {
        "OPENAI_API_KEY": "your_openai_api_key_here",
        "GRAPHQL_ENDPOINT": "https://your-graphql-api.com/graphql",
        "GRAPHQL_API_KEY": "your_api_key_here",
        "GRAPHQL_AUTH_TYPE": "bearer"
      }
    }
  }
}
```

### 3. Alternative: Use Environment Variables

If you prefer using a `.env` file (useful for local development):

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
GRAPHQL_ENDPOINT=https://your-graphql-api.com/graphql
GRAPHQL_API_KEY=your_api_key_here

# Optional - Authentication method (bearer|apikey|direct)
GRAPHQL_AUTH_TYPE=bearer

# Optional - Model settings
MODEL_NAME=gpt-4o
MODEL_TEMPERATURE=0
```

Then use a simplified MCP configuration:

```json
{
  "text-to-graphql": {
    "command": "uv",
    "args": [
      "--directory",
      "/path/to/text-to-graphql-mcp",
      "run",
      "text-to-graphql-mcp"
    ]
  }
}
```

### 4. Run the MCP Server (Optional - for testing)

```bash
# Run the server directly for testing
text-to-graphql-mcp

# Or run as a module
python -m text_to_graphql_mcp.mcp_server
```

## 🔧 Usage

### Available MCP Tools

#### `generate_graphql_query`
Convert natural language to GraphQL queries.

```
Input: "Get all users with their names and emails"
Output: query { users { id name email } }
```

#### `validate_graphql_query`
Validate GraphQL queries against the loaded schema.

#### `execute_graphql_query`
Execute GraphQL queries and return formatted results.

#### `get_query_history`
Retrieve the history of all queries in the current session.

#### `get_query_examples`
Get example queries to understand the system's capabilities.

### Example Interactions

**Natural Language Input:**
```
"Show me all blog posts from the last week with their authors and comment counts"
```

**Generated GraphQL:**
```graphql
query {
  posts(where: { createdAt: { gte: "2024-06-05T00:00:00Z" } }) {
    id
    title
    content
    createdAt
    author {
      id
      name
      email
    }
    comments {
      id
    }
    _count {
      comments
    }
  }
}
```

## 🏗 Architecture

The system uses a multi-agent architecture built with LangGraph:

1. **Intent Recognition**: Understands what the user wants to accomplish
2. **Schema Management**: Loads and manages GraphQL schema information
3. **Query Construction**: Builds GraphQL queries from natural language
4. **Query Validation**: Ensures queries are valid against the schema
5. **Query Execution**: Executes queries against the GraphQL endpoint
6. **Data Visualization**: Provides recommendations for visualizing results

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM operations | Required |
| `GRAPHQL_ENDPOINT` | GraphQL API endpoint URL | Required |
| `GRAPHQL_API_KEY` | API key for your GraphQL service | Required |
| `GRAPHQL_AUTH_TYPE` | Authentication method: `bearer`, `apikey`, or `direct` | `bearer` |
| `GRAPHQL_HEADERS` | Custom headers as JSON (overrides auto-auth) | `{}` |
| `MODEL_NAME` | OpenAI model to use | `gpt-4o` |
| `MODEL_TEMPERATURE` | Model temperature for responses | `0` |
| `API_HOST` | Server host address | `127.0.0.1` |
| `API_PORT` | Server port | `8000` |
| `RECURSION_LIMIT` | Max recursion for agent workflow | `10` |

#### Authentication Types

- **`bearer`** (default): Uses `Authorization: Bearer <token>` - standard for most GraphQL APIs
- **`apikey`**: Uses `X-API-Key: <key>` - used by some APIs like Arize
- **`direct`**: Uses `Authorization: <token>` - direct token without Bearer prefix
- **Custom**: Set `GRAPHQL_HEADERS` to override with any custom authentication format

#### Common GraphQL API Examples

**GitHub GraphQL API:**
```env
GRAPHQL_ENDPOINT=https://api.github.com/graphql
GRAPHQL_API_KEY=ghp_your_github_personal_access_token
GRAPHQL_AUTH_TYPE=bearer
```

**Shopify GraphQL API:**
```env
GRAPHQL_ENDPOINT=https://your-shop.myshopify.com/admin/api/2023-10/graphql.json
GRAPHQL_API_KEY=your_shopify_access_token
GRAPHQL_AUTH_TYPE=bearer
```

**Arize GraphQL API:**
```env
GRAPHQL_ENDPOINT=https://app.arize.com/graphql
GRAPHQL_API_KEY=your_arize_developer_api_key
# Auth type auto-detected for Arize
```

**Hasura:**
```env
GRAPHQL_ENDPOINT=https://your-app.hasura.app/v1/graphql
GRAPHQL_HEADERS={"x-hasura-admin-secret": "your_admin_secret"}
```


## 🔍 Observability & Agent Development

Want to build better AI agents quickly? Check out **[Arize Phoenix](https://phoenix.arize.com/)** - an open-source observability platform specifically designed for LLM applications and agents. Phoenix provides:

- **Real-time monitoring** of your agent's performance and behavior
- **Trace visualization** to understand complex agent workflows
- **Evaluation frameworks** for testing and improving agent responses
- **Data quality insights** to identify issues with your training data
- **Cost tracking** for LLM API usage optimization

Phoenix integrates seamlessly with LangChain and LangGraph (which this project uses) and can help you:
- Debug agent behavior when queries aren't generated correctly
- Monitor GraphQL query quality and success rates
- Track user satisfaction and query complexity
- Optimize your agent's prompt engineering

**Get started with Phoenix:**
```bash
pip install arize-phoenix
phoenix serve
```

Visit [docs.arize.com/phoenix](https://docs.arize.com/phoenix) for comprehensive guides on agent observability and development best practices.

## 🧪 Development

### Setup Development Environment

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy src/
```

### Project Structure

```
text-to-graphql-mcp/
├── src/text_to_graphql_mcp/     # Main package
│   ├── mcp_server.py            # MCP server implementation
│   ├── agent.py                 # LangGraph agent logic
│   ├── config.py                # Configuration management
│   ├── logger.py                # Logging utilities
│   ├── tools/                   # Agent tools
│   └── ...
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml              # Package configuration
└── README.md
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the Elastic License 2.0 (ELv2) - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

**"No module named 'text_to_graphql_mcp'"**
- Ensure you've installed the package: `pip install text-to-graphql-mcp`

**"OpenAI API key not found"**
- Set your `OPENAI_API_KEY` environment variable
- Check your `.env` file configuration

**"GraphQL endpoint not reachable"**
- Verify your `GRAPHQL_ENDPOINT` URL
- Check network connectivity and authentication

**"Schema introspection failed"**
- Ensure the GraphQL endpoint supports introspection
- Check authentication headers if required

## 🔗 Links

- [Issues & Bug Reports](https://github.com/yourusername/text-to-graphql-mcp/issues)
- [MCP Protocol Documentation](https://spec.modelcontextprotocol.io/)

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/)
- Uses [FastMCP](https://github.com/jlowin/fastmcp) for MCP server implementation

---