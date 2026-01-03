import logging

from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM
from core.logger import init_logging
from hippo_rag.openie import AsyncOpenIE, OpenIEConfig
from domain_test.enviroment import llm

from domain_test.hippo_rag.openie_integration import TestAsyncOpenIE


init_logging("info")
logger = logging.getLogger(__name__)


class TestAsyncOpenIEOllama(TestAsyncOpenIE):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        self.llm = OpenAIAsyncLLM(
            ConfigOpenAI(
                model=llm.OPENAI_MODEL,
                max_tokens=8192,
                api_key=llm.OPENAI_HOST_KEY,
                timeout=60,
                temperature=0.5,
                context_cutoff=int(128_000 * 0.90),
                base_url=llm.OPENAI_HOST,
            )
        )
        self.openie = AsyncOpenIE(self.llm, OpenIEConfig(retries=2))


SAMPLE_PASSAGE = """
Overview of the FGK and its collaboration partners**Zeit Online** (03.03.2021)Overview and description of the FGK<https://www.zeit.de/campus/angebote/forschungskosmos/zukunftsfragen-der-forschung/fh-erfurt/nachhaltige-land-und-bodennutzung/index?utm_referrer=https%3A%2F%2Fwww.google.com%2F>**MDR Television** (25.08.2020)On Monday 13 July 2020, the Research Centre for Horticultural Crops was visited by a team from MDR.They are currently filming a feature for the series "Der Osten, entdecke wo du lebst" ("East Germany, explore your surroundings") on the topic of Erfurt's horticultural traditions.Alongside various horticultural businesses in and around Erfurt, who will report on the challenges they face today and their ideas for the future, the report will also feature us as a scientific institution.The research group for cultivation control will briefly present its work on the root development of cuttings, which is influenced by various factors such as lighting conditions.Many ornamental plants are propagated via cuttings, which are produced and grown during the winter months so that they are available for sale in the spring as ready-to-use products.For this reason, we are investigating, for example, how deliberate modification of the light spectrum affects the rooting of petunia cuttings.The analysis of root development and the mechanisms involved in the cuttings is expected to open up new approaches for businesses to dispense with chemical rooting agents and thus save energy by shortening the rooting phase.The report will be broadcast on Tuesday 25 August 2020 at 9 p.m. on MDR television and will also be available in the ARD Mediathek (media library) from 6 p.m. on 18 August 2020.**Kinder Uni**(13.02.2020)By: Luise ReiberCan plants feel stress?Research Centre for Horticultural Crops introduces young people to its workThe Research Centre for Horticultural Crops at the University of Applied Sciences Erfurt recently welcomed schoolchildren to two events as part of Erfurt's "Children's University".Today, under the guidance of PD Dr. Uwe Drüge, four pupils explored the question of how plants react to stress and what hormones and sugar have to do with this.They first learned about the theory of what plant stress really is and how it affects the plant.During an exercise on sugar analysis in plants, the pupils then gained an insight into practical plant research.On 4 and 5 February, seven pupils from the 11th grade of the Evangelisches Ratsgymnasium took part in the event entitled "How to become a genetic engineer", in which Professor Dr Philipp Franken informed the group about molecular biology and what genetic engineering is all about.They then carried out various experiments themselves, verified the results and discussed them in the group."Such in-depth exploration of a topic sadly does not happen in everyday school settings for a variety of reasons," explains Heidrun Poltermann, who accompanied the group."We are therefore grateful that Professor Franken and his staff took the time to introduce these young people to an area that would have remained unknown to them without the Kinder-Uni. A fantastic event that was very individual and professional!""The students were very enthusiastic, and it is always nice for us to experience this kind of thing," said Professor Dr Philipp Franken, Director of the Research Centre, who hosted the event."Erfurt's Children's University is a collaborative project involving the University, the University of Applied Sciences and Helios Klinikum Erfurt.In both the summer and winter semesters, they offer a broad range of activities for different age groups on a wide variety of topics.The group from the Ratsgymnasium at the Research Centre for Horticultural Crops.**Kinder Uni**(04.-05.02.2020)How to become a genetic engineer (presentation and experiment)FH Erfurt press release**Lange Nacht der Wissenschaften** (15.11.2019)What's growing?For the "Long Night of Science" in Erfurt, the Research Centre for Horticultural Crops took a closer look at microbiology.Visitors had the opportunity to make specimen dishes and test various objects such as coins, banknotes, mobile phones, the surface of the skin or even their own hair for the presence of microorganisms.If you have any questions, please contact: katja.burow@fh-erfurt.de
"""
