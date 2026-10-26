from __future__ import annotations

import argparse
from pathlib import Path

from src.analyzer import FeedbackAnalyzer
from src.reporting import export_excel, export_powerpoint


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze customer reviews with LangChain and create reports.")
    parser.add_argument("--input", default="data/sample_reviews.csv", help="Path to a review CSV.")
    parser.add_argument("--output", default="output", help="Directory for generated reports.")
    parser.add_argument(
        "--mode",
        choices=("ollama", "openai", "offline"),
        default="ollama",
        help="Use local Ollama, hosted OpenAI, or offline rules.",
    )
    parser.add_argument("--use-llm", action="store_true", help="Backward-compatible alias for --mode ollama.")
    parser.add_argument("--model", default=None, help="Optional model name.")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server URL.")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    analyzer = FeedbackAnalyzer()
    reviews = analyzer.load_reviews(args.input)
    classified = analyzer.classify_reviews(reviews)
    if args.mode in ("ollama", "openai") or args.use_llm:
        from src.llm import LangChainEnricher

        provider = "ollama" if args.use_llm else args.mode
        default_model = "llama3.1:8b" if provider == "ollama" else "gpt-4o-mini"
        classified = LangChainEnricher(
            provider=provider,
            model_name=args.model or default_model,
            base_url=args.ollama_url,
        ).classify(classified)
    insights = analyzer.build_insights(classified)
    classified.to_csv(output / "classified_reviews.csv", index=False)
    export_excel(classified, insights, output / "feedback_analysis.xlsx")
    export_powerpoint(insights, output / "customer_insights.pptx")
    print(f"Analyzed {len(classified)} reviews.")
    print(f"Created reports in {output.resolve()}")


if __name__ == "__main__":
    main()
