"""
Layout Manager for PDF Generation

This module provides the LayoutManager class for consistent positioning and layout
management in PDF documents. Handles safe positioning, page breaks, and alignment.
"""

import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from reportlab.lib.pagesizes import A4
from pdf_config import PDFConfig, LayoutError


@dataclass
class Position:
    """Represents a position in the PDF coordinate system."""
    x: float
    y: float
    
    def __post_init__(self):
        """Validate position values."""
        if self.x < 0 or self.y < 0:
            raise ValueError("Position coordinates must be non-negative")


@dataclass
class Dimensions:
    """Represents width and height dimensions."""
    width: float
    height: float
    
    def __post_init__(self):
        """Validate dimension values."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Dimensions must be positive")


@dataclass
class BoundingBox:
    """Represents a rectangular area with position and dimensions."""
    position: Position
    dimensions: Dimensions
    
    @property
    def left(self) -> float:
        """Left edge X coordinate."""
        return self.position.x
    
    @property
    def right(self) -> float:
        """Right edge X coordinate."""
        return self.position.x + self.dimensions.width
    
    @property
    def top(self) -> float:
        """Top edge Y coordinate."""
        return self.position.y + self.dimensions.height
    
    @property
    def bottom(self) -> float:
        """Bottom edge Y coordinate."""
        return self.position.y
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within this bounding box."""
        return (self.left <= x <= self.right and 
                self.bottom <= y <= self.top)
    
    def overlaps_with(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box overlaps with another."""
        return not (self.right <= other.left or 
                   other.right <= self.left or
                   self.top <= other.bottom or 
                   other.top <= self.bottom)


class LayoutManager:
    """
    Manages layout calculations and positioning for PDF generation.
    
    Provides methods for safe positioning, page break detection, centering,
    and alignment utilities to ensure consistent and professional PDF layout.
    """
    
    def __init__(self, config: PDFConfig = None, logger: Optional[logging.Logger] = None):
        """
        Initialize LayoutManager with configuration.
        
        Args:
            config: PDF configuration object. If None, uses default PDFConfig.
            logger: Optional logger instance. If None, creates a default logger.
        """
        self.config = config or PDFConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Current page tracking
        self._current_page = 1
        self._current_y_position = self.config.page_height - self.config.margin
        
        # Layout state
        self._elements_on_page: list[BoundingBox] = []
        self._page_break_callbacks: list[callable] = []
        
        self.logger.debug(f"LayoutManager initialized with page size: "
                         f"{self.config.page_width}x{self.config.page_height}")
    
    @property
    def current_page(self) -> int:
        """Get the current page number."""
        return self._current_page
    
    @property
    def current_y_position(self) -> float:
        """Get the current Y position on the page."""
        return self._current_y_position
    
    @property
    def available_height(self) -> float:
        """Get the remaining available height on the current page."""
        return self._current_y_position - self.config.margin - self.config.footer_height
    
    @property
    def content_area(self) -> BoundingBox:
        """Get the content area bounding box for the current page."""
        return BoundingBox(
            position=Position(self.config.margin, self.config.margin + self.config.footer_height),
            dimensions=Dimensions(self.config.content_width, self.config.content_height)
        )
    
    def calculate_safe_position(self, element_height: float, 
                              spacing_before: float = None) -> Tuple[float, bool]:
        """
        Calculate a safe Y position for an element to prevent content overflow.
        
        Args:
            element_height: Height of the element to be placed
            spacing_before: Optional spacing to add before the element
        
        Returns:
            Tuple of (y_position, needs_new_page)
        
        Raises:
            LayoutError: If element is too large to fit on any page
        """
        if spacing_before is None:
            spacing_before = self.config.spacing_medium
        
        # Check if element can fit on any page
        max_available_height = self.config.content_height
        total_element_height = element_height + spacing_before
        
        if total_element_height > max_available_height:
            raise LayoutError(
                element_type="oversized_element",
                position_info=f"Element height ({total_element_height}) exceeds maximum page content height ({max_available_height})"
            )
        
        # Calculate position with spacing
        proposed_y = self._current_y_position - spacing_before - element_height
        min_y_position = self.config.margin + self.config.footer_height
        
        # Check if element fits on current page
        if proposed_y >= min_y_position:
            # Element fits on current page
            safe_y = self._current_y_position - spacing_before
            self.logger.debug(f"Element fits on current page at Y={safe_y}")
            return safe_y, False
        else:
            # Element needs new page
            new_page_y = self.config.page_height - self.config.margin - spacing_before
            self.logger.debug(f"Element requires new page, will be placed at Y={new_page_y}")
            return new_page_y, True
    
    def needs_new_page(self, element_height: float, spacing_before: float = None) -> bool:
        """
        Determine if a new page is needed for an element.
        
        Args:
            element_height: Height of the element to be placed
            spacing_before: Optional spacing to add before the element
        
        Returns:
            True if new page is needed, False otherwise
        """
        try:
            _, needs_new_page = self.calculate_safe_position(element_height, spacing_before)
            return needs_new_page
        except LayoutError:
            # If element is too large, it still needs a new page attempt
            return True
    
    def get_centered_x(self, element_width: float) -> float:
        """
        Calculate centered X position for an element.
        
        Args:
            element_width: Width of the element to center
        
        Returns:
            X coordinate for centered positioning
        
        Raises:
            LayoutError: If element is wider than available content width
        """
        if element_width > self.config.content_width:
            raise LayoutError(
                element_type="oversized_element",
                position_info=f"Element width ({element_width}) exceeds content width ({self.config.content_width})"
            )
        
        centered_x = self.config.margin + (self.config.content_width - element_width) / 2
        self.logger.debug(f"Centered X position calculated: {centered_x} for width {element_width}")
        return centered_x
    
    def get_aligned_x(self, element_width: float, alignment: str = 'left') -> float:
        """
        Calculate X position for element alignment.
        
        Args:
            element_width: Width of the element
            alignment: Alignment type ('left', 'center', 'right')
        
        Returns:
            X coordinate for aligned positioning
        
        Raises:
            LayoutError: If element is wider than available content width
            ValueError: If alignment type is invalid
        """
        if element_width > self.config.content_width:
            raise LayoutError(
                element_type="oversized_element",
                position_info=f"Element width ({element_width}) exceeds content width ({self.config.content_width})"
            )
        
        alignment = alignment.lower()
        
        if alignment == 'left':
            return self.config.margin
        elif alignment == 'center':
            return self.get_centered_x(element_width)
        elif alignment == 'right':
            return self.config.margin + self.config.content_width - element_width
        else:
            raise ValueError(f"Invalid alignment type: {alignment}. Must be 'left', 'center', or 'right'")
    
    def advance_position(self, element_height: float, spacing_after: float = None) -> float:
        """
        Advance the current Y position after placing an element.
        
        Args:
            element_height: Height of the element that was placed
            spacing_after: Optional spacing to add after the element
        
        Returns:
            New current Y position
        """
        if spacing_after is None:
            spacing_after = self.config.spacing_medium
        
        self._current_y_position -= (element_height + spacing_after)
        
        # Ensure we don't go below minimum position
        min_position = self.config.margin + self.config.footer_height
        if self._current_y_position < min_position:
            self._current_y_position = min_position
        
        self.logger.debug(f"Position advanced to Y={self._current_y_position}")
        return self._current_y_position
    
    def start_new_page(self) -> float:
        """
        Start a new page and reset positioning.
        
        Returns:
            Initial Y position for the new page
        """
        self._current_page += 1
        self._current_y_position = self.config.page_height - self.config.margin
        self._elements_on_page.clear()
        
        # Execute page break callbacks
        for callback in self._page_break_callbacks:
            try:
                callback(self._current_page)
            except Exception as e:
                self.logger.error(f"Page break callback failed: {e}")
        
        self.logger.info(f"Started new page {self._current_page} at Y={self._current_y_position}")
        return self._current_y_position
    
    def register_element(self, x: float, y: float, width: float, height: float, 
                        element_type: str = None) -> BoundingBox:
        """
        Register an element's position and dimensions for overlap detection.
        
        Args:
            x: X coordinate of the element
            y: Y coordinate of the element (bottom edge)
            width: Width of the element
            height: Height of the element
            element_type: Optional element type for debugging
        
        Returns:
            BoundingBox representing the registered element
        """
        bbox = BoundingBox(
            position=Position(x, y),
            dimensions=Dimensions(width, height)
        )
        
        self._elements_on_page.append(bbox)
        
        if element_type:
            self.logger.debug(f"Registered {element_type} element at ({x}, {y}) with size {width}x{height}")
        
        return bbox
    
    def check_overlap(self, x: float, y: float, width: float, height: float) -> bool:
        """
        Check if a proposed element would overlap with existing elements.
        
        Args:
            x: X coordinate of the proposed element
            y: Y coordinate of the proposed element (bottom edge)
            width: Width of the proposed element
            height: Height of the proposed element
        
        Returns:
            True if overlap detected, False otherwise
        """
        proposed_bbox = BoundingBox(
            position=Position(x, y),
            dimensions=Dimensions(width, height)
        )
        
        for existing_bbox in self._elements_on_page:
            if proposed_bbox.overlaps_with(existing_bbox):
                self.logger.warning(f"Overlap detected at ({x}, {y}) with size {width}x{height}")
                return True
        
        return False
    
    def get_next_available_position(self, width: float, height: float, 
                                  alignment: str = 'left') -> Tuple[float, float, bool]:
        """
        Find the next available position for an element without overlaps.
        
        Args:
            width: Width of the element
            height: Height of the element
            alignment: Preferred alignment ('left', 'center', 'right')
        
        Returns:
            Tuple of (x, y, needs_new_page)
        """
        # Try current position first
        try:
            x = self.get_aligned_x(width, alignment)
            y, needs_new_page = self.calculate_safe_position(height)
            
            if not needs_new_page and not self.check_overlap(x, y - height, width, height):
                return x, y, False
        except (LayoutError, ValueError):
            pass
        
        # If current position doesn't work, try new page
        new_page_y = self.config.page_height - self.config.margin
        try:
            x = self.get_aligned_x(width, alignment)
            return x, new_page_y, True
        except (LayoutError, ValueError) as e:
            raise LayoutError(
                element_type="positioning_failed",
                position_info=f"Cannot find suitable position for element {width}x{height}: {str(e)}"
            )
    
    def add_page_break_callback(self, callback: callable):
        """
        Add a callback function to be executed when a new page is started.
        
        Args:
            callback: Function to call with page number as argument
        """
        self._page_break_callbacks.append(callback)
        self.logger.debug("Added page break callback")
    
    def get_layout_stats(self) -> Dict[str, Any]:
        """
        Get current layout statistics for debugging and monitoring.
        
        Returns:
            Dictionary with layout statistics
        """
        return {
            'current_page': self._current_page,
            'current_y_position': self._current_y_position,
            'available_height': self.available_height,
            'elements_on_page': len(self._elements_on_page),
            'content_width': self.config.content_width,
            'content_height': self.config.content_height,
            'page_margins': self.config.margin,
            'footer_height': self.config.footer_height
        }
    
    def reset(self):
        """Reset the layout manager to initial state."""
        self._current_page = 1
        self._current_y_position = self.config.page_height - self.config.margin
        self._elements_on_page.clear()
        self.logger.debug("LayoutManager reset to initial state")
    
    def validate_element_fits(self, width: float, height: float) -> bool:
        """
        Validate that an element can fit within the page constraints.
        
        Args:
            width: Width of the element
            height: Height of the element
        
        Returns:
            True if element can fit, False otherwise
        """
        return (width <= self.config.content_width and 
                height <= self.config.content_height)
    
    def get_remaining_space(self) -> Dimensions:
        """
        Get the remaining space available on the current page.
        
        Returns:
            Dimensions object with available width and height
        """
        return Dimensions(
            width=self.config.content_width,
            height=self.available_height
        )