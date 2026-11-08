"""SchemaForge v1 QLoRA training run.

Loss is computed on the JSON completion only: the prompt and the target are tokenised
separately and concatenated, so the label mask boundary is exact rather than inferred
from chat-template string matching.

    python train_sf.py --data out --out /content/schemaforge-v1
    python train_sf.py --smoke          # 200 examples / 1 epoch, validates the pipeline
"""
import argparse
import json
import os
import time

import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          Trainer, TrainingArguments)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import TrainerCallback


def log(*a):
    print(*a, flush=True)


class StopOnNaN(TrainerCallback):
    """Abort as soon as the loss stops being a number.

    Running a bf16-native model in fp16 fails by going to NaN and staying there,
    and the trainer will happily keep stepping for the remaining two hours. The
    last good checkpoint is still on disk, so stopping early costs nothing.
    """

    def on_log(self, args, state, control, logs=None, **kw):
        loss = (logs or {}).get("loss")
        if loss is not None and (loss != loss or loss in (float("inf"), float("-inf"))):
            log("loss is %s at step %s - stopping. If this is Qwen3 in fp16, the "
                "dynamic range was not enough; use an sm_80+ GPU and --dtype bf16."
                % (loss, state.global_step))
            control.should_training_stop = True
        return control


class Packed(Dataset):
    def __init__(self, enc):
        self.enc = enc

    def __len__(self):
        return len(self.enc)

    def __getitem__(self, i):
        e = self.enc[i]
        return {"input_ids": e["input_ids"], "labels": e["labels"]}


def make_collate(pad_id):
    def collate(batch):
        n = max(len(b["input_ids"]) for b in batch)
        out = {"input_ids": [], "attention_mask": [], "labels": []}
        for b in batch:
            k = n - len(b["input_ids"])
            out["input_ids"].append(b["input_ids"] + [pad_id] * k)
            out["attention_mask"].append([1] * len(b["input_ids"]) + [0] * k)
            out["labels"].append(b["labels"] + [-100] * k)
        return dict((k, torch.tensor(v, dtype=torch.long)) for k, v in out.items())
    return collate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="out")
    ap.add_argument("--out", default="/content/schemaforge-v1")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lora-r", type=int, default=32)
    ap.add_argument("--lora-alpha", type=int, default=64)
    ap.add_argument("--batch", type=int, default=0)
    ap.add_argument("--accum", type=int, default=0)
    ap.add_argument("--smoke", action="store_true")
    # A free Colab T4 can be reclaimed mid-run, and with save_strategy="epoch" on a
    # one-epoch run that means the adapter is only ever written at the very end -
    # an interrupted run loses everything. Checkpoint by steps instead, and allow
    # resuming from the last one.
    ap.add_argument("--save-steps", type=int, default=25)
    ap.add_argument("--resume", action="store_true",
                    help="continue from the newest checkpoint in <out>/ckpt")
    # Qwen3-4B-Instruct-2507 is Apache-2.0 where Qwen2.5-3B is Qwen-Research
    # (non-commercial), so the base model is a licensing decision as much as a
    # quality one. It is a bf16 model, but a T4 is sm_75 and has no real bf16, so
    # running it there means fp16 - which can overflow on a model never trained in
    # it. Hence an explicit dtype flag rather than inferring it from the GPU, and a
    # NaN guard that stops the run instead of burning two hours on a dead loss.
    ap.add_argument("--dtype", choices=["auto", "fp16", "bf16"], default="auto",
                    help="auto = bf16 on sm_80+, else fp16")
    ap.add_argument("--ckpt-dir", default=None,
                    help="checkpoint elsewhere (e.g. a mounted Drive) so a run "
                         "survives the runtime being reclaimed")
    args = ap.parse_args()

    assert torch.cuda.is_available(), "No GPU. Runtime > Change runtime type > GPU."
    props = torch.cuda.get_device_properties(0)
    # NB: torch.cuda.is_bf16_supported() returns True on a T4 (it counts
    # emulation), which would pick the 4B model and emulated bf16. Check the
    # compute capability instead: real bf16 starts at sm_80 (A100/L4).
    real_bf16 = (props.major >= 8)
    if args.dtype == "auto":
        bf16 = real_bf16
    else:
        bf16 = (args.dtype == "bf16")
        if bf16 and not real_bf16:
            raise SystemExit("--dtype bf16 needs sm_80+ (A100/L4); this GPU is sm_%d%d"
                             % (props.major, props.minor))
    log("GPU: %s | %.1f GB | sm_%d%d | bf16=%s | torch %s"
        % (props.name, props.total_memory / 1e9, props.major, props.minor,
           bf16, torch.__version__))
    if not bf16 and real_bf16:
        log("NOTE: this GPU supports bf16 but fp16 was requested")

    model_id = args.model or ("Qwen/Qwen3-4B-Instruct-2507" if bf16
                              else "Qwen/Qwen2.5-3B-Instruct")
    if "Qwen3" in model_id and not bf16:
        log("WARNING: %s is distributed in bf16 and is being run in fp16. Watch the "
            "first few logged losses - a NaN means the dynamic range was not enough."
            % model_id)
    # Gradient checkpointing must stay on: a T4 OOMs without it at 15.6 GB.
    # batch 2 + accum 8 is ~1.25x faster than batch 1 + accum 16 on a T4.
    batch = args.batch or 2
    accum = args.accum or max(1, 16 // batch)
    epochs = 1.0 if args.smoke else args.epochs
    os.makedirs(args.out, exist_ok=True)
    log("model=%s batch=%d accum=%d eff_batch=%d epochs=%s max_len=%d"
        % (model_id, batch, accum, batch * accum, epochs, args.max_len))

    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    end_id = tok.convert_tokens_to_ids("<|im_end|>")
    if end_id is None or end_id == tok.unk_token_id:
        end_id = tok.eos_token_id

    def encode(ex):
        prompt = tok.apply_chat_template(ex["messages"][:2], tokenize=False,
                                         add_generation_prompt=True)
        p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
        t_ids = tok(ex["messages"][2]["content"],
                    add_special_tokens=False)["input_ids"] + [end_id]
        return {"input_ids": p_ids + t_ids,
                "labels": [-100] * len(p_ids) + t_ids,
                "n_target": len(t_ids)}

    def load(split, limit=0):
        rows = [json.loads(l) for l in
                open(os.path.join(args.data, split), encoding="utf-8")]
        return rows[:limit] if limit else rows

    train_rows = load("train.jsonl", 200 if args.smoke else 0)
    val_rows = load("val_seen.jsonl", 40 if args.smoke else 250)
    train_enc = [encode(r) for r in train_rows]
    val_enc = [encode(r) for r in val_rows]
    lens = np.array([len(e["input_ids"]) for e in train_enc])
    log("token length: mean %d | p95 %d | p99 %d | max %d"
        % (lens.mean(), np.percentile(lens, 95), np.percentile(lens, 99), lens.max()))
    train_enc = [e for e in train_enc if len(e["input_ids"]) <= args.max_len]
    val_enc = [e for e in val_enc if len(e["input_ids"]) <= args.max_len]
    log("kept %d/%d train, %d val within max_len"
        % (len(train_enc), len(lens), len(val_enc)))
    log("label-mask check, first example decodes to:")
    s = train_enc[0]
    log("  " + tok.decode([t for t, l in zip(s["input_ids"], s["labels"]) if l != -100])[:300])

    compute_dtype = torch.bfloat16 if bf16 else torch.float16
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_use_double_quant=True,
                             bnb_4bit_compute_dtype=compute_dtype)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, quantization_config=bnb, device_map={"": 0},
        attn_implementation="sdpa", torch_dtype=compute_dtype)
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    ckpt_dir = args.ckpt_dir or os.path.join(args.out, "ckpt")
    os.makedirs(ckpt_dir, exist_ok=True)
    targs = TrainingArguments(
        output_dir=ckpt_dir,
        per_device_train_batch_size=batch,
        gradient_accumulation_steps=accum,
        num_train_epochs=epochs,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        max_grad_norm=0.3,
        logging_steps=10,
        optim="paged_adamw_8bit",
        bf16=bf16, fp16=not bf16,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        per_device_eval_batch_size=1,
        eval_strategy="epoch",
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=2,
        report_to="none",
        seed=7,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=Packed(train_enc),
                      eval_dataset=Packed(val_enc),
                      data_collator=make_collate(tok.pad_token_id),
                      callbacks=[StopOnNaN()])
    log("optimizer steps ~ %d" % int(len(train_enc) / (batch * accum) * epochs))
    resume = False
    if args.resume and os.path.isdir(ckpt_dir):
        resume = any(d.startswith("checkpoint-") for d in os.listdir(ckpt_dir))
        log("resuming from newest checkpoint in %s" % ckpt_dir if resume
            else "no checkpoint found in %s, starting fresh" % ckpt_dir)
    log("checkpointing every %d steps -> %s" % (args.save_steps, ckpt_dir))
    t0 = time.time()
    out = trainer.train(resume_from_checkpoint=True if resume else None)
    log("train metrics: %s" % out.metrics)
    log("wall clock: %.1f min" % ((time.time() - t0) / 60))

    model.save_pretrained(os.path.join(args.out, "adapter"))
    tok.save_pretrained(os.path.join(args.out, "adapter"))
    json.dump({"base_model": model_id, "max_len": args.max_len, "epochs": epochs,
               "lr": args.lr, "lora_r": args.lora_r, "lora_alpha": args.lora_alpha,
               "effective_batch": batch * accum, "train_examples": len(train_enc),
               "metrics": out.metrics},
              open(os.path.join(args.out, "train_config.json"), "w"), indent=2)
    log("saved adapter -> %s" % os.path.join(args.out, "adapter"))


if __name__ == "__main__":
    main()
