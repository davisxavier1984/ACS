"""
Unit tests for LayoutManager class.

Tests layout calculations, positioning, page breaks, and alignment utilities.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from layout_manager import LayoutManager, Position, Dimensions, BoundingBox
from pdf_config import PDFConfig, LayoutError


class TestPosition:
    """Test Position dataclass."""
    
    def test_valid_position(self):
        """Test creating valid position."""
        pos = Position(100.0, 200.0)
        assert pos.x == 100.0
        assert pos.y == 200.0
    
    def test_invalid_position_negative_x(self):
        """Test that negative X raises ValueError."""
        with pytest.raises(ValueError, match="Position coordinates must be non-negative"):
            Position(-10.0, 200.0)
    
    def test_invalid_position_negative_y(self):
        """Test that negative Y raises ValueError."""
        with pytest.raises(ValueError, match="Position coordinates must be non-negative"):
            Position(100.0, -50.0)
    
    def test_zero_position(self):
        """Test that zero coordinates are valid."""
        pos = Position(0.0, 0.0)
        assert pos.x == 0.0
        assert pos.y == 0.0


class TestDimensions:
    """Test Dimensions dataclass."""
    
    def test_valid_dimensions(self):
        """Test creating valid dimensions."""
        dim = Dimensions(100.0, 200.0)
        assert dim.width == 100.0
        assert dim.height == 200.0
    
    def test_invalid_dimensions_zero_width(self):
        """Test that zero width raises ValueError."""
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            Dimensions(0.0, 200.0)
    
    def test_invalid_dimensions_negative_height(self):
        """Test that negative height raises ValueError."""
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            Dimensions(100.0, -50.0)


class TestBoundingBox:
    """Test BoundingBox dataclass."""
    
    def test_bounding_box_properties(self):
        """Test bounding box edge properties."""
        bbox = BoundingBox(
            position=Position(10.0, 20.0),
            dimensions=Dimensions(100.0, 50.0)
        )
        
        assert bbox.left == 10.0
        assert bbox.right == 110.0
        assert bbox.bottom == 20.0
        assert bbox.top == 70.0
    
    def test_contains_point(self):
        """Test point containment check."""
        bbox = BoundingBox(
            position=Position(10.0, 20.0),
            dimensions=Dimensions(100.0, 50.0)
        )
        
        # Points inside
        assert bbox.contains_point(50.0, 40.0)
        assert bbox.contains_point(10.0, 20.0)  # Bottom-left corner
        assert bbox.contains_point(110.0, 70.0)  # Top-right corner
        
        # Points outside
        assert not bbox.contains_point(5.0, 40.0)  # Left of box
        assert not bbox.contains_point(50.0, 15.0)  # Below box
        assert not bbox.contains_point(120.0, 40.0)  # Right of box
        assert not bbox.contains_point(50.0, 80.0)  # Above box
    
    def test_overlaps_with(self):
        """Test bounding box overlap detection."""
        bbox1 = BoundingBox(
            position=Position(10.0, 20.0),
            dimensions=Dimensions(100.0, 50.0)
        )
        
        # Overlapping box
        bbox2 = BoundingBox(
            position=Position(50.0, 40.0),
            dimensions=Dimensions(100.0, 50.0)
        )
        assert bbox1.overlaps_with(bbox2)
        assert bbox2.overlaps_with(bbox1)
        
        # Non-overlapping box
        bbox3 = BoundingBox(
            position=Position(150.0, 20.0),
            dimensions=Dimensions(50.0, 50.0)
        )
        assert not bbox1.overlaps_with(bbox3)
        assert not bbox3.overlaps_with(bbox1)
        
        # Adjacent box (touching but not overlapping)
        bbox4 = BoundingBox(
            position=Position(110.0, 20.0),
            dimensions=Dimensions(50.0, 50.0)
        )
        assert not bbox1.overlaps_with(bbox4)


class TestLayoutManager:
    """Test LayoutManager class."""
    
    @pytest.fixture
    def config(self):
        """Create test PDF configuration."""
        return PDFConfig(
            page_width=595.0,  # A4 width
            page_height=842.0,  # A4 height
            margin=40.0,
            footer_height=80.0,
            spacing_medium=20.0
        )
    
    @pytest.fixture
    def layout_manager(self, config):
        """Create LayoutManager instance for testing."""
        return LayoutManager(config=config)
    
    def test_initialization(self, layout_manager, config):
        """Test LayoutManager initialization."""
        assert layout_manager.config == config
        assert layout_manager.current_page == 1
        assert layout_manager.current_y_position == config.page_height - config.margin
        assert len(layout_manager._elements_on_page) == 0
    
    def test_initialization_with_defaults(self):
        """Test LayoutManager initialization with default config."""
        lm = LayoutManager()
        assert isinstance(lm.config, PDFConfig)
        assert lm.current_page == 1
    
    def test_content_area_property(self, layout_manager, config):
        """Test content area calculation."""
        content_area = layout_manager.content_area
        
        assert content_area.position.x == config.margin
        assert content_area.position.y == config.margin + config.footer_height
        assert content_area.dimensions.width == config.content_width
        assert content_area.dimensions.height == config.content_height
    
    def test_available_height_property(self, layout_manager, config):
        """Test available height calculation."""
        expected_height = (config.page_height - config.margin - 
                          config.margin - config.footer_height)
        assert layout_manager.available_height == expected_height
    
    def test_calculate_safe_position_fits_on_page(self, layout_manager):
        """Test safe position calculation when element fits on current page."""
        element_height = 100.0
        spacing_before = 20.0
        
        y_pos, needs_new_page = layout_manager.calculate_safe_position(
            element_height, spacing_before
        )
        
        assert not needs_new_page
        assert y_pos == layout_manager.config.page_height - layout_manager.config.margin - spacing_before
    
    def test_calculate_safe_position_needs_new_page(self, layout_manager):
        """Test safe position calculation when element needs new page."""
        # Set current position very low
        layout_manager._current_y_position = 150.0
        
        element_height = 100.0
        spacing_before = 20.0
        
        y_pos, needs_new_page = layout_manager.calculate_safe_position(
            element_height, spacing_before
        )
        
        assert needs_new_page
        assert y_pos == layout_manager.config.page_height - layout_manager.config.margin - spacing_before
    
    def test_calculate_safe_position_element_too_large(self, layout_manager):
        """Test safe position calculation with oversized element."""
        element_height = layout_manager.config.content_height + 100.0
        
        with pytest.raises(LayoutError, match="Element height .* exceeds maximum page content height"):
            layout_manager.calculate_safe_position(element_height)
    
    def test_needs_new_page(self, layout_manager):
        """Test page break detection."""
        # Element that fits
        assert not layout_manager.needs_new_page(100.0)
        
        # Set position low to force new page
        layout_manager._current_y_position = 150.0
        assert layout_manager.needs_new_page(100.0)
    
    def test_get_centered_x(self, layout_manager):
        """Test centered X position calculation."""
        element_width = 200.0
        expected_x = (layout_manager.config.margin + 
                     (layout_manager.config.content_width - element_width) / 2)
        
        centered_x = layout_manager.get_centered_x(element_width)
        assert centered_x == expected_x
    
    def test_get_centered_x_oversized_element(self, layout_manager):
        """Test centered X position with oversized element."""
        element_width = layout_manager.config.content_width + 100.0
        
        with pytest.raises(LayoutError, match="Element width .* exceeds content width"):
            layout_manager.get_centered_x(element_width)
    
    def test_get_aligned_x_left(self, layout_manager):
        """Test left alignment."""
        element_width = 200.0
        aligned_x = layout_manager.get_aligned_x(element_width, 'left')
        assert aligned_x == layout_manager.config.margin
    
    def test_get_aligned_x_center(self, layout_manager):
        """Test center alignment."""
        element_width = 200.0
        aligned_x = layout_manager.get_aligned_x(element_width, 'center')
        expected_x = layout_manager.get_centered_x(element_width)
        assert aligned_x == expected_x
    
    def test_get_aligned_x_right(self, layout_manager):
        """Test right alignment."""
        element_width = 200.0
        aligned_x = layout_manager.get_aligned_x(element_width, 'right')
        expected_x = (layout_manager.config.margin + 
                     layout_manager.config.content_width - element_width)
        assert aligned_x == expected_x
    
    def test_get_aligned_x_invalid_alignment(self, layout_manager):
        """Test invalid alignment type."""
        with pytest.raises(ValueError, match="Invalid alignment type"):
            layout_manager.get_aligned_x(200.0, 'invalid')
    
    def test_advance_position(self, layout_manager):
        """Test position advancement."""
        initial_y = layout_manager.current_y_position
        element_height = 100.0
        spacing_after = 20.0
        
        new_y = layout_manager.advance_position(element_height, spacing_after)
        
        expected_y = initial_y - element_height - spacing_after
        assert new_y == expected_y
        assert layout_manager.current_y_position == expected_y
    
    def test_advance_position_with_minimum_constraint(self, layout_manager):
        """Test position advancement with minimum position constraint."""
        # Set position close to minimum
        min_position = layout_manager.config.margin + layout_manager.config.footer_height
        layout_manager._current_y_position = min_position + 10.0
        
        # Try to advance beyond minimum
        layout_manager.advance_position(50.0, 10.0)
        
        # Should be clamped to minimum
        assert layout_manager.current_y_position == min_position
    
    def test_start_new_page(self, layout_manager):
        """Test starting a new page."""
        # Add some elements to current page
        layout_manager.register_element(100, 200, 50, 30)
        assert len(layout_manager._elements_on_page) == 1
        
        # Start new page
        new_y = layout_manager.start_new_page()
        
        assert layout_manager.current_page == 2
        assert new_y == layout_manager.config.page_height - layout_manager.config.margin
        assert layout_manager.current_y_position == new_y
        assert len(layout_manager._elements_on_page) == 0
    
    def test_start_new_page_with_callback(self, layout_manager):
        """Test starting new page with callback."""
        callback_mock = Mock()
        layout_manager.add_page_break_callback(callback_mock)
        
        layout_manager.start_new_page()
        
        callback_mock.assert_called_once_with(2)
    
    def test_register_element(self, layout_manager):
        """Test element registration."""
        x, y, width, height = 100.0, 200.0, 50.0, 30.0
        
        bbox = layout_manager.register_element(x, y, width, height, "test_element")
        
        assert len(layout_manager._elements_on_page) == 1
        assert bbox.position.x == x
        assert bbox.position.y == y
        assert bbox.dimensions.width == width
        assert bbox.dimensions.height == height
    
    def test_check_overlap_no_overlap(self, layout_manager):
        """Test overlap detection with no overlap."""
        # Register an element
        layout_manager.register_element(100, 200, 50, 30)
        
        # Check non-overlapping position
        assert not layout_manager.check_overlap(200, 200, 50, 30)
    
    def test_check_overlap_with_overlap(self, layout_manager):
        """Test overlap detection with overlap."""
        # Register an element
        layout_manager.register_element(100, 200, 50, 30)
        
        # Check overlapping position
        assert layout_manager.check_overlap(120, 210, 50, 30)
    
    def test_get_next_available_position_current_page(self, layout_manager):
        """Test getting next available position on current page."""
        width, height = 200.0, 100.0
        
        x, y, needs_new_page = layout_manager.get_next_available_position(width, height)
        
        assert not needs_new_page
        assert x == layout_manager.config.margin  # Left alignment by default
    
    def test_get_next_available_position_new_page_needed(self, layout_manager):
        """Test getting next available position when new page is needed."""
        # Set position very low
        layout_manager._current_y_position = 150.0
        
        width, height = 200.0, 100.0
        
        x, y, needs_new_page = layout_manager.get_next_available_position(width, height)
        
        assert needs_new_page
        assert y == layout_manager.config.page_height - layout_manager.config.margin
    
    def test_validate_element_fits(self, layout_manager):
        """Test element fit validation."""
        # Element that fits
        assert layout_manager.validate_element_fits(200.0, 100.0)
        
        # Element too wide
        assert not layout_manager.validate_element_fits(
            layout_manager.config.content_width + 10.0, 100.0
        )
        
        # Element too tall
        assert not layout_manager.validate_element_fits(
            200.0, layout_manager.config.content_height + 10.0
        )
    
    def test_get_remaining_space(self, layout_manager):
        """Test remaining space calculation."""
        remaining = layout_manager.get_remaining_space()
        
        assert remaining.width == layout_manager.config.content_width
        assert remaining.height == layout_manager.available_height
    
    def test_get_layout_stats(self, layout_manager):
        """Test layout statistics."""
        # Add some elements
        layout_manager.register_element(100, 200, 50, 30)
        layout_manager.register_element(200, 300, 60, 40)
        
        stats = layout_manager.get_layout_stats()
        
        assert stats['current_page'] == 1
        assert stats['elements_on_page'] == 2
        assert stats['content_width'] == layout_manager.config.content_width
        assert stats['content_height'] == layout_manager.config.content_height
    
    def test_reset(self, layout_manager):
        """Test layout manager reset."""
        # Modify state
        layout_manager.start_new_page()
        layout_manager.register_element(100, 200, 50, 30)
        layout_manager.advance_position(100, 20)
        
        # Reset
        layout_manager.reset()
        
        assert layout_manager.current_page == 1
        assert layout_manager.current_y_position == layout_manager.config.page_height - layout_manager.config.margin
        assert len(layout_manager._elements_on_page) == 0
    
    def test_page_break_callback_exception_handling(self, layout_manager, caplog):
        """Test that page break callback exceptions are handled gracefully."""
        def failing_callback(page_num):
            raise Exception("Callback failed")
        
        layout_manager.add_page_break_callback(failing_callback)
        
        with caplog.at_level(logging.ERROR):
            layout_manager.start_new_page()
        
        # Should still complete page break despite callback failure
        assert layout_manager.current_page == 2
        assert "Page break callback failed" in caplog.text


class TestLayoutManagerIntegration:
    """Integration tests for LayoutManager."""
    
    def test_typical_pdf_layout_workflow(self):
        """Test a typical PDF layout workflow."""
        config = PDFConfig()
        lm = LayoutManager(config)
        
        # Add header
        header_height = 60.0
        header_y, needs_new_page = lm.calculate_safe_position(header_height)
        assert not needs_new_page
        
        lm.register_element(
            lm.config.margin, 
            header_y - header_height, 
            lm.config.content_width, 
            header_height,
            "header"
        )
        lm.advance_position(header_height)
        
        # Add chart
        chart_height = 300.0
        chart_width = 400.0
        chart_x = lm.get_centered_x(chart_width)
        chart_y, needs_new_page = lm.calculate_safe_position(chart_height)
        assert not needs_new_page
        
        lm.register_element(chart_x, chart_y - chart_height, chart_width, chart_height, "chart")
        lm.advance_position(chart_height)
        
        # Add table that might need new page
        table_height = 400.0
        table_y, needs_new_page = lm.calculate_safe_position(table_height)
        
        if needs_new_page:
            lm.start_new_page()
            table_y, _ = lm.calculate_safe_position(table_height)
        
        lm.register_element(
            lm.config.margin,
            table_y - table_height,
            lm.config.content_width,
            table_height,
            "table"
        )
        lm.advance_position(table_height)
        
        # Verify final state
        stats = lm.get_layout_stats()
        assert stats['elements_on_page'] >= 1  # At least the table
        assert lm.current_page >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])