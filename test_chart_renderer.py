"""
Unit tests for ChartRenderer module.

Tests chart rendering functionality, error handling, and resource management.
"""

import unittest
import io
import logging
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import plotly.graph_objects as go
from PIL import Image as PILImage

from chart_renderer import ChartRenderer
from pdf_config import (
    ChartConfig, 
    ChartConversionError, 
    ResourceManager,
    PDFGenerationError
)


class TestChartRenderer(unittest.TestCase):
    """Test cases for ChartRenderer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = ChartRenderer()
        
        # Sample data for testing
        self.sample_data = pd.DataFrame({
            'competencia': ['2024/01', '2024/02', '2024/03'],
            'vlEsperado': [100000, 110000, 120000],
            'vlTotalAcs': [95000, 105000, 115000],
            'qtTotalCredenciado': [50, 55, 60],
            'qtTotalPago': [48, 52, 58]
        })
        
        # Configure logging for tests
        logging.basicConfig(level=logging.DEBUG)
    
    def test_plotly_to_image_success(self):
        """Test successful chart to image conversion."""
        # Create a simple test figure
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['A', 'B', 'C'], y=[1, 2, 3]))
        
        # Convert to image
        image = ChartRenderer.plotly_to_image(fig, width=400, height=300, dpi=100)
        
        # Verify result
        self.assertIsInstance(image, PILImage.Image)
        self.assertEqual(image.size, (400, 300))
        
        # Clean up
        if image:
            image.close()
    
    def test_plotly_to_image_with_none_figure(self):
        """Test handling of None figure input."""
        image = ChartRenderer.plotly_to_image(None)
        self.assertIsNone(image)
    
    @patch('chart_renderer.go.Figure.to_image')
    def test_plotly_to_image_conversion_error(self, mock_to_image):
        """Test handling of chart conversion errors."""
        # Mock to_image to raise an exception
        mock_to_image.side_effect = Exception("Kaleido conversion failed")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['A', 'B'], y=[1, 2]))
        
        # Should raise ChartConversionError for kaleido errors
        with self.assertRaises(ChartConversionError) as context:
            ChartRenderer.plotly_to_image(fig)
        
        self.assertIn("kaleido", str(context.exception).lower())
    
    @patch('chart_renderer.go.Figure.to_image')
    def test_plotly_to_image_graceful_degradation(self, mock_to_image):
        """Test graceful degradation for non-critical errors."""
        # Mock to_image to raise a non-critical exception
        mock_to_image.side_effect = Exception("Generic conversion error")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['A', 'B'], y=[1, 2]))
        
        # Should return None for non-critical errors
        image = ChartRenderer.plotly_to_image(fig)
        self.assertIsNone(image)
    
    def test_plotly_to_image_with_resource_manager(self):
        """Test image conversion with ResourceManager integration."""
        with ResourceManager() as rm:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=['A', 'B'], y=[1, 2]))
            
            image = ChartRenderer.plotly_to_image(
                fig, width=300, height=200, resource_manager=rm
            )
            
            # Verify image was created and registered
            self.assertIsInstance(image, PILImage.Image)
            self.assertGreater(rm.get_resource_count(), 0)
            
            # Resources should be cleaned up automatically on context exit
    
    def test_create_placeholder_image(self):
        """Test placeholder image creation."""
        placeholder = ChartRenderer.create_placeholder_image(
            width=500, height=300, message="Test error"
        )
        
        self.assertIsInstance(placeholder, PILImage.Image)
        self.assertEqual(placeholder.size, (500, 300))
        
        # Clean up
        placeholder.close()
    
    def test_create_placeholder_image_with_resource_manager(self):
        """Test placeholder creation with ResourceManager."""
        with ResourceManager() as rm:
            placeholder = ChartRenderer.create_placeholder_image(
                width=400, height=250, resource_manager=rm
            )
            
            self.assertIsInstance(placeholder, PILImage.Image)
            self.assertEqual(rm.get_resource_count(), 1)
    
    def test_create_financial_chart_success(self):
        """Test successful financial chart creation."""
        fig = ChartRenderer.create_financial_chart(self.sample_data)
        
        self.assertIsInstance(fig, go.Figure)
        
        # Verify chart has expected traces
        self.assertEqual(len(fig.data), 2)  # Expected and received values
        self.assertEqual(fig.data[0].name, 'Valor Esperado')
        self.assertEqual(fig.data[1].name, 'Valor Recebido')
    
    def test_create_financial_chart_with_config(self):
        """Test financial chart creation with custom config."""
        config = ChartConfig(width=1000, height=500, dpi=200)
        fig = ChartRenderer.create_financial_chart(self.sample_data, config=config)
        
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.layout.width, 1000)
        self.assertEqual(fig.layout.height, 500)
    
    def test_create_financial_chart_empty_data(self):
        """Test financial chart creation with empty data."""
        empty_df = pd.DataFrame()
        
        with self.assertRaises(PDFGenerationError) as context:
            ChartRenderer.create_financial_chart(empty_df)
        
        self.assertIn("No data provided", str(context.exception))
    
    def test_create_financial_chart_missing_columns(self):
        """Test financial chart creation with missing required columns."""
        incomplete_df = pd.DataFrame({
            'competencia': ['2024/01', '2024/02'],
            'vlEsperado': [100000, 110000]
            # Missing 'vlTotalAcs' column
        })
        
        with self.assertRaises(PDFGenerationError) as context:
            ChartRenderer.create_financial_chart(incomplete_df)
        
        self.assertIn("Missing required columns", str(context.exception))
    
    def test_create_personnel_chart_success(self):
        """Test successful personnel chart creation."""
        fig = ChartRenderer.create_personnel_chart(self.sample_data)
        
        self.assertIsInstance(fig, go.Figure)
        
        # Verify chart has expected traces
        self.assertEqual(len(fig.data), 2)  # Credentialed and paid ACS
        self.assertEqual(fig.data[0].name, 'ACS Credenciados')
        self.assertEqual(fig.data[1].name, 'ACS Pagos')
    
    def test_create_personnel_chart_with_config(self):
        """Test personnel chart creation with custom config."""
        config = ChartConfig(width=800, height=350, dpi=150)
        fig = ChartRenderer.create_personnel_chart(self.sample_data, config=config)
        
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.layout.width, 800)
        self.assertEqual(fig.layout.height, 350)
    
    def test_create_personnel_chart_empty_data(self):
        """Test personnel chart creation with empty data."""
        empty_df = pd.DataFrame()
        
        with self.assertRaises(PDFGenerationError) as context:
            ChartRenderer.create_personnel_chart(empty_df)
        
        self.assertIn("No data provided", str(context.exception))
    
    def test_create_personnel_chart_missing_columns(self):
        """Test personnel chart creation with missing required columns."""
        incomplete_df = pd.DataFrame({
            'competencia': ['2024/01', '2024/02'],
            'qtTotalCredenciado': [50, 55]
            # Missing 'qtTotalPago' column
        })
        
        with self.assertRaises(PDFGenerationError) as context:
            ChartRenderer.create_personnel_chart(incomplete_df)
        
        self.assertIn("Missing required columns", str(context.exception))
    
    def test_render_chart_with_fallback_success(self):
        """Test successful chart rendering with fallback method."""
        def mock_chart_func(**kwargs):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=['A', 'B'], y=[1, 2]))
            return fig
        
        image = self.renderer.render_chart_with_fallback(
            chart_func=mock_chart_func,
            chart_type="test_chart",
            width=400,
            height=300
        )
        
        self.assertIsInstance(image, PILImage.Image)
        self.assertEqual(image.size, (400, 300))
        
        # Clean up
        image.close()
    
    def test_render_chart_with_fallback_chart_creation_error(self):
        """Test fallback when chart creation fails."""
        def failing_chart_func(**kwargs):
            raise Exception("Chart creation failed")
        
        image = self.renderer.render_chart_with_fallback(
            chart_func=failing_chart_func,
            chart_type="failing_chart",
            width=400,
            height=300
        )
        
        # Should return placeholder image
        self.assertIsInstance(image, PILImage.Image)
        self.assertEqual(image.size, (400, 300))
        
        # Clean up
        image.close()
    
    @patch.object(ChartRenderer, 'plotly_to_image')
    def test_render_chart_with_fallback_conversion_error(self, mock_plotly_to_image):
        """Test fallback when chart conversion fails."""
        # Mock plotly_to_image to return None (conversion failure)
        mock_plotly_to_image.return_value = None
        
        def mock_chart_func(**kwargs):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=['A', 'B'], y=[1, 2]))
            return fig
        
        image = self.renderer.render_chart_with_fallback(
            chart_func=mock_chart_func,
            chart_type="conversion_failing_chart",
            width=400,
            height=300
        )
        
        # Should return placeholder image
        self.assertIsInstance(image, PILImage.Image)
        self.assertEqual(image.size, (400, 300))
        
        # Clean up
        image.close()
    
    def test_render_chart_with_fallback_with_resource_manager(self):
        """Test chart rendering with fallback using ResourceManager."""
        def mock_chart_func(**kwargs):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=['A', 'B'], y=[1, 2]))
            return fig
        
        with ResourceManager() as rm:
            image = self.renderer.render_chart_with_fallback(
                chart_func=mock_chart_func,
                chart_type="test_chart",
                width=300,
                height=200,
                resource_manager=rm
            )
            
            self.assertIsInstance(image, PILImage.Image)
            self.assertGreater(rm.get_resource_count(), 0)
    
    def test_get_chart_dimensions(self):
        """Test chart dimensions extraction from config."""
        config = ChartConfig(width=1200, height=600, dpi=200)
        width, height = self.renderer.get_chart_dimensions(config)
        
        self.assertEqual(width, 1200)
        self.assertEqual(height, 600)
    
    def test_chart_config_defaults(self):
        """Test ChartConfig default configurations."""
        financial_config = ChartConfig.default_financial_chart()
        self.assertEqual(financial_config.width, 800)
        self.assertEqual(financial_config.height, 400)
        self.assertEqual(financial_config.dpi, 150)
        
        personnel_config = ChartConfig.default_personnel_chart()
        self.assertEqual(personnel_config.width, 800)
        self.assertEqual(personnel_config.height, 350)
        self.assertEqual(personnel_config.dpi, 150)


class TestChartRendererIntegration(unittest.TestCase):
    """Integration tests for ChartRenderer with real data scenarios."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.renderer = ChartRenderer()
        
        # More realistic test data
        self.realistic_data = pd.DataFrame({
            'competencia': ['2024/01', '2024/02', '2024/03'],
            'vlEsperado': [303600, 333960, 364320],  # Realistic ACS values
            'vlTotalAcs': [289420, 317562, 346084],
            'qtTotalCredenciado': [100, 110, 120],
            'qtTotalPago': [95, 104, 114]
        })
    
    def test_end_to_end_financial_chart_rendering(self):
        """Test complete financial chart creation and rendering."""
        with ResourceManager() as rm:
            # Create chart
            fig = ChartRenderer.create_financial_chart(
                self.realistic_data,
                config=ChartConfig.default_financial_chart()
            )
            
            # Convert to image
            image = ChartRenderer.plotly_to_image(
                fig, width=800, height=400, dpi=150, resource_manager=rm
            )
            
            # Verify result
            self.assertIsInstance(image, PILImage.Image)
            self.assertEqual(image.size, (800, 400))
            
            # Verify resource management
            self.assertGreater(rm.get_resource_count(), 0)
    
    def test_end_to_end_personnel_chart_rendering(self):
        """Test complete personnel chart creation and rendering."""
        with ResourceManager() as rm:
            # Create chart
            fig = ChartRenderer.create_personnel_chart(
                self.realistic_data,
                config=ChartConfig.default_personnel_chart()
            )
            
            # Convert to image
            image = ChartRenderer.plotly_to_image(
                fig, width=800, height=350, dpi=150, resource_manager=rm
            )
            
            # Verify result
            self.assertIsInstance(image, PILImage.Image)
            self.assertEqual(image.size, (800, 350))
            
            # Verify resource management
            self.assertGreater(rm.get_resource_count(), 0)
    
    def test_fallback_rendering_with_realistic_scenario(self):
        """Test fallback rendering in realistic error scenarios."""
        renderer = ChartRenderer()
        
        # Test with financial chart
        financial_image = renderer.render_chart_with_fallback(
            chart_func=ChartRenderer.create_financial_chart,
            chart_type="financial",
            width=800,
            height=400,
            df_3_meses=self.realistic_data
        )
        
        self.assertIsInstance(financial_image, PILImage.Image)
        financial_image.close()
        
        # Test with personnel chart
        personnel_image = renderer.render_chart_with_fallback(
            chart_func=ChartRenderer.create_personnel_chart,
            chart_type="personnel",
            width=800,
            height=350,
            df_3_meses=self.realistic_data
        )
        
        self.assertIsInstance(personnel_image, PILImage.Image)
        personnel_image.close()
    
    def test_memory_management_with_multiple_charts(self):
        """Test memory management when creating multiple charts."""
        with ResourceManager() as rm:
            images = []
            
            # Create multiple charts
            for i in range(5):
                fig = ChartRenderer.create_financial_chart(self.realistic_data)
                image = ChartRenderer.plotly_to_image(
                    fig, width=400, height=300, resource_manager=rm
                )
                images.append(image)
            
            # Verify all images were created
            self.assertEqual(len(images), 5)
            for image in images:
                self.assertIsInstance(image, PILImage.Image)
            
            # Verify resource tracking
            self.assertGreater(rm.get_resource_count(), 5)
            
            # Resources should be cleaned up automatically on context exit


if __name__ == '__main__':
    # Set up logging for test output
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(name)s - %(message)s'
    )
    
    # Run tests
    unittest.main(verbosity=2)