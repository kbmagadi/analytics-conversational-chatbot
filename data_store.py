# chatbot/data_store.py
import pandas as pd
from pathlib import Path
from datetime import timedelta
from causal_graph import CausalGraph 
from functools import lru_cache

class MetricsStore:
    """
    Single source of truth for metric data.
    Backed by a Pandas DataFrame (MVP).
    """
    def __init__(self, data_path: str = "data/sales.csv"):
        self.data_path = Path(data_path)
        self.df = self._load_data()
        self.latest_date = self.df["date"].max()
        self.graph = CausalGraph()

    @lru_cache(maxsize=256)
    def get_value(self, metric: str, period: str) -> float:
        date = self._resolve_period(period)
        row = self.df[self.df["date"] == date]
        
        if row.empty:
            raise ValueError(f"No data for date: {date.date()}")
        
        if metric not in row.columns:
            raise ValueError(f"Metric not found: {metric}")
        
        return float(row.iloc[0][metric])
    
    # Clear cache when data is updated
    def clear_cache(self):
        self.get_value.cache_clear()
        self.get_comparison.cache_clear()

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _load_data(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")

        # Use Windows-friendly encoding
        df = pd.read_csv(self.data_path, encoding="cp1252")

        # Parse InvoiceDate and create date column
        if "InvoiceDate" in df.columns:
            df["date"] = pd.to_datetime(df["InvoiceDate"]).dt.normalize()
        elif "date" not in df.columns:
            raise ValueError(
                "Dataset must contain a 'date' or 'InvoiceDate' column"
            )

        # Aggregate sales data into daily metrics
        if "Invoice" in df.columns and "Price" in df.columns and "Quantity" in df.columns:
            # Calculate Revenue (sum of Quantity * Price per day)
            df["Revenue"] = df["Quantity"] * df["Price"]
            
            # Group by date and aggregate
            daily_metrics = df.groupby("date").agg({
                "Revenue": "sum",
                "Invoice": "nunique",  # Unique orders per day
                "Customer ID": lambda x: x.nunique() if pd.notna(x).any() else 0  # Unique customers (Traffic)
            }).reset_index()
            
            # Rename columns to match expected metrics
            daily_metrics.rename(columns={
                "Invoice": "Orders",
                "Customer ID": "Traffic"
            }, inplace=True)
            
            # Calculate Conversion Rate (simplified: Orders / Traffic * 100)
            # If Traffic is 0, set to 0 or a default value
            daily_metrics["Conversion Rate"] = (
                (daily_metrics["Orders"] / daily_metrics["Traffic"] * 100)
                .fillna(0)
                .round(2)
            )
            
            # Select only the columns we need
            df = daily_metrics[["date", "Revenue", "Orders", "Traffic", "Conversion Rate"]]
        else:
            # If it's already in metrics format, just normalize the date
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()

        df.sort_values("date", inplace=True)
        return df

    # data_store.py

    def _resolve_period(self, period: str):
        """
        More flexible period resolution with relative dates.
        """
        if not period:
            raise ValueError("Time period must be specified explicitly.")
        
        # Absolute periods
        if period in {"latest", "today"}:
            return self.latest_date
        
        if period == "yesterday":
            return self.latest_date - timedelta(days=1)
        
        if period == "day_before":
            return self.latest_date - timedelta(days=2)
        
        # Relative periods (e.g., "3_days_ago")
        if period.endswith("_days_ago") or period.endswith("_day_ago"):
            try:
                days = int(period.split("_")[0])
                return self.latest_date - timedelta(days=days)
            except ValueError:
                pass
        
        # Week-based
        if period == "last_week":
            return self.latest_date - timedelta(days=7)
        
        if period == "week_before":
            return self.latest_date - timedelta(days=14)
        
        # Try parsing as date string
        try:
            parsed_date = pd.to_datetime(period)
            if parsed_date <= self.latest_date:
                return parsed_date.normalize()
        except:
            pass
        
        raise ValueError(f"Unsupported period: {period}. Available: latest, yesterday, day_before, last_week, or specific dates.")

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_value(self, metric: str, period: str) -> float:
        date = self._resolve_period(period)

        row = self.df[self.df["date"] == date]

        if row.empty:
            raise ValueError(f"No data for date: {date.date()}")

        if metric not in row.columns:
            raise ValueError(f"Metric not found: {metric}")

        return float(row.iloc[0][metric])

    def get_comparison(self, metric: str, period: str, compare_to: str) -> dict:
        return {
            "current": self.get_value(metric, period),
            "baseline": self.get_value(metric, compare_to),
        }

    def get_series(self, metric: str, period: str) -> pd.DataFrame:
        if metric not in self.df.columns:
            raise ValueError(f"Metric not found: {metric}")

        if period == "last_7_days":
            end = self.latest_date
            start = end - timedelta(days=6)

            mask = (self.df["date"] >= start) & (self.df["date"] <= end)
            return self.df.loc[mask, ["date", metric]]

        raise ValueError(f"Unsupported period for series: {period}")

    def get_aggregate(self, metric: str, period: str, agg: str) -> float:
        if metric not in self.df.columns:
            raise ValueError(f"Metric not found: {metric}")

        end = self.latest_date

        if period == "last_7_days":
            start = end - timedelta(days=6)

        elif period == "last_week":
            # Previous full 7-day window
            end = self.latest_date - timedelta(days=7)
            start = end - timedelta(days=6)

        else:
            raise ValueError(f"Unsupported aggregation period: {period}")

        subset = self.df[
            (self.df["date"] >= start) &
            (self.df["date"] <= end)
        ][metric]

        if subset.empty:
            raise ValueError("Not enough data for aggregation")

        if agg == "sum":
            return float(subset.sum())
        if agg == "avg":
            return float(subset.mean())

        raise ValueError(f"Unsupported aggregation type: {agg}")

    def get_aggregate_range(self, metric: str, start_offset: int, end_offset: int, agg: str):
        end = self.latest_date - timedelta(days=end_offset)
        start = self.latest_date - timedelta(days=start_offset)

        subset = self.df[
            (self.df["date"] >= start) &
            (self.df["date"] <= end)
        ][metric]

        if subset.empty:
            raise ValueError("Not enough data for aggregation")

        if agg == "sum":
            return float(subset.sum())
        if agg == "avg":
            return float(subset.mean())

        raise ValueError(f"Unsupported aggregation type: {agg}")