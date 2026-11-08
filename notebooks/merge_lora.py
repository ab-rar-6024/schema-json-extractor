"""Merge the SchemaForge LoRA adapter into the base weights and save fp16.

The merged model is just base + adapter: if you have the 240 MB adapter and a network
connection, you can reproduce this locally in a couple of minutes rather than moving
6 GB around.

    python merge_lora.py --adapter /content/schemaforge-v1/adapter \
        --out /content/schemaforge-v1-merged
"""
import argparse
import json
import os
import shutil

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def dirsize(p):
    n = 0
    for root, _, files in os.walk(p):
        for f in files:
            n += os.path.getsize(os.path.join(root, f))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="/content/schemaforge-v1/adapter")
    ap.add_argument("--out", default="/content/schemaforge-v1-merged")
    ap.add_argument("--base", default=None,
                    help="defaults to base_model from train_config.json next to --adapter")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    args = ap.parse_args()

    base = args.base
    if base is None:
        cfg = os.path.join(os.path.dirname(args.adapter.rstrip("/")), "train_config.json")
        if os.path.exists(cfg):
            base = json.load(open(cfg, encoding="utf-8"))["base_model"]
    if base is None:
        base = "Qwen/Qwen2.5-3B-Instruct"
    print("base    : %s" % base)
    print("adapter : %s" % args.adapter)

    dev = args.device
    if dev == "auto":
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device  : %s" % dev)

    # fp16 on the GPU: a T4 has room for a 3B at 6.2 GB and CPU RAM on free Colab
    # is tighter than VRAM once a merged copy is held alongside the original.
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.float16,
        device_map={"": 0} if dev == "cuda" else None,
        low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(model, args.adapter, torch_dtype=torch.float16)
    model = model.merge_and_unload()
    model = model.half()
    model.config.use_cache = True

    os.makedirs(args.out, exist_ok=True)
    model.save_pretrained(args.out, safe_serialization=True, max_shard_size="2GB")

    tok = AutoTokenizer.from_pretrained(args.adapter)
    tok.save_pretrained(args.out)

    for name in ("train_config.json",):
        src = os.path.join(os.path.dirname(args.adapter.rstrip("/")), name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(args.out, name))

    print("\nmerged -> %s  (%.2f GB)" % (args.out, dirsize(args.out) / 1e9))
    for f in sorted(os.listdir(args.out)):
        print("  %-42s %8.1f MB"
              % (f, os.path.getsize(os.path.join(args.out, f)) / 1e6))


if __name__ == "__main__":
    main()
