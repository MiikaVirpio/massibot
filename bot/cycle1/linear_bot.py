from langgraph.graph import StateGraph, END, MessagesState
from langchain_openai import ChatOpenAI

"""
This is the single LLM bot to test out raw LLM answers.
"""

# o4-mini (1.1$/1M), chatgpt-4o-latest (5$/1M)
llm = ChatOpenAI(model="chatgpt-4o-latest")

def language_model(state: MessagesState):
    messages = state.get("messages")
    response = llm.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(MessagesState)
workflow.add_node("llm", language_model)
workflow.set_entry_point("llm")
workflow.add_edge("llm", END)
graph = workflow.compile()

prompt = "Miksi Osakesäästötili on parempi?"

# o4 mini hallucinates ETFs to be allowed and even says that derivatives are possible with a special permission.
o4_mini_response = """Osakesäästötilin (OST) “paremmuus” verrattuna perinteiseen arvo-osuustiliin tai rahastosijoittamiseen perustuu pääasiassa verotuksen ja hallinnoinnin etuihin. Tässä tärkeimmät syyt, miksi moni sijoittaja valitsee OST:n:

1. Verotus lykkääntyy poisostohetkeen asti  
   - OST:llä toteutuneita arvonnousuja ja osinkoja ei veroteta vuosittain eikä kaupankäyntitapahtumasta, vaan vasta silloin kun nostat käteistä tililtä.  

...

Yhteenveto  
Jos tavoitteena on pitkäjänteinen osakesijoittaminen, aktiivinen kauppojen tekeminen tai salkun rebalance ilman kertasuorituksia verottajalle, osakesäästötili tarjoaa selkeitä etuja. Verojen lykkääminen nostoon asti, automaattinen kirjanpito ja mahdollisuus käyttää koko tuotot uudelleen sijoittamiseen tekevät OST:stä monelle sijoittajalle “paremman” vaihtoehdon perinteiselle arvo-osuustilille.
"""


# ChatGPT does a mistake in the limit, but knows which instrumets are allowed.
chatgpt_4o_response = """Osakesäästötili voi olla parempi vaihtoehto tietyissä tilanteissa sijoittajalle, joka haluaa sijoittaa osakkeisiin pitkällä aikavälillä. Tässä on useita syitä, miksi osakesäästötili voi olla kannattava ratkaisu:

1. **Verotuksen lykkääntyminen**  
   Osakesäästötilillä ei makseta veroa myyntivoitoista tai osingoista heti niiden realisoituessa. Sen sijaan vero maksetaan vasta silloin, kun tililtä nostetaan rahaa. Tämä antaa sijoittajalle mahdollisuuden:

...

**Yhteenveto:**
Osakesäästötili on erityisen hyödyllinen pitkän aikavälin sijoittajalle, joka haluaa hyödyntää korkoa korolle -efektiä mahdollisimman tehokkaasti ja lykätä verojen maksua. Se tarjoaa joustavuutta ja kantaa etuja aktiivisellekin osakesijoittajalle, kunhan sijoitusten luonne ja tavoitteet sopivat tilin rajoituksiin.

"""







