# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an ACS (Agentes Comunitários de Saúde / Community Health Agents) analytics system built with Streamlit. The application provides comprehensive dashboards for analyzing Brazilian health data from the Ministry of Health APIs, specifically focusing on community health agents' metrics and financial transfers.

## Common Development Commands

### Environment Setup
```bash
# Activate virtual environment (Windows)
venv_acs\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Main dashboard (comprehensive multi-competency analysis)
streamlit run app.py

# Alternative dashboard (single competency analysis with debug features)
streamlit run dashboard_acs.py
```

### Dependencies
Core packages (from requirements.txt):
- `streamlit` - Web application framework
- `requests` - HTTP API calls to Ministry of Health
- `pandas` - Data manipulation and analysis
- `plotly` - Interactive visualizations

## Architecture Overview

### Core Components

1. **Main Applications**
   - `app.py` - Primary Streamlit dashboard with comprehensive multi-competency analysis
   - `dashboard_acs.py` - Alternative dashboard with single competency analysis and debug features

2. **API Layer**
   - `saude_api.py` - Wrapper for Ministry of Health APIs
     - UF/municipality data retrieval
     - Available time periods (competencias)
     - Standardized headers for API calls

3. **Data Processing**
   - `acs_analyzer.py` - Core ACS metrics extraction and calculations
     - Extracts 6 key ACS metrics from API responses
     - Handles both detailed and budget-only data formats
     - Calculates financial efficiency and loss metrics
   
   - `competencias_manager.py` - Multi-period data management
     - Batch queries across multiple time periods
     - Data consolidation and temporal analysis
     - Progress tracking for long-running operations

4. **Data Models**
   - `ACSMetrics` - Main metrics dataclass with 6 key indicators
   - `ACSDetalhePeriodo` - Time-series data structure
   - `CompetenciaData` - Individual period query results

### Key Metrics (The 6 Main ACS Indicators)

The system focuses on these 6 core metrics for Community Health Agents:

1. **quantidade_teto** - Maximum approved ACS limit
2. **quantidade_credenciado** - Total credentialed ACS (direct + indirect)
3. **quantidade_pago** - Total ACS who received payment
4. **total_deveria_receber** - Expected federal transfer amount
5. **total_recebido** - Actual federal transfer received
6. **total_perda** - Loss in federal transfers (difference between expected and received)

### API Integration

The system integrates with the Brazilian Ministry of Health APIs:
- Base URL: `https://relatorioaps-prd.saude.gov.br`
- Main endpoints: `/ibge/municipios`, `/data/parcelas`, `/financiamento/pagamento`
- Requires specific headers mimicking browser requests
- Data covers periods from 2020-2025 (Jan-Jul for 2025)

### Data Flow

1. User selects UF (state) and municipality via dropdown
2. System queries available time periods (competencias)
3. For comprehensive analysis: batch queries across multiple periods
4. Data extraction focuses on ACS-related fields in API responses
5. Metrics calculation and aggregation
6. Visualization through interactive Plotly charts
7. Export capabilities (CSV, JSON)

## Development Notes

### API Data Structure
- ACS data is primarily in the `pagamentos` section of API responses
- Key fields start with `qtTetoAcs`, `qtAcsDirecto*`, `qtAcsIndireto*`, `vlTotalAcs*`
- Fallback to `resumosPlanosOrcamentarios` for budget-only data when detailed data unavailable

### Error Handling
- Graceful degradation when API calls fail
- Handles both detailed quantitative data and budget-only responses
- Progress bars and status updates for long-running operations

### Testing
- Use municipality "Abaré/PE" (Pernambuco) for testing - confirmed to have ACS data
- Test period: 2025/06 (June 2025) has reliable data for most municipalities

### UI/UX Patterns
- Color-coded metric cards (green/yellow/red based on performance thresholds)
- Multi-column layouts for dashboard organization
- Expandable sections for technical details
- Download buttons for data export

## Additional Technical Details

### Application Architecture Patterns

The codebase follows a clear separation of concerns:

1. **API Layer** (`saude_api.py`): Pure API wrapper with static methods and standardized headers
2. **Data Processing** (`acs_analyzer.py`): Functional approach with static methods for data extraction and transformation
3. **Business Logic** (`competencias_manager.py`): Orchestrates multi-period queries and data consolidation
4. **Presentation Layer** (`app.py`, `dashboard_acs.py`): Streamlit-based UI with visualization logic

### Key Data Transformations

1. **API Response Parsing**: Prioritizes `pagamentos` section over `resumosPlanosOrcamentarios` for detailed ACS data
2. **Metric Calculation**: Derives 6 core metrics from raw API fields using consistent business logic
3. **Temporal Aggregation**: Consolidates multi-competency data for trend analysis
4. **Financial Calculations**: Estimates expected transfers based on actual payment ratios

### Error Handling Strategy

- **Graceful Degradation**: Falls back to budget-only data when detailed metrics unavailable
- **Progress Tracking**: Real-time status updates for long-running multi-competency queries
- **Data Validation**: Checks for presence of ACS-specific fields before processing
- **User Feedback**: Clear error messages and suggestions for data availability issues

### Performance Considerations

- Uses Streamlit's `@st.cache_data` decorator for API responses
- Implements request throttling (0.5s delays) to respect API rate limits
- Batches competency queries to minimize API calls
- Local UF data to avoid unnecessary API requests

### Development Workflow

1. **Data Exploration**: Use `dashboard_acs.py` for debugging single competencies
2. **Production Analysis**: Use `app.py` for comprehensive multi-period reports
3. **Testing**: Municipality "Abaré/PE" with competency "202506" has confirmed ACS data
4. **API Headers**: Critical for API access - maintains browser-like request signature