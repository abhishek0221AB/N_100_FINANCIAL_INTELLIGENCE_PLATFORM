# Sprint 2 Retrospective — Financial Ratio Engine

## Sprint Goal

Compute 50+ financial KPIs across all 92 approved companies and populate the `financial_ratios` table with more than 1,100 company-year rows.

## Completed Work

- Implemented profitability ratios:
  - Net Profit Margin
  - Operating Profit Margin
  - ROE
  - ROCE
  - ROA
- Implemented leverage and efficiency ratios:
  - Debt-to-Equity
  - Interest Coverage
  - Net Debt
  - Asset Turnover
- Implemented CAGR engine:
  - Revenue CAGR
  - PAT CAGR
  - EPS CAGR
  - 3-year, 5-year and 10-year windows
- Implemented six CAGR edge-case flags:
  - VALID
  - DECLINE_TO_LOSS
  - TURNAROUND
  - BOTH_NEGATIVE
  - ZERO_BASE
  - INSUFFICIENT
- Implemented cash-flow KPIs:
  - Free Cash Flow
  - CFO/PAT quality
  - CapEx intensity
  - FCF conversion
- Implemented all eight capital-allocation patterns.
- Populated `financial_ratios` with 1,164 rows and 36 columns.
- Generated `output/capital_allocation.csv`.
- Generated `output/ratio_edge_cases.log`.
- Verified the Financials-sector leverage carve-out.

## Formula Decisions

- ROE uses:
  `net_profit / (equity_capital + reserves) × 100`
- ROCE uses:
  `(profit_before_tax + interest) / (equity + reserves + borrowings) × 100`
- Debt-to-Equity returns `0` for debt-free companies.
- Interest Coverage returns `None` when interest expense is zero and displays `Debt Free`.
- Free Cash Flow uses:
  `operating_activity + investing_activity`
- Book value per share uses:
  `(equity_capital + reserves) / equity_capital`
- Financial-sector companies are excluded from the standard high-leverage warning.

## Edge Cases Resolved

- Negative or zero equity returns `None` for ROE.
- Zero sales returns `None` for margin calculations.
- Zero total assets returns `None` for ROA and Asset Turnover.
- TTM and interim rows are handled separately from annual CAGR calculations.
- CAGR turnaround, decline-to-loss, both-negative and zero-base cases are flagged instead of producing misleading values.
- Financial-sector leverage is treated differently because high leverage is structurally normal.
- Source ROE and ROCE anomalies are retained for display but computed ratios are used for analytics.

## Data and Documentation Findings

- Sector data contains 23 Financials companies, while the task document mentions 19.
- 42 ROE/ROCE anomalies were documented.
- 36 anomalies were categorised as formula discrepancies.
- 6 anomalies were categorised as source-data issues.
- No Financials-sector company was incorrectly flagged for high leverage.

## Testing Results

- 83 total unit tests passed.
- 0 test failures.
- `financial_ratios` contains 1,164 rows.
- 92 companies are covered.
- 36 ratio columns are populated.
- No null-only columns exist.
- Foreign-key violations: 0.
- Database integrity: `ok`.

## Sprint Outcome

Sprint 2 technical implementation is complete. Final sign-off requires team-lead review of the ratio table, edge-case log, screener preview and three-company manual spot-check.

## Extreme ROE Source-Scale Finding

The latest ratios for BEL, HAL and INDIGO produced ROE values above 200%.

Direct recalculation confirmed that the ratio engine correctly applied:

`net_profit / (equity_capital + reserves) × 100`

However, the P&L and balance-sheet values appear to use incompatible units or scales for these companies. No speculative scaling correction was applied.

These records were:

- Retained in the database
- Documented as `DATA_SOURCE_ISSUE`
- Added to `output/ratio_edge_cases.log`
- Excluded from the standard screener using an ROE upper-bound filter of 200%

After adding the extreme-value checks, the final anomaly summary was:

- Total anomalies: 45
- Formula discrepancies: 36
- Data-source issues: 9
- Financial-sector leverage violations: 0