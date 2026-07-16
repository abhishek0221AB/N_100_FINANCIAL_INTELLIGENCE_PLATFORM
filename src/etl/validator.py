import re
import pandas as pd

from src.etl.normaliser import normalize_year, normalize_ticker
from pathlib import Path

class DataValidator:
    """
    Data Quality Validator

    Implements DQ-01 to DQ-16
    """

    def __init__(self):
        self.failures = []

    # ==========================================================
    # Helper Methods
    # ==========================================================

    def log_failure(
        self,
        rule_id,
        severity,
        dataset,
        column,
        message
    ):
        """
        Store validation failures.
        """

        self.failures.append({
            "rule_id": rule_id,
            "severity": severity,
            "dataset": dataset,
            "column": column,
            "message": message
        })

    def generate_report(self):
        """
        Return validation report with consistent columns,
        even when no failures are found.
        """

        columns = [
            "rule_id",
            "severity",
            "dataset",
            "column",
            "message",
        ]

        return pd.DataFrame(
            self.failures,
            columns=columns,
        )

    def save_report(self, filename="validation_failures.csv"):

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        report = self.generate_report()

        report_path = output_dir / filename

        report.to_csv(report_path, index=False)

        return report

    # ==========================================================
    # DQ-01
    # Company PK Uniqueness
    # ==========================================================

    def dq01_company_pk(self, companies):

        duplicates = companies[
            companies["id"].duplicated()
        ]

        for _, row in duplicates.iterrows():

            self.log_failure(
                rule_id="DQ-01",
                severity="CRITICAL",
                dataset="companies",
                column="id",
                message=f"Duplicate company id {row['id']}"
            )

    # ==========================================================
    # DQ-02
    # Annual PK Uniqueness
    # ==========================================================

    def dq02_annual_pk(self,dataframe,dataset_name):

        duplicate_groups = (
            dataframe
            .groupby(
                ["company_id", "year"],
                dropna=False
            )
            .size()
            .reset_index(name="row_count")
        )

        duplicate_groups = duplicate_groups[
            duplicate_groups["row_count"] > 1
        ]

        for _, row in duplicate_groups.iterrows():

            self.log_failure(
                rule_id="DQ-02",
                severity="CRITICAL",
                dataset=dataset_name,
                column="company_id, year",
                message=(
                    f"Duplicate key "
                    f"({row['company_id']}, {row['year']}) "
                    f"appears {row['row_count']} times"
                )
            )

    # ==========================================================
    # DQ-03
    # FK Integrity
    # ==========================================================

    def dq03_fk_integrity(
        self,
        child_df,
        companies_df,
        dataset_name
    ):

        valid_ids = set(companies_df["id"])

        invalid = child_df[
            ~child_df["company_id"].isin(valid_ids)
        ]

        for _, row in invalid.iterrows():

            self.log_failure(
                rule_id="DQ-03",
                severity="CRITICAL",
                dataset=dataset_name,
                column="company_id",
                message=f"Invalid company_id {row['company_id']}"
            )

    # ==========================================================
    # DQ-07
    # Year Format
    # ==========================================================

    def dq07_year_format(
        self,
        dataframe,
        dataset_name
    ):

        for idx, value in dataframe["year"].items():

            value_text = str(value).strip().upper()

            # TTM is a valid non-annual reporting period
            if value_text == "TTM":
                continue

            try:

                year = normalize_year(value)

                if year is None:

                    self.log_failure(
                        rule_id="DQ-07",
                        severity="CRITICAL",
                        dataset=dataset_name,
                        column="year",
                        message=f"Invalid year '{value}'"
                    )
            except Exception:

                self.log_failure(
                    rule_id="DQ-07",
                    severity="CRITICAL",
                    dataset=dataset_name,
                    column="year",
                    message=f"Unable to parse '{value}'"
                )

    # ==========================================================
    # DQ-08
    # Ticker Format
    # ==========================================================

    def dq08_ticker_format(
        self,
        dataframe,
        dataset_name,
        column_name="company_id"
    ):

        if column_name not in dataframe.columns:
            return

        for _, row in dataframe.iterrows():

            ticker = normalize_ticker(
                row[column_name]
            )

            if ticker is None:

                self.log_failure(
                    rule_id="DQ-08",
                    severity="CRITICAL",
                    dataset=dataset_name,
                    column=column_name,
                    message="Ticker is NULL"
                )

                continue

            if len(ticker) < 2 or len(ticker) > 12:

                self.log_failure(
                    rule_id="DQ-08",
                    severity="CRITICAL",
                    dataset=dataset_name,
                    column=column_name,
                    message=f"Invalid ticker '{ticker}'"
                )

            dataframe.at[
                row.name,
                column_name
            ] = ticker
    # ==========================================================
    # DQ-04
    # Balance Sheet Balance
    # ==========================================================

    def dq04_balance_sheet(self, balancesheet):

        for _, row in balancesheet.iterrows():

            assets = row["total_assets"]
            liabilities = row["total_liabilities"]

            if pd.isna(assets) or pd.isna(liabilities):
                continue

            if assets == 0:
                continue

            difference = abs(assets - liabilities) / assets

            if difference >= 0.01:

                self.log_failure(
                    rule_id="DQ-04",
                    severity="WARNING",
                    dataset="balancesheet",
                    column="total_assets,total_liabilities",
                    message=f"Assets ({assets}) and liabilities ({liabilities}) differ by {difference:.2%}"
                )

    # ==========================================================
    # DQ-05
    # OPM Cross Check
    # ==========================================================

    def dq05_opm(self, pnl):

        for _, row in pnl.iterrows():

            sales = row["sales"]
            operating_profit = row["operating_profit"]
            opm = row["opm_percentage"]

            if pd.isna(sales) or pd.isna(operating_profit) or pd.isna(opm):
                continue

            if sales == 0:
                continue

            calculated = (operating_profit / sales) * 100

            if abs(calculated - opm) >= 1:

                self.log_failure(
                    rule_id="DQ-05",
                    severity="WARNING",
                    dataset="profitandloss",
                    column="opm_percentage",
                    message=f"Expected {calculated:.2f} but found {opm:.2f}"
                )

    # ==========================================================
    # DQ-06
    # Positive Sales
    # ==========================================================

    def dq06_positive_sales(self, pnl):

        invalid = pnl[pnl["sales"] <= 0]

        for _, row in invalid.iterrows():

            self.log_failure(
                rule_id="DQ-06",
                severity="WARNING",
                dataset="profitandloss",
                column="sales",
                message=f"Sales is {row['sales']}"
            )

    # ==========================================================
    # DQ-09
    # Net Cash Check
    # ==========================================================

    def dq09_net_cash(self, cashflow):

        for _, row in cashflow.iterrows():

            cfo = row["operating_activity"]
            cfi = row["investing_activity"]
            cff = row["financing_activity"]
            net = row["net_cash_flow"]

            if (
                pd.isna(cfo)
                or pd.isna(cfi)
                or pd.isna(cff)
                or pd.isna(net)
            ):
                continue

            calculated = cfo + cfi + cff

            if abs(net - calculated) > 10:

                self.log_failure(
                    rule_id="DQ-09",
                    severity="WARNING",
                    dataset="cashflow",
                    column="net_cash_flow",
                    message=f"Expected {calculated} but found {net}"
                )

    # ==========================================================
    # DQ-10
    # Non-Negative Fixed Assets
    # ==========================================================

    def dq10_fixed_assets(self, balancesheet):

        invalid = balancesheet[
            balancesheet["fixed_assets"] < 0
        ]

        for _, row in invalid.iterrows():

            self.log_failure(
                rule_id="DQ-10",
                severity="WARNING",
                dataset="balancesheet",
                column="fixed_assets",
                message=f"Negative value {row['fixed_assets']}"
            )

    # ==========================================================
    # DQ-11
    # Tax Percentage
    # ==========================================================

    def dq11_tax_percentage(self, pnl):

        invalid = pnl[
            (pnl["tax_percentage"] < 0)
            | (pnl["tax_percentage"] > 60)
        ]

        for _, row in invalid.iterrows():

            self.log_failure(
                rule_id="DQ-11",
                severity="WARNING",
                dataset="profitandloss",
                column="tax_percentage",
                message=f"Invalid tax percentage {row['tax_percentage']}"
            )

    # ==========================================================
    # DQ-12
    # Dividend Payout
    # ==========================================================

    def dq12_dividend(self, pnl):

        invalid = pnl[
            pnl["dividend_payout"] > 200
        ]

        for _, row in invalid.iterrows():

            self.log_failure(
                rule_id="DQ-12",
                severity="WARNING",
                dataset="profitandloss",
                column="dividend_payout",
                message=f"Dividend payout {row['dividend_payout']}"
            )

    # ==========================================================
    # DQ-14
    # EPS Sign Consistency
    # ==========================================================

    def dq14_eps(self, pnl):

        invalid = pnl[
            (pnl["net_profit"] > 0)
            & (pnl["eps"] <= 0)
        ]

        for _, row in invalid.iterrows():

            self.log_failure(
                rule_id="DQ-14",
                severity="WARNING",
                dataset="profitandloss",
                column="eps",
                message=f"Net profit={row['net_profit']} EPS={row['eps']}"
            )
    # ==========================================================
    # DQ-13
    # Annual Report URL Validation
    # ==========================================================

    # def dq13_document_urls(self, documents):

    #     try:
    #         import requests
    #     except ImportError:
    #         return

    #     for _, row in documents.iterrows():

    #         url = row["Annual_Report"]

    #         if pd.isna(url):
    #             continue

    #         try:

    #             response = requests.head(
    #                 url,
    #                 timeout=5,
    #                 allow_redirects=True
    #             )

    #             if response.status_code != 200:

    #                 self.log_failure(
    #                     rule_id="DQ-13",
    #                     severity="WARNING",
    #                     dataset="documents",
    #                     column="Annual_Report",
    #                     message=f"HTTP {response.status_code}: {url}"
    #                 )

    #         except Exception:

    #             self.log_failure(
    #                 rule_id="DQ-13",
    #                 severity="WARNING",
    #                 dataset="documents",
    #                 column="Annual_Report",
    #                 message=f"Unable to access {url}"
    #             )
    def dq13_document_urls(self, documents):

        url_pattern = re.compile(r"^https?://")

        for _, row in documents.iterrows():

            url = row["Annual_Report"]

            if pd.isna(url):
                continue

            if not url_pattern.match(str(url)):
                self.log_failure(
                        rule_id="DQ-13",
                        severity="WARNING",
                        dataset="documents",
                        column="Annual_Report",
                        message=f"Invalid URL format: {url}"
                )   

    # ==========================================================
    # DQ-15
    # Informational Balance Check
    # ==========================================================

    def dq15_balance_info(self, balancesheet):

        for _, row in balancesheet.iterrows():

            assets = row["total_assets"]
            liabilities = row["total_liabilities"]

            if pd.isna(assets) or pd.isna(liabilities):
                continue

            if assets != liabilities:

                self.log_failure(
                    rule_id="DQ-15",
                    severity="INFO",
                    dataset="balancesheet",
                    column="total_assets,total_liabilities",
                    message=f"{assets} != {liabilities}"
                )

    # ==========================================================
    # DQ-16
    # Coverage Check
    # ==========================================================

    def dq16_coverage(
        self,
        balancesheet,
        cashflow,
        profitandloss
    ):

        bs = balancesheet.groupby("company_id").size()
        cf = cashflow.groupby("company_id").size()
        pnl = profitandloss.groupby("company_id").size()

        company_ids = (
            set(bs.index)
            | set(cf.index)
            | set(pnl.index)
        )

        for company in company_ids:

            bs_count = bs.get(company, 0)
            cf_count = cf.get(company, 0)
            pnl_count = pnl.get(company, 0)

            minimum = min(
                bs_count,
                cf_count,
                pnl_count
            )

            if minimum < 5:

                self.log_failure(
                    rule_id="DQ-16",
                    severity="WARNING",
                    dataset="financials",
                    column="company_id",
                    message=(
                        f"{company} has "
                        f"{minimum} years of history"
                    )
                )

    # ==========================================================
    # Run All Rules
    # ==========================================================

    def validate_all(self, datasets):

        companies = datasets["companies"]
        balancesheet = datasets["balancesheet"]
        cashflow = datasets["cashflow"]
        profitandloss = datasets["profitandloss"]
        documents = datasets["documents"]

        # ------------------------
        # Critical Rules
        # ------------------------
        print("DQ01")
        self.dq01_company_pk(companies)

        print("DQ02 BS")
        self.dq02_annual_pk(
            balancesheet,
            "balancesheet"
        )
        print("DQ02 CF")
        self.dq02_annual_pk(
            cashflow,
            "cashflow"
        )
        print("DQ02 PNL")
        self.dq02_annual_pk(
            profitandloss,
            "profitandloss"
        )
        print("DQ03 BS")
        self.dq03_fk_integrity(
            balancesheet,
            companies,
            "balancesheet"
        )
        print("DQ03 CF")
        self.dq03_fk_integrity(
            cashflow,
            companies,
            "cashflow"
        )
        print("DQ03 PNL")
        self.dq03_fk_integrity(
            profitandloss,
            companies,
            "profitandloss"
        )
        print("DQ03 DOC")
        self.dq03_fk_integrity(
            documents,
            companies,
            "documents"
        )
        print("DQ07 BS")
        self.dq07_year_format(
            balancesheet,
            "balancesheet"
        )
        print("DQ07 CF")
        self.dq07_year_format(
            cashflow,
            "cashflow"
        )
        print("DQ07 PNL")
        self.dq07_year_format(
            profitandloss,
            "profitandloss"
        )
        print("DQ08 BS")
        self.dq08_ticker_format(
            balancesheet,
            "balancesheet"
        )
        print("DQ08 CF")
        self.dq08_ticker_format(
            cashflow,
            "cashflow"
        )
        print("DQ08 PNL")
        self.dq08_ticker_format(
            profitandloss,
            "profitandloss"
        )

        print("DQ08 DOC")
        self.dq08_ticker_format(
            documents,
            "documents"
        )

        # ------------------------
        # Warning Rules
        # ------------------------
        print("DQ04")
        self.dq04_balance_sheet(
            balancesheet
        )

        print("DQ05")
        self.dq05_opm(
            profitandloss
        )

        print("DQ06")
        self.dq06_positive_sales(
            profitandloss
        )

        print("DQ09")
        self.dq09_net_cash(
            cashflow
        )

        print("DQ10")
        self.dq10_fixed_assets(
            balancesheet
        )

        print("DQ11")
        self.dq11_tax_percentage(
            profitandloss
        )

        print("DQ12")
        self.dq12_dividend(
            profitandloss
        )

        print("DQ13")
        self.dq13_document_urls(
            documents
        )

        print("DQ14")
        self.dq14_eps(
            profitandloss
        )

        print("DQ15")
        self.dq15_balance_info(
            balancesheet
        )

        print("DQ16")
        self.dq16_coverage(
            balancesheet,
            cashflow,
            profitandloss
        )

        return self.generate_report()
# ==========================================================
# Standalone Validator Runner
# ==========================================================

RAW_PATH = Path("data/raw")
OUTPUT_PATH = Path("output")


def load_validation_datasets():
    """
    Load the seven core Excel datasets without modifying
    the original company-provided files.
    """

    dataset_names = [
        "companies",
        "analysis",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "prosandcons",
    ]

    datasets = {}

    for dataset_name in dataset_names:

        file_path = RAW_PATH / f"{dataset_name}.xlsx"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required file not found: {file_path}"
            )

        datasets[dataset_name] = pd.read_excel(file_path)

    return datasets


def prepare_validation_scope(datasets):
    """
    Normalize tickers and limit child datasets to the approved
    92-company master universe.

    Out-of-scope source rows are already documented separately
    by loader.py in output/out_of_scope_rows.csv.
    """

    companies = datasets["companies"].copy()

    companies["id"] = (
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    valid_company_ids = set(companies["id"])

    ticker_map = {
        "AGTL": "ATGL",
    }

    prepared = {
        "companies": companies,
    }

    for dataset_name, dataframe in datasets.items():

        if dataset_name == "companies":
            continue

        df = dataframe.copy()

        if "company_id" in df.columns:

            df["company_id"] = (
                df["company_id"]
                .astype(str)
                .str.strip()
                .str.upper()
                .replace(ticker_map)
            )

            df = df[
                df["company_id"].isin(valid_company_ids)
            ].copy()
        
                # Remove exact duplicate source rows, ignoring the row ID.
        if dataset_name in {
            "profitandloss",
            "balancesheet",
            "cashflow",
        }:

            comparison_columns = [
                column
                for column in df.columns
                if column != "id"
            ]

            df = df.drop_duplicates(
                subset=comparison_columns,
                keep="first",
            ).copy()

        # Remove the known mislabeled ABB cash-flow block.
        if dataset_name == "cashflow":

            source_error_mask = (
                df["company_id"].eq("ABB")
                & df["id"].between(73, 83)
            )

            df = df[
                ~source_error_mask
            ].copy()

        prepared[dataset_name] = df

    return prepared


def main():

    print("=" * 70)
    print("SPRINT 1 — DATA QUALITY VALIDATION")
    print("=" * 70)

    datasets = load_validation_datasets()

    datasets = prepare_validation_scope(datasets)

    validator = DataValidator()

    report = validator.validate_all(datasets)

    OUTPUT_PATH.mkdir(exist_ok=True)

    report_path = OUTPUT_PATH / "validation_failures.csv"

    report.to_csv(
        report_path,
        index=False,
    )

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(f"Total failures: {len(report)}")

    if report.empty:

        print("No validation failures found.")

    else:

        summary = (
            report.groupby(
                ["rule_id", "severity"]
            )
            .size()
            .reset_index(name="failure_count")
        )

        print(summary.to_string(index=False))

        critical_count = len(
            report[
                report["severity"]
                .astype(str)
                .str.upper()
                .eq("CRITICAL")
            ]
        )

        print(f"\nCRITICAL failures: {critical_count}")

    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()