"""
Core protocol definitions for the LLM Task Framework.

This module defines the fundamental interfaces that all task implementations
must follow. These protocols ensure consistency and interoperability across
different task types while maintaining flexibility for task-specific logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# Base data models
class TaskInput(ABC):
    """Base class for task input data."""
    pass


class TaskResult(ABC):
    """Base class for task results."""
    pass


# Core task component protocols
@runtime_checkable
class TaskExtractor(Protocol):
    """
    Protocol for extracting and parsing input data for tasks.
    
    Extractors are responsible for parsing various input formats
    (files, directories, URLs, etc.) and converting them into
    structured data that can be processed by analyzers.
    """

    def extract(self, input_data: TaskInput) -> Dict[str, Any]:
        """
        Extract structured data from input.

        Args:
            input_data: Task-specific input data

        Returns:
            Dictionary containing extracted and structured data

        Raises:
            ExtractionError: If extraction fails
        """
        ...


@runtime_checkable
class TaskAnalyzer(Protocol):
    """
    Protocol for analyzing extracted data.
    
    Analyzers process the structured data from extractors to understand
    patterns, identify issues, or gather context needed for suggestion
    generation.
    """

    def analyze(self, extraction_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze extracted data to understand context and patterns.

        Args:
            extraction_results: Results from a TaskExtractor

        Returns:
            Dictionary containing analysis results and insights

        Raises:
            AnalysisError: If analysis fails
        """
        ...


@runtime_checkable
class TaskSuggester(Protocol):
    """
    Protocol for generating suggestions based on analysis results.
    
    Suggesters use the analysis results to generate actionable
    suggestions, typically leveraging LLM capabilities for
    intelligent recommendations.
    """

    def suggest(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate suggestions based on analysis results.

        Args:
            analysis_results: Results from a TaskAnalyzer

        Returns:
            List of suggestions with metadata

        Raises:
            SuggestionError: If suggestion generation fails
        """
        ...


@runtime_checkable
class TaskApplier(Protocol):
    """
    Protocol for applying suggestions to target resources.
    
    Appliers take suggestions and apply them to files, databases,
    or other resources, typically with validation and rollback
    capabilities.
    """

    def apply(
        self, 
        suggestions: List[Dict[str, Any]], 
        validation_tests: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply suggestions to target resources.

        Args:
            suggestions: List of suggestions to apply
            validation_tests: Optional validation commands/tests

        Returns:
            Results of the application including success status

        Raises:
            ApplicationError: If application fails
        """
        ...


# Task orchestration protocols
@runtime_checkable
class TaskExecutor(Protocol):
    """
    Protocol for executing complete task workflows.
    
    Executors coordinate the entire task pipeline: extraction,
    analysis, suggestion generation, and optional application.
    """

    def execute(
        self, 
        input_data: TaskInput,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """
        Execute the complete task workflow.

        Args:
            input_data: Task input data
            context: Optional execution context

        Returns:
            Task execution results

        Raises:
            TaskExecutionError: If task execution fails
        """
        ...


@runtime_checkable
class TaskValidator(Protocol):
    """
    Protocol for validating task inputs and results.
    
    Validators ensure that inputs meet requirements and that
    results are properly formatted and valid.
    """

    def validate_input(self, input_data: TaskInput) -> Dict[str, Any]:
        """
        Validate task input data.

        Args:
            input_data: Input data to validate

        Returns:
            Validation results with success status and messages

        Raises:
            ValidationError: If validation fails critically
        """
        ...

    def validate_result(self, result: TaskResult) -> Dict[str, Any]:
        """
        Validate task result data.

        Args:
            result: Result data to validate

        Returns:
            Validation results with success status and messages

        Raises:
            ValidationError: If validation fails critically
        """
        ...


# LLM service protocol
@runtime_checkable
class LLMService(Protocol):
    """
    Protocol for language model services.
    
    LLM services provide the AI capabilities needed by suggesters
    and other components that require natural language processing.
    """

    def generate_completion(
        self, 
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate a completion from the language model.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional model-specific parameters

        Returns:
            The generated completion

        Raises:
            LLMServiceError: If generation fails
        """
        ...

    async def generate_completion_async(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate a completion asynchronously.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional model-specific parameters

        Returns:
            The generated completion

        Raises:
            LLMServiceError: If generation fails
        """
        ...


# State machine protocols (for complex workflows)
@runtime_checkable
class TaskState(Protocol):
    """Protocol for task state machine states."""

    @property
    def name(self) -> str:
        """Get the name of the state."""
        ...

    def on_enter(self, context: Dict[str, Any]) -> None:
        """Execute actions when entering the state."""
        ...

    def on_exit(self, context: Dict[str, Any]) -> None:
        """Execute actions when exiting the state."""
        ...


@runtime_checkable
class TaskStateMachine(Protocol):
    """Protocol for task state machines."""

    @property
    def current_state(self) -> TaskState:
        """Get the current state."""
        ...

    def trigger(self, trigger_name: str, **kwargs: Any) -> bool:
        """
        Trigger a state transition.

        Args:
            trigger_name: Name of the trigger
            **kwargs: Additional trigger data

        Returns:
            True if transition was successful, False otherwise
        """
        ...


# Task configuration and metadata
class TaskMetadata:
    """Metadata about a task implementation."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.dependencies = dependencies or []
        self.tags = tags or []


@runtime_checkable  
class TaskDefinition(Protocol):
    """
    Protocol for complete task definitions.
    
    Task definitions bundle all the components needed for a task
    along with metadata and configuration.
    """

    @property
    def metadata(self) -> TaskMetadata:
        """Get task metadata."""
        ...

    @property
    def extractor(self) -> TaskExtractor:
        """Get the task extractor."""
        ...

    @property
    def analyzer(self) -> TaskAnalyzer:
        """Get the task analyzer."""
        ...

    @property
    def suggester(self) -> TaskSuggester:
        """Get the task suggester."""
        ...

    @property
    def applier(self) -> TaskApplier:
        """Get the task applier."""
        ...

    @property
    def validator(self) -> Optional[TaskValidator]:
        """Get the task validator (optional)."""
        ...


# Error types
class TaskFrameworkError(Exception):
    """Base exception for task framework errors."""
    pass


class ExtractionError(TaskFrameworkError):
    """Error during data extraction."""
    pass


class AnalysisError(TaskFrameworkError):
    """Error during data analysis."""
    pass


class SuggestionError(TaskFrameworkError):
    """Error during suggestion generation."""
    pass


class ApplicationError(TaskFrameworkError):
    """Error during suggestion application."""
    pass


class ValidationError(TaskFrameworkError):
    """Error during validation."""
    pass


class TaskExecutionError(TaskFrameworkError):
    """Error during task execution."""
    pass


class LLMServiceError(TaskFrameworkError):
    """Error in LLM service operations."""
    pass