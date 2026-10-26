from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


TOPIC_KEYWORDS = {
    "Delivery": ["delivery", "arrived", "late", "package", "tracking", "shipping"],
    "Support": ["support", "agent", "reply", "replied", "wait", "helpful"],
    "Checkout & Payments": ["checkout", "payment", "apple pay", "charged", "refund", "price"],
    "Product Quality": ["quality", "feature", "reporting", "export", "value"],
    "Usability & Reliability": ["easy", "confusing", "reset", "password", "slow", "crash", "onboarding"],
}

POSITIVE = {"excellent", "easy", "fast", "great", "smooth", "useful", "helpful", "friendly", "value", "quickly"}
NEGATIVE = {"late", "never", "cannot", "confusing", "slow", "crashes", "missing", "long", "twice", "high", "error"}


@dataclass
class FeedbackAnalyzer:
    """Offline-first review classifier and insight builder."""

    def load_reviews(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        required = {"review_id", "review_text"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Input is missing required columns: {', '.join(sorted(missing))}")
        df = df.copy()
        df["review_text"] = df["review_text"].fillna("").astype(str).str.strip()
        if df["review_text"].eq("").any():
            raise ValueError("review_text cannot be empty.")
        df["rating"] = pd.to_numeric(df.get("rating", 3), errors="coerce").fillna(3).clip(1, 5)
        if "date" in df:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for column in ("product", "region", "channel"):
            if column not in df:
                df[column] = "Unknown"
            df[column] = df[column].fillna("Unknown").astype(str)
        return df

    def classify_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        result["sentiment"] = result.apply(lambda row: self._sentiment(row["review_text"], row["rating"]), axis=1)
        result["topic"] = result["review_text"].map(self._topic)
        result["priority"] = result.apply(
            lambda row: self._priority(row["review_text"], row["rating"], row["sentiment"]), axis=1
        )
        result["issue_or_opportunity"] = result.apply(self._opportunity, axis=1)
        result["sentiment_score"] = result.apply(
            lambda row: round((row["rating"] - 3) / 2, 2), axis=1
        )
        result["classification_source"] = "offline_rules"
        result["model"] = "keyword_lexicon_v1"
        return result

    def build_insights(self, classified: pd.DataFrame) -> dict[str, pd.DataFrame]:
        total = len(classified)
        topic = (
            classified.groupby("topic", as_index=False)
            .agg(reviews=("review_id", "count"), avg_rating=("rating", "mean"))
            .assign(share=lambda x: x["reviews"] / total)
            .sort_values(["reviews", "avg_rating"], ascending=[False, True])
        )
        sentiment = classified["sentiment"].value_counts().rename_axis("sentiment").reset_index(name="reviews")
        priority = classified["priority"].value_counts().rename_axis("priority").reset_index(name="reviews")
        opportunities = (
            classified[classified["priority"].isin(["High", "Medium"])]
            .groupby(["topic", "issue_or_opportunity"], as_index=False)
            .agg(reviews=("review_id", "count"), avg_rating=("rating", "mean"))
            .sort_values("reviews", ascending=False)
        )
        kpis = pd.DataFrame(
            [
                ("Total reviews", total),
                ("Average rating", round(classified["rating"].mean(), 2)),
                ("Positive rate", round((classified["sentiment"] == "Positive").mean(), 3)),
                ("Negative rate", round((classified["sentiment"] == "Negative").mean(), 3)),
                ("High-priority rate", round((classified["priority"] == "High").mean(), 3)),
                ("Topics identified", classified["topic"].nunique()),
            ],
            columns=["KPI", "Value"],
        )
        return {"kpis": kpis, "topics": topic, "sentiment": sentiment, "priority": priority, "opportunities": opportunities}

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z']+", text.lower()))

    def _sentiment(self, text: str, rating: float) -> str:
        tokens = self._tokens(text)
        score = len(tokens & POSITIVE) - len(tokens & NEGATIVE) + (rating - 3) * 0.8
        return "Positive" if score >= 1 else "Negative" if score <= -1 else "Neutral"

    def _topic(self, text: str) -> str:
        lowered = text.lower()
        scores = {topic: sum(keyword in lowered for keyword in words) for topic, words in TOPIC_KEYWORDS.items()}
        return max(scores, key=scores.get) if max(scores.values()) else "General Experience"

    def _priority(self, text: str, rating: float, sentiment: str) -> str:
        urgent = ("refund", "charged twice", "cannot", "crash", "never replied", "error")
        if rating <= 2 or any(word in text.lower() for word in urgent):
            return "High"
        if rating == 3 or sentiment == "Neutral":
            return "Medium"
        return "Low"

    def _opportunity(self, row: Any) -> str:
        mapping = {
            "Delivery": "Improve delivery visibility and SLA communication",
            "Support": "Reduce support wait time and improve response follow-through",
            "Checkout & Payments": "Reduce payment friction and prevent billing errors",
            "Product Quality": "Prioritize product polish and export quality",
            "Usability & Reliability": "Fix reliability blockers and simplify self-service",
        }
        return mapping.get(row["topic"], "Monitor feedback and identify a repeatable improvement")
