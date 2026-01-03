import logging
import pytest

from domain.hippo_rag.interfaces import OpenIEInterface
from domain_test import AsyncTestBase


logger = logging.getLogger(__name__)


class TestAsyncOpenIE(AsyncTestBase):
    openie: OpenIEInterface

    async def test_ner_basic(self):
        passage = (
            "Albert Einstein was born in Ulm and later worked at ETH Zurich and "
            "Princeton University with colleagues such as Niels Bohr."
        )
        res = await self.openie.ner(chunk_key="c1", passage=passage)
        if res.is_error():
            logger.error("NER error: %s", res.get_error())
        assert res.is_ok()

        out = res.get_ok()
        assert out.chunk_id == "c1"
        assert isinstance(out.unique_entities, list)
        assert len(out.unique_entities) > 0
        assert all(e.strip() for e in out.unique_entities)

    async def test_triple_extraction_basic(self):
        passage = (
            "Albert Einstein developed the theory of relativity and worked at Princeton University. "
            "He collaborated with Niels Bohr."
        )
        named_entities = [
            "Albert Einstein",
            "Niels Bohr",
            "Princeton University",
            "theory of relativity",
        ]

        res = await self.openie.triple_extraction(
            chunk_key="c2",
            passage=passage,
            named_entities=named_entities,
        )
        if res.is_error():
            logger.error("Triples error: %s", res.get_error())
        assert res.is_ok()

        out = res.get_ok()
        assert out.chunk_id == "c2"
        assert isinstance(out.triples, list)
        assert len(out.triples) > 0
        for t in out.triples:
            assert len(t) == 3
            assert all(x.strip() for x in t)

    async def test_openie_chain(self):
        passage = (
            "Marie Curie discovered radium and polonium in Paris. "
            "She worked at the University of Paris and won two Nobel Prizes."
        )

        res = await self.openie.openie(chunk_key="c3", passage=passage)
        if res.is_error():
            logger.error("OpenIE chain error: %s", res.get_error())
        assert res.is_ok()

        combined = res.get_ok()
        ner_out = combined.ner
        tri_out = combined.triplets

        assert len(ner_out.unique_entities) > 0
        assert isinstance(tri_out.triples, list)
        for t in tri_out.triples:
            assert len(t) == 3

    async def test_batch_openie(self):
        chunks = {
            "k1": "Ada Lovelace worked with Charles Babbage on the Analytical Engine in London.",
            "k2": "Alan Turing studied at Cambridge University and worked at Bletchley Park.",
            "k3": "Grace Hopper developed COBOL while serving in the U.S. Navy.",
        }

        res = await self.openie.batch_openie(chunks)
        if res.is_error():
            pytest.fail(f"batch_openie failed: {res.get_error()}")

        ner_ok, triples_ok = res.get_ok()
        assert isinstance(ner_ok, dict)
        assert isinstance(triples_ok, dict)
        assert len(ner_ok) >= 1

        for k, ner_out in ner_ok.items():
            assert k in chunks
            assert isinstance(ner_out.unique_entities, list)

        for k, tri_out in triples_ok.items():
            assert k in chunks
            assert isinstance(tri_out.triples, list)
            for t in tri_out.triples:
                assert len(t) == 3

    async def test_batch_openie_metadata(self):
        metadata = {"source": "Ada Lovelance Live Story"}
        chunks = {
            "k1": "Ada Lovelace worked with Charles Babbage on the Analytical Engine in London.",
            "k2": "Alan Turing studied at Cambridge University and worked at Bletchley Park.",
            "k3": "Grace Hopper developed COBOL while serving in the U.S. Navy.",
        }

        res = await self.openie.batch_openie(chunks, metadata)
        if res.is_error():
            pytest.fail(f"batch_openie failed: {res.get_error()}")

        ner_ok, triples_ok = res.get_ok()
        assert isinstance(ner_ok, dict)
        assert isinstance(triples_ok, dict)
        assert len(ner_ok) >= 1

        for k, ner_out in ner_ok.items():
            assert k in chunks
            assert isinstance(ner_out.unique_entities, list)

        for k, tri_out in triples_ok.items():
            assert k in chunks
            assert isinstance(tri_out.triples, list)
            for t in tri_out.triples:
                assert len(t) == 3

    async def test_playground(self):
        metadata = {"source": "Ada Lovelance Live Story"}
        chunks = {"k1": DOZENTEN_TEXT}

        res = await self.openie.batch_openie(chunks, metadata)
        if res.is_error():
            pytest.fail(f"batch_openie failed: {res.get_error()}")

        ner_ok, triples_ok = res.get_ok()
        assert isinstance(ner_ok, dict)
        assert isinstance(triples_ok, dict)
        assert len(ner_ok) >= 1

        for k, ner_out in ner_ok.items():
            logger.error(ner_out.unique_entities)
            assert k in chunks
            assert isinstance(ner_out.unique_entities, list)

        for k, tri_out in triples_ok.items():
            logger.error(tri_out.triples)
            assert k in chunks
            assert isinstance(tri_out.triples, list)
            for t in tri_out.triples:
                assert len(t) == 3


DOZENTEN_TEXT = """
Dozenten der Angewandten Informatik
===================================
#### Prof. Dr. Oksana Arnold
Professur Theoretische Informatik / Künstliche Intelligenz
0361 / 6700 5531 und +4915253509461
[oksana.arnold[at]fh-erfurt.de](#)
#### Prof. Dr. Steffen Avemarg
Professur Praktische Informatik / Mobile Computing
0361 / 6700-5511
[steffen.avemarg[at]fh-erfurt.de](#)
#### Prof. Dr. Kay Gürtzig
Professur Grundlagen der Informatik und Betriebssysteme
0361 / 6700-5513
[kay.guertzig[at]fh-erfurt.de](#)
#### Dipl.Math. Anja Haußen
Lehrkraft für besondere Aufgaben
0361 / 6700 5533
[anja.haussen[at]fh-erfurt.de](#)
#### Prof. Dr. Volker Herwig
Professur Wirtschaftsinformatik
0361 / 6700-5512
[volker.herwig[at]fh-erfurt.de](#)
#### Prof. Rolf Kruse
Professur Digitale Medien und Gestaltung
+49 172 302 86 58
[rolf.kruse[at]fh-erfurt.de](#)
#### Prof. Dr. Anna Neovesky
Professur für Digital Humanities - Hybride Bildungs- und Kommunikationsräume
0361 / 6700-5610
[anna.neovesky[at]fh-erfurt.de](#)
#### Prof. Dr. Jörg Sahm
Professur Grafische Datenverarbeitung / Softwaretechnik
0361 / 6700 5517
[joerg.sahm[at]fh-erfurt.de](#)
#### Prof. Dr. Gunar Schorcht
Professur Netzwerke, IT-Sicherheit, Kryptologie
0361 / 6700 5515
[schorcht[at]fh-erfurt.de](#)
#### Prof. Dr. Marcel Spehr
Professur Web-Engineering
0361 / 6700 5539
[marcel.spehr[at]fh-erfurt.de](#)
#### Prof. Dr. Nadine Steinmetz
Professur Data Engineering / Data Science
+49 361 6700 5543
[nadine.steinmetz[at]fh-erfurt.de](#)
#### Prof. Dr. Volker Zerbe
Professur Technische Informatik / Eingebettete Systeme
0361 / 6700 5536 und +491733727314
[volker.zerbe[at]fh-erfurt.de](#)
* Contact
**Visiting address:**
Fachhochschule Erfurt
**Mailing address:**
Postfach 45 01 55
* University
* [About us](https://www.fh-erfurt.de)
* [Student Portal](http://www.ab-in-den-hoersaal.de/)
* [Approach](#collapseContactDesktop)
* [Library]( https://www.fh-erfurt.de/fhe/zentrale-einrichtungen/bibo/startseite/)
* [Mensa]( http://www.stw-thueringen.de/deutsch/mensen/einrichtungen/erfurt/mensa-altonaer-strasse.html#speisepl)
* Service
* [Office](/en/fachrichtung/gremien-leitung/studiengangsleitung)
* [Webmail](https://fhemail.fh-erfurt.de/)
* [Moodle](https://moodle.fh-erfurt.de/login/index.php)
* [FHEcampus](https://ecampus.fh-erfurt.de)
* Others
* [Contact](/en/schulze)
* [Imprint](/en/impressum)
* [Data protection](/en/datenschutz)
* [Search](/en/suche)
"""
