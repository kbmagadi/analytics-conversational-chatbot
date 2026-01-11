from datetime import timedelta

ENABLE_CACHE_LOGS = True

def _log_cache(event: str, metric=None, period=None, operation=None):
    if not ENABLE_CACHE_LOGS:
        return

    parts = [f"[CACHE {event}]"]
    if metric:
        parts.append(f"metric={metric}")
    if period:
        parts.append(f"period={period}")
    if operation:
        parts.append(f"op={operation}")

    print(" ".join(parts))

class SummaryContext:
    """
    Deterministic cached summary derived from MetricsStore.
    """

    def __init__(self, metrics_store):
        self.store = metrics_store
        self.cache = {}
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

        for metric in self.store.graph.metrics():
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
        # Populate cache with values for fast lookup
        # -----------------------------
        for metric, info in self.daily.items():
            # Cache latest value
            self.cache[(metric, "latest", "value")] = info["current"]
            
            # Cache yesterday value if available
            try:
                yesterday_value = self.store.get_value(metric, "yesterday")
                self.cache[(metric, "yesterday", "value")] = yesterday_value
            except Exception:
                pass  # Skip if yesterday value not available

    # -----------------------------
    # Capability checks
    # -----------------------------

    def _normalize_period(self, period):
        """Normalize period strings to standard format."""
        if period == "today":
            return "latest"
        return period
        
    def can_answer_value(self, metric, period):
        period = self._normalize_period(period)

        can_answer = (
            (metric, period, "value") in self.cache
            and period in {"latest", "yesterday"}
        )

        _log_cache(
            "HIT" if can_answer else "MISS",
            metric=metric,
            period=period,
            operation="value-check"
        )

        return can_answer


    def can_answer_summary(self, period):
        can_answer = period in {"latest", "today", "yesterday"} and bool(self.cache)

        _log_cache(
            "HIT" if can_answer else "MISS",
            period=period,
            operation="summary-check"
        )

        return can_answer

    # -----------------------------
    # Retrieval
    # -----------------------------

    def get_value(self, metric, period):
        period = self._normalize_period(period)
        key = (metric, period, "value")

        if key in self.cache:
            _log_cache("HIT", metric, period, "value")
            return self.cache[key]

        _log_cache("MISS", metric, period, "value")
        raise KeyError("Value not available in summary cache.")


    def get_summary(self):
        return self.daily

    def get_or_compute(self, metric, period, operation, compute_fn):
        key = (metric, period, operation)

        if key in self.cache:
            _log_cache("HIT", metric, period, operation)
            return self.cache[key]

        _log_cache("MISS", metric, period, operation)
        value = compute_fn()
        self.cache[key] = value
        return value