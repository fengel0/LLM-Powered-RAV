# tests/test_advanced_sentence_splitter.py

import logging

from core.logger import init_logging
from domain_test import AsyncTestBase

from domain.file_converter.model import Page, TableFragement, TextFragement
from domain.rag.indexer.interface import SplitNode, Document
from text_splitter.node_splitter import (
    AdvancedSentenceSplitter,
    NodeSplitterConfig,
)

init_logging("debug")
logger = logging.getLogger(__name__)


class TestAdvancedSentenceSplitter(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        # Small-ish chunk/overlap to exercise packing & overlap in tests
        self.config = NodeSplitterConfig(
            chunk_size=80,  # token cap per chunk
            chunk_overlap=24,  # token overlap between chunks
            default_language="en",
            overflow_strategy="fallback_split",  # default behavior for huge units
        )
        self.splitter = AdvancedSentenceSplitter(self.config)

    # --- helpers --------------------------------------------------------

    def _tok_len(self, txt: str) -> int:
        # use the splitter's tokenizer to count tokens exactly as runtime
        return self.splitter._tok.count(txt)  # type: ignore[attr-defined]

    def _head_tokens(self, txt: str, k: int) -> list[int]:
        ids = self.splitter._tok.encode(txt)  # type: ignore[attr-defined]
        return ids[: min(k, len(ids))]

    def _tail_tokens(self, txt: str, k: int) -> list[int]:
        ids = self.splitter._tok.encode(txt)  # type: ignore[attr-defined]
        return ids[-min(k, len(ids)) :]

    # --- core behavior --------------------------------------------------

    def test_plain_string_two_chunks_with_overlap(self):
        config = NodeSplitterConfig(
            chunk_size=15,  # token cap per chunk
            chunk_overlap=5,  # token overlap between chunks
            default_language="en",
            overflow_strategy="fallback_split",  # default behavior for huge units
        )
        splitter = AdvancedSentenceSplitter(config)

        text = (
            "This is sentence one. "
            "This is sentence two. "
            "This is sentence five that is a bit longer to push the token count."
            "This is sentence three. "
            "This is sentence four. "
        )
        doc = Document(
            id="doc1", content=text, metadata={"test": "lol", "count": 3, "price": 3.5}
        )

        nodes = splitter.split_documents(doc)
        for node in nodes:
            logger.debug("NODE: %s", node)

        # Should produce at least 2 chunks and all must respect token cap
        assert len(nodes) > 2
        for n in nodes:
            assert self._tok_len(n.content) <= self.config.chunk_size

        # Metadata checks
        for n in nodes:
            assert isinstance(n, SplitNode)
            assert "unit" in n.metadata
            assert n.metadata["unit"] == "sentence_chunk"
            assert "detected_language" in n.metadata
            assert n.metadata["detected_language"]

        # Overlap check (token overlap, not sentence overlap):
        # compare tail of chunk[i] and head of chunk[i+1]

    def test_single_long_sentence_exceeds_cap(self):
        # Single very long "sentence" forces fallback
        long_word = "supercalifragilisticexpialidocious"
        long_sentence = " ".join([long_word] * 120) + "."
        doc = Document(id="doc2", content=long_sentence, metadata={})

        nodes = self.splitter.split_documents(doc)
        assert len(nodes) > 1
        for n in nodes:
            assert len(n.content) > 0
            assert "detected_language" in n.metadata
            assert self._tok_len(n.content) <= self.config.chunk_size

    def test_empty_string_returns_no_nodes(self):
        doc = Document(id="doc3", content="", metadata={})
        nodes = self.splitter.split_documents(doc)
        assert len(nodes) == 0

    def test_paginated_text_fragments(self):
        page1 = Page(
            document_fragements=[
                TextFragement(text="First page. Has two sentences."),
                TextFragement(text="Another fragment here."),
            ],
        )
        page2 = Page(
            document_fragements=[TextFragement(text="Second page content only.")],
        )
        doc = Document(id="doc4", content=[page1, page2], metadata={})

        nodes = self.splitter.split_documents(doc)
        assert len(nodes) == 1
        # page metadata present for all nodes
        assert all("pages" in n.metadata for n in nodes)
        assert str(1) in nodes[0].metadata["pages"]
        assert str(2) in nodes[0].metadata["pages"]

        # language detection metadata present
        assert all("detected_language" in n.metadata for n in nodes)

    def test_table_fragment_rowwise_nodes(self):
        header_md = """| A    | B    |"""
        rows: list[str] = ["| r1c1 | r1c2 |", "| r2c1 | r2c2 |", "| r3c1 | r3c2 |"]
        page = Page(
            document_fragements=[
                TableFragement(full_tabel="", header=header_md, column=rows)
            ],
        )
        doc = Document(id="doc5", content=[page], metadata={})

        nodes = self.splitter.split_documents(doc)

        # One node per row
        assert len(nodes) == len(rows)

        # Metadata checks
        for idx, n in enumerate(nodes):
            assert "page" in n.metadata
            assert n.metadata["page"] == str(1)
            assert "order" in n.metadata
            assert "row_number" in n.metadata
            assert n.metadata["row_number"] == str(idx)
            assert "detected_language" in n.metadata
            assert n.metadata["detected_language"]

        # Content should include header and the row content
        assert "A" in nodes[0].content
        assert "B" in nodes[0].content
        assert "r1c1" in nodes[0].content

    def test_ids_change_when_content_changes(self):
        text1 = "Alpha. Beta."
        text2 = "Alpha. Beta changed."
        d1 = Document(id="doc7", content=text1, metadata={})
        d2 = Document(id="doc7", content=text2, metadata={})

        n1 = self.splitter.split_documents(d1)
        n2 = self.splitter.split_documents(d2)

        assert {x.id for x in n1} != {y.id for y in n2}

    def test_long_paragraph_small_chunk_size(self):
        text = (
            "In a small and thoroughly unremarkable town there lived a collection of people "
            "who were convinced their daily routines held profound meaning, even though most of them "
            "spent their mornings grumbling about the weather, their afternoons staring at screens "
            "that displayed endless streams of numbers, emails, and notifications, and their evenings "
            "pretending they were not exhausted from the cycle they swore they would one day break "
            "but somehow never managed to escape. "
            "Among these people was a particularly indecisive character who would wander into the bakery "
            "every morning, stare for ten minutes at the identical rows of bread, and finally order "
            "the same roll they had ordered the day before while muttering something about wanting variety "
            "and change in life, which was funny because the act of muttering itself had become just as much "
            "of a routine as the bread selection they refused to alter. "
        )
        doc = Document(id="doc1", content=text, metadata={})

        tiny_cfg = NodeSplitterConfig(
            chunk_size=40,  # tiny to force multiple chunks
            chunk_overlap=12,
            default_language="en",
        )
        splitter = AdvancedSentenceSplitter(tiny_cfg)
        nodes = splitter.split_documents(doc)

        assert len(nodes) > 0
        for n in nodes:
            assert isinstance(n, SplitNode)
            assert "unit" in n.metadata
            assert n.metadata["unit"] == "sentence_chunk"
            assert "detected_language" in n.metadata
            assert n.metadata["detected_language"] == "en"
            assert self._tok_len(n.content) <= tiny_cfg.chunk_size

    def test_german_text_detects_language_de(self):
        text = (
            "In einem kleinen und völlig unscheinbaren Dorf lebte eine Gruppe von Menschen, "
            "die überzeugt waren, dass ihre täglichen Routinen eine tiefere Bedeutung hätten, "
            "obwohl die meisten von ihnen ihre Morgen damit verbrachten, über das Wetter zu klagen, "
            "ihre Nachmittage vor Bildschirmen voller Zahlen und Nachrichten zu verbringen "
            "und ihre Abende damit, so zu tun, als wären sie nicht erschöpft von dem Kreislauf, "
            "den sie eines Tages zu durchbrechen schwören würden, es aber nie schafften."
        )
        doc = Document(id="doc_de", content=text, metadata={})

        nodes = self.splitter.split_documents(doc)

        assert len(nodes) > 0, "Expected at least one chunk from German text"
        for n in nodes:
            assert isinstance(n, SplitNode)
            assert "detected_language" in n.metadata
            assert n.metadata["detected_language"] == "de"
            assert len(n.content) > 0

    # --- single-unit overflow behavior ----------------------------------

    def test_single_unit_overflow_fallback_split(self):
        cfg = NodeSplitterConfig(
            chunk_size=30,
            chunk_overlap=0,
            default_language="en",
            overflow_strategy="fallback_split",
        )
        splitter = AdvancedSentenceSplitter(cfg)

        # One monster sentence (no natural sentence boundary helps)
        text = "antidisestablishmentarianism-" * 20
        doc = Document(id="hard1", content=text, metadata={})
        nodes = splitter.split_documents(doc)

        assert len(nodes) > 0
        # All chunks must respect token cap
        for n in nodes:
            assert self._tok_len(n.content) <= cfg.chunk_size

        # Expect multiple nodes because fallback_split will break the unit
        assert len(nodes) >= 2

    def test_single_unit_overflow_truncate(self):
        cfg = NodeSplitterConfig(
            chunk_size=40,
            chunk_overlap=0,
            default_language="en",
            overflow_strategy="truncate",  # trim huge unit to fit
            truncate_marker="",  # keep marker empty to avoid token drift
        )
        splitter = AdvancedSentenceSplitter(cfg)

        text = "supercalifragilisticexpialidocious " * 20
        doc = Document(id="hard2", content=text, metadata={})
        nodes = splitter.split_documents(doc)

        # There may still be multiple chunks (greedy packing),
        # but every individual piece must obey the cap.
        assert len(nodes) > 1
        for n in nodes:
            assert self._tok_len(n.content) <= cfg.chunk_size

    # --- misc -----------------------------------------------------------

    def test_table_fragment_language_detection_from_rows(self):
        # Default language is EN, but the rows are German—expect detection to switch to 'de'
        header_md = "| Name | Alter | Wohnort | PLZ | Straße"
        rows: list[str] = [
            "| Hans | 30 | Erfurt | 99085 | Altonaustraße",
            "| Jonas | 30 | Erfurt | 99085 | Altonaustraße",
            "| Sina | 30 | Erfurt | 99085 | Altonaustraße",
        ]
        page = Page(
            document_fragements=[
                TableFragement(full_tabel="", header=header_md, column=rows)
            ]
        )
        cfg = NodeSplitterConfig(
            chunk_size=100,
            chunk_overlap=0,
            default_language="en",
            overflow_strategy="fallback_split",
        )
        splitter = AdvancedSentenceSplitter(cfg)

        doc = Document(id="table_de", content=[page], metadata={})
        nodes = splitter.split_documents(doc)

        assert len(nodes) == len(rows)
        for n in nodes:
            assert "detected_language" in n.metadata
        # At least one likely German
        assert any(n.metadata["detected_language"] == "de" for n in nodes)

    def test_no_empty_or_whitespace_only_chunks(self):
        cfg = NodeSplitterConfig(
            chunk_size=30,
            chunk_overlap=8,
            default_language="en",
            overflow_strategy="fallback_split",
        )
        splitter = AdvancedSentenceSplitter(cfg)

        text = "A.   \n\n  B.   C.   "
        doc = Document(id="spaces", content=text, metadata={})
        nodes = splitter.split_documents(doc)

        assert nodes
        for n in nodes:
            assert n.content.strip()
            assert not n.content.isspace()

    def test_ids_stable_when_content_and_config_identical(self):
        cfg = NodeSplitterConfig(
            chunk_size=64,
            chunk_overlap=16,
            default_language="en",
            overflow_strategy="fallback_split",
        )
        splitter = AdvancedSentenceSplitter(cfg)

        text = "Alpha. Beta. Gamma. Delta."
        d1 = Document(id="same", content=text, metadata={"k": "v"})
        d2 = Document(id="same", content=text, metadata={"k": "v"})
        n1 = splitter.split_documents(d1)
        n2 = splitter.split_documents(d2)

        assert [x.id for x in n1] == [y.id for y in n2]

    def test_every_node_respects_chunk_size(self):
        cfg = NodeSplitterConfig(
            chunk_size=48,
            chunk_overlap=12,
            default_language="en",
            overflow_strategy="fallback_split",
        )
        splitter = AdvancedSentenceSplitter(cfg)

        text = (
            "This is a long paragraph intended to exceed the token budget when "
            "grouped into greedy chunks. It contains several sentences that repeat "
            "similar structures to inflate the token count significantly. "
            "By doing so, we ensure that the fallback splitting logic is exercised "
            "and that no resulting node goes beyond the configured chunk size."
        ) * 2
        doc = Document(id="cap_all", content=text, metadata={})
        nodes = splitter.split_documents(doc)

        assert nodes
        for n in nodes:
            assert self._tok_len(n.content) <= cfg.chunk_size

    def test_playground(self):
        text = """Acme Government Solutions is a government industry company established on June 1, 2001 in Washington, D.C., specializing in providing comprehensive government services and solutions.\nIn January 2021, Acme Government Solutions made a significant decision to distribute $5 million of dividends to its shareholders. This move not only enhanced shareholder returns but also showcased the company's commitment to rewarding its investors. This dividend distribution was a result of the company's successful acquisition of a major government contract worth $100 million in March 2021. This acquisition expanded Acme Government Solutions' service portfolio and increased its revenue potential. Furthermore, in April 2021, the company announced plans to establish regional offices in three new states, thereby expanding its presence and market reach. This strategic move allowed Acme Government Solutions to tap into new geographic markets, increasing its market share and potential customer base.\nIn May 2021, Acme Government Solutions forged a strategic partnership with a leading technology firm. This partnership aimed to jointly develop innovative solutions for government agencies, providing Acme Government Solutions with access to advanced technology and expertise. This strategic collaboration also gave the company a competitive advantage in the market. Additionally, in June 2021, Acme Government Solutions successfully completed a high-profile project for a government client, showcasing its capabilities and establishing a reputation for excellence. This successful project delivery further enhanced the company's brand reputation and credibility in the industry.\nIn February 2021, Acme Government Solutions completed the asset acquisition of Nationwide Security Services, with a total value of $20 million. This acquisition expanded the company's business scope and enhanced its market competitiveness. To support its expansion and development, the company conducted a large-scale financing activity in March 2021, raising $50 million of funds. This significant financial boost strengthened Acme Government Solutions' financial strength and provided the necessary resources for its growth plans.\nIn May 2021, the company further expanded its market share by completing the acquisition of 51% equity of Government IT Solutions. This acquisition not only increased Acme Government Solutions' control but also broadened its business areas, enhancing its profitability. Moreover, in June 2021, the company invested $30 million in the Modernizing Public Infrastructure project. This strategic investment allowed Acme Government Solutions to diversify its business areas and further capitalize on emerging opportunities.\nTo optimize its capital structure, Acme Government Solutions underwent debt restructuring in August 2021, reducing its liabilities by $15 million. This move improved the company's financial condition and reduced its financial costs. In September 2021, the company underwent an asset restructuring, optimizing its business structure. This restructuring initiative aimed to improve operational efficiency and increase the company's overall value.\nThese significant events have had a direct impact on Acme Government Solutions' financial indicators. The company's operating income reached $100 million, driven by increased market demand and changes in product prices. This strong operating income contributed to a net profit of $20 million, reflecting effective cost control measures and non-recurring gains and losses. Acme Government Solutions' total assets stood at $500 million, primarily influenced by asset acquisitions, disposals, and revaluations. The company's total liabilities amounted to $200 million, influenced by new debt issuances, debt repayments, and debt restructuring activities.\nShareholder equity, on the other hand, reached $300 million, driven by the company's net profit, dividend distributions, and capital reserves. Acme Government Solutions' cash flow amounted to $50 million, reflecting the company's efficient management of operating, investment, and financing activities. The company's debt ratio stood at 0.4, indicating a moderate level of debt, while the debt to assets ratio was 40%, highlighting the company's financial leverage. Finally, the return on equity was 6.67%, reflecting the operational efficiency of shareholder equity.\nLooking ahead, Acme Government Solutions has outlined its future outlook. The company plans to implement various cost control measures to improve profitability and optimize capital operations to ensure efficient resource utilization. Additionally, Acme Government Solutions intends to invest heavily in research and development to introduce innovative solutions for public services. The company also aims to expand its presence in emerging markets through strategic partnerships. To mitigate financial risks, Acme Government Solutions has implemented robust risk management strategies, considering factors such as changes in government policies, economic downturns, and cybersecurity threats. These strategies ensure the company's business continuity and long-term success in the government industry.\nThe purpose of this Corporate Governance Report is to provide an in-depth overview of Acme Government Solutions' governance structure and practices, highlighting significant events and indicators that have impacted corporate governance. Additionally, this report will discuss the company's efforts to enhance transparency, accountability, and stakeholder engagement.\nOne of the key events that had a significant impact on Acme Government Solutions' governance structure and operational strategies was the Shareholders' Meeting Resolution held in February 2021. This resolution resulted in several sub-events that shaped the company's direction and decision-making process. Firstly, the Board of Directors Election took place, leading to changes in the governance structure and operational strategies. The election of new board members brought fresh perspectives and expertise to the company's leadership.\nAnother sub-event following the Shareholders' Meeting Resolution was the appointment of a new CEO in March 2021. This change in leadership had a profound impact on the company's direction and decision-making process. The new CEO brought a strategic vision and implemented changes to improve operational efficiency and effectiveness.\nIn April 2021, Acme Government Solutions conducted a Financial Performance Review, which had a direct impact on the company's financial health and identified areas for improvement. The review provided valuable insights into the company's financial performance, allowing for strategic adjustments to enhance profitability and sustainability.\nFurthermore, in May 2021, Acme Government Solutions announced a Strategic Partnership, which expanded the company's capabilities and market reach. This partnership opened doors to new opportunities and positioned the company for growth in a competitive market.\nIn June 2021, Acme Government Solutions unveiled a New Market Expansion Plan, which aimed to diversify revenue streams and expand the client base. This initiative demonstrated the company's commitment to adapt to changing market dynamics and seize new business opportunities.\nCompliance and regulatory updates in March 2021 also played a crucial role in Acme Government Solutions' corporate governance. These updates ensured the company's adherence to laws and regulations, reinforcing its commitment to ethical practices and transparency.\nIn April 2021, a change in the Board of Directors further shaped the company's strategic direction and long-term development. The new board members brought diverse expertise and perspectives, contributing to effective decision-making and governance.\nMay 2021 witnessed senior management changes within Acme Government Solutions, which had a direct impact on the company's operational focus and strategic priorities. These changes aimed to align the management team with the company's vision and goals, enhancing overall performance.\nAcme Government Solutions also made significant progress in sustainability and social responsibility initiatives in June 2021. The company's commitment to environmental protection, social responsibility, and corporate citizenship positively impacted its public image and market competitiveness.\nThese events and indicators are closely tied to Acme Government Solutions' governance structure and practices. The company's commitment to information disclosure, related transactions, and internal control has been instrumental in ensuring transparency, fairness, and accountability.\nAcme Government Solutions has prioritized regular and timely information disclosure, providing stakeholders with the necessary information to make informed decisions. This commitment to transparency and accountability has strengthened the company's relationships with shareholders and other stakeholders.\nFurthermore, Acme Government Solutions has implemented policies, procedures, and measures to prevent conflicts of interest and ensure fairness in related transactions. This strict compliance with ethical standards has fostered trust and confidence among stakeholders.\nThe company has also established a robust internal control system, safeguarding its assets and preventing financial misstatements. The architecture, implementation, and effectiveness of this system have been continuously assessed to ensure its reliability and efficiency.\nTo further enhance corporate governance, Acme Government Solutions has outlined governance improvement plans. These plans include strengthening the function of the Board of Directors and Supervisory Board, enhancing transparency and the quality of information disclosure, and establishing an Ethics Committee. These initiatives aim to improve governance efficiency, promote ethical standards, and ensure the company's long-term success.\nIn terms of risk management strategy, Acme Government Solutions has focused on strengthening its internal control system, integrating sustainable development and social responsibility into its strategy, and enhancing cybersecurity measures. These efforts aim to identify, assess, monitor, and report risks effectively, while also addressing emerging challenges in the digital landscape.\nIn conclusion, Acme Government Solutions has demonstrated a strong commitment to corporate governance, with a clear focus on transparency, accountability, and stakeholder engagement. The significant events and indicators discussed in this report have shaped the company's governance structure, operational strategies, and long-term development. Through continuous improvement and a proactive approach to risk management, Acme Government Solutions is well-positioned for future success in the government services industry."""
        pages = text.split("\n")
        cfg = NodeSplitterConfig(
            chunk_size=128,
            chunk_overlap=64,
            default_language="en",
            overflow_strategy="fallback_split",
        )

        splitter = AdvancedSentenceSplitter(cfg)
        pages_d = [Page(document_fragements=[TextFragement(text=c)]) for c in pages]
        header_md = "| Name | Alter | Wohnort | PLZ | Straße"
        rows: list[str] = [
            "| Hans | 30 | Erfurt | 99085 | Altonaustraße",
            "| Jonas | 30 | Erfurt | 99085 | Altonaustraße",
            "| Sina | 30 | Erfurt | 99085 | Altonaustraße",
        ]
        page_t = Page(
            document_fragements=[
                TableFragement(full_tabel="", header=header_md, column=rows)
            ]
        )
        first_p = pages_d[:5]
        last_p = pages_d[5:]

        pages_d = [*first_p, page_t, *last_p]
        doc = Document(
            id="cap_all",
            content=pages_d,
            metadata={},
        )
        nodes = splitter.split_documents(doc)
        print("playground nodes:", len(nodes))
        for n in nodes:
            logger.error(n.content)
            logger.error(n.metadata)
            print(self._tok_len(n.content), cfg.chunk_size)
