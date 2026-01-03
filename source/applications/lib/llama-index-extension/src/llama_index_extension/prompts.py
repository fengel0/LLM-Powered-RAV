DEFAULT_SUB_PROMPT = """
# Given a user question, and a list of tools, output a list of relevant sub-questions in json markdown that when composed can help answer the full user question:

# Example
<Tools>
```json
{
    "uber_10k": "Provides information about Uber financials for year 2021",
    "lyft_10k": "Provides information about Lyft financials for year 2021"
}
```

<User Question>
Compare and contrast the revenue growth and EBITDA of Uber and Lyft for year 2021


<Output>
```json
{
    "items": [
        {
            "sub_question": "What is the revenue growth of Uber",
            "tool_name": "uber_10k"
        },
        {
            "sub_question": "What is the EBITDA of Uber",
            "tool_name": "uber_10k"
        },
        {
            "sub_question": "What is the revenue growth of Lyft",
            "tool_name": "lyft_10k"
        },
        {
            "sub_question": "What is the EBITDA of Lyft",
            "tool_name": "lyft_10k"
        }
    ]
}
```
# Prompt
<Tools>
```json
{tools_str}
```
<User Question>
{query_str}

<Output>

"""

DEFAULT_CONDENSE_TEMPLATE = """\
Given a conversation (between Human and Assistant) and a follow up message from Human, \
rewrite the message to be a standalone question that captures all relevant context \
from the conversation.

<Chat History>
{chat_history}

<Follow Up Message>
{question}

<Standalone question>
"""

DEFAULT_TEXT_WRAPPER_TMPL = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context information and not prior knowledge, "
    "answer the query.\n"
    "Query: {query_str}\n"
    "Answer: "
)

DEFAULT_TEXT_QA_PROMPT_TMPL = (
    "Context information for the Query is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
)


DEFAULT_SYSTEM_PROMPT = (
    "You are an fucking expert Q&A system that is trusted around the world.\n"
    "Always answer the query using the provided context information, "
    "and not prior knowledge.\n"
    "Some rules to follow:\n"
    "1. Never directly reference the given context in your answer.\n"
    "2. Avoid statements like 'Based on the context, ...' or "
    "'The context information ...' or anything along "
    "those lines."
)
