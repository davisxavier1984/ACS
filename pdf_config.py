"""
PDF Configuration and Data Models

This module contains configuration classes and custom exceptions for PDF generation.
Provides centralized configuration management and proper error handling.
"""

import logging
import weakref
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Callable
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage
import io


@dataclass
class PDFConfig:
    """Configuration class for PDF layout and styling constants."""
    
    # Page dimensions
    page_width: float = A4[0]
    page_height: float = A4[1]
    
    # Margins and spacing
    margin: float = 40
    spacing_large: float = 60
    spacing_medium: float = 40
    spacing_small: float = 20
    footer_height: float = 80
    
    # Chart dimensions
    chart_width: int = 800
    chart_height: int = 400
    chart_dpi: int = 150
    
    # Text styling
    title_font_size: int = 16
    header_font_size: int = 14
    body_font_size: int = 10
    small_font_size: int = 8
    
    # Dashboard ACS Colors (based on reference design)
    dashboard_blue: str = '#1F497D'      # Main blue for title and table headers
    dashboard_green: str = '#00B050'     # Section titles and positive values
    dashboard_orange: str = '#FFA500'    # Personnel charts
    dashboard_gray: str = '#A6A6A6'      # Neutral elements
    dashboard_light_green: str = '#E2EFDA'  # Highlighted table rows
    text_color: str = '#000000'
    background_color: str = '#ffffff'
    table_stripe_color: tuple = (0.94, 0.94, 0.94)  # Light gray RGB for ReportLab
    
    # Legacy colors (keep for compatibility)
    primary_color: str = '#1F497D'
    secondary_color: str = '#00B050'
    
    # Table settings
    table_row_height: float = 20
    table_header_height: float = 25
    
    # Dashboard mode (enables Dashboard ACS format)
    dashboard_mode: bool = False
    
    @property
    def content_width(self) -> float:
        """Calculate available content width after margins."""
        return self.page_width - (2 * self.margin)
    
    @property
    def content_height(self) -> float:
        """Calculate available content height after margins and footer."""
        return self.page_height - (2 * self.margin) - self.footer_height


@dataclass
class ChartConfig:
    """Configuration class for chart rendering settings."""
    
    width: int
    height: int
    dpi: int
    background_color: str = 'white'
    margin_config: Dict[str, int] = field(default_factory=lambda: {
        'l': 40,  # left
        'r': 40,  # right
        't': 50,  # top
        'b': 40   # bottom
    })
    
    # Chart styling
    font_family: str = 'Arial'
    font_size: int = 12
    title_font_size: int = 14
    
    # Export settings
    format: str = 'png'
    scale: float = 2.0
    
    @classmethod
    def default_financial_chart(cls) -> 'ChartConfig':
        """Create default configuration for financial charts."""
        return cls(
            width=800,
            height=400,
            dpi=150,
            background_color='white'
        )
    
    @classmethod
    def default_personnel_chart(cls) -> 'ChartConfig':
        """Create default configuration for personnel charts."""
        return cls(
            width=800,
            height=350,
            dpi=150,
            background_color='white'
        )


# Custom Exception Classes

class PDFGenerationError(Exception):
    """Base exception for PDF generation errors."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ChartConversionError(PDFGenerationError):
    """Exception raised when Plotly chart conversion fails."""
    
    def __init__(self, chart_type: str = None, original_error: Exception = None):
        self.chart_type = chart_type
        self.original_error = original_error
        
        message = "Failed to convert chart to image"
        if chart_type:
            message += f" (chart type: {chart_type})"
        
        details = None
        if original_error:
            details = str(original_error)
        
        super().__init__(message, details)


class ResourceCleanupError(PDFGenerationError):
    """Exception raised when resource cleanup fails."""
    
    def __init__(self, resource_type: str = None, original_error: Exception = None):
        self.resource_type = resource_type
        self.original_error = original_error
        
        message = "Failed to cleanup resources"
        if resource_type:
            message += f" (resource type: {resource_type})"
        
        details = None
        if original_error:
            details = str(original_error)
        
        super().__init__(message, details)


class LayoutError(PDFGenerationError):
    """Exception raised when content layout fails."""
    
    def __init__(self, element_type: str = None, position_info: str = None):
        self.element_type = element_type
        self.position_info = position_info
        
        message = "Failed to layout content properly"
        if element_type:
            message += f" (element: {element_type})"
        
        details = position_info
        
        super().__init__(message, details)


class DataValidationError(PDFGenerationError):
    """Exception raised when input data validation fails."""
    
    def __init__(self, field_name: str = None, validation_rule: str = None):
        self.field_name = field_name
        self.validation_rule = validation_rule
        
        message = "Data validation failed"
        if field_name:
            message += f" (field: {field_name})"
        
        details = validation_rule
        
        super().__init__(message, details)


class ResourceManager:
    """
    Context manager for proper resource cleanup during PDF generation.
    
    Handles registration and cleanup of various resources including:
    - PIL Images
    - File handles
    - BytesIO objects
    - Custom cleanup functions
    
    Usage:
        with ResourceManager() as rm:
            image = rm.register_resource(PILImage.open('logo.png'))
            buffer = rm.register_resource(io.BytesIO())
            # Resources are automatically cleaned up on exit
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize ResourceManager.
        
        Args:
            logger: Optional logger instance. If None, creates a default logger.
        """
        self._resources: List[Dict[str, Any]] = []
        self._cleanup_functions: List[Callable] = []
        self._logger = logger or logging.getLogger(__name__)
        self._is_active = False
    
    def register_resource(self, resource: Any, cleanup_method: str = None, 
                         resource_type: str = None) -> Any:
        """
        Register a resource for automatic cleanup.
        
        Args:
            resource: The resource to register (PIL Image, file handle, etc.)
            cleanup_method: Optional custom cleanup method name
            resource_type: Optional resource type description for logging
        
        Returns:
            The registered resource (for chaining)
        
        Raises:
            ResourceCleanupError: If resource registration fails
        """
        if not self._is_active:
            self._logger.warning("ResourceManager not active. Resource may not be cleaned up properly.")
        
        try:
            # Determine resource type and cleanup method
            if resource_type is None:
                resource_type = type(resource).__name__
            
            if cleanup_method is None:
                cleanup_method = self._determine_cleanup_method(resource)
            
            # Store resource info
            resource_info = {
                'resource': resource,
                'cleanup_method': cleanup_method,
                'resource_type': resource_type,
                'weak_ref': None
            }
            
            # Use weak reference for objects that support it
            try:
                resource_info['weak_ref'] = weakref.ref(resource)
            except TypeError:
                # Some objects don't support weak references
                pass
            
            self._resources.append(resource_info)
            
            self._logger.debug(f"Registered resource: {resource_type} with cleanup method: {cleanup_method}")
            
            return resource
            
        except Exception as e:
            raise ResourceCleanupError(
                resource_type=resource_type or "unknown",
                original_error=e
            )
    
    def register_cleanup_function(self, cleanup_func: Callable, description: str = None):
        """
        Register a custom cleanup function.
        
        Args:
            cleanup_func: Function to call during cleanup
            description: Optional description for logging
        """
        self._cleanup_functions.append({
            'function': cleanup_func,
            'description': description or 'custom cleanup function'
        })
        
        self._logger.debug(f"Registered cleanup function: {description or 'unnamed'}")
    
    def cleanup_all(self):
        """
        Clean up all registered resources and execute cleanup functions.
        
        This method is called automatically when exiting the context manager,
        but can also be called manually if needed.
        """
        cleanup_errors = []
        resources_cleaned = 0
        
        # Execute custom cleanup functions first
        for func_info in self._cleanup_functions:
            try:
                func_info['function']()
                self._logger.debug(f"Executed cleanup function: {func_info['description']}")
            except Exception as e:
                error_msg = f"Failed to execute cleanup function {func_info['description']}: {str(e)}"
                self._logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Clean up registered resources
        for resource_info in reversed(self._resources):  # Cleanup in reverse order
            try:
                resource = resource_info['resource']
                cleanup_method = resource_info['cleanup_method']
                resource_type = resource_info['resource_type']
                
                # Check if resource still exists (for weak references)
                if resource_info['weak_ref'] is not None:
                    if resource_info['weak_ref']() is None:
                        self._logger.debug(f"Resource {resource_type} already garbage collected")
                        continue
                
                # Perform cleanup
                if cleanup_method and hasattr(resource, cleanup_method):
                    getattr(resource, cleanup_method)()
                    self._logger.debug(f"Cleaned up {resource_type} using {cleanup_method}")
                    resources_cleaned += 1
                elif cleanup_method == 'del':
                    del resource
                    self._logger.debug(f"Deleted {resource_type}")
                    resources_cleaned += 1
                else:
                    self._logger.warning(f"No cleanup method available for {resource_type}")
                
            except Exception as e:
                error_msg = f"Failed to cleanup {resource_info['resource_type']}: {str(e)}"
                self._logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Clear resource lists
        self._resources.clear()
        self._cleanup_functions.clear()
        
        # Log summary
        if cleanup_errors:
            self._logger.warning(f"Resource cleanup completed with {len(cleanup_errors)} errors. "
                               f"Successfully cleaned {resources_cleaned} resources.")
        else:
            self._logger.info(f"Successfully cleaned up {resources_cleaned} resources.")
        
        # Raise exception if there were critical errors
        if cleanup_errors:
            raise ResourceCleanupError(
                resource_type="multiple",
                original_error=Exception(f"Multiple cleanup errors: {'; '.join(cleanup_errors)}")
            )
    
    def _determine_cleanup_method(self, resource: Any) -> str:
        """
        Determine the appropriate cleanup method for a resource.
        
        Args:
            resource: The resource to analyze
        
        Returns:
            String name of the cleanup method
        """
        # PIL Image
        if isinstance(resource, PILImage.Image):
            return 'close'
        
        # File-like objects
        if hasattr(resource, 'close') and callable(getattr(resource, 'close')):
            return 'close'
        
        # BytesIO and similar
        if isinstance(resource, io.IOBase):
            return 'close'
        
        # Default to deletion
        return 'del'
    
    def get_resource_count(self) -> int:
        """
        Get the number of currently registered resources.
        
        Returns:
            Number of registered resources
        """
        return len(self._resources)
    
    def get_resource_summary(self) -> Dict[str, int]:
        """
        Get a summary of registered resources by type.
        
        Returns:
            Dictionary with resource types as keys and counts as values
        """
        summary = {}
        for resource_info in self._resources:
            resource_type = resource_info['resource_type']
            summary[resource_type] = summary.get(resource_type, 0) + 1
        return summary
    
    def __enter__(self):
        """Enter the context manager."""
        self._is_active = True
        self._logger.debug("ResourceManager context entered")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and cleanup all resources."""
        self._is_active = False
        
        if exc_type is not None:
            self._logger.warning(f"Exiting ResourceManager due to exception: {exc_type.__name__}: {exc_val}")
        
        try:
            self.cleanup_all()
        except ResourceCleanupError as e:
            self._logger.error(f"Resource cleanup failed: {e}")
            # Don't suppress the original exception if there was one
            if exc_type is None:
                raise
        
        self._logger.debug("ResourceManager context exited")
        
        # Don't suppress exceptions
        return False