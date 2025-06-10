import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

"""
https://huggingface.co/iiiorg/piiranha-v1-detect-personal-information
Thanks to iiiorg fine-tuning DeBERTa for PII detection, this tool maskes personal information in text with emojis.
Rudimentatry unmasking implemented, but as expanded in the thesis, it is far from functional.
"""

class EmojiMasker:
    def __init__(self, model_name="iiiorg/piiranha-v1-detect-personal-information"):
        self.device = "cuda"
        self.model = AutoModelForTokenClassification.from_pretrained(model_name).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.original_labels = self.model.config.id2label
        self.labels = {
            0: "🧾",
            1: "🏠",
            2: "🏙️",
            3: "💳",
            4: "🎂",
            5: "🚗",
            6: "📧",
            7: "😊",
            8: "🆔",
            9: "🔑",
            10: "🫂",
            11: "🛣️",
            12: "👤",
            13: "⚖️",
            14: "📞",
            15: "🧑‍💻",
            16: "🏷️",
            17: "🆗"
        }

    def mask_text(self, text_input):
        # Start-end character offsets for each token
        offset_mapping = self.tokenizer.encode_plus(text_input, return_offsets_mapping=True, add_special_tokens=True)["offset_mapping"]
        # Input tensors for the model
        input_tensors = self.tokenizer(text_input, return_tensors="pt", truncation=True, padding=True)
        input_tensors = {k: v.to(self.device) for k, v in input_tensors.items()}
        with torch.no_grad():
            outputs = self.model(**input_tensors) # outputs dims: [batch_size, sequence_length, num_labels]
        predicted = torch.argmax(outputs.logits, dim=2)[0] # Sequence length tensor of argmax predictions
        encoded_input = self.tokenizer.encode_plus(text_input, return_offsets_mapping=True, add_special_tokens=True)
        offset_mapping = encoded_input["offset_mapping"]
        input_ids = encoded_input["input_ids"]
        # Iterate sequence offset aware
        maskings = []
        char_list = list(text_input)
        masking = False
        masking_label = None
        masking_start = None
        masked_ids = []
        for i, (start_char, end_char) in enumerate(offset_mapping):
            if start_char == end_char:
                continue
            input_id = input_ids[i]
            label = predicted[i].item()
            if label != 17: # Bad stuff found
                if not masking: # Hit a new baddie
                    masking = True # Start masking token or continue
                    masking_label = label # This label is being masked
                    masking_start = start_char # Masking starts here
                    masked_ids = [] # Stare new masked ids
                elif label != masking_label: # Masking, but hit a new baddie
                    maskings.append([i, masking_start, start_char, masked_ids, masking_label]) # Store previous mask
                    masking_label = label # Label to mask changed
                    masking_start = start_char # Masking new baddie starts here
                    masked_ids = [] # Start new masked ids
                # Masking baddies continues
                masked_ids.append(input_id)# This input is masked
            elif masking: # No bad stuff, stop masking
                maskings.append([i, masking_start, end_char, masked_ids, masking_label]) # Store the mask
                masking = False
        if masking: # Still masking, last token baddie
            maskings.append([len(offset_mapping), masking_start, len(char_list),masked_ids, masking_label])
        # Mask input text and return maskings
        for mask in maskings:
            for j in range(mask[1], mask[2]):
                char_list[j] = ""
            char_list[mask[1]] = self.labels.get(mask[4])
        output_text = "".join(char_list)
        return output_text, maskings

    def unmask_same_text(self, masked_text, maskings):
        for mask in maskings:
            masked_label = self.labels.get(mask[4])
            i = masked_text.find(masked_label)
            l_pad = " " if masked_text[i-1:i] != " " else ""
            r_pad = " " if masked_text[i+1:i+2] != " " else ""
            text_piece = self.tokenizer.decode(mask[3], skip_special_tokens=True)
            right_half = r_pad + masked_text[i+1:] if i + 1 < len(masked_text) else ""
            masked_text = masked_text[:i] + l_pad + text_piece + right_half
        return masked_text

    def unmask_new_text(self, masked_text, maskings):
        # Format a set from maskings with key being the labe and balue first hit masked_ids
        label_set = {}
        for mask in maskings:
            label_set[mask[4]] = mask[3]  # Use first masked id for each label
        # Replace each label in masked_text with the corresponding text from label_set
        for label, masked_ids in label_set.items():
            masked_label = self.labels.get(label)
            while masked_label in masked_text:  # Handle multiple occurrences of the same label
                i = masked_text.find(masked_label)
                if i != -1:  # If the label is found in the text
                    l_pad = " " if masked_text[i-1:i] != " " else ""
                    r_pad = " " if masked_text[i+1:i+2] != " " else ""
                    text_piece = self.tokenizer.decode(masked_ids, skip_special_tokens=True)
                    right_half = r_pad + masked_text[i+1:] if i + 1 < len(masked_text) else ""
                    masked_text = masked_text[:i] + l_pad + text_piece + right_half
        return masked_text

#example_text = "Hello, its Miika, I would like to order pizzat to Kattokatu 123, 00403 Helsinki. Call me at +358401234567 or email me at miika@bestconsultancy.fi, if you get lost."
#masked_text, maskings = mask_maker.mask_text(example_text)
## 'Hello, its😊 I would like to order pizzat to🛣️🏠🏷️🏙️ Call me at📞 email me at🧑\u200d💻bestconsultancy.fi, if you get lost.'
#unmasked_text = mask_maker.unmask_same_text(masked_text, maskings) # Use maskings for same text
## 'Hello, its Miika I would like to order pizzat to Kattokatu ️ 123 00403 ️ Helsinki ️ Call me at +358401234567 email me at miika \u200d💻bestconsultancy.fi, if you get lost.'
#new_text_example = "I cant reach you 😊 but I know your friend 😊 phonenumber is 📞, or I drop by his house at 🛣️."
#new_text_unmasked = mask_maker.unmask_new_text(new_text_example, maskings) # Use maskings for different text
## 'I cant reach you Miika but I know your friend Miika phonenumber is +358401234567 , or I drop by his house at Kattokatu ️.'
