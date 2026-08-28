from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from ftfy import fix_text


DATA_PATH = Path("data/cars.xlsx")
CLEANED_SHEET = "cleaned dataset"


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = html.unescape(str(value))
    text = fix_text(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def json_safe_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            return None

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def parse_number(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    match = re.search(r"\d[\d,\s]*", text)

    if not match:
        return None

    digits = re.sub(r"[,\s]", "", match.group())

    try:
        return int(digits)
    except ValueError:
        return None


def extract_price(text: str) -> Optional[int]:
    """
    Extract a cash/listed AED price.

    Monthly finance values are deliberately ignored:
    - AED 5,805/mo
    - AED 2,340 monthly
    - AED 1,611 per month
    - AED 713/month
    """

    monthly_pattern = re.compile(
        r"""
        (?:aed|د\.إ)?\s*
        [\d,\s]+
        \s*
        (?:
            /?\s*mo(?:nth)?s?
            |monthly
            |per\s+month
            |p\.?\s*m\.?
        )
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    cleaned_text = monthly_pattern.sub(" ", text)

    cash_patterns = [
        r"""
        (?:selling\s+price|cash\s+price)
        \s*[:\-]?\s*
        (?:aed|د\.إ)?
        \s*
        ([\d,\s]{4,})
        """,
        r"""
        selling\s+price
        \s*[:\-]?\s*
        ([\d,\s]{4,})
        \s*
        (?:aed|د\.إ)
        """,
        r"""
        (?:aed|د\.إ)
        \s*
        ([\d,]{4,})
        (?!\s*(?:/|monthly|per\s+month|p\.?\s*m\.?))
        """,
        r"""
        ([\d,]{4,})
        \s*
        (?:aed|د\.إ)
        (?!\s*(?:/|monthly|per\s+month|p\.?\s*m\.?))
        """,
    ]

    for pattern in cash_patterns:
        matches = re.findall(
            pattern,
            cleaned_text,
            flags=re.IGNORECASE | re.VERBOSE,
        )

        for value in matches:
            number = parse_number(value)

            if number and 3_000 <= number <= 10_000_000:
                return number

    return None


def extract_mileage(text: str) -> Optional[int]:
    """
    Extract mileage while supporting:
    - 23,900 km
    - 23 900 kms
    - 23900 km
    - Mileage: 23 900 kms
    """

    patterns = [
        r"""
        (?:mileage|odometer)
        \s*[:\-]?\s*
        ([\d][\d,\s]*)
        \s*
        (?:km|kms)
        """,
        r"""
        ([\d][\d,\s]*)
        \s*
        (?:km|kms)
        """,
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE | re.VERBOSE,
        )

        for value in matches:
            number = parse_number(value)

            if number is not None and 0 <= number <= 1_000_000:
                return number

    return None


class InventoryService:
    def __init__(
        self,
        path: Path = DATA_PATH,
        sheet_name: str = CLEANED_SHEET,
    ):
        self.path = path
        self.sheet_name = sheet_name
        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {self.path.resolve()}"
            )

        workbook = pd.ExcelFile(self.path)

        if self.sheet_name not in workbook.sheet_names:
            raise ValueError(
                f"Sheet '{self.sheet_name}' not found. "
                f"Available sheets: {workbook.sheet_names}"
            )

        print(f"Using Excel sheet: {self.sheet_name}")

        df = pd.read_excel(
            self.path,
            sheet_name=self.sheet_name,
        )

        df.columns = [
            str(column)
            .strip()
            .lower()
            .replace(" ", "_")
            for column in df.columns
        ]

        df = df.rename(
            columns={
                "listingid": "listing_id",
                "photourl": "photo_url",
            }
        )

        required_columns = [
            "listing_id",
            "year",
            "make",
            "model",
            "trim",
            "title",
            "description",
            "photo_url",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing columns: {missing_columns}. "
                f"Found columns: {list(df.columns)}"
            )

        df["listing_id"] = pd.to_numeric(
            df["listing_id"],
            errors="raise",
        ).astype(int)

        df["year"] = pd.to_numeric(
            df["year"],
            errors="raise",
        ).astype(int)

        for column in [
            "make",
            "model",
            "trim",
            "title",
            "description",
            "photo_url",
        ]:
            df[column] = df[column].apply(clean_text)

        if df["listing_id"].duplicated().any():
            raise ValueError(
                "Duplicate Listing_ID values found."
            )

        df["search_text"] = (
            df[
                [
                    "make",
                    "model",
                    "trim",
                    "title",
                    "description",
                ]
            ]
            .astype(str)
            .agg(" ".join, axis=1)
            .str.lower()
        )

        df["price_aed"] = df["search_text"].apply(
            extract_price
        )

        df["mileage_km"] = df["search_text"].apply(
            extract_mileage
        )

        print(f"Loaded listings: {len(df)}")

        return df

    @staticmethod
    def _safe_records(
        records: list[dict],
    ) -> list[dict]:
        return [
            {
                key: json_safe_value(value)
                for key, value in record.items()
            }
            for record in records
        ]

    @staticmethod
    def _split_keywords(keywords: str) -> list[str]:
        normalized = keywords.replace(";", ",")
        parts = re.split(r",|\s{2,}", normalized)

        return [
            part.strip().lower()
            for part in parts
            if part.strip()
        ]

    def search(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        keywords: Optional[str] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        max_price: Optional[int] = None,
        limit: int = 5,
    ) -> list[dict]:
        results = self.df.copy()

        if make:
            results = results[
                results["make"].str.contains(
                    re.escape(make.strip()),
                    case=False,
                    na=False,
                )
            ]

        if model:
            results = results[
                results["model"].str.contains(
                    re.escape(model.strip()),
                    case=False,
                    na=False,
                )
            ]

        if min_year is not None:
            results = results[
                results["year"] >= min_year
            ]

        if max_year is not None:
            results = results[
                results["year"] <= max_year
            ]

        if max_price is not None:
            results = results[
                results["price_aed"].notna()
                & (
                    results["price_aed"]
                    <= max_price
                )
            ]

        if keywords:
            keyword_list = self._split_keywords(keywords)

            for keyword in keyword_list:
                results = results[
                    results["search_text"].str.contains(
                        re.escape(keyword),
                        case=False,
                        na=False,
                    )
                ]

        safe_limit = max(
            1,
            min(int(limit), 10),
        )

        columns = [
            "listing_id",
            "year",
            "make",
            "model",
            "trim",
            "title",
            "description",
            "photo_url",
            "price_aed",
            "mileage_km",
        ]

        results = results.head(safe_limit)

        records = results[columns].to_dict(
            orient="records"
        )

        return self._safe_records(records)

    def get_listing(
        self,
        listing_id: int,
    ) -> Optional[dict]:
        result = self.df[
            self.df["listing_id"] == listing_id
        ]

        if result.empty:
            return None

        record = result.iloc[0][
            [
                "listing_id",
                "year",
                "make",
                "model",
                "trim",
                "title",
                "description",
                "photo_url",
                "price_aed",
                "mileage_km",
            ]
        ].to_dict()

        return self._safe_records(
            [record]
        )[0]

    def available_makes(self) -> list[str]:
        return sorted(
            {
                str(value).strip()
                for value in self.df["make"].unique()
                if str(value).strip()
            }
        )

    def available_models(self) -> list[str]:
        return sorted(
            {
                str(value).strip()
                for value in self.df["model"].unique()
                if str(value).strip()
            }
        )


inventory_service = InventoryService()