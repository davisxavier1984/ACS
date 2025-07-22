"""
PDF Coordinate Validation Utility
=================================

This utility provides tools to validate PDF coordinate calculations and detect layout issues
in the ReportLab-based PDF generation function.

Key Features:
1. Coordinate boundary validation
2. Element overlap detection
3. Layout debugging tools
4. Visual coordinate mapping
5. Margin and spacing validation
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
import json


@dataclass
class PDFElement:
    """Represents a PDF element with position and dimensions"""
    name: str
    x: float
    y: float
    width: float
    height: float
    page: int = 1
    element_type: str = "generic"  # text, image, table, line, etc.
    
    def __post_init__(self):
        """Validate element properties"""
        if self.width < 0 or self.height < 0:
            raise ValueError(f"Element {self.name} has negative dimensions")
        if self.x < 0 or self.y < 0:
            raise ValueError(f"Element {self.name} has negative coordinates")
    
    @property
    def right(self) -> float:
        """Right edge coordinate"""
        return self.x + self.width
    
    @property
    def bottom(self) -> float:
        """Bottom edge coordinate (ReportLab coordinates)"""
        return self.y - self.height
    
    @property
    def center_x(self) -> float:
        """Center X coordinate"""
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        """Center Y coordinate"""
        return self.y - self.height / 2
    
    def overlaps_with(self, other: 'PDFElement') -> bool:
        """Check if this element overlaps with another element"""
        if self.page != other.page:
            return False
            
        # Check for overlap in both X and Y dimensions
        x_overlap = not (self.right <= other.x or other.right <= self.x)
        y_overlap = not (self.bottom >= other.y or other.bottom >= self.y)
        
        return x_overlap and y_overlap
    
    def distance_to(self, other: 'PDFElement') -> float:
        """Calculate distance between element centers"""
        if self.page != other.page:
            return float('inf')
            
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return (dx ** 2 + dy ** 2) ** 0.5
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'page': self.page,
            'element_type': self.element_type,
            'right': self.right,
            'bottom': self.bottom
        }


class PDFCoordinateValidator:
    """Validates PDF coordinates and layout"""
    
    def __init__(self, page_size: Tuple[float, float] = A4, margin: float = 20):
        self.page_width, self.page_height = page_size
        self.MARGIN = margin
        self.elements: List[PDFElement] = []
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []
    
    def add_element(self, element: PDFElement) -> None:
        """Add an element to the validation list"""
        self.elements.append(element)
    
    def add_from_coords(self, name: str, x: float, y: float, width: float, height: float, 
                       page: int = 1, element_type: str = "generic") -> None:
        """Add element from coordinates"""
        element = PDFElement(name, x, y, width, height, page, element_type)
        self.add_element(element)
    
    def validate_boundaries(self) -> List[str]:
        """Validate all elements are within page boundaries"""
        errors = []
        
        for element in self.elements:
            # Check left boundary
            if element.x < self.MARGIN:
                errors.append(f"Element '{element.name}' extends beyond left margin (x={element.x:.2f})")
            
            # Check right boundary  
            if element.right > self.page_width - self.MARGIN:
                errors.append(f"Element '{element.name}' extends beyond right margin (right={element.right:.2f})")
            
            # Check top boundary
            if element.y > self.page_height - self.MARGIN:
                errors.append(f"Element '{element.name}' extends beyond top margin (y={element.y:.2f})")
            
            # Check bottom boundary
            if element.bottom < self.MARGIN:
                errors.append(f"Element '{element.name}' extends beyond bottom margin (bottom={element.bottom:.2f})")
        
        return errors
    
    def detect_overlaps(self) -> List[Tuple[str, str, str]]:
        """Detect overlapping elements"""
        overlaps = []
        
        for i, elem1 in enumerate(self.elements):
            for j, elem2 in enumerate(self.elements):
                if i < j and elem1.overlaps_with(elem2):
                    overlap_type = self._classify_overlap(elem1, elem2)
                    overlaps.append((elem1.name, elem2.name, overlap_type))
        
        return overlaps
    
    def _classify_overlap(self, elem1: PDFElement, elem2: PDFElement) -> str:
        """Classify the type of overlap"""
        # Calculate overlap area
        overlap_left = max(elem1.x, elem2.x)
        overlap_right = min(elem1.right, elem2.right)
        overlap_top = min(elem1.y, elem2.y)
        overlap_bottom = max(elem1.bottom, elem2.bottom)
        
        overlap_width = overlap_right - overlap_left
        overlap_height = overlap_top - overlap_bottom
        overlap_area = overlap_width * overlap_height
        
        # Calculate overlap percentage
        elem1_area = elem1.width * elem1.height
        elem2_area = elem2.width * elem2.height
        smaller_area = min(elem1_area, elem2_area)
        
        overlap_percentage = (overlap_area / smaller_area) * 100
        
        if overlap_percentage > 50:
            return "major_overlap"
        elif overlap_percentage > 20:
            return "moderate_overlap" 
        else:
            return "minor_overlap"
    
    def validate_spacing(self, minimum_spacing: float = 10) -> List[str]:
        """Validate minimum spacing between elements"""
        spacing_errors = []
        
        for i, elem1 in enumerate(self.elements):
            for j, elem2 in enumerate(self.elements):
                if i < j and elem1.page == elem2.page:
                    distance = elem1.distance_to(elem2)
                    if distance < minimum_spacing and not elem1.overlaps_with(elem2):
                        spacing_errors.append(
                            f"Elements '{elem1.name}' and '{elem2.name}' are too close (distance={distance:.2f})"
                        )
        
        return spacing_errors
    
    def validate_text_readability(self) -> List[str]:
        """Validate text elements have adequate space"""
        text_errors = []
        
        text_elements = [e for e in self.elements if e.element_type == "text"]
        
        for text_elem in text_elements:
            # Check if text has minimum height for readability
            if text_elem.height < 12:  # Assuming 12pt minimum font size
                text_errors.append(f"Text element '{text_elem.name}' may be too small (height={text_elem.height:.2f})")
            
            # Check if text has adequate width
            if text_elem.width < 50:  # Minimum readable width
                text_errors.append(f"Text element '{text_elem.name}' may be too narrow (width={text_elem.width:.2f})")
        
        return text_errors
    
    def generate_layout_map(self) -> Dict:
        """Generate a visual layout map"""
        layout_map = {
            'page_dimensions': {
                'width': self.page_width,
                'height': self.page_height
            },
            'margins': self.MARGIN,
            'content_area': {
                'width': self.page_width - 2 * self.MARGIN,
                'height': self.page_height - 2 * self.MARGIN
            },
            'elements': [elem.to_dict() for elem in self.elements],
            'pages': {}
        }
        
        # Group elements by page
        for element in self.elements:
            page = element.page
            if page not in layout_map['pages']:
                layout_map['pages'][page] = []
            layout_map['pages'][page].append(element.to_dict())
        
        return layout_map
    
    def run_full_validation(self) -> Dict:
        """Run all validation checks"""
        validation_results = {
            'boundary_errors': self.validate_boundaries(),
            'overlaps': self.detect_overlaps(),
            'spacing_errors': self.validate_spacing(),
            'text_readability_errors': self.validate_text_readability(),
            'layout_map': self.generate_layout_map(),
            'summary': {}
        }
        
        # Generate summary
        total_errors = (len(validation_results['boundary_errors']) + 
                       len(validation_results['overlaps']) +
                       len(validation_results['spacing_errors']) +
                       len(validation_results['text_readability_errors']))
        
        validation_results['summary'] = {
            'total_elements': len(self.elements),
            'total_errors': total_errors,
            'pages_used': len(set(e.page for e in self.elements)),
            'validation_passed': total_errors == 0
        }
        
        return validation_results
    
    def export_validation_report(self, filename: str) -> None:
        """Export validation report to JSON file"""
        results = self.run_full_validation()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    def clear_elements(self) -> None:
        """Clear all elements and errors"""
        self.elements.clear()
        self.validation_errors.clear()
        self.warnings.clear()


class PDFLayoutAnalyzer:
    """Analyzes existing PDF layout patterns from the municipal dashboard"""
    
    @staticmethod
    def analyze_municipal_pdf_layout() -> PDFCoordinateValidator:
        """Analyze the layout used in the municipal PDF generation"""
        validator = PDFCoordinateValidator()
        width, height = A4
        MARGIN = 20
        
        # === PAGE 1 ELEMENTS ===
        
        # Enhanced Logo Header
        validator.add_from_coords(
            "logo_background", MARGIN, height - MARGIN - 90, 95, 65, 1, "image"
        )
        
        # Header Information
        validator.add_from_coords(
            "header_info", MARGIN + 110, height - MARGIN - 90, 400, 70, 1, "text"
        )
        
        # Header separator line
        validator.add_from_coords(
            "header_separator", MARGIN, height - MARGIN - 110, width - 2*MARGIN, 2, 1, "line"
        )
        
        # Financial Graph (Page 1)
        graph_y = height - MARGIN - 160
        validator.add_from_coords(
            "financial_graph", MARGIN, graph_y - 300, width - 2*MARGIN, 300, 1, "image"
        )
        
        # Page 1 Footer
        validator.add_from_coords(
            "footer_page1", MARGIN, 60, width - 2*MARGIN, 20, 1, "text"
        )
        
        # === PAGE 2 ELEMENTS ===
        
        # Simple Header (Page 2)
        validator.add_from_coords(
            "simple_header", MARGIN, height - MARGIN - 40, width - 2*MARGIN, 40, 2, "text"
        )
        
        # Personnel Graph (Page 2)
        graph_y_p2 = height - MARGIN - 90
        validator.add_from_coords(
            "personnel_graph", MARGIN, graph_y_p2 - 300, width - 2*MARGIN, 300, 2, "image"
        )
        
        # Summary Table (Page 2)
        table_y = graph_y_p2 - 340
        col_widths = [80, 100, 90, 70, 70]
        table_width = sum(col_widths)
        table_x = (width - table_width) / 2
        validator.add_from_coords(
            "summary_table", table_x, table_y - 120, table_width, 120, 2, "table"
        )
        
        # Status Card (Page 2)
        status_y = table_y - 160
        validator.add_from_coords(
            "status_card", MARGIN, status_y - 100, width - 2*MARGIN, 100, 2, "text"
        )
        
        # Page 2 Footer
        validator.add_from_coords(
            "footer_page2", MARGIN, 40, width - 2*MARGIN, 40, 2, "text"
        )
        
        return validator
    
    @staticmethod
    def get_recommended_fixes() -> List[Dict]:
        """Get recommended fixes for common layout issues"""
        return [
            {
                "issue": "Graph positioning overlap",
                "description": "Financial graph on page 1 may overlap with header",
                "fix": "Increase spacing between header and graph from 50 to 80 pixels",
                "code_location": "Line 153: graph_y = y_pos - 50  # Should be y_pos - 80"
            },
            {
                "issue": "Table centering calculation",
                "description": "Table centering may not account for content width properly",
                "fix": "Add validation to ensure table_x + table_width <= page_width - MARGIN",
                "code_location": "Line 272: table_x = (width - table_width) / 2"
            },
            {
                "issue": "Status card positioning",
                "description": "Status card may overlap with footer on page 2",
                "fix": "Add minimum footer clearance validation",
                "code_location": "Line 336: status_y = table_y - 120  # Add footer clearance check"
            },
            {
                "issue": "Multi-page content validation",
                "description": "No validation that all elements fit within their respective pages",
                "fix": "Add element bounds checking before drawing",
                "code_location": "Throughout gerar_pdf_municipal function"
            },
            {
                "issue": "Dynamic content sizing",
                "description": "Fixed heights may not accommodate varying data sizes",
                "fix": "Implement dynamic sizing based on data content",
                "code_location": "Graph and table height calculations"
            }
        ]


def main():
    """Example usage of the coordinate validator"""
    print("PDF Coordinate Validator - Municipal Dashboard Analysis")
    print("=" * 60)
    
    # Analyze the municipal PDF layout
    validator = PDFLayoutAnalyzer.analyze_municipal_pdf_layout()
    
    # Run validation
    results = validator.run_full_validation()
    
    # Print results
    print(f"Total Elements: {results['summary']['total_elements']}")
    print(f"Pages Used: {results['summary']['pages_used']}")
    print(f"Total Errors: {results['summary']['total_errors']}")
    print(f"Validation Passed: {results['summary']['validation_passed']}")
    
    print("\n--- Boundary Errors ---")
    for error in results['boundary_errors']:
        print(f"❌ {error}")
    
    print("\n--- Element Overlaps ---")
    for elem1, elem2, overlap_type in results['overlaps']:
        print(f"⚠️  {elem1} overlaps with {elem2} ({overlap_type})")
    
    print("\n--- Spacing Issues ---")
    for error in results['spacing_errors']:
        print(f"📏 {error}")
    
    print("\n--- Text Readability Issues ---")
    for error in results['text_readability_errors']:
        print(f"📖 {error}")
    
    # Export detailed report
    validator.export_validation_report("pdf_validation_report.json")
    print("\n✅ Detailed report exported to: pdf_validation_report.json")
    
    # Show recommended fixes
    print("\n--- Recommended Fixes ---")
    fixes = PDFLayoutAnalyzer.get_recommended_fixes()
    for i, fix in enumerate(fixes, 1):
        print(f"\n{i}. {fix['issue']}")
        print(f"   Description: {fix['description']}")
        print(f"   Fix: {fix['fix']}")
        print(f"   Location: {fix['code_location']}")


if __name__ == "__main__":
    main()