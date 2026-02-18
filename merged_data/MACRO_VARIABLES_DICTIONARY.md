# Macroeconomic Variables Data Dictionary

## New Variables Added to HDB Resale Dataset

### 1. sora_3m
**Description**: 3-Month Compounded Singapore Overnight Rate Average (SORA)  
**Units**: Percentage (%)  
**Calculation**: End-of-quarter value from daily 3-month compounded SORA  
**Source**: Monetary Authority of Singapore (MAS)  
**Expected Range**: 0.1% to 4.0%  
**Notes**: 
- This is the benchmark interest rate for housing loans in Singapore
- Each daily value is already a 3-month backward-looking compounded average
- We use the LAST trading day of each quarter as the representative value

### 2. inflation_yoy
**Description**: Year-over-year inflation rate based on HDB Resale Price Index (RPI)  
**Units**: Percentage (%)  
**Calculation**: `((RPI_current_quarter - RPI_same_quarter_last_year) / RPI_same_quarter_last_year) * 100`  
**Source**: Derived from HDB Resale Price Index  
**Expected Range**: -2% to 5%  
**Notes**:
- First 4 quarters (2017 Q1-Q4) have NaN values (no prior year for comparison)
- Uses housing-specific price index (RPI) rather than general CPI
- Negative values indicate deflation in housing prices

### 3. real_interest_rate
**Description**: Real interest rate adjusted for inflation  
**Units**: Percentage (%)  
**Calculation**: `sora_3m - inflation_yoy`  
**Expected Range**: -3% to 5%  
**Notes**:
- Represents the true cost of borrowing after accounting for inflation
- Negative values indicate that inflation exceeds nominal interest rates
- More economically meaningful than nominal rates for housing affordability

### 4. sora_3m_lag1
**Description**: Previous quarter's 3-month compounded SORA  
**Units**: Percentage (%)  
**Calculation**: Lag-1 shift of sora_3m  
**Notes**:
- First quarter (2017 Q1) has NaN value
- Captures lagged effect of interest rates on housing prices
- Housing prices typically respond to interest rate changes with 1-3 quarter delay

### 5. real_interest_rate_lag1
**Description**: Previous quarter's real interest rate  
**Units**: Percentage (%)  
**Calculation**: Lag-1 shift of real_interest_rate  
**Notes**:
- First 5 quarters have NaN values (needs both inflation and lag)
- Captures lagged real borrowing cost effect

## Usage Guidelines for Modeling

### For Linear Regression / Hedonic Models:
**Recommended**: Use `real_interest_rate` OR `real_interest_rate_lag1` (NOT both, and NOT with sora_3m or inflation_yoy)

**Rationale**: Avoid multicollinearity
- real_interest_rate = sora_3m - inflation_yoy (perfect mathematical relationship)
- Including multiple related variables causes unstable coefficients

**Example feature set**:
```python
features_linear = ['floor_area_sqm', 'storey_range', 'town', 'real_interest_rate']
```

### For Random Forest / Tree-Based Models:
**Recommended**: Use ALL macro variables

**Rationale**: Let the model select the most predictive features
- Tree-based models handle multicollinearity well
- Can discover which lag period is most predictive

**Example feature set**:
```python
features_rf = ['floor_area_sqm', 'storey_range', 'town', 
               'sora_3m', 'sora_3m_lag1', 'inflation_yoy', 
               'real_interest_rate', 'real_interest_rate_lag1']
```

### For Neural Networks:
**Recommended**: Use ALL macro variables (network can learn relationships)

## Expected Missing Value Patterns

| Variable | Expected NaN Count | Affected Quarters | Reason |
|----------|-------------------|-------------------|--------|
| sora_3m | 0 | None | SORA data available for all quarters |
| inflation_yoy | 4 quarters worth | 2017 Q1-Q4 | Need prior year for YoY calculation |
| real_interest_rate | 4 quarters worth | 2017 Q1-Q4 | Depends on inflation_yoy |
| sora_3m_lag1 | 1 quarter worth | 2017 Q1 | First quarter has no prior |
| real_interest_rate_lag1 | 5 quarters worth | 2017 Q1-2018 Q1 | Combines inflation + lag |

## Data Quality Checks Performed

1. Value ranges within expected bounds
2. No gaps in quarterly coverage (2017 Q1 onwards)
3. Consistent merge with transaction data
4. Correlation matrix validated
5. Temporal consistency (no future data leakage)

## References

- SORA: https://www.mas.gov.sg/monetary-policy/sora
- HDB Resale Price Index: https://data.gov.sg/

## Version History

- v1.0 (2025-02): Initial creation with 5 macro variables
