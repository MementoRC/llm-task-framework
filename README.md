# LLM Task Framework

A generic framework for building LLM-powered task execution systems with built-in **MCP (Model Context Protocol) server interface** and pluggable task implementations.

## Overview

This framework provides a clean, extensible architecture for creating AI-powered tools that automatically expose **MCP server capabilities**. Any task implementation immediately becomes available via MCP protocol for integration with Claude Desktop, Cursor, and other MCP-compatible clients.

### Supported Task Types
- **Test Analysis** (pytest failure analysis and fix suggestions)
- **Documentation Generation** (automated docstring generation)
- **Code Analysis** (static analysis and recommendations) 
- **Content Generation** (markdown documentation, API docs)
- **Custom Tasks** (easily extensible)

## Key Features

### 🚀 **Built-in MCP Server Interface**
- **Auto-generated MCP endpoints** for every task type
- **Multiple transports** - STDIO, HTTP, WebSocket
- **Schema auto-generation** from task definitions
- **Unified client interface** across all tasks

### 🔧 **Pluggable Task Architecture**
- **Protocol-based design** with clear contracts
- **Dependency Injection** for flexible component composition
- **State Machine workflow** management
- **Easy task registration** and discovery

### 🤖 **Multi-LLM Support**
- **Anthropic Claude** integration
- **OpenAI GPT** support
- **Custom LLM providers** via protocol interface
- **Configurable model selection** per task

## Quick Start

### Using via MCP (Recommended)

```bash
# Start MCP server with multiple tasks
llm-task-framework --mcp-transport stdio --tasks pytest_analysis,docstring_generation

# Available MCP tools automatically include:
# - analyze_pytest_output
# - apply_suggestion  
# - generate_docstrings
# - apply_docstrings
# - list_available_tasks
# - get_task_schema
```

### Using Programmatically

```python
from llm_task_framework import TaskFramework

# Execute pytest analysis
framework = TaskFramework.create("pytest_analysis")
results = framework.execute(
    input_path="tests/",
    max_suggestions=5
)

# Execute docstring generation
docstring_framework = TaskFramework.create("docstring_generation")
results = docstring_framework.execute(
    input_path="src/",
    style="google",
    include_examples=True
)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Interface                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   STDIO Transport│  │  HTTP Transport │  │ WS Transport │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│              Generic Task Framework                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Task Registry  │  │  MCP Router     │  │  Schema Gen  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Task Execution Engine                      │ │
│  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │ │
│  │  │Extractor  │ │Analyzer  │ │Suggester │ │Applier   │  │ │
│  │  └───────────┘ └──────────┘ └──────────┘ └──────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                   Task Implementations                      │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ pytest_analysis │ │docstring_gen    │ │ custom_tasks    │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install llm-task-framework
```

## MCP Integration

### Claude Desktop Integration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "llm-task-framework": {
      "command": "llm-task-framework",
      "args": ["--mcp-transport", "stdio", "--tasks", "pytest_analysis,docstring_generation"]
    }
  }
}
```

### Available MCP Tools

#### Universal Tools (available for all tasks)
- `list_available_tasks` - Get all registered task types
- `get_task_schema` - Get input/output schema for a task
- `execute_task` - Generic task execution interface

#### Pytest Analysis Tools
- `analyze_pytest_output` - Analyze test failures from output files
- `run_and_analyze` - Run tests and analyze failures
- `apply_suggestion` - Apply a suggested fix
- `suggest_fixes` - Generate fix suggestions for failures

#### Docstring Generation Tools  
- `generate_docstrings` - Generate docstrings for Python code
- `apply_docstrings` - Apply generated docstrings to files
- `analyze_code_structure` - Analyze Python file structure

## Creating Custom Tasks

### 1. Define Task Models

```python
from dataclasses import dataclass
from llm_task_framework.core.protocols import TaskInput, TaskResult

@dataclass
class MyTaskInput(TaskInput):
    source_path: str
    options: dict

@dataclass  
class MyTaskResult(TaskResult):
    processed_data: dict
    suggestions: list
```

### 2. Implement Task Components

```python
from llm_task_framework.core.protocols import (
    TaskExtractor, TaskAnalyzer, TaskSuggester, TaskApplier
)

class MyTaskExtractor(TaskExtractor):
    def extract(self, input_data: MyTaskInput) -> dict:
        # Parse and extract data from source
        return extracted_data

class MyTaskAnalyzer(TaskAnalyzer):
    def analyze(self, extraction_results: dict) -> dict:
        # Analyze extracted data
        return analysis_results

class MyTaskSuggester(TaskSuggester):
    def suggest(self, analysis_results: dict) -> list:
        # Generate LLM-powered suggestions
        return suggestions

class MyTaskApplier(TaskApplier):
    def apply(self, suggestions: list) -> dict:
        # Apply suggestions to target files
        return application_results
```

### 3. Define MCP Endpoints

```python
from llm_task_framework.mcp.decorators import mcp_tool

@mcp_tool("my_task_execute")
async def execute_my_task(source_path: str, options: dict) -> dict:
    """Execute my custom task."""
    framework = get_task_framework("my_task")
    input_data = MyTaskInput(source_path=source_path, options=options)
    return await framework.execute(input_data)

@mcp_tool("my_task_validate")  
async def validate_my_task_input(source_path: str) -> dict:
    """Validate input for my task."""
    # Validation logic
    return {"valid": True, "message": "Input is valid"}
```

### 4. Register Task

```python
from llm_task_framework.core.registry import TaskRegistry

TaskRegistry.register("my_task", {
    "extractor": MyTaskExtractor,
    "analyzer": MyTaskAnalyzer,
    "suggester": MyTaskSuggester, 
    "applier": MyTaskApplier,
    "mcp_endpoints": [execute_my_task, validate_my_task_input],
    "description": "My custom task implementation"
})
```

## Configuration

```python
from llm_task_framework import TaskConfig

config = TaskConfig(
    # LLM Configuration
    llm_provider="anthropic",  # or "openai", "custom"
    api_key="your_key_here",
    model="claude-3-sonnet-20240229",
    max_tokens=4000,
    
    # MCP Configuration
    mcp_transport="stdio",  # or "http", "websocket"
    mcp_host="localhost",
    mcp_port=8000,
    
    # Task Configuration
    enabled_tasks=["pytest_analysis", "docstring_generation"],
    task_settings={
        "docstring_generation": {
            "style": "google",
            "include_examples": True
        },
        "pytest_analysis": {
            "max_suggestions": 5,
            "confidence_threshold": 0.7
        }
    }
)
```

## Development

```bash
git clone https://github.com/yourusername/llm-task-framework.git
cd llm-task-framework
pip install -e ".[dev]"

# Run tests
pytest

# Start development MCP server
llm-task-framework --dev --mcp-transport stdio
```

## License

MIT License - see LICENSE file for details.