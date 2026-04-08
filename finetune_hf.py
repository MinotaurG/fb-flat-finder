# finetune_hf.py
"""Finetune using transformers + PEFT for portable GGUF output."""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

# Config
BASE_MODEL = "google/gemma-3-1b-it"
OUTPUT_DIR = "flat-finder-hf"
EPOCHS = 6
BATCH_SIZE = 1
LEARNING_RATE = 2e-5
MAX_SEQ_LENGTH = 512

# Use MPS (Apple Silicon GPU) if available
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map=device,
)

print("Adding LoRA adapters...")
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

print("Loading training data...")
dataset = load_dataset("json", data_files="training_data_chat.jsonl", split="train")


def format_chat(example):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


dataset = dataset.map(format_chat)
dataset = dataset.train_test_split(test_size=0.1, seed=42)

print(f"Train: {len(dataset['train'])} | Valid: {len(dataset['test'])}")
print("Starting training...")

trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    args=SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=8,
        learning_rate=LEARNING_RATE,
        fp16=True,
        logging_steps=20,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        warmup_steps=10,
        optim="adamw_torch",
        seed=42,
        dataloader_pin_memory=False,
        max_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
    ),
)

trainer.train()

print("Merging LoRA weights into base model...")
merged = model.merge_and_unload()
merged.save_pretrained(f"{OUTPUT_DIR}-merged")
tokenizer.save_pretrained(f"{OUTPUT_DIR}-merged")

print(f"\nDone! Merged model saved to {OUTPUT_DIR}-merged/")
print(f"\nTo convert to GGUF:")
print(f"  python3 /tmp/llama.cpp/convert_hf_to_gguf.py {OUTPUT_DIR}-merged --outfile flat-finder.gguf --outtype q8_0")
print(f"\nTo load into Ollama:")
print(f"  ollama create flat-finder -f Modelfile")
