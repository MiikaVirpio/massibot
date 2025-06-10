
import os
os.environ["WANDB_PROJECT"]="finellama"
os.environ["WANDB_LOG_MODEL"]="false"
os.environ["WANDB_WATCH"]="false"
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer, SFTConfig, ModelConfig, get_quantization_config, get_peft_config, get_kbit_device_map

model_config = ModelConfig(
    model_name_or_path="meta-llama/Llama-3.2-1B-Instruct",
    trust_remote_code=True,
    use_peft=True,
    load_in_4bit=True,
)
quantization_config = get_quantization_config(model_config)
peft_config = get_peft_config(model_config)
training_config = SFTConfig(
    output_dir="output",
    num_train_epochs=20,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    learning_rate=2e-5,
    gradient_accumulation_steps=2,
    logging_steps=25,
    save_steps=150,
    max_grad_norm=2,
    log_level="info",
    report_to="wandb",
    run_name="run2",
)

model = AutoModelForCausalLM.from_pretrained(
    model_config.model_name_or_path,
    revision=model_config.model_revision,
    trust_remote_code=model_config.trust_remote_code,
    attn_implementation=model_config.attn_implementation,
    torch_dtype=model_config.torch_dtype,
    use_cache=False,
    device_map=get_kbit_device_map() if quantization_config is not None else None,
    quantization_config=quantization_config,
    )
tokenizer = AutoTokenizer.from_pretrained(model_config.model_name_or_path, trust_remote_code=model_config.trust_remote_code, use_fast=True)

dataset = load_dataset("json", data_files="semigenerated1.jsonl")["train"].train_test_split(test_size=0.05, seed=42)

trainer = SFTTrainer(
    model=model,
    args=training_config,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    processing_class=tokenizer,
    peft_config=peft_config,
)

# ------- Start training ------- #

trainer.train()

# Save the model
trainer.save_model(training_config.output_dir)



"""
***** Running training *****
  Num examples = 189
  Num Epochs = 20
  Instantaneous batch size per device = 4
  Total train batch size (w. parallel, distributed & accumulation) = 8
  Gradient Accumulation steps = 2
  Total optimization steps = 480
  Number of trainable parameters = 1,703,936
TrainOutput(global_step=480, training_loss=2.363597800334295, 
metrics={'train_runtime': 1496.8479, 'train_samples_per_second': 2.525, 
'train_steps_per_second': 0.321, 'total_flos': 1.4449751880781824e+16, 
'train_loss': 2.363597800334295})
"""