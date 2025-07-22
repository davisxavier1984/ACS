"""
ChartRenderer Module

This module provides improved chart rendering capabilities with proper error handling,
memory management, and resource cleanup for PDF generation.
"""

import io
import logging
from typing import Optional, Dict, Any, Tuple
from PIL import Image as PILImage
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from pdf_config import (
    ChartConfig, 
    ChartConversionError, 
    ResourceManager,
    PDFGenerationError
)


class ChartRenderer:
    """
    Handles Plotly chart to image conversion with proper cleanup and error handling.
    
    This class provides methods for converting Plotly figures to PIL Images with
    comprehensive error handling, memory management, and resource cleanup.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize ChartRenderer.
        
        Args:
            logger: Optional logger instance. If None, creates a default logger.
        """
        self._logger = logger or logging.getLogger(__name__)
    
    @staticmethod
    def plotly_to_image(
        fig: go.Figure, 
        width: int = 800, 
        height: int = 400, 
        dpi: int = 150,
        resource_manager: Optional[ResourceManager] = None
    ) -> Optional[PILImage.Image]:
        """
        Convert a Plotly figure to PIL Image with proper error handling and cleanup.
        
        Args:
            fig: Plotly figure to convert
            width: Image width in pixels
            height: Image height in pixels
            dpi: Image resolution (dots per inch)
            resource_manager: Optional ResourceManager for automatic cleanup
        
        Returns:
            PIL Image object or None if conversion fails
        
        Raises:
            ChartConversionError: If chart conversion fails critically
        """
        logger = logging.getLogger(__name__)
        
        if fig is None:
            logger.warning("Cannot convert None figure to image")
            return None
        
        try:
            # Configure figure for optimal PDF rendering
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=40, r=40, t=50, b=40),
                font=dict(family="Arial", size=12),
                showlegend=True
            )
            
            # Convert DPI to scale factor for Plotly
            scale_factor = dpi / 72.0
            
            logger.debug(f"Converting chart to image: {width}x{height} @ {dpi} DPI (scale: {scale_factor:.2f})")
            
            # Generate image bytes using Plotly's to_image method
            img_bytes = fig.to_image(
                format="png",
                width=width,
                height=height,
                scale=scale_factor
            )
            
            # Create PIL Image from bytes
            image_buffer = io.BytesIO(img_bytes)
            pil_image = PILImage.open(image_buffer)
            
            # Register resources for cleanup if ResourceManager provided
            if resource_manager:
                resource_manager.register_resource(image_buffer, resource_type="Chart Image Buffer")
                resource_manager.register_resource(pil_image, resource_type="Chart PIL Image")
            
            logger.debug(f"Successfully converted chart to {pil_image.size} image")
            return pil_image
            
        except Exception as e:
            error_msg = f"Failed to convert Plotly figure to image: {str(e)}"
            logger.error(error_msg)
            
            # For critical errors, raise ChartConversionError
            if "kaleido" in str(e).lower() or "orca" in str(e).lower():
                raise ChartConversionError(
                    chart_type="plotly_figure",
                    original_error=e
                )
            
            # For other errors, log and return None (graceful degradation)
            logger.warning("Chart conversion failed, will use placeholder")
            return None
    
    @staticmethod
    def create_placeholder_image(
        width: int = 800, 
        height: int = 400,
        message: str = "Chart conversion failed",
        resource_manager: Optional[ResourceManager] = None
    ) -> PILImage.Image:
        """
        Create a placeholder image for failed chart conversions.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
            message: Error message to display
            resource_manager: Optional ResourceManager for automatic cleanup
        
        Returns:
            PIL Image with error placeholder
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Create a light gray background
            placeholder = PILImage.new('RGB', (width, height), color='#f0f0f0')
            
            # Register for cleanup if ResourceManager provided
            if resource_manager:
                resource_manager.register_resource(placeholder, resource_type="Placeholder Image")
            
            logger.debug(f"Created placeholder image: {width}x{height}")
            return placeholder
            
        except Exception as e:
            logger.error(f"Failed to create placeholder image: {e}")
            # Return minimal placeholder
            return PILImage.new('RGB', (width, height), color='white')
    
    @classmethod
    def create_financial_chart(
        cls, 
        df_3_meses: pd.DataFrame,
        config: Optional[ChartConfig] = None,
        resource_manager: Optional[ResourceManager] = None
    ) -> go.Figure:
        """
        Create financial comparison chart from 3-month data.
        
        Args:
            df_3_meses: DataFrame with 3 months of financial data
            config: Optional ChartConfig for customization
            resource_manager: Optional ResourceManager for cleanup
        
        Returns:
            Plotly Figure object
        
        Raises:
            PDFGenerationError: If chart creation fails
        """
        logger = logging.getLogger(__name__)
        
        if config is None:
            config = ChartConfig.default_financial_chart()
        
        try:
            # Validate input data
            if df_3_meses is None or df_3_meses.empty:
                raise PDFGenerationError("No data provided for financial chart")
            
            required_columns = ['competencia', 'vlEsperado', 'vlTotalAcs']
            missing_columns = [col for col in required_columns if col not in df_3_meses.columns]
            if missing_columns:
                raise PDFGenerationError(f"Missing required columns: {missing_columns}")
            
            # Prepare data (reverse order for chronological display)
            meses = [comp.replace('/', '/') for comp in df_3_meses['competencia'].tolist()[::-1]]
            valores_esperados = df_3_meses['vlEsperado'].tolist()[::-1]
            valores_recebidos = df_3_meses['vlTotalAcs'].tolist()[::-1]
            
            logger.debug(f"Creating financial chart for {len(meses)} months")
            
            # Create figure
            fig = go.Figure()
            
            # Add expected values bar
            fig.add_trace(go.Bar(
                name='Valor Esperado',
                x=meses,
                y=valores_esperados,
                marker_color='#2E7D32',  # Dark green
                text=[f'{v/1000:.0f}K' for v in valores_esperados],
                textposition='auto',
                textfont={'size': 11, 'color': 'white'}
            ))
            
            # Add received values bar
            fig.add_trace(go.Bar(
                name='Valor Recebido',
                x=meses,
                y=valores_recebidos,
                marker_color='#4CAF50',  # Medium green
                text=[f'{v/1000:.0f}K' for v in valores_recebidos],
                textposition='auto',
                textfont={'size': 11, 'color': 'white'}
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    'text': '💰 Análise Financeira',
                    'font': {'size': config.title_font_size, 'color': '#2E7D32'},
                    'x': 0.5
                },
                xaxis={'tickfont': {'size': config.font_size}},
                yaxis={'tickfont': {'size': config.font_size}},
                barmode='group',
                height=config.height,
                width=config.width,
                showlegend=True,
                legend={
                    'font': {'size': config.font_size},
                    'orientation': 'h',
                    'y': 1.12,
                    'x': 0.5,
                    'xanchor': 'center'
                },
                plot_bgcolor=config.background_color,
                paper_bgcolor=config.background_color,
                margin=config.margin_config
            )
            
            logger.debug("Financial chart created successfully")
            return fig
            
        except Exception as e:
            error_msg = f"Failed to create financial chart: {str(e)}"
            logger.error(error_msg)
            raise PDFGenerationError(error_msg, str(e))
    
    @classmethod
    def create_personnel_chart(
        cls, 
        df_3_meses: pd.DataFrame,
        config: Optional[ChartConfig] = None,
        resource_manager: Optional[ResourceManager] = None
    ) -> go.Figure:
        """
        Create personnel comparison chart from 3-month data.
        
        Args:
            df_3_meses: DataFrame with 3 months of personnel data
            config: Optional ChartConfig for customization
            resource_manager: Optional ResourceManager for cleanup
        
        Returns:
            Plotly Figure object
        
        Raises:
            PDFGenerationError: If chart creation fails
        """
        logger = logging.getLogger(__name__)
        
        if config is None:
            config = ChartConfig.default_personnel_chart()
        
        try:
            # Validate input data
            if df_3_meses is None or df_3_meses.empty:
                raise PDFGenerationError("No data provided for personnel chart")
            
            required_columns = ['competencia', 'qtTotalCredenciado', 'qtTotalPago']
            missing_columns = [col for col in required_columns if col not in df_3_meses.columns]
            if missing_columns:
                raise PDFGenerationError(f"Missing required columns: {missing_columns}")
            
            # Prepare data (reverse order for chronological display)
            meses = [comp.replace('/', '/') for comp in df_3_meses['competencia'].tolist()[::-1]]
            acs_credenciados = df_3_meses['qtTotalCredenciado'].tolist()[::-1]
            acs_pagos = df_3_meses['qtTotalPago'].tolist()[::-1]
            
            logger.debug(f"Creating personnel chart for {len(meses)} months")
            
            # Create figure
            fig = go.Figure()
            
            # Add credentialed ACS bar
            fig.add_trace(go.Bar(
                name='ACS Credenciados',
                x=meses,
                y=acs_credenciados,
                marker_color='#81C784',  # Light green
                text=acs_credenciados,
                textposition='auto',
                textfont={'size': 11, 'color': 'white'}
            ))
            
            # Add paid ACS bar
            fig.add_trace(go.Bar(
                name='ACS Pagos',
                x=meses,
                y=acs_pagos,
                marker_color='#388E3C',  # Intense green
                text=acs_pagos,
                textposition='auto',
                textfont={'size': 11, 'color': 'white'}
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    'text': '👥 Análise de Pessoal',
                    'font': {'size': config.title_font_size, 'color': '#2E7D32'},
                    'x': 0.5
                },
                xaxis={'tickfont': {'size': config.font_size}},
                yaxis={'tickfont': {'size': config.font_size}},
                barmode='group',
                height=config.height,
                width=config.width,
                showlegend=True,
                legend={
                    'font': {'size': config.font_size},
                    'orientation': 'h',
                    'y': 1.12,
                    'x': 0.5,
                    'xanchor': 'center'
                },
                plot_bgcolor=config.background_color,
                paper_bgcolor=config.background_color,
                margin=config.margin_config
            )
            
            logger.debug("Personnel chart created successfully")
            return fig
            
        except Exception as e:
            error_msg = f"Failed to create personnel chart: {str(e)}"
            logger.error(error_msg)
            raise PDFGenerationError(error_msg, str(e))
    
    def render_chart_with_fallback(
        self,
        chart_func,
        chart_type: str,
        width: int = 800,
        height: int = 400,
        dpi: int = 150,
        resource_manager: Optional[ResourceManager] = None,
        **chart_kwargs
    ) -> PILImage.Image:
        """
        Render a chart with automatic fallback to placeholder on failure.
        
        Args:
            chart_func: Function that creates the Plotly figure
            chart_type: Description of chart type for error messages
            width: Image width in pixels
            height: Image height in pixels
            dpi: Image resolution
            resource_manager: Optional ResourceManager for cleanup
            **chart_kwargs: Additional arguments for chart_func
        
        Returns:
            PIL Image (either chart or placeholder)
        """
        try:
            # Create the chart
            fig = chart_func(**chart_kwargs)
            
            # Convert to image
            image = self.plotly_to_image(
                fig, width=width, height=height, dpi=dpi,
                resource_manager=resource_manager
            )
            
            if image is not None:
                return image
            else:
                # Conversion failed, use placeholder
                self._logger.warning(f"Chart conversion failed for {chart_type}, using placeholder")
                return self.create_placeholder_image(
                    width=width, height=height,
                    message=f"{chart_type} conversion failed",
                    resource_manager=resource_manager
                )
        
        except Exception as e:
            self._logger.error(f"Chart creation failed for {chart_type}: {e}")
            return self.create_placeholder_image(
                width=width, height=height,
                message=f"{chart_type} creation failed",
                resource_manager=resource_manager
            )
    
    def get_chart_dimensions(self, config: ChartConfig) -> Tuple[int, int]:
        """
        Get chart dimensions from configuration.
        
        Args:
            config: ChartConfig instance
        
        Returns:
            Tuple of (width, height)
        """
        return (config.width, config.height)