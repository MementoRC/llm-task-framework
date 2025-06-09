# LLM Task Framework

A generic framework for building LLM-powered task execution systems with built-in MCP server interface and pluggable task implementations.

## Quick Start

```python
from llm_task_framework import TaskConfig

config = TaskConfig(
    llm_provider="anthropic",
    api_key="your_key_here",
    model="claude-3-sonnet-20240229",
)
```

## Features

- Generic task execution framework
- LLM provider integration (Anthropic, OpenAI)
- MCP (Model Context Protocol) server interface
- Pluggable task implementations
- Built-in quality assurance

## Documentation

- [Overview](overview.md) - Architecture and concepts
- [CI/CD Guide](cicd-guide.md) - Development workflow
- [Git Flow](git-flow-workflow.md) - Git workflow patterns