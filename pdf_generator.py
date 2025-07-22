"""
PDFGenerator Module

This module provides the main PDFGenerator class for creating professional PDF reports
with proper resource management, error handling, and modular design.
"""

import io
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white, green
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from PIL import Image as PILImage

from pdf_config import (
    PDFConfig, 
    ChartConfig, 
    ResourceManager, 
    PDFGenerationError,
    ChartConversionError,
    LayoutError,
    DataValidationError
)
from chart_renderer import ChartRenderer
from layout_manager import LayoutManager


class PDFGenerator:
    """
    Main PDF generator class for creating professional municipal ACS reports.
    
    This class orchestrates the entire PDF generation process with proper resource
    management, error handling, and modular design. It integrates ChartRenderer,
    LayoutManager, and ResourceManager for comprehensive PDF creation.
    """
    
    def __init__(self, 
                 municipio: str, 
                 uf: str, 
                 df_3_meses: pd.DataFrame, 
                 dados_atual: pd.Series, 
                 competencias: List[str],
                 config: Optional[PDFConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize PDFGenerator with data and configuration.
        
        Args:
            municipio: Municipality name
            uf: State abbreviation
            df_3_meses: DataFrame with 3 months of data
            dados_atual: Current month data as Series
            competencias: List of competency periods
            config: Optional PDF configuration
            logger: Optional logger instance
        
        Raises:
            DataValidationError: If required data is missing or invalid
        """
        # Validate required parameters
        if not municipio or not isinstance(municipio, str):
            raise DataValidationError("municipio", "Must be a non-empty string")
        
        if not uf or not isinstance(uf, str):
            raise DataValidationError("uf", "Must be a non-empty string")
        
        if df_3_meses is None or df_3_meses.empty:
            raise DataValidationError("df_3_meses", "Must be a non-empty DataFrame")
        
        if dados_atual is None or dados_atual.empty:
            raise DataValidationError("dados_atual", "Must be a non-empty Series")
        
        if not competencias or not isinstance(competencias, list):
            raise DataValidationError("competencias", "Must be a non-empty list")
        
        # Initialize components
        self.municipio = municipio.strip()
        self.uf = uf.strip().upper()
        self.df_3_meses = df_3_meses.copy()
        self.dados_atual = dados_atual.copy()
        self.competencias = competencias.copy()
        
        self.config = config or PDFConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize helper components
        self.chart_renderer = ChartRenderer(logger=self.logger)
        self.layout_manager = LayoutManager(config=self.config, logger=self.logger)
        
        # PDF generation state
        self._canvas = None
        self._resource_manager = None
        
        self.logger.info(f"PDFGenerator initialized for {self.municipio}/{self.uf}")
    
    def generate_pdf(self) -> io.BytesIO:
        """
        Generate the complete PDF report with proper resource management.
        
        Returns:
            BytesIO buffer containing the generated PDF
        
        Raises:
            PDFGenerationError: If PDF generation fails
        """
        self.logger.info(f"Starting PDF generation for {self.municipio}/{self.uf}")
        
        try:
            with ResourceManager(logger=self.logger) as rm:
                self._resource_manager = rm
                
                # Create PDF buffer
                pdf_buffer = io.BytesIO()
                rm.register_resource(pdf_buffer, resource_type="PDF Buffer")
                
                # Initialize canvas
                self._canvas = canvas.Canvas(pdf_buffer, pagesize=A4)
                
                # Reset layout manager
                self.layout_manager.reset()
                
                # Generate PDF content
                self._generate_content()
                
                # Finalize PDF
                self._canvas.save()
                
                # Get PDF data
                pdf_data = pdf_buffer.getvalue()
                
                self.logger.info(f"PDF generation completed successfully. Size: {len(pdf_data)} bytes")
                
                # Return new buffer with PDF data
                result_buffer = io.BytesIO(pdf_data)
                return result_buffer
                
        except Exception as e:
            error_msg = f"PDF generation failed for {self.municipio}/{self.uf}: {str(e)}"
            self.logger.error(error_msg)
            raise PDFGenerationError(error_msg, str(e))
        
        finally:
            # Clean up references
            self._canvas = None
            self._resource_manager = None
    
    def _generate_content(self):
        """Generate dashboard PDF content sections."""
        try:
            # Always generate dashboard content (single format)
            self._generate_dashboard_content()
            
            self.logger.debug("Dashboard PDF content generated successfully")
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise PDFGenerationError(f"Content generation failed: {str(e)}")
    
    
    def _generate_dashboard_content(self):
        """Generate Dashboard ACS content with proper multi-page layout."""
        # Create Dashboard ACS header
        current_y = self._create_dashboard_header()
        
        # Add compact spacing after header
        current_y -= 25
        
        # Add Indicadores Principais section
        current_y = self._add_indicadores_principais(current_y)
        
        # Add compact spacing between sections
        current_y -= 30
        
        # Add Análise Comparativa section
        current_y = self._add_analise_comparativa(current_y)
        
        # Strategic page break after financial chart for better 2-page layout
        if current_y < 350:
            self._canvas.showPage()
            current_y = self.config.page_height - self.config.margin
        
        # Add compact spacing between sections
        current_y -= 30
        
        # Add Análise de Pessoal section
        current_y = self._add_analise_pessoal(current_y)
        
        # Add compact spacing between sections
        current_y -= 30
        
        # Add Resumo Detalhado por Mês section
        current_y = self._add_resumo_detalhado(current_y)
        
        # Add compact spacing between sections
        current_y -= 25
        
        # Add Alerta Regulamentar section
        current_y = self._add_alerta_regulamentar(current_y)
        
        # Add footer
        self._add_dashboard_footer()
    
    
    def _create_dashboard_header(self) -> float:
        """
        Create Dashboard ACS header with logo integration.
        
        Returns:
            Y position after header creation
        """
        try:
            from reportlab.lib.colors import HexColor
            
            # Start from top of page
            current_y = self.config.page_height - self.config.margin
            
            # Add logo aligned with title (not below it)
            logo_height = 60  # Slightly reduced for better proportion
            logo_max_width = 120
            title_y = current_y - 35  # Define title position first
            logo_width, logo_x = self._load_and_add_logo(title_y + 10, logo_height, logo_max_width)  # Align logo with title level
            
            # Title text (centralizado, azul escuro, negrito)
            self._canvas.setFont("Helvetica-Bold", 20)
            self._canvas.setFillColor(HexColor(self.config.dashboard_blue))
            
            title_text = "Dashboard ACS - Análise Municipal"
            title_width = self._canvas.stringWidth(title_text, "Helvetica-Bold", 20)
            title_x = (self.config.page_width - title_width) / 2  # Centralizado
            
            # Blue rectangle to the left of the centered title
            rect_width = 15
            rect_height = 8
            rect_x = title_x - 25  # Position rectangle to the left of title
            rect_y = title_y - 2
            
            self._canvas.setFillColor(HexColor(self.config.dashboard_blue))
            self._canvas.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
            
            # Draw the title
            self._canvas.setFillColor(HexColor(self.config.dashboard_blue))
            self._canvas.drawString(title_x, title_y, title_text)
            
            # Informações do cabeçalho (posicionadas à direita do logo para evitar sobreposição)
            info_x = logo_x + logo_width + 25  # Start after logo with safe margin
            info_y = title_y - 40
            self._canvas.setFont("Helvetica", 12)
            self._canvas.setFillColor(HexColor(self.config.text_color))
            
            # Município
            municipio_text = f"Município: {self.municipio}"
            self._canvas.drawString(info_x, info_y, municipio_text)
            
            # Estado  
            info_y -= 18
            estado_text = f"Estado: {self.uf}"
            self._canvas.drawString(info_x, info_y, estado_text)
            
            # Período
            info_y -= 18
            if len(self.competencias) > 1:
                periodo_text = f"Período: {self.competencias[0]} a {self.competencias[-1]}"
            else:
                periodo_text = f"Período: {self.competencias[-1] if self.competencias else 'N/A'}"
            self._canvas.drawString(info_x, info_y, periodo_text)
            
            # Data do Relatório
            info_y -= 18
            data_relatorio = datetime.now().strftime("%d/%m/%Y %H:%M")
            data_text = f"Data do Relatório: {data_relatorio}"
            self._canvas.drawString(info_x, info_y, data_text)
            
            # Separator line
            separator_y = info_y - 20
            self._canvas.setStrokeColor(HexColor('#CCCCCC'))
            self._canvas.setLineWidth(1)
            self._canvas.line(
                self.config.margin,
                separator_y,
                self.config.page_width - self.config.margin,
                separator_y
            )
            
            final_y = separator_y - 20
            self.logger.debug(f"Dashboard header created, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            self.logger.error(f"Dashboard header creation failed: {e}")
            raise PDFGenerationError(f"Dashboard header creation failed: {str(e)}")
    
    def _load_and_add_logo(self, current_y: float, logo_height: int, logo_max_width: int) -> Tuple[int, float]:
        """
        Load and add logo with improved error handling and fallback support.
        
        Args:
            current_y: Current Y position
            logo_height: Desired logo height
            logo_max_width: Maximum allowed logo width
        
        Returns:
            Tuple of (actual_logo_width, logo_x_position)
        """
        logo_paths = ['logo.png', 'logo.jpg', 'logo.jpeg', 'assets/logo.png', 'images/logo.png']
        logo_width = 0
        logo_x = self.config.margin
        
        for logo_path in logo_paths:
            try:
                if os.path.exists(logo_path):
                    self.logger.debug(f"Attempting to load logo from: {logo_path}")
                    
                    # Load and validate logo image
                    logo_img = PILImage.open(logo_path)
                    self._resource_manager.register_resource(logo_img, resource_type="Logo Image")
                    
                    # Ensure white background for logo
                    if logo_img.mode == 'RGBA':
                        # Create white background for transparent images
                        white_bg = PILImage.new('RGB', logo_img.size, (255, 255, 255))
                        white_bg.paste(logo_img, mask=logo_img.split()[-1])  # Use alpha channel as mask
                        logo_img = white_bg
                        self.logger.debug(f"Applied white background to transparent logo")
                    elif logo_img.mode not in ['RGB', 'L']:
                        logo_img = logo_img.convert('RGB')
                        self.logger.debug(f"Converted logo to RGB mode")
                    
                    # Calculate logo dimensions maintaining aspect ratio
                    original_width, original_height = logo_img.size
                    aspect_ratio = original_width / original_height
                    
                    # Calculate width based on height constraint
                    calculated_width = int(logo_height * aspect_ratio)
                    
                    # Apply maximum width constraint
                    if calculated_width > logo_max_width:
                        logo_width = logo_max_width
                        logo_height = int(logo_max_width / aspect_ratio)
                    else:
                        logo_width = calculated_width
                    
                    # Position logo
                    logo_y = current_y - logo_height - 10
                    
                    # Add logo to canvas with error handling
                    try:
                        self._canvas.drawInlineImage(
                            logo_img, 
                            logo_x, 
                            logo_y, 
                            width=logo_width, 
                            height=logo_height,
                            preserveAspectRatio=True
                        )
                        
                        self.logger.info(f"Logo successfully loaded from {logo_path} at ({logo_x}, {logo_y}) "
                                       f"with size {logo_width}x{logo_height}")
                        return logo_width, logo_x
                        
                    except Exception as draw_error:
                        self.logger.warning(f"Failed to draw logo from {logo_path}: {draw_error}")
                        continue
                        
                else:
                    self.logger.debug(f"Logo file not found: {logo_path}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to load logo from {logo_path}: {e}")
                continue
        
        # Fallback: Create a simple text-based logo placeholder
        self.logger.info("No logo found, creating text-based fallback")
        self._create_logo_fallback(logo_x, current_y - 40)
        return 80, logo_x  # Return standard width for text placeholder
    
    def _create_logo_fallback(self, x: float, y: float):
        """
        Create a text-based logo fallback when no logo image is available.
        Uses white background as specified.
        
        Args:
            x: X position for fallback
            y: Y position for fallback
        """
        try:
            # Create a simple bordered text placeholder with white background
            self._canvas.setStrokeColor(colors.darkblue)
            self._canvas.setFillColor(colors.white)  # White background
            self._canvas.setLineWidth(2)
            
            # Draw border rectangle with white fill
            rect_width = 75
            rect_height = 35
            self._canvas.rect(x, y - rect_height, rect_width, rect_height, fill=1, stroke=1)
            
            # Add text
            self._canvas.setFillColor(colors.darkblue)
            self._canvas.setFont("Helvetica-Bold", 12)
            text_x = x + rect_width / 2 - 15  # Center text approximately
            text_y = y - rect_height / 2 - 3
            self._canvas.drawString(text_x, text_y, "ACS")
            
            # Reset colors
            self._canvas.setFillColor(colors.black)
            self._canvas.setStrokeColor(colors.black)
            
            self.logger.debug("Logo fallback created successfully with white background")
            
        except Exception as e:
            self.logger.warning(f"Failed to create logo fallback: {e}")
    
    
    
    def _add_charts(self, current_y: float) -> float:
        """
        Add financial and personnel charts to the PDF.
        
        Args:
            current_y: Current Y position
        
        Returns:
            Y position after charts
        
        Raises:
            PDFGenerationError: If chart addition fails critically
        """
        try:
            self.logger.debug("Adding charts to PDF")
            
            # Chart configuration
            chart_config = ChartConfig.default_financial_chart()
            chart_width = 400  # Scaled down for PDF
            chart_height = 250
            
            # Calculate positions for side-by-side charts
            chart_spacing = 20
            total_width = (chart_width * 2) + chart_spacing
            
            if total_width > self.config.content_width:
                # Stack charts vertically if they don't fit side by side
                chart_width = int(self.config.content_width * 0.8)
                chart_height = int(chart_height * chart_width / 400)  # Maintain aspect ratio
                
                # Financial chart
                financial_y = self._add_single_chart(
                    current_y, 
                    "financial", 
                    chart_width, 
                    chart_height,
                    chart_config
                )
                
                # Personnel chart
                personnel_y = self._add_single_chart(
                    financial_y - self.config.spacing_medium, 
                    "personnel", 
                    chart_width, 
                    chart_height,
                    chart_config
                )
                
                return personnel_y
            else:
                # Side-by-side charts
                chart_y = current_y - chart_height - self.config.spacing_medium
                
                # Check if charts fit on current page
                if self.layout_manager.needs_new_page(chart_height + self.config.spacing_medium):
                    self.layout_manager.start_new_page()
                    self._canvas.showPage()
                    chart_y = self.layout_manager.current_y_position - chart_height
                
                # Left chart (Financial)
                left_x = self.config.margin
                self._add_chart_at_position(
                    "financial", 
                    left_x, 
                    chart_y, 
                    chart_width, 
                    chart_height,
                    chart_config
                )
                
                # Right chart (Personnel)
                right_x = self.config.margin + chart_width + chart_spacing
                self._add_chart_at_position(
                    "personnel", 
                    right_x, 
                    chart_y, 
                    chart_width, 
                    chart_height,
                    chart_config
                )
                
                # Update position
                self.layout_manager.advance_position(chart_height, self.config.spacing_large)
                
                return chart_y - self.config.spacing_large
                
        except Exception as e:
            # Log error but continue with placeholders
            self.logger.error(f"Chart addition failed: {e}")
            
            # Add error message instead of charts
            error_y = current_y - 50
            self._canvas.setFont("Helvetica", self.config.body_font_size)
            self._canvas.setFillColor(colors.red)
            self._canvas.drawString(
                self.config.margin, 
                error_y, 
                "Erro na geração dos gráficos. Dados podem estar incompletos."
            )
            self._canvas.setFillColor(colors.black)
            
            return error_y - self.config.spacing_medium
    
    def _add_single_chart(self, current_y: float, chart_type: str, 
                         width: int, height: int, config: ChartConfig) -> float:
        """Add a single chart vertically."""
        chart_y = current_y - height - self.config.spacing_medium
        
        # Check if chart fits on current page
        if self.layout_manager.needs_new_page(height + self.config.spacing_medium):
            self.layout_manager.start_new_page()
            self._canvas.showPage()
            chart_y = self.layout_manager.current_y_position - height
        
        # Center the chart
        chart_x = self.layout_manager.get_centered_x(width)
        
        self._add_chart_at_position(chart_type, chart_x, chart_y, width, height, config)
        
        # Update position
        self.layout_manager.advance_position(height, self.config.spacing_medium)
        
        return chart_y - self.config.spacing_medium
    
    def _add_chart_at_position(self, chart_type: str, x: float, y: float, 
                              width: int, height: int, config: ChartConfig):
        """Add a chart at a specific position."""
        try:
            if chart_type == "financial":
                chart_image = self.chart_renderer.render_chart_with_fallback(
                    ChartRenderer.create_financial_chart,
                    "Financial Chart",
                    width=width,
                    height=height,
                    dpi=config.dpi,
                    resource_manager=self._resource_manager,
                    df_3_meses=self.df_3_meses,
                    config=config
                )
            elif chart_type == "personnel":
                chart_image = self.chart_renderer.render_chart_with_fallback(
                    ChartRenderer.create_personnel_chart,
                    "Personnel Chart",
                    width=width,
                    height=height,
                    dpi=config.dpi,
                    resource_manager=self._resource_manager,
                    df_3_meses=self.df_3_meses,
                    config=config
                )
            else:
                raise ValueError(f"Unknown chart type: {chart_type}")
            
            # Add chart to canvas
            self._canvas.drawInlineImage(chart_image, x, y, width=width, height=height)
            
            # Register element with layout manager
            self.layout_manager.register_element(x, y, width, height, f"{chart_type}_chart")
            
            self.logger.debug(f"{chart_type.title()} chart added at ({x}, {y}) with size {width}x{height}")
            
        except Exception as e:
            self.logger.error(f"Failed to add {chart_type} chart: {e}")
            # Add placeholder text
            self._canvas.setFont("Helvetica", self.config.body_font_size)
            self._canvas.setFillColor(colors.red)
            self._canvas.drawString(x, y + height/2, f"Erro: {chart_type} chart não disponível")
            self._canvas.setFillColor(colors.black) 
   
    def _add_summary_table(self, current_y: float) -> float:
        """
        Add detailed summary table to the PDF.
        
        Args:
            current_y: Current Y position
        
        Returns:
            Y position after table
        
        Raises:
            PDFGenerationError: If table creation fails
        """
        try:
            self.logger.debug("Adding summary table to PDF")
            
            # Prepare table data
            table_data = self._prepare_table_data()
            
            if not table_data:
                self.logger.warning("No table data available")
                return current_y - self.config.spacing_medium
            
            # Calculate table dimensions to fit within content width
            available_width = self.config.content_width - 20  # Leave some margin
            col_widths = [
                available_width * 0.25,  # Competência - 25%
                available_width * 0.18,  # ACS Credenc. - 18%
                available_width * 0.17,  # ACS Pagos - 17%
                available_width * 0.20,  # Valor Esperado - 20%
                available_width * 0.20   # Valor Recebido - 20%
            ]
            row_height = self.config.table_row_height
            header_height = self.config.table_header_height
            table_width = sum(col_widths)
            table_height = header_height + (len(table_data) - 1) * row_height
            
            # Check if table fits on current page
            if self.layout_manager.needs_new_page(table_height + self.config.spacing_medium):
                self.layout_manager.start_new_page()
                self._canvas.showPage()
                current_y = self.layout_manager.current_y_position
            
            # Position table
            table_x = self.layout_manager.get_centered_x(table_width)
            table_y = current_y - table_height - self.config.spacing_medium
            
            # Add table title
            title_y = current_y - self.config.spacing_small
            self._canvas.setFont("Helvetica-Bold", self.config.header_font_size)
            title_text = "Resumo Detalhado por Competência"
            title_width = self._canvas.stringWidth(title_text, "Helvetica-Bold", self.config.header_font_size)
            title_x = self.layout_manager.get_centered_x(title_width)
            self._canvas.drawString(title_x, title_y, title_text)
            
            # Create and style table
            table = Table(table_data, colWidths=col_widths, rowHeights=[header_height] + [row_height] * (len(table_data) - 1))
            
            # Apply table styling
            table_style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), self.config.body_font_size),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), self.config.small_font_size),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                
                # Zebra striping for better readability
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, Color(*self.config.table_stripe_color)]),
            ])
            
            table.setStyle(table_style)
            
            # Draw table manually on canvas
            self._draw_table_on_canvas(table, table_x, table_y, table_data, col_widths, row_height, header_height)
            
            # Register element with layout manager
            self.layout_manager.register_element(table_x, table_y, table_width, table_height, "summary_table")
            
            # Update position
            final_y = table_y - self.config.spacing_medium
            self.layout_manager.advance_position(table_height + self.config.spacing_medium * 2, 0)
            
            self.logger.debug(f"Summary table added at ({table_x}, {table_y}) with size {table_width}x{table_height}")
            return final_y
            
        except Exception as e:
            error_msg = f"Summary table creation failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Add error message
            error_y = current_y - 30
            self._canvas.setFont("Helvetica", self.config.body_font_size)
            self._canvas.setFillColor(colors.red)
            self._canvas.drawString(
                self.config.margin, 
                error_y, 
                "Erro na geração da tabela resumo."
            )
            self._canvas.setFillColor(colors.black)
            
            return error_y - self.config.spacing_medium
    
    def _prepare_table_data(self) -> List[List[str]]:
        """Prepare data for the summary table."""
        try:
            # Table headers
            headers = ["Competência", "ACS Credenc.", "ACS Pagos", "Valor Esperado", "Valor Recebido"]
            table_data = [headers]
            
            # Add data rows from df_3_meses
            for _, row in self.df_3_meses.iterrows():
                competencia = row.get('competencia', 'N/A')
                acs_credenc = str(int(row.get('qtTotalCredenciado', 0)))
                acs_pagos = str(int(row.get('qtTotalPago', 0)))
                valor_esperado = f"R$ {row.get('vlEsperado', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                valor_recebido = f"R$ {row.get('vlTotalAcs', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                
                table_data.append([competencia, acs_credenc, acs_pagos, valor_esperado, valor_recebido])
            
            return table_data
            
        except Exception as e:
            self.logger.error(f"Failed to prepare table data: {e}")
            return []
    
    def _draw_table_on_canvas(self, table, x: float, y: float, data: List[List[str]], 
                             col_widths: List[float], row_height: float, header_height: float):
        """Draw table directly on canvas for better control."""
        try:
            current_y = y + sum([header_height] + [row_height] * (len(data) - 1))
            
            for row_idx, row_data in enumerate(data):
                current_x = x
                
                # Determine row height
                height = header_height if row_idx == 0 else row_height
                
                for col_idx, cell_data in enumerate(row_data):
                    cell_width = col_widths[col_idx]
                    
                    # Draw cell background
                    if row_idx == 0:  # Header
                        self._canvas.setFillColor(colors.darkgreen)
                    elif row_idx % 2 == 0:  # Even rows
                        self._canvas.setFillColor(colors.white)
                    else:  # Odd rows
                        self._canvas.setFillColor(Color(*self.config.table_stripe_color))
                    
                    self._canvas.rect(current_x, current_y - height, cell_width, height, fill=1, stroke=1)
                    
                    # Draw cell text
                    if row_idx == 0:  # Header
                        self._canvas.setFillColor(colors.whitesmoke)
                        self._canvas.setFont("Helvetica-Bold", self.config.body_font_size)
                    else:  # Data
                        self._canvas.setFillColor(colors.black)
                        self._canvas.setFont("Helvetica", self.config.small_font_size)
                    
                    # Center text in cell
                    text_x = current_x + cell_width / 2
                    text_y = current_y - height / 2 - 3  # Adjust for text baseline
                    
                    # Draw text centered
                    text_width = self._canvas.stringWidth(str(cell_data))
                    self._canvas.drawString(text_x - text_width / 2, text_y, str(cell_data))
                    
                    current_x += cell_width
                
                current_y -= height
            
        except Exception as e:
            self.logger.error(f"Failed to draw table on canvas: {e}")
    
    def _add_regulatory_status(self, current_y: float) -> float:
        """
        Add regulatory compliance status section with alert cards and proper styling.
        
        Implements conditional rendering based on compliance status, alert cards with
        proper styling, and comprehensive regulatory information formatting.
        
        Args:
            current_y: Current Y position
        
        Returns:
            Y position after regulatory section
        
        Raises:
            PDFGenerationError: If regulatory section creation fails critically
        """
        try:
            self.logger.debug("Adding regulatory status section with enhanced styling")
            
            # Analyze compliance status first to determine section height
            compliance_status = self._analyze_compliance()
            
            # Calculate estimated section height based on compliance items
            base_height = 80  # Title and spacing
            card_height = 45  # Height per alert card
            footer_height = 40  # Footer section
            estimated_height = base_height + (len(compliance_status) * card_height) + footer_height
            
            # Check if we need a new page
            if self.layout_manager.needs_new_page(estimated_height):
                self.layout_manager.start_new_page()
                self._canvas.showPage()
                current_y = self.layout_manager.current_y_position
            
            # Section title with enhanced styling
            title_y = current_y - self.config.spacing_medium
            self._add_regulatory_section_title(title_y)
            
            # Add regulatory alert cards
            cards_start_y = title_y - 40
            cards_end_y = self._add_regulatory_alert_cards(cards_start_y, compliance_status)
            
            # Add regulatory information summary
            summary_y = self._add_regulatory_summary(cards_end_y - self.config.spacing_small)
            
            # Add generation footer
            footer_y = self._add_regulatory_footer(summary_y - self.config.spacing_small)
            
            # Update layout manager position
            total_height = current_y - footer_y
            self.layout_manager.advance_position(total_height, self.config.spacing_medium)
            
            final_y = footer_y - self.config.spacing_medium
            self.logger.debug(f"Regulatory status section completed, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            error_msg = f"Regulatory status section failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Add error fallback with proper styling
            return self._add_regulatory_error_fallback(current_y, error_msg)
    
    def _add_regulatory_section_title(self, title_y: float):
        """Add the regulatory section title with professional styling."""
        try:
            # Main title
            self._canvas.setFont("Helvetica-Bold", self.config.header_font_size + 2)
            self._canvas.setFillColor(colors.darkblue)
            
            title_text = "STATUS REGULATÓRIO E CONFORMIDADE"
            title_width = self._canvas.stringWidth(title_text)
            title_x = self.layout_manager.get_centered_x(title_width)
            
            self._canvas.drawString(title_x, title_y, title_text)
            
            # Add decorative underline
            underline_y = title_y - 5
            underline_start_x = title_x - 10
            underline_end_x = title_x + title_width + 10
            
            self._canvas.setStrokeColor(colors.darkblue)
            self._canvas.setLineWidth(2)
            self._canvas.line(underline_start_x, underline_y, underline_end_x, underline_y)
            
            # Reset colors
            self._canvas.setFillColor(colors.black)
            self._canvas.setStrokeColor(colors.black)
            
            self.logger.debug("Regulatory section title added with styling")
            
        except Exception as e:
            self.logger.warning(f"Failed to add regulatory section title: {e}")
            # Simple fallback
            self._canvas.setFont("Helvetica-Bold", self.config.header_font_size)
            self._canvas.drawString(self.config.margin, title_y, "Status Regulatório")
    
    def _add_regulatory_alert_cards(self, start_y: float, compliance_status: List[Dict[str, Any]]) -> float:
        """
        Add alert cards for each compliance item with conditional styling.
        
        Args:
            start_y: Starting Y position for cards
            compliance_status: List of compliance status items
        
        Returns:
            Y position after all cards
        """
        try:
            current_y = start_y
            card_height = 40
            card_margin = 5
            
            for i, status_item in enumerate(compliance_status):
                # Determine card styling based on compliance status
                if status_item['compliant']:
                    card_color = Color(0.9, 0.95, 0.9)  # Light green
                    border_color = colors.darkgreen
                    icon_color = colors.darkgreen
                    icon_symbol = "✓"
                    status_text = "CONFORME"
                else:
                    card_color = Color(0.95, 0.9, 0.9)  # Light red
                    border_color = colors.darkred
                    icon_color = colors.darkred
                    icon_symbol = "⚠"
                    status_text = "NÃO CONFORME"
                
                # Calculate card position
                card_y = current_y - card_height
                card_width = self.config.content_width - (card_margin * 2)
                card_x = self.config.margin + card_margin
                
                # Draw card background with border
                self._canvas.setFillColor(card_color)
                self._canvas.setStrokeColor(border_color)
                self._canvas.setLineWidth(1.5)
                self._canvas.roundRect(
                    card_x, card_y, card_width, card_height,
                    radius=3, fill=1, stroke=1
                )
                
                # Add status icon
                icon_x = card_x + 10
                icon_y = card_y + card_height/2 + 3
                self._canvas.setFont("Helvetica-Bold", 14)
                self._canvas.setFillColor(icon_color)
                self._canvas.drawString(icon_x, icon_y, icon_symbol)
                
                # Add status label
                status_x = icon_x + 20
                status_y = card_y + card_height - 12
                self._canvas.setFont("Helvetica-Bold", 8)
                self._canvas.setFillColor(icon_color)
                self._canvas.drawString(status_x, status_y, status_text)
                
                # Add description text
                desc_y = card_y + card_height/2 - 2
                self._canvas.setFont("Helvetica", self.config.body_font_size - 1)
                self._canvas.setFillColor(colors.black)
                
                # Wrap text if too long
                description = status_item['description']
                max_width = card_width - 100  # Leave space for icon and margins
                wrapped_text = self._wrap_text(description, max_width, "Helvetica", self.config.body_font_size - 1)
                
                for j, line in enumerate(wrapped_text[:2]):  # Max 2 lines per card
                    line_y = desc_y - (j * 10)
                    self._canvas.drawString(status_x, line_y, line)
                
                # Add severity indicator for non-compliant items
                if not status_item['compliant']:
                    severity = status_item.get('severity', 'medium')
                    severity_x = card_x + card_width - 60
                    severity_y = card_y + 5
                    
                    severity_colors = {
                        'high': colors.red,
                        'medium': colors.orange,
                        'low': colors.yellow
                    }
                    
                    self._canvas.setFillColor(severity_colors.get(severity, colors.orange))
                    self._canvas.setFont("Helvetica-Bold", 7)
                    severity_text = f"PRIORIDADE {severity.upper()}"
                    self._canvas.drawString(severity_x, severity_y, severity_text)
                
                current_y = card_y - card_margin
                
                self.logger.debug(f"Alert card {i+1} added: {status_item['description'][:50]}...")
            
            # Reset colors
            self._canvas.setFillColor(colors.black)
            self._canvas.setStrokeColor(colors.black)
            
            return current_y
            
        except Exception as e:
            self.logger.error(f"Failed to add regulatory alert cards: {e}")
            # Simple fallback
            fallback_y = start_y - 20
            self._canvas.setFont("Helvetica", self.config.body_font_size)
            self._canvas.drawString(self.config.margin, fallback_y, "Erro na geração dos cartões de conformidade")
            return fallback_y - 20
    
    def _add_regulatory_summary(self, start_y: float) -> float:
        """
        Add regulatory information summary section.
        
        Args:
            start_y: Starting Y position
        
        Returns:
            Y position after summary
        """
        try:
            current_y = start_y
            
            # Summary title
            self._canvas.setFont("Helvetica-Bold", self.config.body_font_size)
            self._canvas.setFillColor(colors.darkblue)
            self._canvas.drawString(self.config.margin, current_y, "Resumo da Conformidade:")
            
            current_y -= 20
            
            # Calculate compliance statistics
            compliance_status = self._analyze_compliance()
            total_items = len(compliance_status)
            compliant_items = sum(1 for item in compliance_status if item['compliant'])
            compliance_rate = (compliant_items / total_items * 100) if total_items > 0 else 0
            
            # Add compliance rate
            self._canvas.setFont("Helvetica", self.config.body_font_size)
            self._canvas.setFillColor(colors.black)
            
            rate_text = f"Taxa de Conformidade: {compliance_rate:.1f}% ({compliant_items}/{total_items} itens)"
            self._canvas.drawString(self.config.margin + 10, current_y, rate_text)
            
            current_y -= 15
            
            # Add compliance level indicator
            if compliance_rate >= 90:
                level_text = "Nível: EXCELENTE"
                level_color = colors.darkgreen
            elif compliance_rate >= 70:
                level_text = "Nível: BOM"
                level_color = colors.orange
            else:
                level_text = "Nível: REQUER ATENÇÃO"
                level_color = colors.red
            
            self._canvas.setFillColor(level_color)
            self._canvas.setFont("Helvetica-Bold", self.config.body_font_size)
            self._canvas.drawString(self.config.margin + 10, current_y, level_text)
            
            current_y -= 20
            
            # Add recommendations if needed
            if compliance_rate < 90:
                self._canvas.setFillColor(colors.black)
                self._canvas.setFont("Helvetica", self.config.small_font_size)
                
                recommendations = self._get_compliance_recommendations(compliance_status)
                if recommendations:
                    self._canvas.drawString(self.config.margin, current_y, "Recomendações:")
                    current_y -= 12
                    
                    for rec in recommendations[:3]:  # Max 3 recommendations
                        self._canvas.drawString(self.config.margin + 10, current_y, f"• {rec}")
                        current_y -= 10
            
            # Reset colors
            self._canvas.setFillColor(colors.black)
            
            return current_y
            
        except Exception as e:
            self.logger.error(f"Failed to add regulatory summary: {e}")
            return start_y - 30
    
    def _add_regulatory_footer(self, start_y: float) -> float:
        """
        Add regulatory section footer with generation info.
        
        Args:
            start_y: Starting Y position
        
        Returns:
            Y position after footer
        """
        try:
            current_y = start_y
            
            # Add separator line
            separator_y = current_y - 5
            self._canvas.setStrokeColor(colors.lightgrey)
            self._canvas.setLineWidth(0.5)
            self._canvas.line(
                self.config.margin, 
                separator_y, 
                self.config.page_width - self.config.margin, 
                separator_y
            )
            
            current_y = separator_y - 15
            
            # Add generation timestamp
            self._canvas.setFont("Helvetica", self.config.small_font_size)
            self._canvas.setFillColor(colors.gray)
            
            timestamp = datetime.now().strftime('%d/%m/%Y às %H:%M')
            footer_text = f"Status regulatório gerado automaticamente em {timestamp}"
            self._canvas.drawString(self.config.margin, current_y, footer_text)
            
            current_y -= 12
            
            # Add data source info
            competencia_atual = self.competencias[-1] if self.competencias else "N/A"
            source_text = f"Baseado nos dados da competência {competencia_atual}"
            self._canvas.drawString(self.config.margin, current_y, source_text)
            
            # Reset colors
            self._canvas.setFillColor(colors.black)
            self._canvas.setStrokeColor(colors.black)
            
            return current_y
            
        except Exception as e:
            self.logger.error(f"Failed to add regulatory footer: {e}")
            return start_y - 20
    
    def _add_regulatory_error_fallback(self, current_y: float, error_msg: str) -> float:
        """
        Add error fallback for regulatory section.
        
        Args:
            current_y: Current Y position
            error_msg: Error message to display
        
        Returns:
            Y position after error section
        """
        try:
            error_y = current_y - self.config.spacing_medium
            
            # Error title
            self._canvas.setFont("Helvetica-Bold", self.config.header_font_size)
            self._canvas.setFillColor(colors.red)
            self._canvas.drawString(self.config.margin, error_y, "Erro no Status Regulatório")
            
            error_y -= 25
            
            # Error message
            self._canvas.setFont("Helvetica", self.config.body_font_size)
            self._canvas.setFillColor(colors.black)
            self._canvas.drawString(
                self.config.margin, 
                error_y, 
                "Não foi possível gerar a seção de status regulatório."
            )
            
            error_y -= 15
            
            # Technical details (if in debug mode)
            if self.logger.isEnabledFor(logging.DEBUG):
                self._canvas.setFont("Helvetica", self.config.small_font_size)
                self._canvas.setFillColor(colors.gray)
                self._canvas.drawString(self.config.margin, error_y, f"Detalhes: {error_msg[:100]}...")
                error_y -= 12
            
            # Reset colors
            self._canvas.setFillColor(colors.black)
            
            return error_y - self.config.spacing_medium
            
        except Exception as e:
            self.logger.error(f"Error fallback failed: {e}")
            return current_y - 100  # Simple fallback
    
    def _wrap_text(self, text: str, max_width: float, font_name: str, font_size: int) -> List[str]:
        """
        Wrap text to fit within specified width.
        
        Args:
            text: Text to wrap
            max_width: Maximum width in points
            font_name: Font name
            font_size: Font size
        
        Returns:
            List of wrapped text lines
        """
        try:
            # Use canvas if available, otherwise create temporary one for measurement
            if self._canvas is not None:
                canvas_to_use = self._canvas
            else:
                # Create temporary canvas for text measurement
                temp_buffer = io.BytesIO()
                canvas_to_use = canvas.Canvas(temp_buffer, pagesize=A4)
            
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                text_width = canvas_to_use.stringWidth(test_line, font_name, font_size)
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # Single word is too long, add it anyway
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
            
        except Exception as e:
            self.logger.error(f"Text wrapping failed: {e}")
            return [text]  # Return original text as fallback
    
    def _get_compliance_recommendations(self, compliance_status: List[Dict[str, Any]]) -> List[str]:
        """
        Generate compliance recommendations based on status.
        
        Args:
            compliance_status: List of compliance status items
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        try:
            for item in compliance_status:
                if not item['compliant']:
                    description = item['description'].lower()
                    
                    if 'pagamento' in description or 'acs' in description:
                        recommendations.append("Verificar processos de pagamento dos ACS")
                    elif 'financeira' in description or 'execução' in description:
                        recommendations.append("Revisar execução orçamentária e financeira")
                    elif 'dados' in description or 'consistência' in description:
                        recommendations.append("Melhorar coleta e consistência dos dados")
                    else:
                        recommendations.append("Revisar conformidade regulatória")
            
            # Add general recommendations
            if len([item for item in compliance_status if not item['compliant']]) > 1:
                recommendations.append("Implementar plano de ação para múltiplas não conformidades")
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append("Consultar equipe técnica para orientações")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _analyze_compliance(self) -> List[Dict[str, Any]]:
        """
        Analyze data for comprehensive regulatory compliance.
        
        Performs detailed analysis of ACS payment rates, financial execution,
        data consistency, and regulatory requirements to determine compliance status.
        
        Returns:
            List of compliance items with status, description, and severity
        """
        compliance_items = []
        
        try:
            self.logger.debug("Performing comprehensive compliance analysis")
            
            # Check if current data exists and is valid
            if not self.dados_atual.empty:
                
                # 1. ACS Payment Compliance Analysis
                acs_credenciados = self.dados_atual.get('qtTotalCredenciado', 0)
                acs_pagos = self.dados_atual.get('qtTotalPago', 0)
                
                if acs_credenciados > 0:
                    payment_rate = (acs_pagos / acs_credenciados) * 100
                    
                    # Determine compliance and severity
                    if payment_rate >= 95:
                        compliant = True
                        severity = 'low'
                    elif payment_rate >= 80:
                        compliant = True
                        severity = 'medium'
                    elif payment_rate >= 60:
                        compliant = False
                        severity = 'medium'
                    else:
                        compliant = False
                        severity = 'high'
                    
                    compliance_items.append({
                        'compliant': compliant,
                        'severity': severity,
                        'category': 'payment',
                        'description': f"Taxa de pagamento ACS: {payment_rate:.1f}% ({acs_pagos}/{acs_credenciados})",
                        'details': f"Meta: ≥80% | Atual: {payment_rate:.1f}%"
                    })
                else:
                    compliance_items.append({
                        'compliant': False,
                        'severity': 'high',
                        'category': 'payment',
                        'description': "Dados de ACS credenciados não disponíveis",
                        'details': "Impossível calcular taxa de pagamento"
                    })
                
                # 2. Financial Execution Compliance
                valor_esperado = self.dados_atual.get('vlEsperado', 0)
                valor_recebido = self.dados_atual.get('vlTotalAcs', 0)
                
                if valor_esperado > 0:
                    financial_rate = (valor_recebido / valor_esperado) * 100
                    
                    # Determine compliance and severity
                    if financial_rate >= 95:
                        compliant = True
                        severity = 'low'
                    elif financial_rate >= 85:
                        compliant = True
                        severity = 'medium'
                    elif financial_rate >= 70:
                        compliant = False
                        severity = 'medium'
                    else:
                        compliant = False
                        severity = 'high'
                    
                    compliance_items.append({
                        'compliant': compliant,
                        'severity': severity,
                        'category': 'financial',
                        'description': f"Execução financeira: {financial_rate:.1f}%",
                        'details': f"R$ {valor_recebido:,.2f} de R$ {valor_esperado:,.2f} esperados"
                    })
                else:
                    compliance_items.append({
                        'compliant': False,
                        'severity': 'medium',
                        'category': 'financial',
                        'description': "Dados financeiros incompletos",
                        'details': "Valores esperados não informados"
                    })
                
                # 3. Coverage and Population Analysis
                populacao_coberta = self.dados_atual.get('qtPopulacaoCoberta', 0)
                populacao_total = self.dados_atual.get('qtPopulacaoTotal', 0)
                
                if populacao_total > 0:
                    coverage_rate = (populacao_coberta / populacao_total) * 100
                    
                    compliance_items.append({
                        'compliant': coverage_rate >= 70,
                        'severity': 'medium' if coverage_rate < 70 else 'low',
                        'category': 'coverage',
                        'description': f"Cobertura populacional: {coverage_rate:.1f}%",
                        'details': f"{populacao_coberta:,} de {populacao_total:,} habitantes"
                    })
                
                # 4. Temporal Consistency Analysis
                if len(self.df_3_meses) >= 3:
                    # Check for data consistency across months
                    recent_months = self.df_3_meses.tail(3)
                    
                    # Check for significant variations in ACS numbers
                    acs_variations = recent_months['qtTotalCredenciado'].std() if 'qtTotalCredenciado' in recent_months.columns else 0
                    mean_acs = recent_months['qtTotalCredenciado'].mean() if 'qtTotalCredenciado' in recent_months.columns else 0
                    
                    if mean_acs > 0:
                        variation_coefficient = (acs_variations / mean_acs) * 100
                        
                        compliance_items.append({
                            'compliant': variation_coefficient <= 15,
                            'severity': 'low' if variation_coefficient <= 15 else 'medium',
                            'category': 'consistency',
                            'description': f"Estabilidade dos dados: {100-variation_coefficient:.1f}%",
                            'details': f"Coeficiente de variação: {variation_coefficient:.1f}%"
                        })
            
            # 5. Data Completeness Check
            data_months = len(self.df_3_meses)
            expected_months = 3
            
            compliance_items.append({
                'compliant': data_months >= expected_months,
                'severity': 'high' if data_months < 2 else 'medium',
                'category': 'data_quality',
                'description': f"Completude dos dados: {data_months}/{expected_months} meses",
                'details': f"Histórico disponível: {data_months} competências"
            })
            
            # 6. Regulatory Timeline Compliance
            if self.competencias:
                latest_competencia = self.competencias[-1]
                try:
                    # Parse competencia format (assuming YYYYMM)
                    if len(latest_competencia) >= 6:
                        comp_year = int(latest_competencia[:4])
                        comp_month = int(latest_competencia[4:6])
                        
                        current_date = datetime.now()
                        comp_date = datetime(comp_year, comp_month, 1)
                        
                        # Check if data is recent (within 3 months)
                        months_diff = (current_date.year - comp_date.year) * 12 + (current_date.month - comp_date.month)
                        
                        compliance_items.append({
                            'compliant': months_diff <= 3,
                            'severity': 'medium' if months_diff > 3 else 'low',
                            'category': 'timeliness',
                            'description': f"Atualidade dos dados: {months_diff} meses de defasagem",
                            'details': f"Última competência: {latest_competencia}"
                        })
                        
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Failed to parse competencia date: {e}")
                    compliance_items.append({
                        'compliant': False,
                        'severity': 'low',
                        'category': 'timeliness',
                        'description': "Formato de competência inválido",
                        'details': f"Competência: {latest_competencia}"
                    })
            
            # Log compliance summary
            total_items = len(compliance_items)
            compliant_items = sum(1 for item in compliance_items if item['compliant'])
            self.logger.info(f"Compliance analysis completed: {compliant_items}/{total_items} items compliant")
            
        except Exception as e:
            self.logger.error(f"Compliance analysis failed: {e}")
            compliance_items.append({
                'compliant': False,
                'severity': 'high',
                'category': 'system',
                'description': "Erro na análise de conformidade",
                'details': f"Erro técnico: {str(e)[:50]}..."
            })
        
        return compliance_items
    
    def _add_indicadores_principais(self, current_y: float) -> float:
        """
        Adiciona seção 'Indicadores Principais' no formato dashboard.
        
        Args:
            current_y: Posição Y atual
        
        Returns:
            Nova posição Y após a seção
        """
        try:
            from reportlab.lib.colors import HexColor
            
            # Título da seção com retângulo verde
            section_y = current_y - 15  # Espaço mínimo antes do título
            
            # Retângulo verde
            rect_width = 15
            rect_height = 8
            rect_x = self.config.margin
            rect_y = section_y - 2
            
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
            
            # Título
            title_x = rect_x + rect_width + 10
            self._canvas.setFont("Helvetica-Bold", 14)
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.drawString(title_x, section_y, "Indicadores Principais")
            
            # Preparar dados da tabela
            table_y = section_y - 40
            
            # Dados atuais do último período
            if not self.dados_atual.empty:
                valor_recebido = self.dados_atual.get('vlTotalAcs', 0)
                acs_pagos = int(self.dados_atual.get('qtTotalPago', 0))
                valor_esperado = self.dados_atual.get('vlEsperado', 0)
                
                # Calcular variações (comparar com período anterior se disponível)
                variacao_valor = 0
                variacao_acs = 0
                if len(self.df_3_meses) >= 2:
                    periodo_anterior = self.df_3_meses.iloc[-2]
                    variacao_valor = valor_recebido - periodo_anterior.get('vlTotalAcs', 0)
                    variacao_acs = acs_pagos - int(periodo_anterior.get('qtTotalPago', 0))
                
                # Formatar valores
                valor_recebido_str = self._format_currency_dashboard(valor_recebido)
                valor_esperado_str = self._format_currency_dashboard(valor_esperado)
                variacao_valor_str = self._format_currency_dashboard(variacao_valor, show_sign=True)
                variacao_acs_str = f"{variacao_acs:+d}" if variacao_acs != 0 else "0"
            else:
                valor_recebido_str = "R$ 0"
                valor_esperado_str = "R$ 0"
                variacao_valor_str = "R$ 0,00"
                acs_pagos = 0
                variacao_acs_str = "0"
            
            # Dados da tabela
            table_data = [
                ["Métrica", "Valor Atual", "Variação Mensal"],
                [f"Valor Recebido (R$)", valor_recebido_str, variacao_valor_str],
                ["ACS Pagos", str(acs_pagos), variacao_acs_str],
                [f"Valor Esperado (R$)", valor_esperado_str, "R$ 0,00"]
            ]
            
            # Configurações da tabela
            col_widths = [150, 100, 100]
            row_height = 25
            table_width = sum(col_widths)
            table_height = len(table_data) * row_height
            
            # Posicionar tabela centralizada
            table_x = self.config.margin + (self.config.content_width - table_width) / 2
            
            # Desenhar tabela
            current_table_y = table_y
            
            for row_idx, row_data in enumerate(table_data):
                current_x = table_x
                
                for col_idx, cell_data in enumerate(row_data):
                    cell_width = col_widths[col_idx]
                    
                    # Cor do fundo
                    if row_idx == 0:  # Cabeçalho
                        self._canvas.setFillColor(HexColor(self.config.dashboard_blue))
                    else:  # Dados
                        self._canvas.setFillColor(HexColor('#FFFFFF'))
                    
                    # Desenhar célula
                    self._canvas.rect(current_x, current_table_y - row_height, 
                                    cell_width, row_height, fill=1, stroke=1)
                    
                    # Texto
                    if row_idx == 0:  # Cabeçalho
                        self._canvas.setFillColor(HexColor('#FFFFFF'))
                        self._canvas.setFont("Helvetica-Bold", 10)
                    else:  # Dados
                        self._canvas.setFillColor(HexColor('#000000'))
                        self._canvas.setFont("Helvetica", 10)
                    
                    # Centralizar texto na célula
                    text_width = self._canvas.stringWidth(str(cell_data))
                    text_x = current_x + (cell_width - text_width) / 2
                    text_y = current_table_y - row_height/2 - 3
                    
                    self._canvas.drawString(text_x, text_y, str(cell_data))
                    
                    current_x += cell_width
                
                current_table_y -= row_height
            
            final_y = current_table_y - 20
            self.logger.debug(f"Indicadores Principais section added, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            self.logger.error(f"Failed to add Indicadores Principais: {e}")
            return current_y - 100  # Fallback
    
    def _format_currency_dashboard(self, valor: float, show_sign: bool = False) -> str:
        """
        Formatar moeda no padrão do dashboard (R$ XMil).
        
        Args:
            valor: Valor a ser formatado
            show_sign: Se deve mostrar sinal + ou -
        
        Returns:
            String formatada
        """
        if valor is None or valor == 0:
            return "R$ 0,00" if not show_sign else "R$ 0,00"
        
        sign = ""
        if show_sign:
            sign = "+" if valor > 0 else ""
        
        abs_valor = abs(valor)
        
        if abs_valor >= 1_000_000:
            formatted = f"R$ {sign}{valor/1_000_000:.1f}Mi"
        elif abs_valor >= 1_000:
            formatted = f"R$ {sign}{valor/1_000:.0f}Mil"
        else:
            formatted = f"R$ {sign}{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return formatted
    
    def _add_analise_comparativa(self, current_y: float) -> float:
        """
        Adiciona seção 'Análise Comparativa' com gráfico Esperado vs Recebido.
        
        Args:
            current_y: Posição Y atual
        
        Returns:
            Nova posição Y após a seção
        """
        try:
            from reportlab.lib.colors import HexColor
            
            # Título da seção com retângulo verde
            section_y = current_y - 15  # Espaço mínimo antes do título
            
            # Retângulo verde
            rect_width = 15
            rect_height = 8
            rect_x = self.config.margin
            rect_y = section_y - 2
            
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
            
            # Título
            title_x = rect_x + rect_width + 10
            self._canvas.setFont("Helvetica-Bold", 14)
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.drawString(title_x, section_y, "Análise Comparativa")
            
            # Criar gráfico usando ChartRenderer
            chart_y = section_y - 25
            chart_width = 450  # Mais compacto
            chart_height = 300  # Otimizado para melhor fit
            
            # Verificar se temos dados suficientes
            if len(self.df_3_meses) >= 2:
                try:
                    # Criar gráfico financeiro customizado para Dashboard ACS
                    fig = self._create_dashboard_financial_chart()
                    
                    # Converter para imagem
                    chart_image = self.chart_renderer.plotly_to_image(
                        fig, 
                        width=chart_width, 
                        height=chart_height,
                        resource_manager=self._resource_manager
                    )
                    
                    if chart_image:
                        # Posicionar gráfico centralizado
                        chart_x = self.config.margin + (self.config.content_width - chart_width) / 2
                        
                        # Desenhar gráfico
                        self._canvas.drawInlineImage(
                            chart_image, 
                            chart_x, 
                            chart_y - chart_height, 
                            width=chart_width, 
                            height=chart_height
                        )
                        
                        final_y = chart_y - chart_height - 20
                    else:
                        # Fallback se conversão falhar
                        final_y = self._add_chart_fallback(chart_y, "Análise Comparativa")
                        
                except Exception as chart_error:
                    self.logger.error(f"Failed to create comparative chart: {chart_error}")
                    final_y = self._add_chart_fallback(chart_y, "Análise Comparativa")
            else:
                # Não temos dados suficientes
                final_y = self._add_chart_fallback(chart_y, "Análise Comparativa", 
                                                 "Dados insuficientes para gráfico comparativo")
            
            self.logger.debug(f"Análise Comparativa section added, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            self.logger.error(f"Failed to add Análise Comparativa: {e}")
            return current_y - 100  # Fallback
    
    def _add_chart_fallback(self, y_position: float, section_name: str, 
                           message: str = "Gráfico indisponível") -> float:
        """
        Adiciona um placeholder quando o gráfico não pode ser gerado.
        
        Args:
            y_position: Posição Y para o placeholder
            section_name: Nome da seção
            message: Mensagem a exibir
        
        Returns:
            Nova posição Y
        """
        from reportlab.lib.colors import HexColor
        
        # Desenhar retângulo placeholder
        placeholder_width = 500
        placeholder_height = 200
        placeholder_x = self.config.margin + (self.config.content_width - placeholder_width) / 2
        placeholder_y = y_position - placeholder_height
        
        # Fundo cinza claro
        self._canvas.setFillColor(HexColor('#F5F5F5'))
        self._canvas.setStrokeColor(HexColor('#CCCCCC'))
        self._canvas.rect(placeholder_x, placeholder_y, placeholder_width, placeholder_height, 
                         fill=1, stroke=1)
        
        # Texto centralizado
        self._canvas.setFillColor(HexColor('#666666'))
        self._canvas.setFont("Helvetica", 12)
        
        text_x = placeholder_x + placeholder_width / 2
        text_y = placeholder_y + placeholder_height / 2
        
        # Centralizar texto
        text_width = self._canvas.stringWidth(message, "Helvetica", 12)
        text_x_centered = text_x - text_width / 2
        
        self._canvas.drawString(text_x_centered, text_y, message)
        
        return placeholder_y - 20
    
    def _add_analise_pessoal(self, current_y: float) -> float:
        """
        Adiciona seção 'Análise de Pessoal' com gráfico Credenciados vs Pagos.
        
        Args:
            current_y: Posição Y atual
        
        Returns:
            Nova posição Y após a seção
        """
        try:
            from reportlab.lib.colors import HexColor
            
            # Título da seção com retângulo verde
            section_y = current_y - 15  # Espaço mínimo antes do título
            
            # Retângulo verde
            rect_width = 15
            rect_height = 8
            rect_x = self.config.margin
            rect_y = section_y - 2
            
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
            
            # Título
            title_x = rect_x + rect_width + 10
            self._canvas.setFont("Helvetica-Bold", 14)
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.drawString(title_x, section_y, "Análise de Pessoal")
            
            # Criar gráfico de pessoal
            chart_y = section_y - 25
            chart_width = 450  # Mais compacto
            chart_height = 300  # Otimizado para melhor fit
            
            # Verificar se temos dados suficientes
            if len(self.df_3_meses) >= 2:
                try:
                    # Criar gráfico de pessoal customizado para Dashboard ACS
                    fig = self._create_dashboard_personnel_chart()
                    
                    # Converter para imagem
                    chart_image = self.chart_renderer.plotly_to_image(
                        fig, 
                        width=chart_width, 
                        height=chart_height,
                        resource_manager=self._resource_manager
                    )
                    
                    if chart_image:
                        # Posicionar gráfico centralizado
                        chart_x = self.config.margin + (self.config.content_width - chart_width) / 2
                        
                        # Desenhar gráfico
                        self._canvas.drawInlineImage(
                            chart_image, 
                            chart_x, 
                            chart_y - chart_height, 
                            width=chart_width, 
                            height=chart_height
                        )
                        
                        final_y = chart_y - chart_height - 20
                    else:
                        # Fallback se conversão falhar
                        final_y = self._add_chart_fallback(chart_y, "Análise de Pessoal")
                        
                except Exception as chart_error:
                    self.logger.error(f"Failed to create personnel chart: {chart_error}")
                    final_y = self._add_chart_fallback(chart_y, "Análise de Pessoal")
            else:
                # Não temos dados suficientes
                final_y = self._add_chart_fallback(chart_y, "Análise de Pessoal", 
                                                 "Dados insuficientes para gráfico de pessoal")
            
            self.logger.debug(f"Análise de Pessoal section added, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            self.logger.error(f"Failed to add Análise de Pessoal: {e}")
            return current_y - 100  # Fallback
    
    def _add_resumo_detalhado(self, current_y: float) -> float:
        """
        Adiciona seção 'Resumo Detalhado por Mês' com tabela de 5 colunas.
        
        Args:
            current_y: Posição Y atual
        
        Returns:
            Nova posição Y após a seção
        """
        try:
            from reportlab.lib.colors import HexColor
            
            # Título da seção com retângulo verde
            section_y = current_y - 15  # Espaço mínimo antes do título
            
            # Retângulo verde
            rect_width = 15
            rect_height = 8
            rect_x = self.config.margin
            rect_y = section_y - 2
            
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
            
            # Título
            title_x = rect_x + rect_width + 10
            self._canvas.setFont("Helvetica-Bold", 14)
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.drawString(title_x, section_y, "Resumo Detalhado por Mês")
            
            # Preparar dados da tabela
            table_y = section_y - 40
            
            # Cabeçalhos da tabela
            headers = ["Mês/Ano", "Valor Recebido (R$)", "Variação (R$)", "ACS Pagos", "Variação ACS"]
            table_data = [headers]
            
            # Adicionar dados dos meses (ordenados do mais recente para o mais antigo)
            df_sorted = self.df_3_meses.sort_values('competencia', ascending=False)
            
            for i, (_, row) in enumerate(df_sorted.iterrows()):
                competencia = row.get('competencia', 'N/A')
                valor_recebido = row.get('vlTotalAcs', 0)
                acs_pagos = int(row.get('qtTotalPago', 0))
                
                # Calcular variações (comparar com o período anterior)
                variacao_valor = 0
                variacao_acs = 0
                
                if i < len(df_sorted) - 1:
                    # Há um período anterior para comparar
                    periodo_anterior = df_sorted.iloc[i + 1]
                    variacao_valor = valor_recebido - periodo_anterior.get('vlTotalAcs', 0)
                    variacao_acs = acs_pagos - int(periodo_anterior.get('qtTotalPago', 0))
                
                # Formatar valores
                valor_recebido_str = f"R$ {valor_recebido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                variacao_valor_str = f"{variacao_valor:+,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                variacao_acs_str = f"{variacao_acs:+d}" if variacao_acs != 0 else "0"
                
                # Formatação do mês/ano - corrigir formato de data
                if '/' in competencia:
                    # Formato já está em YYYY/MM
                    parts = competencia.split('/')
                    if len(parts) == 2:
                        ano, mes = parts
                        mes_ano = f"{mes}/{ano}"
                    else:
                        mes_ano = competencia
                elif len(competencia) >= 6:
                    # Formato YYYYMM
                    ano = competencia[:4]
                    mes = competencia[4:6]
                    mes_ano = f"{mes}/{ano}"
                else:
                    mes_ano = competencia
                
                table_data.append([
                    mes_ano,
                    valor_recebido_str,
                    variacao_valor_str,
                    str(acs_pagos),
                    variacao_acs_str
                ])
            
            # Configurações da tabela
            col_widths = [80, 120, 100, 80, 100]  # Total: 480px
            row_height = 25
            table_width = sum(col_widths)
            table_height = len(table_data) * row_height
            
            # Posicionar tabela centralizada
            table_x = self.config.margin + (self.config.content_width - table_width) / 2
            
            # Desenhar tabela
            current_table_y = table_y
            
            for row_idx, row_data in enumerate(table_data):
                current_x = table_x
                
                for col_idx, cell_data in enumerate(row_data):
                    cell_width = col_widths[col_idx]
                    
                    # Determinar cor do fundo
                    if row_idx == 0:  # Cabeçalho
                        self._canvas.setFillColor(HexColor(self.config.dashboard_green))
                    elif row_idx == 1:  # Primeira linha de dados (mês atual)
                        self._canvas.setFillColor(HexColor(self.config.dashboard_light_green))
                    else:  # Demais linhas
                        self._canvas.setFillColor(HexColor('#FFFFFF'))
                    
                    # Desenhar célula
                    self._canvas.rect(current_x, current_table_y - row_height, 
                                    cell_width, row_height, fill=1, stroke=1)
                    
                    # Configurar texto
                    if row_idx == 0:  # Cabeçalho
                        self._canvas.setFillColor(HexColor('#FFFFFF'))
                        self._canvas.setFont("Helvetica-Bold", 9)
                    else:  # Dados
                        self._canvas.setFillColor(HexColor('#000000'))
                        self._canvas.setFont("Helvetica", 9)
                    
                    # Centralizar texto na célula
                    text_width = self._canvas.stringWidth(str(cell_data))
                    text_x = current_x + (cell_width - text_width) / 2
                    text_y = current_table_y - row_height/2 - 3
                    
                    self._canvas.drawString(text_x, text_y, str(cell_data))
                    
                    current_x += cell_width
                
                current_table_y -= row_height
            
            final_y = current_table_y - 20
            self.logger.debug(f"Resumo Detalhado section added, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            self.logger.error(f"Failed to add Resumo Detalhado: {e}")
            return current_y - 100  # Fallback
    
    def _add_alerta_regulamentar(self, current_y: float) -> float:
        """
        Adiciona seção 'Alerta Regulamentar' com destaque visual impactante.
        
        Args:
            current_y: Posição Y atual
        
        Returns:
            Nova posição Y após a seção
        """
        try:
            from reportlab.lib.colors import HexColor
            
            # Calcular dimensões da caixa de destaque com proteção contra sobreposição do rodapé
            box_width = self.config.content_width - 20
            box_height = 120
            box_x = self.config.margin + 10
            footer_safety_zone = 100  # Zona de segurança para o rodapé
            required_space = box_height + footer_safety_zone
            
            # Verificar se há espaço suficiente na página atual
            if current_y - required_space < self.config.margin:
                # Adicionar rodapé à página atual antes de quebrar
                self._add_dashboard_footer()
                # Forçar nova página se não há espaço suficiente
                self._canvas.showPage()
                current_y = self.config.page_height - self.config.margin
                self.logger.debug("Started new page for Alerta Regulamentar to avoid footer overlap")
            
            box_y = current_y - box_height - 25  # Espaçamento adequado
            
            # Fundo amarelo claro para destaque
            self._canvas.setFillColor(HexColor('#FFF8E1'))
            self._canvas.setStrokeColor(HexColor('#FFA726'))
            self._canvas.setLineWidth(2)
            self._canvas.roundRect(box_x, box_y, box_width, box_height, radius=5, fill=1, stroke=1)
            
            # Título da seção com retângulo verde
            section_y = box_y + box_height - 25
            
            # Retângulo verde
            rect_width = 15
            rect_height = 8
            rect_x = box_x + 15
            rect_y = section_y - 2
            
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
            
            # Título (fonte maior, negrito, maiúsculas, verde)
            title_x = rect_x + rect_width + 10
            self._canvas.setFont("Helvetica-Bold", 16)  # Fonte maior
            self._canvas.setFillColor(HexColor(self.config.dashboard_green))
            self._canvas.drawString(title_x, section_y, "ALERTA REGULAMENTAR")
            
            # Conteúdo do alerta
            content_y = section_y - 25
            line_height = 14
            
            # Linha 1: Portaria GM/MS (texto normal)
            self._canvas.setFont("Helvetica", 10)
            self._canvas.setFillColor(HexColor('#000000'))
            portaria_text = "Portaria GM/MS Nº 6.907, de 29 de abril de 2025"
            self._canvas.drawString(box_x + 15, content_y, portaria_text)
            
            # Linha 2: Observação (texto normal)
            content_y -= line_height
            observacao_text = "Observadas 3 (seis) competências consecutivas de ausência de envio de"
            self._canvas.drawString(box_x + 15, content_y, observacao_text)
            
            # Linha 3: Continuação da observação (texto normal)
            content_y -= line_height
            observacao_text2 = "informação sobre a produção do SISAB."
            self._canvas.drawString(box_x + 15, content_y, observacao_text2)
            
            # Linha 4: Perda mensal (negrito, maiúsculas, vermelho)
            content_y -= line_height + 8  # Espaço extra
            self._canvas.setFont("Helvetica-Bold", 12)  # Fonte maior
            self._canvas.setFillColor(HexColor('#D32F2F'))  # Vermelho para impacto
            perda_text = "PERDA APROXIMADAMENTE R$ 8MIL/MÊS"
            self._canvas.drawString(box_x + 15, content_y, perda_text)
            
            final_y = box_y - 15
            self.logger.debug(f"Enhanced Alerta Regulamentar section added, final Y: {final_y}")
            return final_y
            
        except Exception as e:
            self.logger.error(f"Failed to add Alerta Regulamentar: {e}")
            return current_y - 100  # Fallback
    
    def _add_dashboard_footer(self):
        """Adiciona rodapé do dashboard."""
        try:
            from reportlab.lib.colors import HexColor
            
            footer_y = self.config.margin + 20
            self._canvas.setFont("Helvetica", 8)
            self._canvas.setFillColor(HexColor('#666666'))
            
            copyright_text = "© Mais Gestor (2025) - Todos os direitos reservados"
            self._canvas.drawString(self.config.margin, footer_y, copyright_text)
            
        except Exception as e:
            self.logger.error(f"Failed to add dashboard footer: {e}")
    
    def _create_dashboard_financial_chart(self):
        """
        Cria gráfico financeiro usando o visual da visão municipal.
        
        Returns:
            Plotly Figure configurado conforme visão municipal
        """
        import plotly.graph_objects as go
        
        try:
            # Preparar dados - ordenar por competência (ordem cronológica inversa como na visão municipal)
            df_sorted = self.df_3_meses.sort_values('competencia', ascending=False)
            
            # Extrair dados
            meses = [comp.replace('/', '/') for comp in df_sorted['competencia'].tolist()]
            valores_esperados = df_sorted['vlEsperado'].tolist()
            valores_recebidos = df_sorted['vlTotalAcs'].tolist()
            
            # Criar figura usando o estilo da visão municipal
            fig = go.Figure()
            
            # Adicionar barras para Valor Esperado (azul escuro da visão municipal)
            fig.add_trace(go.Bar(
                name='Valor Esperado',
                x=meses,
                y=valores_esperados,
                marker_color='#003366',  # Azul Escuro da visão municipal
                text=[f'R$ {v:,.0f}' for v in valores_esperados],
                textposition='auto'
            ))
            
            # Adicionar barras para Valor Recebido (verde vibrante da visão municipal)
            fig.add_trace(go.Bar(
                name='Valor Recebido',
                x=meses,
                y=valores_recebidos,
                marker_color='#2ca02c',  # Verde Vibrante da visão municipal
                text=[f'R$ {v:,.0f}' for v in valores_recebidos],
                textposition='auto'
            ))
            
            # Configurar layout como na visão municipal
            fig.update_layout(
                title='Comparação: Esperado vs Recebido',
                xaxis_title='Competência',
                yaxis_title='Valor (R$)',
                barmode='group',
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=40, r=40, t=50, b=40)
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Failed to create dashboard financial chart: {e}")
            # Retornar gráfico vazio em caso de erro
            fig = go.Figure()
            fig.add_annotation(
                text="Erro na geração do gráfico financeiro",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
    
    def _create_dashboard_personnel_chart(self):
        """
        Cria gráfico de pessoal usando o visual da visão municipal.
        
        Returns:
            Plotly Figure configurado conforme visão municipal
        """
        import plotly.graph_objects as go
        
        try:
            # Preparar dados - ordenar por competência (ordem cronológica inversa como na visão municipal)
            df_sorted = self.df_3_meses.sort_values('competencia', ascending=False)
            
            # Extrair dados
            meses = [comp.replace('/', '/') for comp in df_sorted['competencia'].tolist()]
            acs_credenciados = df_sorted['qtTotalCredenciado'].tolist()
            acs_pagos_lista = df_sorted['qtTotalPago'].tolist()
            
            # Criar figura usando o estilo da visão municipal
            fig = go.Figure()
            
            # Adicionar barras para ACS Credenciados (cinza médio da visão municipal)
            fig.add_trace(go.Bar(
                name='ACS Credenciados',
                x=meses,
                y=acs_credenciados,
                marker_color='#8c8c8c',  # Cinza Médio da visão municipal
                text=acs_credenciados,
                textposition='auto'
            ))
            
            # Adicionar barras para ACS Pagos (laranja intenso da visão municipal)
            fig.add_trace(go.Bar(
                name='ACS Pagos',
                x=meses,
                y=acs_pagos_lista,
                marker_color='#ff7f0e',  # Laranja Intenso da visão municipal
                text=acs_pagos_lista,
                textposition='auto'
            ))
            
            # Configurar layout como na visão municipal
            fig.update_layout(
                title='Comparação: Credenciados vs Pagos',
                xaxis_title='Competência',
                yaxis_title='Quantidade de ACS',
                barmode='group',
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=40, r=40, t=50, b=40)
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Failed to create dashboard personnel chart: {e}")
            # Retornar gráfico vazio em caso de erro
            fig = go.Figure()
            fig.add_annotation(
                text="Erro na geração do gráfico de pessoal",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the PDF generation process.
        
        Returns:
            Dictionary with generation statistics
        """
        return {
            'municipio': self.municipio,
            'uf': self.uf,
            'data_periods': len(self.df_3_meses),
            'competencias': self.competencias,
            'layout_stats': self.layout_manager.get_layout_stats() if self.layout_manager else {},
            'config': {
                'page_size': f"{self.config.page_width}x{self.config.page_height}",
                'margins': self.config.margin,
                'chart_size': f"{self.config.chart_width}x{self.config.chart_height}"
            }
        }


def gerar_pdf_municipal(municipio: str, uf: str, df_3_meses: pd.DataFrame, 
                       dados_atual: pd.Series, competencias: List[str],
                       config: Optional[PDFConfig] = None) -> io.BytesIO:
    """
    Generate municipal PDF report using Dashboard ACS format.
    
    Args:
        municipio: Municipality name
        uf: State abbreviation
        df_3_meses: DataFrame with 3 months of data
        dados_atual: Current month data as Series
        competencias: List of competency periods
        config: Optional PDF configuration
    
    Returns:
        BytesIO buffer containing the generated PDF
    
    Raises:
        PDFGenerationError: If PDF generation fails
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating Dashboard ACS PDF for {municipio}/{uf}")
    
    try:
        # Use default configuration if none provided
        if config is None:
            config = PDFConfig()
        
        # Create PDF generator
        generator = PDFGenerator(
            municipio=municipio,
            uf=uf,
            df_3_meses=df_3_meses,
            dados_atual=dados_atual,
            competencias=competencias,
            config=config,
            logger=logger
        )
        
        # Generate PDF
        pdf_buffer = generator.generate_pdf()
        
        logger.info(f"PDF generation completed for {municipio}/{uf}")
        return pdf_buffer
        
    except Exception as e:
        error_msg = f"PDF generation failed for {municipio}/{uf}: {str(e)}"
        logger.error(error_msg)
        raise PDFGenerationError(error_msg, str(e))