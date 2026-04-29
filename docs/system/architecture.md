# System Architecture

```mermaid
flowchart LR
  A[EHR / HIS exported prescription data] --> B[De-identification]
  B --> C[Data Cleaning & Validation]
  C --> D[Structured Prompt Builder]
  K[Clinical Knowledge Base] --> VS[Vector Store / File Search]
  D --> AI[Knowledge-Based Generative AI]
  VS --> AI
  AI --> O[Structured JSON Output]
  O --> E[Post-processing]
  E --> M[Multi-label Metrics]
  R[Pharmacist Reference Standard] --> M
```

## Components

1. **Data input**: de-identified prescription data from HIS/EHR.
2. **Knowledge base**: medication error definitions, taxonomy, medication list, local formulary.
3. **Vector store**: indexed knowledge files for file search retrieval.
4. **Inference engine**: OpenAI Responses API with strict system prompt and JSON output.
5. **Evaluation module**: compares AI output with pharmacist reference standard.
