"""Aggregation queries powering insights + the anomaly detectors. Tenant-scoped."""

from __future__ import annotations

from src.db.repositories.base import UserScopedRepository


class AnalyticsRepository(UserScopedRepository):
    def category_monthly_series(self) -> list[dict]:
        """Per-category monthly spend totals, oldest first."""
        self.cur.execute(
            "SELECT c.category_name, "
            "       date_trunc('month', e.date)::date AS month, "
            "       SUM(e.amount) AS total "
            "FROM expenses e LEFT JOIN categories c ON e.category_id = c.category_id "
            "WHERE e.user_id = %s AND e.date IS NOT NULL AND e.amount IS NOT NULL "
            "GROUP BY c.category_name, month ORDER BY month",
            (self.user_id,),
        )
        return self.cur.fetchall()

    def same_day_amount_duplicates(self) -> list[dict]:
        """Same amount charged multiple times on the same day."""
        self.cur.execute(
            "SELECT e.date, e.amount, COUNT(*) AS occurrences, "
            "       array_agg(e.transaction_id) AS transaction_ids "
            "FROM expenses e "
            "WHERE e.user_id = %s AND e.date IS NOT NULL AND e.amount IS NOT NULL "
            "GROUP BY e.date, e.amount HAVING COUNT(*) > 1 "
            "ORDER BY e.date DESC LIMIT 50",
            (self.user_id,),
        )
        return self.cur.fetchall()

    def monthly_summary(self) -> list[dict]:
        """Total spend + count per month."""
        self.cur.execute(
            "SELECT date_trunc('month', date)::date AS month, "
            "       SUM(amount) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = %s AND date IS NOT NULL "
            "GROUP BY month ORDER BY month DESC LIMIT 12",
            (self.user_id,),
        )
        return self.cur.fetchall()

    def category_breakdown(self, *, months: int = 1) -> list[dict]:
        self.cur.execute(
            "SELECT c.category_name, SUM(e.amount) AS total, COUNT(*) AS count "
            "FROM expenses e LEFT JOIN categories c ON e.category_id = c.category_id "
            "WHERE e.user_id = %s AND e.date >= (CURRENT_DATE - (%s || ' months')::interval) "
            "GROUP BY c.category_name ORDER BY total DESC NULLS LAST",
            (self.user_id, months),
        )
        return self.cur.fetchall()
