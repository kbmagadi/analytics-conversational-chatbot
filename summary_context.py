from datetime import timedelta


class SummaryContext:
    """
    Deterministic cached summary derived from MetricsStore.
    """

    def __init__(self, metrics_store):
        self.store = metrics_store
        self._build()

    def _build(self):
        """
        Build daily and weekly summaries from the dataset.
        """
        dates = self.store.df["date"].sort_values().unique()

        if len(dates) < 2:
            self.daily = {}
            return

        latest = dates[-1]
        prev = dates[-2]

        self.latest_date = latest

        self.daily = {}

        for metric in self.store.df.columns:
            if metric == "date":
                continue

            try:
                curr = self.store.get_value(metric, "latest")
                base = self.store.get_value(metric, "yesterday")

                change_pct = (
                    round(((curr - base) / base) * 100, 2)
                    if base != 0 else 0.0
                )

                self.daily[metric] = {
                    "current": curr,
                    "change_pct": change_pct
                }

            except Exception:
                continue

    # -----------------------------
    # Capability checks
    # -----------------------------

    def can_answer_value(self, metric, period):
        return (
            period in {"latest", "today", "yesterday"}
            and metric in self.daily
        )

    def can_answer_summary(self, period):
        return period in {"latest", "today", "yesterday"} and bool(self.daily)

    # -----------------------------
    # Retrieval
    # -----------------------------

    def get_value(self, metric):
        return self.daily[metric]["current"]

    def get_summary(self):
        return self.daily
