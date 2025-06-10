from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from peft import AutoPeftModelForCausalLM

model = AutoPeftModelForCausalLM.from_pretrained("output/checkpoint-300").to("cuda:0")
#model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")

pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")

messages = [{"role": "user", "content": 
    "Miksi Osakesäästötili on parempi?"
}]

outputs = pipe(messages)

outputs[0]["generated_text"][-1]

with_lore = """ Osakesäästötili voi olla parempi kuin muu 
taloudellinen tili, jos se antaa vähemmän kuin yksityiselle pankkikortille 
osakekaupan yhteiskäytäntö. Osakesäästötili tarjoaa myös mahdollisuuden 
hankkia osakekaupan tavoitteella, että osakekauppa on vähemmän kuin yksityiselle 
pankkikortille.
"""

without_lora = """Osakesäästötila on yksi osakeyhtiön tarpeesta osakkaan 
tarjoamassa toiminnasta ja hoidosta. Tämä tarkoittaa, että osakkaat voivat 
osallistua säästörajoitteeseen ja ylläpitää osakkeen säästöpäästöä. 
Osakesäästötila on paremmin kuin osakkaan tarjoamat säästörahjeet, koska 
säästörahjeet ovat osa yhteisöjä säästöpäästöä.\n\nOsakesäästötila on myös 
yksi yhtiön toiminnanvaihtelun ja -tapahtumien vaikutusta. Tämä tarkoittaa, 
että yhtiö on yhtenäisesti tarjoava toiminta ja -tapahtuma, jolloin osakkaat 
ovat yhtenäisesti tarjoavat säästörahjeita. Osakesäästötila on myös tärkeä osa yhtiön
"""