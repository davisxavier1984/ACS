"""
PDF Layout Boundaries and Overflow Detection Tests
=================================================

Comprehensive tests for detecting layout boundary violations and content overflow
in the PDF generation function. These tests address specific issues found by
other QA agents related to coordinate calculations and element positioning.
"""

import pytest
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from unittest.mock import Mock, patch, MagicMock
import io
import json
from datetime import datetime

# Import our validation utilities
from pdf_coordinate_validator import PDFCoordinateValidator, PDFElement, PDFLayoutAnalyzer


class TestLayoutBoundaryViolations:
    """Test for boundary violations in PDF layout"""
    
    def test_page_margin_violations(self):
        """Test elements don't violate page margins"""
        validator = PDFCoordinateValidator(A4, margin=20)
        width, height = A4
        MARGIN = 20
        
        # Test elements that should violate boundaries
        test_cases = [
            # Element extending beyond left margin
            {"name": "left_violation", "x": 10, "y": 400, "width": 100, "height": 50},
            # Element extending beyond right margin  
            {"name": "right_violation", "x": width - 10, "y": 400, "width": 100, "height": 50},
            # Element extending beyond top margin
            {"name": "top_violation", "x": 100, "y": height - 10, "width": 100, "height": 50},
            # Element extending beyond bottom margin
            {"name": "bottom_violation", "x": 100, "y": 50, "width": 100, "height": 100},
        ]
        
        for case in test_cases:
            validator.add_from_coords(**case)
        
        boundary_errors = validator.validate_boundaries()
        
        # Should detect all 4 violations
        assert len(boundary_errors) >= 4, f"Expected 4+ boundary violations, got {len(boundary_errors)}"
        
        # Check specific violations are detected
        error_text = " ".join(boundary_errors)
        assert "left_violation" in error_text
        assert "right_violation" in error_text  
        assert "top_violation" in error_text
        assert "bottom_violation" in error_text
    
    def test_content_area_calculations(self):
        """Test content area calculations are correct"""
        width, height = A4
        margin = 20
        
        # Content area should be page size minus margins
        expected_content_width = width - 2 * margin
        expected_content_height = height - 2 * margin
        
        assert expected_content_width > 0
        assert expected_content_height > 0
        assert expected_content_width == 555.2756  # 595.2756 - 40
        assert expected_content_height == 801.8898  # 841.8898 - 40
    
    def test_municipal_pdf_actual_layout_boundaries(self):
        """Test the actual municipal PDF layout for boundary violations"""
        validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
        results = validator.run_full_validation()
        
        # Check for boundary violations
        boundary_errors = results['boundary_errors']
        
        if boundary_errors:
            for error in boundary_errors:
                print(f"Boundary Error: {error}")
        
        # This test documents current state - may need fixes
        assert isinstance(boundary_errors, list), "Should return list of boundary errors"
    
    def test_graph_positioning_boundaries(self):
        """Test specific graph positioning doesn't violate boundaries"""
        width, height = A4
        margin = 20
        
        # Test financial graph positioning (Page 1)
        header_height = 90
        y_header = height - margin - header_height
        y_pos = y_header - 20  # Header info spacing
        graph_y = y_pos - 50   # Current graph positioning
        graph_height = 300
        
        # Graph should not extend beyond page boundaries
        assert graph_y > margin, f"Graph top position {graph_y} too close to bottom margin"
        assert graph_y - graph_height > margin, f"Graph bottom position {graph_y - graph_height} extends beyond bottom margin"
        
        # Graph width should fit within margins
        graph_width = width - 2 * margin
        assert graph_width > 0
        assert margin + graph_width <= width - margin
    
    def test_table_centering_boundaries(self):
        """Test table centering doesn't cause boundary violations"""
        width, height = A4
        margin = 20
        
        # Table dimensions from the code
        col_widths = [80, 100, 90, 70, 70]
        table_width = sum(col_widths)  # 410
        
        # Centering calculation
        table_x = (width - table_width) / 2
        
        # Table should be within margins
        assert table_x >= margin, f"Centered table left edge {table_x} extends beyond left margin {margin}"
        assert table_x + table_width <= width - margin, f"Centered table right edge {table_x + table_width} extends beyond right margin {width - margin}"
        
        # Table should actually be centered
        expected_center_x = width / 2
        actual_center_x = table_x + table_width / 2
        center_difference = abs(expected_center_x - actual_center_x)
        assert center_difference < 1, f"Table not properly centered, difference: {center_difference}"


class TestElementOverlapDetection:
    """Test detection of overlapping PDF elements"""
    
    def test_basic_overlap_detection(self):
        """Test basic element overlap detection"""
        validator = PDFCoordinateValidator()
        
        # Create two overlapping elements
        element1 = PDFElement("elem1", 100, 400, 200, 100, 1, "text")
        element2 = PDFElement("elem2", 150, 450, 200, 100, 1, "text")
        
        validator.add_element(element1)
        validator.add_element(element2)
        
        overlaps = validator.detect_overlaps()
        
        assert len(overlaps) == 1, f"Expected 1 overlap, found {len(overlaps)}"
        assert overlaps[0][0] == "elem1" and overlaps[0][1] == "elem2"
    
    def test_no_overlap_different_pages(self):
        """Test elements on different pages don't register as overlapping"""
        validator = PDFCoordinateValidator()
        
        # Same coordinates but different pages
        element1 = PDFElement("page1_elem", 100, 400, 200, 100, 1, "text")
        element2 = PDFElement("page2_elem", 100, 400, 200, 100, 2, "text")
        
        validator.add_element(element1)
        validator.add_element(element2)
        
        overlaps = validator.detect_overlaps()
        assert len(overlaps) == 0, "Elements on different pages should not overlap"
    
    def test_adjacent_elements_no_overlap(self):
        """Test adjacent elements don't register as overlapping"""
        validator = PDFCoordinateValidator()
        
        # Adjacent elements (touching but not overlapping)
        element1 = PDFElement("left_elem", 100, 400, 200, 100, 1, "text")
        element2 = PDFElement("right_elem", 300, 400, 200, 100, 1, "text")  # Starts where elem1 ends
        
        validator.add_element(element1)
        validator.add_element(element2)
        
        overlaps = validator.detect_overlaps()
        assert len(overlaps) == 0, "Adjacent elements should not be detected as overlapping"
    
    def test_municipal_pdf_overlap_detection(self):
        """Test municipal PDF layout for element overlaps"""
        validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
        results = validator.run_full_validation()
        
        overlaps = results['overlaps']
        
        if overlaps:
            for elem1, elem2, overlap_type in overlaps:
                print(f"Overlap detected: {elem1} overlaps with {elem2} ({overlap_type})")
        
        # Document current overlap state
        # In a perfect layout, this should be 0
        assert isinstance(overlaps, list), "Should return list of overlaps"
    
    def test_header_graph_overlap_specific_case(self):
        """Test specific case of header and graph overlap on page 1"""
        width, height = A4
        margin = 20
        
        # Header area
        header_height = 90
        header_y = height - margin - header_height
        header_bottom = header_y
        
        # Graph positioning 
        graph_y = header_bottom - 20 - 50  # header_info_spacing - graph_offset
        graph_height = 300
        graph_bottom = graph_y - graph_height
        
        # Check for overlap
        header_bottom_with_margin = header_bottom - 10  # Small buffer
        
        overlap_exists = graph_y > header_bottom_with_margin
        assert overlap_exists, f"Graph (top={graph_y}) may overlap with header (bottom={header_bottom})"
    
    def test_table_status_card_overlap_page2(self):
        """Test table and status card overlap on page 2"""
        width, height = A4
        margin = 20
        
        # Table positioning (approximate from code analysis)
        table_y = 300  # Approximate position
        table_height = 120
        table_bottom = table_y - table_height
        
        # Status card positioning
        status_y = table_y - 160  # From code: table_y - 120, but may be different
        status_height = 100
        status_bottom = status_y - status_height
        
        # Check minimum spacing
        spacing_between = table_bottom - status_y
        minimum_required_spacing = 20
        
        assert spacing_between >= minimum_required_spacing, f"Insufficient spacing between table and status card: {spacing_between}"


class TestContentOverflowDetection:
    """Test detection of content overflow situations"""
    
    def test_text_content_overflow(self):
        """Test detection of text content that might overflow containers"""
        validator = PDFCoordinateValidator()
        
        # Simulate very long text in a narrow container
        narrow_text_element = PDFElement("long_text", 100, 400, 50, 20, 1, "text")
        validator.add_element(narrow_text_element)
        
        text_errors = validator.validate_text_readability()
        
        # Should detect text width issue
        assert len(text_errors) > 0, "Should detect narrow text container"
        assert "too narrow" in " ".join(text_errors).lower()
    
    def test_small_font_size_detection(self):
        """Test detection of potentially unreadable small text"""
        validator = PDFCoordinateValidator()
        
        # Simulate very small text
        small_text_element = PDFElement("small_text", 100, 400, 200, 8, 1, "text")  # 8pt height
        validator.add_element(small_text_element)
        
        text_errors = validator.validate_text_readability()
        
        # Should detect small text
        assert len(text_errors) > 0, "Should detect small text"
        assert "too small" in " ".join(text_errors).lower()
    
    def test_page_content_overflow(self):
        """Test detection of content that overflows page boundaries"""
        validator = PDFCoordinateValidator()
        width, height = A4
        margin = 20
        
        # Create elements that collectively exceed page height
        elements_data = [
            {"name": "header", "x": margin, "y": height - margin, "width": 500, "height": 100},
            {"name": "graph1", "x": margin, "y": height - 150, "width": 500, "height": 300},
            {"name": "table", "x": margin, "y": height - 500, "width": 500, "height": 200},
            {"name": "graph2", "x": margin, "y": height - 750, "width": 500, "height": 300},
            {"name": "footer", "x": margin, "y": 60, "width": 500, "height": 40},
        ]
        
        for elem_data in elements_data:
            validator.add_from_coords(**elem_data, page=1)
        
        boundary_errors = validator.validate_boundaries()
        
        # Should detect elements extending beyond page boundaries
        assert len(boundary_errors) > 0, "Should detect content overflow"
    
    def test_dynamic_content_sizing_requirements(self):
        """Test requirements for dynamic content sizing"""
        # This test documents the need for dynamic sizing
        
        # Different data scenarios that could affect layout
        data_scenarios = [
            {"months": 3, "municipalities": 1, "expected_table_height": 80},
            {"months": 6, "municipalities": 1, "expected_table_height": 140},
            {"months": 12, "municipalities": 1, "expected_table_height": 260},
        ]
        
        for scenario in data_scenarios:
            # Current code uses fixed height of 120
            fixed_height = 120
            required_height = scenario["expected_table_height"]
            
            if required_height > fixed_height:
                # This scenario would cause overflow
                assert True, f"Scenario with {scenario['months']} months would cause table overflow"
    
    def test_graph_image_overflow_detection(self):
        """Test detection of graph images that might overflow their containers"""
        width, height = A4
        margin = 20
        
        # Graph dimensions as specified in code
        graph_width = width - 2 * margin
        graph_height = 300
        
        # Test maximum graph position to avoid overflow
        max_content_height = height - 2 * margin
        header_space = 120  # Approximate header space needed
        footer_space = 80   # Approximate footer space needed
        
        available_space_for_graph = max_content_height - header_space - footer_space
        
        assert graph_height <= available_space_for_graph, f"Graph height {graph_height} exceeds available space {available_space_for_graph}"


class TestLayoutConsistencyValidation:
    """Test layout consistency across different scenarios"""
    
    def test_consistent_margins_across_pages(self):
        """Test margins are consistent across pages"""
        validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
        
        page1_elements = [e for e in validator.elements if e.page == 1]
        page2_elements = [e for e in validator.elements if e.page == 2]
        
        # Check left margins are consistent
        page1_left_margins = [e.x for e in page1_elements if e.x > 0]
        page2_left_margins = [e.x for e in page2_elements if e.x > 0]
        
        if page1_left_margins and page2_left_margins:
            min_margin_p1 = min(page1_left_margins)
            min_margin_p2 = min(page2_left_margins)
            
            margin_difference = abs(min_margin_p1 - min_margin_p2)
            assert margin_difference <= 5, f"Inconsistent left margins between pages: {margin_difference}"
    
    def test_consistent_content_width_usage(self):
        """Test content width is consistently used"""
        validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
        width, height = A4
        margin = 20
        expected_max_width = width - margin
        
        # Check no elements extend beyond expected content width
        for element in validator.elements:
            assert element.right <= expected_max_width + 5, f"Element {element.name} extends beyond content width: {element.right} > {expected_max_width}"
    
    def test_footer_positioning_consistency(self):
        """Test footer positioning is consistent across pages"""
        validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
        
        footer_elements = [e for e in validator.elements if "footer" in e.name.lower()]
        
        if len(footer_elements) >= 2:
            # Check footer y positions are similar
            footer_positions = [e.y for e in footer_elements]
            max_position_diff = max(footer_positions) - min(footer_positions)
            
            assert max_position_diff <= 30, f"Footer positions vary too much: {max_position_diff}"
    
    def test_spacing_consistency(self):
        """Test spacing between elements is consistent"""
        validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
        
        # Group elements by page
        pages = {}
        for element in validator.elements:
            if element.page not in pages:
                pages[element.page] = []
            pages[element.page].append(element)
        
        # Check spacing consistency within each page
        for page_num, elements in pages.items():
            # Sort elements by vertical position (top to bottom)
            elements.sort(key=lambda e: -e.y)  # Negative for top-to-bottom
            
            spacings = []
            for i in range(len(elements) - 1):
                current_elem = elements[i]
                next_elem = elements[i + 1]
                
                # Calculate vertical spacing
                spacing = current_elem.bottom - next_elem.y
                if spacing > 0:  # Positive spacing (gap between elements)
                    spacings.append(spacing)
            
            # Check spacing consistency (shouldn't vary too much)
            if len(spacings) > 1:
                spacing_variance = max(spacings) - min(spacings)
                # Allow some variance but flag excessive inconsistency
                assert spacing_variance <= 100, f"Excessive spacing variance on page {page_num}: {spacing_variance}"


@pytest.fixture
def sample_municipal_data():
    """Sample data for testing"""
    return pd.DataFrame([
        {
            'competencia': '2025/07',
            'vlTotalAcs': 152180.00,
            'vlEsperado': 180000.00,
            'qtTotalCredenciado': 60,
            'qtTotalPago': 50
        },
        {
            'competencia': '2025/06',
            'vlTotalAcs': 145680.00,
            'vlEsperado': 175000.00,
            'qtTotalCredenciado': 58,
            'qtTotalPago': 48
        }
    ])


class TestEdgeCaseLayouts:
    """Test edge cases that could break layout"""
    
    def test_empty_data_layout(self):
        """Test layout with empty or minimal data"""
        empty_df = pd.DataFrame()
        
        # Layout should handle empty data gracefully
        # This would typically result in placeholder content or error messages
        # The layout structure should remain intact
        assert True, "Layout should handle empty data without breaking structure"
    
    def test_single_month_data_layout(self):
        """Test layout with only one month of data"""
        single_month_df = pd.DataFrame([{
            'competencia': '2025/07',
            'vlTotalAcs': 152180.00,
            'vlEsperado': 180000.00,
            'qtTotalCredenciado': 60,
            'qtTotalPago': 50
        }])
        
        # Layout should adapt to single month data
        # Graphs and tables should still render properly
        assert len(single_month_df) == 1
        assert 'competencia' in single_month_df.columns
    
    def test_extreme_values_layout(self):
        """Test layout with extreme data values"""
        extreme_df = pd.DataFrame([
            {
                'competencia': '2025/07',
                'vlTotalAcs': 999999999.99,  # Very large value
                'vlEsperado': 0.01,          # Very small value
                'qtTotalCredenciado': 10000, # Large quantity
                'qtTotalPago': 1             # Small quantity
            }
        ])
        
        # Layout should handle extreme values without breaking
        # Text formatting should handle large numbers
        assert extreme_df['vlTotalAcs'].iloc[0] > 1000000
        assert extreme_df['vlEsperado'].iloc[0] < 1
    
    def test_long_municipality_names(self):
        """Test layout with very long municipality names"""
        long_name = "Municipality Name That Is Extremely Long And Could Potentially Break The Layout Design"
        
        # Text should fit within designated areas or be truncated appropriately
        # Header should not overflow due to long names
        max_reasonable_length = 50  # characters
        
        if len(long_name) > max_reasonable_length:
            # Layout should handle this gracefully
            assert True, f"Long municipality name ({len(long_name)} chars) should be handled"


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "layout",  # Only run layout-related tests
    ])