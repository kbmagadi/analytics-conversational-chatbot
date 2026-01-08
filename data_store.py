# chatbot/data_store.py

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta


class MetricsStore:
    """
    Single source of truth for metric data.
    Backed by a Pandas DataFrame (MVP).
    """

    def __init__(self, data_path: str = "data/metrics.csv"):
        self.data_path = Path(data_path)
        self.df = self._load_data()

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _load_data(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")

        df = pd.read_csv(self.data_path)

        if "date" not in df.columns:
            raise ValueError("Dataset must contain a 'date' column")

        df["date"] = pd.to_datetime(df["date"])
        df.sort_values("date", inplace=True)

        return df

    def _resolve_period(self, period: str):
        """
        Resolve period keywords to actual dates based on dataset availability,
        not calendar arithmetic.
        """
        dates = self.df["date"].sort_values().unique()

        if period == "latest":
            return dates[-1]

        if period == "today":
            return dates[-1]

        if period == "yesterday":
            if len(dates) < 2:
                raise ValueError("Not enough data for 'yesterday'")
            return dates[-2]

        if period == "day_before":
            if len(dates) < 3:
                raise ValueError("Not enough data for 'day_before'")
            return dates[-3]

        raise ValueError(f"Unsupported period: {period}")


    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_value(self, metric: str, period: str) -> float:
        """
        Get a single metric value for a given period.
        """
        date = self._resolve_period(period)

        row = self.df[self.df["date"] == date]

        if row.empty:
            raise ValueError(f"No data for date: {date}")

        if metric not in row.columns:
            raise ValueError(f"Metric not found: {metric}")

        return float(row.iloc[0][metric])

    def get_comparison(self, metric: str, period: str, compare_to: str) -> dict:
        """
        Get metric values for two periods.
        """
        current_value = self.get_value(metric, period)
        baseline_value = self.get_value(metric, compare_to)

        return {
            "current": current_value,
            "baseline": baseline_value
        }

    def get_series(self, metric: str, period: str) -> pd.DataFrame:
        """
        Get time series data for a metric.
        """
        if metric not in self.df.columns:
            raise ValueError(f"Metric not found: {metric}")

        if period == "last_7_days":
            end_date = self.df["date"].max()
            start_date = end_date - timedelta(days=6)

            mask = (self.df["date"] >= start_date) & (self.df["date"] <= end_date)
            return self.df.loc[mask, ["date", metric]]

        raise ValueError(f"Unsupported period for series: {period}")

    def get_aggregate(self, metric: str, period: str, agg: str) -> float:
        """
        Aggregate a metric over a time period.
        Supported periods: last_7_days, last_week
        """
        if metric not in self.df.columns:
            raise ValueError(f"Metric not found: {metric}")

        end_date = self.df["date"].max()

        if period in {"last_7_days", "last_week"}:
            start_date = end_date - timedelta(days=6)
        else:
            raise ValueError(f"Unsupported aggregation period: {period}")

        mask = (self.df["date"] >= start_date) & (self.df["date"] <= end_date)
        subset = self.df.loc[mask, metric]

        if subset.empty:
            raise ValueError("Not enough data for aggregation")

        if agg == "sum":
            return float(subset.sum())

        if agg == "avg":
            return float(subset.mean())

        raise ValueError(f"Unsupported aggregation type: {agg}")
    
    def get_aggregate_range(self, metric: str, start_offset: int, end_offset: int, agg: str):
        """
        Aggregate metric over a relative date window.
        Offsets are in days from latest_date.
        """
        latest = self.df["date"].max()
        start_date = latest - timedelta(days=start_offset)
        end_date = latest - timedelta(days=end_offset)

        subset = self.df[
            (self.df["date"] >= start_date) &
            (self.df["date"] <= end_date)
        ][metric]

        if subset.empty:
            raise ValueError("Not enough data for aggregation")

        if agg == "sum":
            return float(subset.sum())
        if agg == "avg":
            return float(subset.mean())

        raise ValueError(f"Unsupported aggregation type: {agg}")

