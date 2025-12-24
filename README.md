# Model Context Protocol (MCP) – Multi-Server Demo

This repository demonstrates a complete MCP pipeline using:
- A database MCP server
- A file MCP server
- A local LLM (Ollama / llama3)
- An agent that plans and executes multi-step workflows

## What this shows
- Tool vs resource separation
- MCP server chaining
- LLM planning vs agent execution
- Prompt design for MCP

## Requirements
- Python 3.10+
- Ollama
- llama3 model

## Setup

1. Clone the repo
2. Create a virtual environment
3. Install dependencies
4. Run the MCP servers
5. Run the agent

(see detailed steps below)

To Run the exmaple:
1. Make sure you downlaod Ollama
2. run ollama server (ollama serve)
3. To generate a new database (users.db), run init_db.py
5. run mcp_agent.py

db_server.py - has all data access fucntion
file_server.py - has all file actions.

