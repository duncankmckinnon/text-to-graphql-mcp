FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Use UV to create environment and install dependencies
# The --frozen flag is removed to allow UV to resolve dependencies without a lock file
RUN uv sync --no-dev

# Run the MCP server using uv run
ENTRYPOINT ["uv", "run", "python", "-m", "src.text_to_graphql_mcp.mcp_server"] 