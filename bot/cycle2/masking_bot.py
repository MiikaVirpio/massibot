from langgraph.graph import StateGraph, END, MessagesState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage

from bot.cycle2.mask_maker import EmojiMasker

"""
This is a linear graph with nodes for encoding, processing with a language model, and decoding.
It uses the EmojiMasker to mask sensitive information in the input text with emojis, that was created in the end of Cycle 2.
"""

llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0.2, max_tokens=256)
emoji_masker = EmojiMasker()


class MaskingState(MessagesState):
    maskings: list

def encode_node(state: MaskingState):
    user_message = state.get("messages")[-1]
    masked_input, maskings = emoji_masker.mask_text(user_message.content)
    return_messages = [RemoveMessage(id=user_message.id), HumanMessage(content=masked_input)]
    return {"messages": return_messages, "maskings": maskings}

SYSTEM_PROMPT = """You are a helpful assistant answering to questions considering confidental texts.
You will be offered sensitive texts that you must analyze and answer questions about them.
The text will be masked with emojis to protect critical information. If you must refet to a masked part, you must use the emoji as a reference.
Do not comment about masking. Do not preamble. Just answer the question."""

def language_model(state: MaskingState):
    messages = state.get("messages")
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    response = llm.invoke([system_message] + messages)
    return {"messages": [response]}

def decode_node(state: MaskingState):
    maskings = state.get("maskings")
    ai_message = state.get("messages")[-1]
    decoded_content = emoji_masker.unmask_new_text(ai_message.content, maskings)
    return_messages = [RemoveMessage(id=ai_message.id), AIMessage(content=decoded_content)]
    return {"messages": return_messages, "maskings": []} # Remark: Note the adding of decoded message to messages.
    # Remark: Messages would be available to AI next round, revealing the decoded content in past messages.
    # Remark: To fix this, the language_model node could have a separate state storing only the masked messages.

workflow = StateGraph(MaskingState)
workflow.add_node("encode", encode_node)
workflow.add_node("llm", language_model)
workflow.add_node("decode", decode_node)
workflow.set_entry_point("encode")
workflow.add_edge("encode", "llm")
workflow.add_edge("llm", "decode")
workflow.add_edge("decode", END)
graph = workflow.compile()


"""HUMAN: Please help I cant seem to find invoice information in this contract. Is there someone I could call? 

The CONSULTANT (Miika Koodaaja) will be reimbursed after receipt by the COMMISSION’s Contract Manager (Matti Manageri) of 
itemized invoices to miika@superconsultancy.fi. Invoices shall be submitted no later than 45calendar days after the performance of 
work for which the CONSULTANT (Miika Koodaaja) is billing. Invoices shall be mailed to the COMMISSION’s 
Contract Manager (Matti Manageri)  at the following address:  
MegaCorp AB Oyj, 1523 Nurmijärvenpolku, Santa Cruz, Espoo, 95060 
The invoices must include the following information: 
1. Labor (staff name, hours charged, hourly billing rate, current charges and cumulative 
charges) performed during the billing period by task. (Call secretary Laura Laskuttaja at +358 50 123 4567 in case of questions about the invoice); 
2. Itemized expenses incurred during the billing period; 
3. Total invoice/payment requested to account number FI00 1234 5600 0000 0000; 
4. Total amount previously paid under this Agreement; 
5. Report of expenditures by CONSULTANT (Miika Koodaaja)a nd subconsultants for each task and subtask 
6. or milestone and estimated percentage completion by such divisions of wo ctrl+v supgmrn
Gunggu555!xl -----------"""

"""HUMAN_MASKED: Please help I cant seem to find invoice information in this contract. Is there someone I could call? 

The CONSULTANT (😊👤 will be reimbursed after receipt by the COMMISSION’s Contract Manager (Matti Manageri) of 
itemized invoices to🧑‍💻superconsultancy.fi. Invoices shall be submitted no later than 45calendar days after the performance of 
work for which the CONSULTANT (😊👤 is billing. Invoices shall be mailed to the COMMISSION’s 
Contract Manager (Matti Manageri)  at the following address:  
MegaCorp AB Oyj,🏠🛣️🛣️🏙️🏷️ invoices must include the following information: 
1. Labor (staff name, hours charged, hourly billing rate, current charges and cumulative 
charges) performed during the billing period by task. (Call secretary Laura👤📞 case of questions about the invoice); 
2. Itemized expenses incurred during the billing period; 
3. Total invoice/payment requested to account number FI00 1234 5600 0000 0000; 
4. Total amount previously paid under this Agreement; 
5. Report of expenditures by CONSULTANT (😊👤a nd subconsultants for each task and subtask 
6. or milestone and estimated percentage completion by such divisions of🧑‍💻unggu🧑‍💻xl -----------"""

"""AI_MASKED: You can contact secretary Laura👤📞 for questions about the invoice."""

"""AI_UNMASKED: You can contact secretary Laura Koodaaja +358 50 123 4567 for questions about the invoice."""