from mistral_inference.transformer import Transformer
from mistral_inference.generate import generate

from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.protocol.instruct.messages import UserMessage
from mistral_common.protocol.instruct.request import ChatCompletionRequest

tokenizer = MistralTokenizer.from_file("7Bv3/tokenizer.model.v3")
model = Transformer.from_folder("7Bv3")
model.load_lora("lora/3/lora.safetensors")

prompt = "Miksi Osakesäästötili on parempi?"

completion_request = ChatCompletionRequest(messages=[UserMessage(content=prompt)])

tokens = tokenizer.encode_chat_completion(completion_request).tokens

out_tokens, _ = generate([tokens], model, max_tokens=1024, temperature=0.35, eos_id=tokenizer.instruct_tokenizer.tokenizer.eos_id)
result = tokenizer.instruct_tokenizer.tokenizer.decode(out_tokens[0])

with_lora = """Osakesäästötili on usein edullisempaa kuin muut säästötilit, 
koska säästösi kasvattavat lainkaan ei veroteta vuosittain. 
Sen sijaan vero maksetaan vasta tilin otetusta varoista, 
kun noudatat lainan enimmäismaksu- ja -sidonten ehdot. 
Osakesäästötilillä voit sijoittaa osakkeita, rahasto-osuuksia 
ja rahasto-rahastoja, ja säästösi voivat olla täysin automaattisesti 
hoidetut. Huomioi kuitenkin, että osakesäästötilillä ei yleensä ole 
maksuvapaata tilipäivää, joten varmista, että tilille tulevat varat 
ovat suunniteltuja ja et käytä tilipäivänä tilille siirrettyä rahaa."""

without_lora = """Osakesäästötili on parempi siksi, että se säästää 
verot ja antaa yhteisöllisesti hallinnan osallistuvuuden osakkailijalle. 
Se on erityisesti hyötyäntä yrittäjille ja työpaikkojen hankkeille, 
koska se sallii yhteisöllisen osakkailijan osallistumisen yrityksen 
kehityksessä ja toiminnassa. Osakesäästötilin maksut ovat myös alennuttavat 
verotuksen verrattuna tila- ja tuki-tiloihin.\n\nOsakesäästötilin yhteisöllinen 
luonnonsuhteellinen osallistuminen myös edistää yrityksen kokonaisuuden ja 
suunnittelun tarkkuuden, siksi että kaikki osakkailijat voivat osallistua 
yrityksen kehityksessä ja suunnittelussa. Tämä edistää yrityksen kokonaisuuden 
ja suunnittelun tarkkuuden, joten se voi parantaa yrityksen tulokset ja 
kokonaisuus.\n\nOsakesäästötilin yhteisöllinen luonnonsuhteellinen osallistuminen 
myös edistää yrityksen kokonaisuuden ja suunnittelun tarkkuuden, siksi että kaikki 
osakkailijat voivat osallistua yrityksen kehityksessä ja suunnittelussa. 
Tämä edistää yrityksen kokonaisuuden ja suunnittelun tarkkuuden, joten se voi 
parantaa yrityksen tulokset ja kokonaisuus.\n\nOsakesäästötilin yhteisöllinen 
luonnonsuhteellinen osallistuminen myös edistää yrityksen kokonaisuuden ja 
suunnittelun tarkkuuden, siksi että kaikki osakkailijat voivat osallistua 
yrityksen kehityksessä ja suunnittelussa. Tämä edistää yrityksen kokonaisuuden 
ja suunnittelun tarkkuuden, joten se voi parantaa yrityksen tulokset ja 
kokonaisuus.\n\nOsakesäästötilin yhteisöllinen luonnonsuhteellinen 
osallistuminen myös edistää yrityksen kokonaisuuden ja suunnittelun 
tarkkuuden, siksi että kaikki osakkailijat voivat osallistua yrityksen 
kehityksessä ja suunnittelussa. Tämä edistää yrityksen kokonaisuuden ja 
suunnittelun tarkkuuden, joten se voi parantaa yrityksen tulokset ja 
kokonaisuus.\n\nOsakesäästötilin yhteisöllinen luonnonsuhteellinen 
osallistuminen myös edistää yrityksen kokonaisuuden ja suunnittelun 
tarkkuuden, siksi että kaikki osakkailijat voivat osallistua yrityksen 
kehityksessä ja suunnittelussa. Tämä edistää yrityksen kokonaisuuden ja 
suunnittelun tarkkuuden, joten se voi parantaa yrityksen tulokset ja 
kokonaisuus.\n\nOsakesäästötilin yhteisöllinen luonnonsuhteellinen 
osallistuminen myös edistää yrityksen kokonaisuuden ja suunnittelun 
tarkkuuden, siksi että kaikki osakkailijat voivat osallistua yrityksen ke"""

