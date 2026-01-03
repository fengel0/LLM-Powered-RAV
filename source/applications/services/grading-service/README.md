**Grading‑Service – Use‑Case Package**

---

### What the package does  

The **grading‑service** package implements the business logic that evaluates the quality and correctness of a user’s answer against a reference answer. It orchestrates several components:

* an LLM client that produces structured outputs (e.g., rating scores, fact‑check results),  
* a fact‑store that caches previously extracted facts,  
* an OpenIE extractor for generating facts when none are cached, and  
* OpenTelemetry tracing for full observability of the grading workflow.  

---

### Core capabilities  

| Capability | Description |
|------------|-------------|
| **Structured LLM evaluation** | The service sends a prompt containing the question, reference answer, user answer, and any pre‑extracted facts to the LLM and expects a structured rating object (e.g., `SmallRating`). Errors from the LLM are propagated directly [9]. |
| **Fact‑checking against context** | For each fact, the service runs a separate LLM call (`IsTheFactInTheResponse`) to verify whether the fact appears in the provided context, wrapping each check in its own trace span [9]. |
| **Fact extraction & caching** | If no cached facts exist for a passage, the service calls an OpenIE component to extract triples, stores them in a fact store, and reuses them on subsequent requests [9]. |
| **Async processing** | All grading steps are implemented as `async` functions, allowing concurrent handling of multiple fact checks and LLM calls. |
| **Result handling** | Operations return a `Result` object; successful values are accessed via `get_ok()` and errors are propagated with `propagate_exception()`, keeping error handling explicit and consistent [9]. |
| **Observability** | Each major step (overall grading, individual fact‑in‑context checks) is wrapped in an OpenTelemetry span (`self.tracer.start_as_current_span`), providing traceability in distributed systems. |
| **Configuration‑driven prompts** | System prompts for correctness and completeness checks are stored in a configuration model (`self._config.data.system_prompt_correctnes`, `system_prompt_completness_context`), making the prompts easy to adjust without code changes. |
| **Dependency‑free workspace setup** | The package relies only on the shared `core` and `domain` workspaces, as declared in the `pyproject.toml` [1]. |

---

### Typical workflow  

1. **Receive grading request** – The service is called with a `sample` (question, expected answer) and a `answer_container` (user answer).  
2. **Run LLM correctness evaluation** – A prompt combining the question, reference answer, user answer, and any pre‑extracted facts is sent to the LLM; the structured rating is returned [9].  
3. **Fact extraction (if needed)** – If the fact cache returns `None`, the OpenIE component extracts facts from the passage, which are then stored for future reuse [9].  
4. **Fact‑in‑context checks** – For each fact, the service launches an LLM call to verify its presence in the given context, each wrapped in its own trace span [9].  
5. **Return result** – The final structured rating (or any encountered error) is delivered via a `Result` object.

---

### Extensibility  

- **Alternative LLM back‑ends** – Replace the current LLM client with another implementation that respects the same `get_structured_output` interface.  
- **Custom fact stores** – Swap the fact‑store implementation to use a different persistence layer (e.g., Redis, SQL) without changing grading logic.  
- **Additional grading dimensions** – Introduce new system prompts and result models (e.g., completeness, relevance) and call them in the same async, traced manner.  
- **Enhanced tracing** – Add custom attributes (e.g., prompt length, model name) to each OpenTelemetry span for deeper performance analysis.

---

