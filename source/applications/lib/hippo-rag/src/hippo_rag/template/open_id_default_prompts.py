from domain.llm.model import TextChatMessage

### NER

NER_SYSTEM_PROMPT_DEFAULT = """Your task is to extract named entities from the given paragraph. 
Respond with a JSON list of entities.
"""


ONE_SHOT_NER_PARAGRAPH_EXAMPLE = """Radio City
Radio City is India's first private FM radio station and was started on 3 July 2001.
It plays Hindi, English and regional songs.
Radio City recently forayed into New Media in May 2008 with the launch of a music portal - PlanetRadiocity.com that offers music related news, videos, songs, and other music-related features."""


ONE_SHOT_NER_OUTPUT_EXAMPLE = """{"named_entities":
    ["Radio City", "India", "3 July 2001", "Hindi", "English", "May 2008", "PlanetRadiocity.com"]
}
"""

### TRIPLE

TRIPLE_SYSTEM_PROMPT_DEFAULT = """Your task is to construct an RDF (Resource Description Framework) graph from the given passages and named entity lists. 
Respond with a JSON list of triples, with each triple representing a relationship in the RDF graph. 

Pay attention to the following requirements:
- Each triple should contain at least one, but preferably two, of the named entities in the list for each passage.
- Clearly resolve pronouns to their specific names to maintain clarity.

"""


DEFAULT_TRIPLE_EXTRACTION_USER_PROMPT = """Convert the paragraph into a JSON dict, it has a named entity list and a triple list.
Paragraph:
```
{passage}
```

{named_entities}
"""


TRIPLE_EXTRACTION_EXAMPLE_INPUT = DEFAULT_TRIPLE_EXTRACTION_USER_PROMPT.format(
    passage=ONE_SHOT_NER_PARAGRAPH_EXAMPLE,
    named_entities=ONE_SHOT_NER_OUTPUT_EXAMPLE,
)


TRIPLE_EXTRACTION_EXAMPLE_OUTPUT = """{"triples": [
            ["Radio City", "located in", "India"],
            ["Radio City", "is", "private FM radio station"],
            ["Radio City", "started on", "3 July 2001"],
            ["Radio City", "plays songs in", "Hindi"],
            ["Radio City", "plays songs in", "English"],
            ["Radio City", "forayed into", "New Media"],
            ["Radio City", "launched", "PlanetRadiocity.com"],
            ["PlanetRadiocity.com", "launched in", "May 2008"],
            ["PlanetRadiocity.com", "is", "music portal"],
            ["PlanetRadiocity.com", "offers", "news"],
            ["PlanetRadiocity.com", "offers", "videos"],
            ["PlanetRadiocity.com", "offers", "songs"]
    ]
}
"""


DEFAULT_NER_EXTRACTION_HISTORY = [
    TextChatMessage(role="system", content=NER_SYSTEM_PROMPT_DEFAULT),
    TextChatMessage(role="user", content=ONE_SHOT_NER_PARAGRAPH_EXAMPLE),
    TextChatMessage(role="assistant", content=ONE_SHOT_NER_OUTPUT_EXAMPLE),
]


DEFAULT_TRIPLE_EXTRACTION_HISTORY = [
    TextChatMessage(role="system", content=TRIPLE_SYSTEM_PROMPT_DEFAULT),
    TextChatMessage(role="user", content=TRIPLE_EXTRACTION_EXAMPLE_INPUT),
    TextChatMessage(role="assistant", content=TRIPLE_EXTRACTION_EXAMPLE_OUTPUT),
]
