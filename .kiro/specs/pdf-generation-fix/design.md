# Design Document

## Overview

The current PDF generation system in `pages/1_Visao_municipal.py` has several critical issues:

1. **Memory Management**: Plotly image conversion creates memory leaks
2. **Error Handling**: Poor error handling for image conversion failures
3. **Code Structure**: Monolithic function with mixed responsibilities
4. **Resource Cleanup**: Images and file handles not properly closed
5. **Layout Issues**: Inconsistent spacing and potential content overflow
6. **Variable Scope**: Undefined variables like `margin` used instead of `MARGIN`

The redesigned system will use a modular approach with proper resource management, comprehensive error handling, and clean separation of concerns.

## Architecture

### Core Components

1. **PDFGenerator Class**: Main orchestrator for PDF creation
2. **ChartRenderer**: Handles Plotly chart to image conversion with proper cleanup
3. **LayoutManager**: Manages page layout, spacing, and positioning
4. **ResourceManager**: Handles resource allocation and cleanup
5. **ErrorHandler**: Centralized error handling and logging

### Data Flow

```
User Request → PDFGenerator → ChartRenderer → Image Conversion
                ↓
            LayoutManager → Page Layout → Content Positioning
                ↓
            ResourceManager → Cleanup → PDF Output
```

## Components and Interfaces

### PDFGenerator Class

```python
class PDFGenerator:
    def __init__(self, municipio: str, uf: str, df_3_meses: pd.DataFrame, dados_atual: pd.Series, competencias: list):
        # Initialize with data and configuration
        
    def generate_pdf(self) -> io.BytesIO:
        # Main PDF generation method
        
    def _create_header(self, canvas, y_position: float) -> float:
        # Create page header with logo and info
        
    def _add_charts(self, canvas, y_position: float) -> float:
        # Add financial and personnel charts
        
    def _add_summary_table(self, canvas, y_position: float) -> float:
        # Add detailed summary table
        
    def _add_regulatory_status(self, canvas, y_position: float) -> float:
        # Add regulatory compliance section
```

### ChartRenderer Class

```python
class ChartRenderer:
    @staticmethod
    def plotly_to_image(fig, width: int = 800, height: int = 400, dpi: int = 150) -> Optional[PILImage.Image]:
        # Convert Plotly figure to PIL Image with proper error handling
        
    @staticmethod
    def create_financial_chart(df_3_meses: pd.DataFrame) -> go.Figure:
        # Create financial comparison chart
        
    @staticmethod
    def create_personnel_chart(df_3_meses: pd.DataFrame) -> go.Figure:
        # Create personnel comparison chart
```

### LayoutManager Class

```python
class LayoutManager:
    def __init__(self, page_width: float, page_height: float):
        # Initialize layout constants and calculations
        
    def calculate_safe_position(self, current_y: float, element_height: float) -> float:
        # Calculate safe Y position to prevent content overflow
        
    def needs_new_page(self, current_y: float, element_height: float) -> bool:
        # Determine if new page is needed
        
    def get_centered_x(self, element_width: float) -> float:
        # Calculate centered X position
```

### ResourceManager Class

```python
class ResourceManager:
    def __init__(self):
        self._resources = []
        
    def register_resource(self, resource):
        # Register resource for cleanup
        
    def cleanup_all(self):
        # Clean up all registered resources
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()
```

## Data Models

### PDFConfig

```python
@dataclass
class PDFConfig:
    page_width: float = A4[0]
    page_height: float = A4[1]
    margin: float = 40
    spacing_large: float = 60
    spacing_medium: float = 40
    spacing_small: float = 20
    footer_height: float = 80
    chart_width: int = 800
    chart_height: int = 400
    chart_dpi: int = 150
```

### ChartConfig

```python
@dataclass
class ChartConfig:
    width: int
    height: int
    dpi: int
    background_color: str = 'white'
    margin_config: dict = field(default_factory=lambda: {'l': 40, 'r': 40, 't': 50, 'b': 40})
```

## Error Handling

### Error Types

1. **ChartConversionError**: When Plotly chart conversion fails
2. **ResourceCleanupError**: When resource cleanup fails
3. **PDFGenerationError**: General PDF generation failures
4. **LayoutError**: When content doesn't fit properly

### Error Recovery

- **Chart Conversion Failure**: Display placeholder with error message
- **Resource Issues**: Log warning and continue with available resources
- **Layout Problems**: Adjust spacing or create new page
- **Critical Failures**: Return error message to user with troubleshooting tips

## Testing Strategy

### Unit Tests

1. **ChartRenderer Tests**
   - Test successful chart conversion
   - Test error handling for invalid charts
   - Test resource cleanup after conversion

2. **LayoutManager Tests**
   - Test position calculations
   - Test page break detection
   - Test centering calculations

3. **PDFGenerator Tests**
   - Test complete PDF generation
   - Test error scenarios
   - Test resource cleanup

### Integration Tests

1. **End-to-End PDF Generation**
   - Test with real data from dashboard
   - Test with edge cases (empty data, large datasets)
   - Test memory usage during generation

2. **Error Scenarios**
   - Test with missing logo file
   - Test with invalid chart data
   - Test with insufficient memory

### Performance Tests

1. **Memory Usage**
   - Monitor memory consumption during PDF generation
   - Verify proper cleanup after generation
   - Test with multiple concurrent generations

2. **Generation Time**
   - Measure PDF generation time
   - Identify bottlenecks in chart conversion
   - Optimize for reasonable response times

## Implementation Notes

### Key Improvements

1. **Proper Resource Management**: Use context managers and try/finally blocks
2. **Modular Design**: Separate concerns into focused classes
3. **Error Resilience**: Graceful degradation when components fail
4. **Memory Efficiency**: Immediate cleanup of temporary resources
5. **Maintainable Code**: Clear structure and comprehensive documentation

### Dependencies

- `reportlab`: PDF generation
- `plotly`: Chart creation
- `kaleido`: Plotly image export (replaces problematic `to_image` method)
- `Pillow`: Image processing
- `pandas`: Data manipulation

### Configuration

All layout constants will be centralized in `PDFConfig` class to ensure consistency and easy maintenance.