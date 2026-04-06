# finetune.py
"""Finetune a tiny model for flat listing extraction using Unsloth."""
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# Config
BASE_MODEL = "unsloth/gemma-3-1b-it"
OUTPUT_DIR = "flat-finder-model"
MAX_SEQ_LENGTH = 1024
EPOCHS = 3
BATCH_SIZE = 2
LEARNING_RATE = 2e-4

print("Loading base model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=True,
)

print("Adding LoRA adapters...")
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

print("Loading training data...")
dataset = load_dataset("json", data_files="training_data_chat.jsonl", split="train")

def format_chat(example):
    """Format chat messages into the model's expected format."""
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}

dataset = dataset.map(format_chat)

print(f"Training on {len(dataset)} examples...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=4,
        learning_rate=LEARNING_RATE,
        fp16=False,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        warmup_steps=5,
        optim="adamw_8bit",
        seed=42,
    ),
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",
)

print("Starting training...")
trainer.train()

print("Saving model...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

# Also save as GGUF for Ollama
print("Exporting to GGUF for Ollama...")
model.save_pretrained_gguf(
    f"{OUTPUT_DIR}-gguf",
    tokenizer,
    quantization_method="q4_k_m",
)

print(f"Done! Model saved to {OUTPUT_DIR} and {OUTPUT_DIR}-gguf")
print(f"\nTo use with Ollama:")
print(f"  ollama create flat-finder -f {OUTPUT_DIR}-gguf/Modelfile")
