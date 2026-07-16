-- ============================================================
-- NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM
-- SPRINT 1 — DAY 7 EXPLORATORY QUERIES
-- ============================================================


-- ============================================================
-- QUERY 1: ROW COUNT FOR EVERY TABLE
-- ============================================================

SELECT 'companies' AS table_name, COUNT(*) AS row_count
FROM companies

UNION ALL

SELECT 'analysis', COUNT(*)
FROM analysis

UNION ALL

SELECT 'profitandloss', COUNT(*)
FROM profitandloss

UNION ALL

SELECT 'balancesheet', COUNT(*)
FROM balancesheet

UNION ALL

SELECT 'cashflow', COUNT(*)
FROM cashflow

UNION ALL

SELECT 'documents', COUNT(*)
FROM documents

UNION ALL

SELECT 'prosandcons', COUNT(*)
FROM prosandcons

UNION ALL

SELECT 'financial_ratios', COUNT(*)
FROM financial_ratios

UNION ALL

SELECT 'market_cap', COUNT(*)
FROM market_cap

UNION ALL

SELECT 'peer_groups', COUNT(*)
FROM peer_groups

UNION ALL

SELECT 'sectors', COUNT(*)
FROM sectors

UNION ALL

SELECT 'stock_prices', COUNT(*)
FROM stock_prices;


-- ============================================================
-- QUERY 2: COMPANY AND SECTOR DETAILS
-- ============================================================

SELECT
    c.id AS company_id,
    c.company_name,
    s.broad_sector,
    s.sub_sector,
    s.market_cap_category,
    s.index_weight_pct
FROM companies AS c
LEFT JOIN sectors AS s
    ON c.id = s.company_id
ORDER BY
    s.broad_sector,
    c.company_name;


-- ============================================================
-- QUERY 3: NUMBER OF COMPANIES IN EACH SECTOR
-- ============================================================

SELECT
    broad_sector,
    COUNT(DISTINCT company_id) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;


-- ============================================================
-- QUERY 4: COMPANIES WITHOUT SECTOR DATA
-- ============================================================

SELECT
    c.id AS company_id,
    c.company_name
FROM companies AS c
LEFT JOIN sectors AS s
    ON c.id = s.company_id
WHERE s.company_id IS NULL
ORDER BY c.id;


-- ============================================================
-- QUERY 5: TOP 10 COMPANIES BY 2024 MARKET CAPITALISATION
-- ============================================================

SELECT
    m.company_id,
    c.company_name,
    m.year,
    ROUND(m.market_cap_crore, 2) AS market_cap_crore,
    ROUND(m.enterprise_value_crore, 2) AS enterprise_value_crore,
    ROUND(m.pe_ratio, 2) AS pe_ratio
FROM market_cap AS m
JOIN companies AS c
    ON m.company_id = c.id
WHERE CAST(m.year AS TEXT) LIKE '%2024%'
ORDER BY m.market_cap_crore DESC
LIMIT 10;


-- ============================================================
-- QUERY 6: TOP 10 COMPANIES BY NET PROFIT IN FY 2024
-- ============================================================

SELECT
    p.company_id,
    c.company_name,
    p.year,
    ROUND(p.sales, 2) AS sales,
    ROUND(p.net_profit, 2) AS net_profit,
    ROUND(p.eps, 2) AS eps
FROM profitandloss AS p
JOIN companies AS c
    ON p.company_id = c.id
WHERE p.year IN ('Mar 2024', '2024')
ORDER BY p.net_profit DESC
LIMIT 10;


-- ============================================================
-- QUERY 7: TOP 10 COMPANIES BY SALES IN FY 2024
-- ============================================================

SELECT
    p.company_id,
    c.company_name,
    p.year,
    ROUND(p.sales, 2) AS sales,
    ROUND(p.operating_profit, 2) AS operating_profit,
    ROUND(p.opm_percentage, 2) AS opm_percentage
FROM profitandloss AS p
JOIN companies AS c
    ON p.company_id = c.id
WHERE p.year IN ('Mar 2024', '2024')
ORDER BY p.sales DESC
LIMIT 10;


-- ============================================================
-- QUERY 8: COMPANIES WITH THE HIGHEST BORROWINGS IN FY 2024
-- ============================================================

SELECT
    b.company_id,
    c.company_name,
    b.year,
    ROUND(b.borrowings, 2) AS borrowings,
    ROUND(b.total_liabilities, 2) AS total_liabilities,
    ROUND(b.total_assets, 2) AS total_assets
FROM balancesheet AS b
JOIN companies AS c
    ON b.company_id = c.id
WHERE b.year IN ('Mar 2024', '2024')
ORDER BY b.borrowings DESC
LIMIT 10;


-- ============================================================
-- QUERY 9: TOP COMPANIES BY RETURN ON EQUITY
-- ============================================================

SELECT
    f.company_id,
    c.company_name,
    f.year,
    ROUND(f.return_on_equity_pct, 2) AS return_on_equity_pct,
    ROUND(f.net_profit_margin_pct, 2) AS net_profit_margin_pct,
    ROUND(f.debt_to_equity, 2) AS debt_to_equity
FROM financial_ratios AS f
JOIN companies AS c
    ON f.company_id = c.id
WHERE CAST(f.year AS TEXT) LIKE '%2024%'
  AND f.return_on_equity_pct IS NOT NULL
ORDER BY f.return_on_equity_pct DESC
LIMIT 10;


-- ============================================================
-- QUERY 10: COMPANIES WITH HIGH DEBT-TO-EQUITY
-- ============================================================

SELECT
    f.company_id,
    c.company_name,
    f.year,
    ROUND(f.debt_to_equity, 2) AS debt_to_equity,
    ROUND(f.interest_coverage, 2) AS interest_coverage,
    ROUND(f.total_debt_cr, 2) AS total_debt_cr
FROM financial_ratios AS f
JOIN companies AS c
    ON f.company_id = c.id
WHERE CAST(f.year AS TEXT) LIKE '%2024%'
  AND f.debt_to_equity IS NOT NULL
ORDER BY f.debt_to_equity DESC
LIMIT 10;


-- ============================================================
-- QUERY 11: OPERATING, INVESTING AND FINANCING CASH FLOW
-- ============================================================

SELECT
    cf.company_id,
    c.company_name,
    cf.year,
    ROUND(cf.operating_activity, 2) AS operating_cash_flow,
    ROUND(cf.investing_activity, 2) AS investing_cash_flow,
    ROUND(cf.financing_activity, 2) AS financing_cash_flow,
    ROUND(cf.net_cash_flow, 2) AS net_cash_flow
FROM cashflow AS cf
JOIN companies AS c
    ON cf.company_id = c.id
WHERE cf.year IN ('Mar 2024', '2024')
ORDER BY cf.operating_activity DESC
LIMIT 20;


-- ============================================================
-- QUERY 12: COMPANIES WITH NEGATIVE OPERATING CASH FLOW
-- ============================================================

SELECT
    cf.company_id,
    c.company_name,
    cf.year,
    ROUND(cf.operating_activity, 2) AS operating_cash_flow,
    ROUND(cf.net_cash_flow, 2) AS net_cash_flow
FROM cashflow AS cf
JOIN companies AS c
    ON cf.company_id = c.id
WHERE cf.year IN ('Mar 2024', '2024')
  AND cf.operating_activity < 0
ORDER BY cf.operating_activity;


-- ============================================================
-- QUERY 13: FINANCIAL-STATEMENT YEAR COVERAGE
-- ============================================================

SELECT
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT
        CASE
            WHEN p.year NOT LIKE '%TTM%'
            THEN p.year
        END
    ) AS profit_loss_periods,
    COUNT(DISTINCT b.year) AS balance_sheet_periods,
    COUNT(DISTINCT cf.year) AS cashflow_periods
FROM companies AS c
LEFT JOIN profitandloss AS p
    ON c.id = p.company_id
LEFT JOIN balancesheet AS b
    ON c.id = b.company_id
LEFT JOIN cashflow AS cf
    ON c.id = cf.company_id
GROUP BY
    c.id,
    c.company_name
ORDER BY
    profit_loss_periods,
    balance_sheet_periods,
    cashflow_periods;


-- ============================================================
-- QUERY 14: COMPANIES WITH FEWER THAN 5 CASH-FLOW YEARS
-- ============================================================

SELECT
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT cf.year) AS available_years
FROM companies AS c
LEFT JOIN cashflow AS cf
    ON c.id = cf.company_id
GROUP BY
    c.id,
    c.company_name
HAVING COUNT(DISTINCT cf.year) < 5
ORDER BY available_years;


-- ============================================================
-- QUERY 15: COMPANIES WITHOUT SUPPORTING MARKET DATA
-- ============================================================

SELECT
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT f.id) AS ratio_rows,
    COUNT(DISTINCT m.id) AS market_cap_rows,
    COUNT(DISTINCT sp.id) AS stock_price_rows
FROM companies AS c
LEFT JOIN financial_ratios AS f
    ON c.id = f.company_id
LEFT JOIN market_cap AS m
    ON c.id = m.company_id
LEFT JOIN stock_prices AS sp
    ON c.id = sp.company_id
GROUP BY
    c.id,
    c.company_name
HAVING ratio_rows = 0
    OR market_cap_rows = 0
    OR stock_price_rows = 0
ORDER BY c.id;


-- ============================================================
-- QUERY 16: STOCK PRICE RANGE FOR EACH COMPANY
-- ============================================================

SELECT
    sp.company_id,
    c.company_name,
    MIN(sp.date) AS first_price_date,
    MAX(sp.date) AS last_price_date,
    COUNT(*) AS price_records,
    ROUND(MIN(sp.adjusted_close), 2) AS minimum_adjusted_close,
    ROUND(MAX(sp.adjusted_close), 2) AS maximum_adjusted_close
FROM stock_prices AS sp
JOIN companies AS c
    ON sp.company_id = c.id
GROUP BY
    sp.company_id,
    c.company_name
ORDER BY sp.company_id;


-- ============================================================
-- QUERY 17: FOREIGN KEY CHECK
-- ============================================================

PRAGMA foreign_key_check;


-- ============================================================
-- QUERY 18: DATABASE INTEGRITY CHECK
-- ============================================================

PRAGMA integrity_check;