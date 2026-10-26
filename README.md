# AI Customer Feedback & Sales Intelligence Assistant

This project turns customer reviews into:

- sentiment, topic, and business-priority classifications;
- recurring-issue and opportunity summaries;
- Excel workbooks with review-level data and KPIs;
- an executive PowerPoint deck with recommendations.

This version is a LangChain LLM classification pipeline using local Ollama by default. It is not yet a full RAG application. A future RAG version would add embeddings, a vector store, and retrieval of relevant reviews before answering questions.

The main path is now **LangChain + AI structured-output classification**. A local rule-based classifier remains available as a transparent fallback for demos, testing, and situations where an API key is not available.

## 1. Set up

```powershell
cd project-3-ai-customer-feedback-sales-int
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-llm.txt
```

Make sure Ollama is running, then confirm the model exists:

```powershell
ollama list
```

## 2. Run the local Ollama project

```powershell
py main.py --input data\sample_reviews.csv --output output --mode ollama --model llama3.1:8b
```

The command creates:

- `output\feedback_analysis.xlsx`
- `output\customer_insights.pptx`
- `output\classified_reviews.csv`

To use your own file, provide columns named `review_id`, `review_text`, and optionally `rating`, `date`, `product`, `region`, or `channel`.

The default Ollama address is `http://localhost:11434`. Change it when needed:

```powershell
py main.py --mode ollama --model mistral:latest --ollama-url http://localhost:11434
```

## 3. Optional OpenAI mode

```powershell
$env:OPENAI_API_KEY = "your-key"
py main.py --mode openai --model gpt-4o-mini
```

## 4. Offline fallback

The offline mode does not call an external model:

```powershell
py main.py --input data\sample_reviews.csv --output output --mode offline
```

## 5. How the LangChain part works

1. `ChatPromptTemplate` creates a consistent analyst prompt.
2. `ChatOllama` sends the prompt to the local Ollama model by default. `ChatOpenAI` is also supported.
3. `with_structured_output(ReviewClassification)` asks for a typed response instead of free-form text.
4. Pydantic validates the required fields and allowed sentiment/priority values.
5. The validated result is merged into the review DataFrame.
6. `classification_source` and `model` make the result auditable.

The LLM is called once per review in this teaching version. For a larger production dataset, add batching, retries, caching, rate-limit handling, and asynchronous calls. Never commit an API key.

## 5. Learn the project

1. **Ingestion:** `FeedbackAnalyzer.load_reviews()` validates and normalizes the CSV.
2. **Classification:** `FeedbackAnalyzer.classify_reviews()` provides the offline baseline; `LangChainEnricher` provides the LLM path.
3. **Insights:** `build_insights()` aggregates themes, sentiment, priority, and product opportunities.
4. **Reporting:** `export_excel()` writes analysis tables and `export_powerpoint()` turns the same metrics into an executive story.
5. **Orchestration:** `main.py` connects those stages and exposes a command-line interface.

Interview explanation:

> “I used LangChain to build a prompt chain that sends each review to a local Ollama model. I used structured output with a Pydantic schema so the model must return valid sentiment, topic, priority, recommendation, and reasoning fields. I keep an offline rule-based path as a fallback and record the provider, model, and classification source for traceability.”

Suggested exercises:

- Add a new topic in `src/analyzer.py` and test it with a new review.
- Change the priority weights and observe the Excel `KPI Summary` sheet.
- Add a new slide to `src/reporting.py`.
- Replace the sample CSV with anonymized real feedback.
- Compare `--mode offline` with `--mode llm`, then manually review disagreements.

## Data and privacy

Use anonymized feedback only. Reviews sent to an external LLM provider may contain customer information, so confirm your organization's data-processing policy first.
