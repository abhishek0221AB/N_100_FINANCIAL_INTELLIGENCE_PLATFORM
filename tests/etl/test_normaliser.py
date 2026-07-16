import pytest

from src.etl.normaliser import normalize_year, normalize_ticker


@pytest.mark.parametrize(
    "value, expected",
    [
        ("FY23", 2023),
        ("FY24", 2024),
        ("FY25", 2025),
        ("FY2023", 2023),
        ("FY 2024", 2024),
        ("2022-23", 2023),
        ("2023-24", 2024),
        ("2020-2021", 2021),
        ("31-Mar-2024", 2024),
        ("Mar 2025", 2025),
        ("2023", 2023),
        (2022, 2022),
        ("FY99", 2099),
        (None, None),
        ("", None),
        ("ABC", None),
        ("FY01", 2001),
        ("2018-19", 2019),
        ("2015-2016", 2016),
        ("FY 2020", 2020),
    ],
)
def test_normalize_year(value, expected):
    assert normalize_year(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("tcs", "TCS"),
        ("TCS", "TCS"),
        ("TCS.NS", "TCS"),
        ("tcs.ns", "TCS"),
        ("INFY.BO", "INFY"),
        (" infy.bo ", "INFY"),
        ("RELIANCE", "RELIANCE"),
        (" reliance ", "RELIANCE"),
        ("HDFCBANK.NS", "HDFCBANK"),
        ("SBIN.BO", "SBIN"),
        ("LT", "LT"),
        ("lt", "LT"),
        ("abc.ns", "ABC"),
        ("xyz.bo", "XYZ"),
        ("ABC", "ABC"),
        ("  ABC  ", "ABC"),
        ("", ""),
        (None, None),
        ("M&M.NS", "M&M"),
        ("BAJAJ-AUTO.BO", "BAJAJ-AUTO"),
    ],
)
def test_normalize_ticker(value, expected):
    assert normalize_ticker(value) == expected