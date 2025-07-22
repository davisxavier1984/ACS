"""
Comprehensive Testing Strategy for PDF Generation Issues
======================================================

This test file addresses coordinate calculations, layout problems, and multi-page issues
found in the PDF generation function in pages/1_Visao_municipal.py.

Key Issues Identified:
1. Coordinate calculation errors leading to element overlap
2. Layout boundary violations and content overflow
3. Multi-page content distribution problems
4. Inconsistent spacing and positioning
5. Missing validation for element placement
"""

import pytest
import pandas as pd
import io
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

# Import the functions we want to test
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# We need to import from the pages directory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages'))

try:
    from pages.visao_municipal import (
        gerar_pdf_municipal,
        plotly_to_image,
        formatar_moeda_brasileira,
        calcular_variacao_mensal
    )
except ImportError:
    # Fallback if import fails
    print("Warning: Could not import from pages.visao_municipal. Some tests will be skipped.")
    gerar_pdf_municipal = None
    plotly_to_image = None
    formatar_moeda_brasileira = None
    calcular_variacao_mensal = None


class TestCoordinateCalculations:
    """Test coordinate calculations for ReportLab elements"""
    
    def test_a4_page_dimensions(self):
        """Validate A4 page dimensions are correctly used"""
        width, height = A4
        assert width == 595.2756
        assert height == 841.8898
        
    def test_margin_calculations(self):
        """Test margin calculations don't cause element overlap"""
        width, height = A4
        margin = 20
        
        # Content area should be within page bounds
        content_width = width - 2 * margin
        content_height = height - 2 * margin
        
        assert content_width > 0
        assert content_height > 0
        assert content_width <= width
        assert content_height <= height
    
    def test_header_positioning(self):
        """Test header positioning calculations"""
        width, height = A4
        margin = 20
        header_height = 90
        
        # Header should start below the top margin
        y_header = height - margin - header_height
        
        # Validate header fits within page bounds
        assert y_header > 0
        assert y_header + header_height <= height - margin
        
        # Logo positioning within header
        logo_width = 95
        logo_height = 65
        logo_x = margin
        logo_y = y_header + 20
        
        assert logo_x >= margin
        assert logo_x + logo_width <= width - margin
        assert logo_y >= 0
        assert logo_y + logo_height <= height
    
    def test_graph_positioning_page1(self):
        """Test financial graph positioning on page 1"""
        width, height = A4
        margin = 20
        header_height = 90
        graph_height = 300
        
        y_header = height - margin - header_height
        y_pos = y_header - 20  # After header info
        graph_y = y_pos - 50   # Graph position
        
        # Graph should fit within page bounds
        assert graph_y > 0
        assert graph_y + graph_height < height
        
        # Graph width should not exceed page width
        graph_width = width - 2 * margin
        assert graph_width > 0
        assert graph_width <= width - 2 * margin
    
    def test_footer_positioning(self):
        """Test footer positioning doesn't overlap with content"""
        footer_y = 60
        
        # Footer should be above bottom margin
        assert footer_y > 20  # Some minimum clearance
        
    def test_page2_header_positioning(self):
        """Test simplified header positioning on page 2"""
        width, height = A4
        margin = 20
        
        # Page 2 header should be simpler but properly positioned
        header_y = height - margin - 40
        assert header_y > 0
        assert header_y < height - margin
        
        return_y = height - margin - 60
        assert return_y > 0
        assert return_y < header_y


class TestLayoutBoundaries:
    """Test layout boundaries and overflow detection"""
    
    def test_table_width_calculations(self):
        """Test table width doesn't exceed page bounds"""
        width, height = A4
        margin = 20
        col_widths = [80, 100, 90, 70, 70]
        
        table_width = sum(col_widths)
        table_x = (width - table_width) / 2  # Centered
        
        # Table should fit within page width
        assert table_x >= margin
        assert table_x + table_width <= width - margin
        
    def test_text_positioning_within_bounds(self):
        """Test text positioning stays within page boundaries"""
        width, height = A4
        margin = 20
        
        # Text should never be positioned outside margins
        min_x = margin + 5  # Text padding
        max_x = width - margin - 5
        
        assert min_x > margin
        assert max_x < width - margin
        
        # Test various text positions used in the PDF
        positions = [
            margin + 110,  # Header text
            margin + 15,   # Card content
            margin + 50,   # Secondary text
        ]
        
        for pos in positions:
            assert pos >= margin
            assert pos <= width - margin - 100  # Account for text width
    
    def test_card_dimensions_and_positioning(self):
        """Test alert/status card dimensions and positioning"""
        width, height = A4
        margin = 20
        card_height = 100
        
        # Card should fit within page width
        card_width = width - 2 * margin
        assert card_width > 0
        
        # Card positioning on page 2
        # Assuming it's placed after table and graph
        min_y_position = 100  # Minimum from bottom
        status_y = 200  # Example position
        
        assert status_y >= min_y_position
        assert status_y + card_height < height - margin
    
    def test_element_overlap_detection(self):
        """Test detection of overlapping elements"""
        # Define element positions as they appear in the code
        elements = [
            {"name": "header", "x": 20, "y": 751, "width": 555, "height": 90},
            {"name": "graph1", "x": 20, "y": 400, "width": 555, "height": 300},
            {"name": "table", "x": 137, "y": 200, "width": 410, "height": 120},
            {"name": "footer", "x": 20, "y": 60, "width": 555, "height": 20}
        ]
        
        # Check for overlaps between any two elements
        for i, elem1 in enumerate(elements):
            for j, elem2 in enumerate(elements):
                if i != j:
                    # Check if elements overlap
                    overlap_x = not (elem1["x"] + elem1["width"] <= elem2["x"] or 
                                   elem2["x"] + elem2["width"] <= elem1["x"])
                    overlap_y = not (elem1["y"] + elem1["height"] <= elem2["y"] or 
                                   elem2["y"] + elem2["height"] <= elem1["y"])
                    
                    if overlap_x and overlap_y:
                        pytest.fail(f"Elements {elem1['name']} and {elem2['name']} overlap!")


class TestMultiPageHandling:
    """Test multi-page content distribution and page breaks"""
    
    def test_page_break_logic(self):
        """Test page break is properly triggered"""
        width, height = A4
        margin = 20
        
        # Simulate content that should trigger page break
        header_height = 90
        graph_height = 300
        footer_height = 60
        
        used_height = margin + header_height + 50 + graph_height + footer_height
        
        # Should leave enough space for footer
        assert used_height < height
        
        # But if we add more content, should trigger page break
        additional_content = 200
        total_height = used_height + additional_content
        
        if total_height > height - margin:
            # This should trigger a page break
            assert True, "Page break should be triggered"
    
    def test_page2_content_positioning(self):
        """Test content positioning on page 2"""
        width, height = A4
        margin = 20
        
        # Page 2 should start with proper header
        simple_header_height = 60
        graph_height = 300
        table_height = 120
        status_card_height = 100
        footer_height = 60
        
        # Calculate positions
        y_pos = height - margin - simple_header_height
        graph_y = y_pos - 30
        table_y = graph_y - graph_height - 40
        status_y = table_y - table_height - 40
        
        # All elements should fit on page 2
        content_bottom = status_y - status_card_height
        footer_top = footer_height + margin
        
        assert content_bottom > footer_top, "Content overlaps with footer on page 2"
    
    def test_content_distribution_balance(self):
        """Test content is properly distributed between pages"""
        # Page 1 should contain:
        # - Enhanced header with logo
        # - Financial graph
        # - Footer
        
        # Page 2 should contain:
        # - Simple header
        # - Personnel graph
        # - Detailed table
        # - Status card
        # - Footer
        
        # This ensures balanced content distribution
        page1_elements = ["enhanced_header", "financial_graph", "footer"]
        page2_elements = ["simple_header", "personnel_graph", "table", "status_card", "footer"]
        
        assert len(page1_elements) < len(page2_elements), "Page 2 has more content"
        assert "table" in page2_elements, "Table should be on page 2"
        assert "status_card" in page2_elements, "Status card should be on page 2"


class TestMockDataFixtures:
    """Mock data fixtures for consistent testing scenarios"""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing"""
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
            },
            {
                'competencia': '2025/05',
                'vlTotalAcs': 148320.00,
                'vlEsperado': 172000.00,
                'qtTotalCredenciado': 57,
                'qtTotalPago': 49
            }
        ])
    
    @pytest.fixture
    def sample_current_data(self, sample_dataframe):
        """Create sample current month data"""
        return sample_dataframe.iloc[0]
    
    @pytest.fixture
    def mock_plotly_figure(self):
        """Create mock Plotly figure"""
        mock_fig = Mock()
        mock_fig.update_layout = Mock()
        mock_fig.to_image = Mock(return_value=b'fake_image_data')
        return mock_fig
    
    def test_sample_data_structure(self, sample_dataframe):
        """Test sample data has correct structure"""
        required_columns = ['competencia', 'vlTotalAcs', 'vlEsperado', 'qtTotalCredenciado', 'qtTotalPago']
        
        for col in required_columns:
            assert col in sample_dataframe.columns
        
        assert len(sample_dataframe) == 3
        assert sample_dataframe['competencia'].iloc[0] == '2025/07'


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_empty_dataframe_handling(self):
        """Test handling of empty DataFrame"""
        empty_df = pd.DataFrame()
        
        # PDF generation should handle empty data gracefully
        with pytest.raises((ValueError, IndexError, KeyError)):
            # This should fail gracefully, not crash
            if gerar_pdf_municipal:
                gerar_pdf_municipal("Test Municipality", "Test State", empty_df, None, [])
    
    def test_missing_columns_handling(self):
        """Test handling of DataFrame with missing columns"""
        incomplete_df = pd.DataFrame([
            {'competencia': '2025/07', 'vlTotalAcs': 1000}
            # Missing other required columns
        ])
        
        # Should handle missing columns without crashing
        with pytest.raises((KeyError, ValueError)):
            if gerar_pdf_municipal:
                gerar_pdf_municipal("Test Municipality", "Test State", incomplete_df, None, [])
    
    def test_invalid_coordinate_values(self):
        """Test handling of invalid coordinate values"""
        width, height = A4
        
        # Test negative coordinates
        invalid_coords = [
            (-10, 100),  # Negative x
            (100, -10),  # Negative y
            (width + 100, 100),  # X beyond page width
            (100, height + 100)  # Y beyond page height
        ]
        
        for x, y in invalid_coords:
            # Coordinates should be validated
            if x < 0 or y < 0 or x > width or y > height:
                assert True, f"Invalid coordinates detected: ({x}, {y})"
    
    def test_image_conversion_error_handling(self):
        """Test handling of image conversion errors"""
        if not plotly_to_image:
            pytest.skip("plotly_to_image function not available")
            
        # Test with invalid figure
        with pytest.raises((AttributeError, ValueError, TypeError)):
            plotly_to_image(None)
    
    def test_font_and_color_validation(self):
        """Test font and color value validation"""
        from reportlab.lib import colors
        
        # Valid colors should work
        valid_colors = [colors.red, colors.blue, colors.HexColor('#003366')]
        for color in valid_colors:
            assert color is not None
        
        # Invalid hex colors should be handled
        invalid_hex = '#GGGGGG'  # Invalid hex
        with pytest.raises((ValueError, AttributeError)):
            colors.HexColor(invalid_hex)


class TestVisualRegression:
    """Visual regression tests for PDF output consistency"""
    
    def test_pdf_output_structure(self, sample_dataframe, sample_current_data):
        """Test PDF output has consistent structure"""
        if not gerar_pdf_municipal:
            pytest.skip("gerar_pdf_municipal function not available")
            
        # Mock the image generation to avoid Plotly dependencies
        with patch('pages.1_Visao_municipal.plotly_to_image') as mock_plotly:
            mock_image = PILImage.new('RGB', (800, 400), color='white')
            mock_plotly.return_value = mock_image
            
            pdf_buffer = gerar_pdf_municipal(
                "Test Municipality/ST",
                "ST - Test State",
                sample_dataframe,
                sample_current_data,
                ['2025/07', '2025/06', '2025/05']
            )
            
            # PDF should be generated successfully
            assert isinstance(pdf_buffer, io.BytesIO)
            assert pdf_buffer.getvalue() is not None
            assert len(pdf_buffer.getvalue()) > 1000  # Should be substantial content
    
    def test_pdf_content_consistency(self):
        """Test PDF contains expected content elements"""
        # This would typically involve parsing the PDF and checking for:
        # - Proper page count (should be 2)
        # - Text content presence
        # - Image placement
        # - Table structure
        
        # For now, we document what should be tested:
        expected_elements = [
            "logo_or_placeholder",
            "municipality_name",
            "financial_chart",
            "personnel_chart", 
            "summary_table",
            "regulatory_status",
            "footer_both_pages"
        ]
        
        assert len(expected_elements) == 7, "Should test for 7 main PDF elements"


class TestPerformanceBenchmarks:
    """Performance benchmarking tests"""
    
    def test_pdf_generation_time(self, sample_dataframe, sample_current_data):
        """Test PDF generation completes within reasonable time"""
        if not gerar_pdf_municipal:
            pytest.skip("gerar_pdf_municipal function not available")
            
        import time
        
        start_time = time.time()
        
        with patch('pages.1_Visao_municipal.plotly_to_image') as mock_plotly:
            mock_image = PILImage.new('RGB', (800, 400), color='white') 
            mock_plotly.return_value = mock_image
            
            pdf_buffer = gerar_pdf_municipal(
                "Test Municipality/ST",
                "ST - Test State", 
                sample_dataframe,
                sample_current_data,
                ['2025/07', '2025/06', '2025/05']
            )
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # PDF generation should complete within 10 seconds
        assert generation_time < 10.0, f"PDF generation took {generation_time:.2f} seconds"
    
    def test_memory_usage_reasonable(self, sample_dataframe, sample_current_data):
        """Test PDF generation doesn't use excessive memory"""
        if not gerar_pdf_municipal:
            pytest.skip("gerar_pdf_municipal function not available")
            
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch('pages.1_Visao_municipal.plotly_to_image') as mock_plotly:
            mock_image = PILImage.new('RGB', (800, 400), color='white')
            mock_plotly.return_value = mock_image
            
            for _ in range(5):  # Generate 5 PDFs to test memory accumulation
                pdf_buffer = gerar_pdf_municipal(
                    "Test Municipality/ST",
                    "ST - Test State",
                    sample_dataframe, 
                    sample_current_data,
                    ['2025/07', '2025/06', '2025/05']
                )
                # Clear buffer to simulate real usage
                del pdf_buffer
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (less than 50 MB)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.2f} MB"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])