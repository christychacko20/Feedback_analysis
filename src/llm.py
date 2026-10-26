from __future__ import annotations

import os
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field


class ReviewClassification(BaseModel):
    """Schema that the LLM must follow for every review."""

    sentiment: Literal["Positive", "Neutral", "Negative"]
    topic: str = Field(min_length=2, max_length=80)
    priority: Literal["High", "Medium", "Low"]
    issue_or_opportunity: str = Field(min_length=5, max_length=240)
    reasoning: str = Field(min_length=5, max_length=500)


class LangChainEnricher:
    """Classify reviews with a local Ollama or hosted OpenAI model."""

    def __init__(
        self,
        provider: str = "ollama",
        model_name: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        try:
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError as exc:
            raise RuntimeError("Install requirements-llm.txt to use LangChain mode.") from exc

        self.model_name = model_name
        self.provider = provider
        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
            except ImportError as exc:
                raise RuntimeError("Install requirements-llm.txt to use Ollama mode.") from exc
            model = ChatOllama(model=model_name, temperature=0, base_url=base_url)
        elif provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI mode.")
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                raise RuntimeError("Install requirements-llm.txt to use OpenAI mode.") from exc
            model = ChatOpenAI(model=model_name, temperature=0)
        else:
            raise ValueError(f"Unsupported provider: {provider}. Choose 'ollama' or 'openai'.")

        self.chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a customer-experience analyst. Classify reviews consistently. "
                        "Priority means business urgency, not just emotional tone. "
                        "Use a short, business-friendly topic and recommend one practical action.",
                    ),
                    (
                        "human",
                        "Review ID: {review_id}\n"
                        "Rating: {rating}/5\n"
                        "Product: {product}\n"
                        "Review: {review_text}",
                    ),
                ]
            )
            | model.with_structured_output(ReviewClassification)
        )

    def classify(self, reviews: pd.DataFrame) -> pd.DataFrame:
        result = reviews.copy()
        for index, row in result.iterrows():
            classification = self.chain.invoke(
                {
                    "review_id": row["review_id"],
                    "rating": row["rating"],
                    "product": row["product"],
                    "review_text": row["review_text"],
                }
            )
            data = classification.model_dump()
            for column, value in data.items():
                result.at[index, column] = value
            result.at[index, "classification_source"] = f"langchain_{self.provider}"
            result.at[index, "model"] = self.model_name
        return result
