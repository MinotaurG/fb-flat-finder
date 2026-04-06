# finetune.py
"""Finetune a tiny model for flat listing extraction using MLX on Apple Silicon."""
import json
import os
import subprocess

MODEL = "mlx-community/gemma-3-1b-it-4bit"
OUTPUT_DIR = "flat-finder-model"
TRAIN_FILE = "training_data_chat.jsonl"
EPOCHS = 6
BATCH_SIZE = 2
LEARNING_RATE = 1e-5
LORA_RANK = 8

# Step 1: Split training data into train/valid
print("Preparing data...")
with open(TRAIN_FILE) as f:
    data = [json.loads(line) for line in f]

split = int(len(data) * 0.9)
train_data = data[:split]
valid_data = data[split:]

os.makedirs("data", exist_ok=True)
with open("data/train.jsonl", "w") as f:
    for d in train_data:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
with open("data/valid.jsonl", "w") as f:
    for d in valid_data:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"Train: {len(train_data)} | Valid: {len(valid_data)}")

# Step 2: Run finetuning via mlx_lm CLI
print(f"\nFinetuning {MODEL}...")
cmd = [
    "python3", "-m", "mlx_lm", "lora",
    "--model", MODEL,
    "--data", "data",
    "--train",
    "--batch-size", str(BATCH_SIZE),
    "--num-layers", "8",
    "--iters", str(len(train_data) // BATCH_SIZE * EPOCHS),
    "--learning-rate", str(LEARNING_RATE),
    "--adapter-path", OUTPUT_DIR,
]

print(f"Running: {' '.join(cmd)}\n")
result = subprocess.run(cmd)

if result.returncode == 0:
    print(f"\nFinetuning complete! Adapter saved to {OUTPUT_DIR}/")
    print(f"\nTo test:")
    print(f"  python3 -m mlx_lm.generate --model {MODEL} --adapter-path {OUTPUT_DIR} --prompt 'test'")
    print(f"\nTo fuse into a standalone model:")
    print(f"  python3 -m mlx_lm.fuse --model {MODEL} --adapter-path {OUTPUT_DIR} --save-path {OUTPUT_DIR}-fused")
    print(f"\nTo convert to GGUF for Ollama:")
    print(f"  python3 -m mlx_lm.convert --model {OUTPUT_DIR}-fused --quantize q4_k_m --upload-repo YOUR_HF_REPO")
else:
    print(f"\nFinetuning failed with exit code {result.returncode}")
