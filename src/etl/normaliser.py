import re
import pandas as pd


def normalize_year(value):
    """
    Convert different year formats to a standardized 4-digit year.

    Examples:
        FY23        -> 2023
        FY2024      -> 2024
        2022-23     -> 2023
        2020-2021   -> 2021
        Mar 2023    -> 2023
        31-Mar-2024 -> 2024
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    # Handle formats like 2022-23
    match = re.search(r'(\d{4})-(\d{2})$', value)
    if match:
        return 2000 + int(match.group(2))

    # Handle formats like 2020-2021
    match = re.search(r'(\d{4})-(\d{4})$', value)
    if match:
        return int(match.group(2))

    # Find any standalone 4-digit year
    years = re.findall(r'\d{4}', value)
    if years:
        return int(years[-1])

    # Handle FY23, FY24, etc.
    match = re.search(r'(\d{2})$', value)
    if match:
        return 2000 + int(match.group(1))

    return None

def normalize_ticker(value):
    """
    Standardize stock ticker symbols.

    Examples:
        tcs       -> TCS
        TCS.NS    -> TCS
        infy.bo   -> INFY
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    value = value.replace(".NS", "")
    value = value.replace(".BO", "")

    return value