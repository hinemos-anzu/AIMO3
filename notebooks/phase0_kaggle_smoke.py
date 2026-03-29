#!/usr/bin/env python3
"""Phase 0 — Kaggle 環境疎通スモークテスト

目的:
  Kaggle H100 環境で以下の 6 項目を順番に検証する。
  Phase 0 は精度評価ではなく「壊れない配管の確認」である。

  CHECK 1: GPU (H100) が見えるか
  CHECK 2: Internet OFF 前提でモデル重みが読めるか
  CHECK 3: 必要依存が offline で解決できるか (import チェック)
  CHECK 4: 1問だけ推論が最後まで通るか
  CHECK 5: 5桁出力が生成できるか
  CHECK 6: ログと結果ファイルを保存できるか

使い方 (Kaggle Notebook):
  - このファイルをそのまま Kaggle Notebook にコピーして実行する。
  - モデルパスを KAGGLE 環境変数 MODEL_PATH で上書き可能。
  - Internet OFF (No Internet) 設定で動かすこと。

使い方 (ローカル dry-run):
  python notebooks/phase0_kaggle_smoke.py --dry-run
  --dry-run では GPU/モデルチェックをスキップし、ダミー推論で配管のみ確認する。

出力ファイル (WORKING_DIR/ 以下):
  phase0_smoke_log.json   — 全 CHECK の成否と詳細
  phase0_result.csv       — Kaggle 提出フォーマットの 1 行サンプル
  phase0_status.txt       — PASS / FAIL の 1 行要約

設計方針:
  - silent fallback 禁止: 失敗は必ず例外か明示的エラーとして記録する。
  - placeholder / dummy 推論結果を精度評価に使わない。
  - Phase 0 は "通るか通らないか" のみを評価対象とする。
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数 / パス設定
# ---------------------------------------------------------------------------

# Kaggle 環境では /kaggle/working が書き込み先
# ローカル dry-run では /tmp/aimo3_phase0 を使用
_IS_KAGGLE = Path("/kaggle/working").exists()

WORKING_DIR = Path("/kaggle/working") if _IS_KAGGLE else Path("/tmp/aimo3_phase0")
WORKING_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# モデル候補 (GATE1: 1本に確定するまでここを更新する)
#
# 第一候補: GPT-OSS-120B
#   - VRAM: bf16=240GB(不可) / int8=120GB(2xH100) / int4=60GB(1xH100 可)
#   - 1xH100(80GB) で動かすには int4 量子化 or tensor_parallel_size=2 必須
#   - Kaggle dataset 名: 要確認 (TODO: PM に確認して埋める)
#
# 第二候補: Qwen3.5-27B
#   - VRAM: bf16=54GB(1xH100 可) / int4=14GB(余裕)
#   - 1xH100 bf16 でそのまま動く。量子化不要。
#   - Kaggle dataset 名: 要確認 (TODO: PM に確認して埋める)
#
# 切替条件 (Phase 0 判断基準):
#   - GPU メモリ >= 70GB → 第一候補 (int4) を試みる
#   - GPU メモリ <  70GB → 第二候補 (bf16) に切替
#   - 第一候補で CUDA OOM → 第二候補に切替 (FAIL として明示記録)
#   - Phase 0 では第二候補 (Qwen3.5-27B) をデフォルトとして採用する
#     理由: 1xH100 bf16 で確実に動作するため。GPT-OSS-120B は int4 動作確認後に昇格。
# ---------------------------------------------------------------------------

# TODO: 以下の <dataset-name> を実際の Kaggle Dataset 名に置き換えること
#       PM またはコンペページで確認する
MODEL_PRIMARY_NAME = "GPT-OSS-120B"
MODEL_PRIMARY_PATH = "/kaggle/input/TODO-gpt-oss-120b/<dataset-name>/transformers/default/1"
MODEL_PRIMARY_QUANT = "int4"           # 1xH100 で動かすには int4 必須
MODEL_PRIMARY_VRAM_GB = 60             # int4 時の推定 VRAM (GB)

MODEL_SECONDARY_NAME = "Qwen3.5-27B"
MODEL_SECONDARY_PATH = "/kaggle/input/models/qwen-lm/qwen-3-5/transformers/qwen3.5-27b/1"  # 確定済み 2026-03-29
MODEL_SECONDARY_QUANT = "bf16"         # 1xH100 に収まる (54 GB)
MODEL_SECONDARY_VRAM_GB = 54           # bf16 時の推定 VRAM (GB)

# Phase 0 デフォルト: 第二候補 (Qwen3.5-27B, bf16, 1xH100 確実動作)
# GPT-OSS-120B は int4 動作確認後に MODEL_PATH 上書きで試験する
_DEFAULT_KAGGLE_PATH = MODEL_SECONDARY_PATH

# モデルパス: 環境変数 MODEL_PATH で上書き可能
DEFAULT_MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    _DEFAULT_KAGGLE_PATH if _IS_KAGGLE else "/tmp/aimo3_phase0/model_stub",
)

# 競技入力ファイル (Kaggle 提供)
COMPETITION_TEST_CSV = "/kaggle/input/ai-mathematical-olympiad-progress-prize-3/test.csv"

# Phase 0 用スモーク問題 (競技ファイルが読めない場合の fallback)
# AIME 2021 I #1 — 答え 113
SMOKE_PROBLEM = {
    "id": "phase0_smoke",
    "problem": (
        "Zou and Chou are counterclockwise around a circular track of circumference 80. "
        "Zou runs clockwise at speed 6, Chou runs counterclockwise at speed 10. "
        "They start at the same point. How many times will they meet again before "
        "Chou completes his 10th lap?"
    ),
    "expected_raw": 50,  # 確認用 (Phase 0 では正解率評価しない)
}

# タイムアウト設定
INFERENCE_TIMEOUT_SEC = 120  # Phase 0 スモーク用: 2分

# ---------------------------------------------------------------------------
# ログ構造体
# ---------------------------------------------------------------------------

LOG = {
    "phase": "phase0",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "is_kaggle": _IS_KAGGLE,
    "working_dir": str(WORKING_DIR),
    "model_path": DEFAULT_MODEL_PATH,
    "checks": {},
    "overall": "UNKNOWN",
}


def _record(check_name: str, status: str, detail: dict) -> None:
    """CHECK 結果をログに記録する。status は 'PASS' / 'FAIL' / 'SKIP'。"""
    LOG["checks"][check_name] = {
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **detail,
    }
    symbol = {"PASS": "✓", "FAIL": "✗", "SKIP": "−"}.get(status, "?")
    print(f"[{symbol}] {check_name}: {status}  {detail.get('message', '')}", flush=True)


def _save_log() -> None:
    """ログ・結果ファイルを WORKING_DIR に書き出す。"""
    log_path = WORKING_DIR / "phase0_smoke_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(LOG, f, ensure_ascii=False, indent=2)
    print(f"\n[LOG] saved → {log_path}", flush=True)


# ---------------------------------------------------------------------------
# CHECK 1: GPU 確認
# ---------------------------------------------------------------------------

def check_gpu(dry_run: bool) -> None:
    """GPU (H100) が利用可能かを確認する。"""
    if dry_run:
        _record("CHECK_1_GPU", "SKIP", {"message": "dry-run: GPU チェックをスキップ"})
        return

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if not cuda_available:
            _record("CHECK_1_GPU", "FAIL", {
                "message": "CUDA not available",
                "cuda_available": False,
            })
            return

        device_count = torch.cuda.device_count()
        device_name = torch.cuda.get_device_name(0) if device_count > 0 else "N/A"
        total_mem_gb = (
            torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            if device_count > 0
            else 0
        )

        _record("CHECK_1_GPU", "PASS", {
            "message": f"{device_name} ({total_mem_gb:.1f} GB)",
            "cuda_available": True,
            "device_count": device_count,
            "device_name": device_name,
            "total_memory_gb": round(total_mem_gb, 2),
        })

    except Exception as exc:
        _record("CHECK_1_GPU", "FAIL", {
            "message": f"GPU check raised: {type(exc).__name__}: {exc}",
        })


# ---------------------------------------------------------------------------
# CHECK 2: モデル重みの存在確認
# ---------------------------------------------------------------------------

def check_model_weights(dry_run: bool, model_path: str) -> bool:
    """モデルパスが存在し、config.json が読めるかを確認する。"""
    if dry_run:
        _record("CHECK_2_MODEL_WEIGHTS", "SKIP", {
            "message": "dry-run: モデル重みチェックをスキップ"
        })
        return False

    mp = Path(model_path)
    if not mp.exists():
        _record("CHECK_2_MODEL_WEIGHTS", "FAIL", {
            "message": f"MODEL_PATH not found: {model_path}",
            "model_path": model_path,
        })
        return False

    config_file = mp / "config.json"
    if not config_file.exists():
        _record("CHECK_2_MODEL_WEIGHTS", "FAIL", {
            "message": f"config.json not found in {model_path}",
            "model_path": model_path,
        })
        return False

    try:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)
        model_type = config.get("model_type", "unknown")
        arch = config.get("architectures", ["unknown"])[0]
        _record("CHECK_2_MODEL_WEIGHTS", "PASS", {
            "message": f"model_type={model_type} arch={arch}",
            "model_path": model_path,
            "model_type": model_type,
            "architecture": arch,
        })
        return True
    except Exception as exc:
        _record("CHECK_2_MODEL_WEIGHTS", "FAIL", {
            "message": f"config.json parse error: {type(exc).__name__}: {exc}",
        })
        return False


# ---------------------------------------------------------------------------
# CHECK 3: offline 依存解決 (import チェック)
# ---------------------------------------------------------------------------

def check_imports(dry_run: bool) -> None:
    """必要なパッケージが offline でインポートできるかを確認する。

    torch がインポートできても CUDA ビルドでない場合は FAIL とする。
    理由: torch+cpu では GPU 推論が不可能であり、silent fallback と同等の誤検知になるため。
    """
    required = ["torch", "transformers", "accelerate"]
    results = {}
    all_ok = True

    for pkg in required:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "unknown")
            results[pkg] = {"status": "OK", "version": ver}
        except ImportError as exc:
            results[pkg] = {"status": "MISSING", "error": str(exc)}
            all_ok = False

    # torch が import できた場合、CUDA ビルドかどうかを追加確認する
    # torch+cpu は import は通るが GPU 推論ができない → BLOCKER として明示する
    cuda_ok = True
    cuda_detail = {}
    if results.get("torch", {}).get("status") == "OK":
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            torch_ver = torch.__version__
            is_cpu_build = "+cpu" in torch_ver
            cuda_detail = {
                "torch_version": torch_ver,
                "cuda_available": cuda_available,
                "is_cpu_build": is_cpu_build,
            }
            if is_cpu_build or not cuda_available:
                cuda_ok = False
                results["torch"]["cuda_status"] = "CPU_BUILD" if is_cpu_build else "CUDA_NOT_AVAILABLE"
                results["torch"]["cuda_detail"] = cuda_detail
        except Exception as exc:
            cuda_ok = False
            results["torch"]["cuda_status"] = f"CUDA_CHECK_ERROR: {exc}"

    missing = [k for k, v in results.items() if v["status"] == "MISSING"]

    if dry_run and missing:
        _record("CHECK_3_IMPORTS", "SKIP", {
            "message": f"dry-run: missing={missing} (expected in non-Kaggle env)",
            "packages": results,
        })
    elif missing:
        _record("CHECK_3_IMPORTS", "FAIL", {
            "message": f"missing packages: {missing}",
            "packages": results,
        })
    elif not cuda_ok:
        # torch import は通るが CUDA 不可 → GPU 推論ができない BLOCKER
        _record("CHECK_3_IMPORTS", "FAIL", {
            "message": (
                f"BLOCKER: torch={results['torch']['version']} は CUDA ビルドでない。"
                f" GPU 推論不可。Kaggle Notebook の Accelerator を GPU に設定すること。"
                f" cuda_detail={cuda_detail}"
            ),
            "packages": results,
            "cuda_detail": cuda_detail,
        })
    else:
        ver_str = ", ".join(f"{k}={v['version']}" for k, v in results.items())
        _record("CHECK_3_IMPORTS", "PASS", {
            "message": ver_str,
            "packages": results,
            "cuda_detail": cuda_detail,
        })


# ---------------------------------------------------------------------------
# CHECK 4 + 5: 1問推論 + 5桁出力
# ---------------------------------------------------------------------------

def _load_problem(dry_run: bool) -> dict:
    """競技 CSV or スモーク問題を 1 件読み込む。"""
    if not dry_run and Path(COMPETITION_TEST_CSV).exists():
        with open(COMPETITION_TEST_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            first = next(reader, None)
        if first is not None:
            print(f"[INFO] 競技テストファイルから 1 問取得: id={first.get('id')}", flush=True)
            return {"id": first["id"], "problem": first["problem"], "expected_raw": None}

    print("[INFO] スモーク問題を使用 (競技ファイル未使用 or dry-run)", flush=True)
    return SMOKE_PROBLEM.copy()


def _extract_integer_from_output(text: str) -> str | None:
    """モデル出力から整数を抽出する。

    優先順:
      1. \\boxed{N}
      2. 最後の純数字行 (1-6 桁)
      3. テキスト末尾の 1-6 桁整数

    失敗時は None を返す (silent fallback 禁止: 呼び出し元が ValueError を上げる)。
    """
    stripped = text.strip()

    # 1. \boxed{N}
    boxed = re.findall(r"\\boxed\{(\d{1,6})\}", stripped)
    if boxed:
        return boxed[-1]

    # 2. 最後の純数字行
    for line in reversed(stripped.splitlines()):
        line = line.strip()
        if line.isdigit() and 1 <= len(line) <= 6:
            return line

    # 3. 末尾の 1-6 桁整数
    matches = re.findall(r"\b(\d{1,6})\b", stripped)
    if matches:
        return matches[-1]

    return None


def _format_5digit(raw: str | int) -> str:
    """整数を 5 桁ゼロパディング文字列に変換する。"""
    val = int(raw)
    if val < 0 or val > 99999:
        raise ValueError(f"Answer out of range [0, 99999]: {val}")
    return f"{val:05d}"


def check_inference_and_output(dry_run: bool, model_weights_ok: bool, model_path: str) -> str:
    """1問推論を実行し、5桁出力を生成する。

    Returns:
        生成された 5 桁文字列 (FAIL 時は "99999")
    """
    problem = _load_problem(dry_run)

    # dry-run / モデル未ロード時はダミー推論
    if dry_run or not model_weights_ok:
        dummy_answer = "99999"
        _record("CHECK_4_INFERENCE", "SKIP" if dry_run else "FAIL", {
            "message": (
                "dry-run: ダミー推論を使用 (モデルロードなし)"
                if dry_run
                else "モデル重みが読めないため推論スキップ"
            ),
            "problem_id": problem["id"],
            "raw_output": "[dry-run placeholder]",
            "predicted_raw": dummy_answer,
        })
        _record("CHECK_5_5DIGIT_OUTPUT", "SKIP" if dry_run else "FAIL", {
            "message": (
                f"dry-run: 5桁ダミー出力={dummy_answer}"
                if dry_run
                else "推論スキップのため 5 桁出力なし"
            ),
            "predicted_5digit": dummy_answer,
        })
        return dummy_answer

    # 実際の推論
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        _record("CHECK_4_INFERENCE", "FAIL", {
            "message": f"transformers import failed: {exc}",
        })
        _record("CHECK_5_5DIGIT_OUTPUT", "FAIL", {
            "message": "推論不可のため 5 桁出力なし",
        })
        return "99999"

    start = time.monotonic()
    try:
        print(f"[INFO] トークナイザをロード中: {model_path}", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

        print(f"[INFO] モデルをロード中 (bf16, device_map=auto): {model_path}", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )
        model.eval()

        # プロンプト構築
        prompt = (
            "Solve the following AIME competition problem step by step. "
            "At the end, write your final integer answer inside \\boxed{}.\n\n"
            f"Problem: {problem['problem']}\n\nSolution:"
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        input_len = inputs["input_ids"].shape[1]

        elapsed_load = time.monotonic() - start
        print(f"[INFO] モデルロード完了 ({elapsed_load:.1f}s)。推論開始...", flush=True)

        # 推論 (greedy, 最大 512 トークン)
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tokenizer.eos_token_id,
            )

        # 入力トークン除去
        new_tokens = output_ids[0][input_len:]
        raw_output = tokenizer.decode(new_tokens, skip_special_tokens=True)
        elapsed_infer = time.monotonic() - start

        _record("CHECK_4_INFERENCE", "PASS", {
            "message": f"推論完了 (load+infer={elapsed_infer:.1f}s, new_tokens={len(new_tokens)})",
            "problem_id": problem["id"],
            "elapsed_sec": round(elapsed_infer, 2),
            "new_tokens": len(new_tokens),
            "raw_output_preview": raw_output[:200],
        })

    except Exception as exc:
        elapsed = time.monotonic() - start
        tb = traceback.format_exc()
        _record("CHECK_4_INFERENCE", "FAIL", {
            "message": f"{type(exc).__name__}: {exc}",
            "elapsed_sec": round(elapsed, 2),
            "traceback": tb,
        })
        _record("CHECK_5_5DIGIT_OUTPUT", "FAIL", {
            "message": "推論失敗のため 5 桁出力なし",
        })
        return "99999"

    # 5 桁出力
    extracted = _extract_integer_from_output(raw_output)
    if extracted is None:
        _record("CHECK_5_5DIGIT_OUTPUT", "FAIL", {
            "message": f"整数抽出失敗: raw_output_preview={raw_output[:100]!r}",
            "raw_output": raw_output,
        })
        return "99999"

    try:
        answer_5digit = _format_5digit(extracted)
    except ValueError as exc:
        _record("CHECK_5_5DIGIT_OUTPUT", "FAIL", {
            "message": f"5桁変換失敗: {exc}",
            "extracted": extracted,
        })
        return "99999"

    _record("CHECK_5_5DIGIT_OUTPUT", "PASS", {
        "message": f"5桁出力生成成功: {answer_5digit}",
        "predicted_5digit": answer_5digit,
        "extracted_raw": extracted,
    })
    return answer_5digit


# ---------------------------------------------------------------------------
# CHECK 6: ログ・結果ファイル保存
# ---------------------------------------------------------------------------

def check_save_outputs(answer_5digit: str, dry_run: bool) -> None:
    """ログと CSV 結果ファイルを WORKING_DIR に保存する。"""
    errors = []

    # 1. phase0_result.csv (Kaggle 提出フォーマット)
    csv_path = WORKING_DIR / "phase0_result.csv"
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "answer"])
            writer.writeheader()
            writer.writerow({"id": "phase0_smoke", "answer": int(answer_5digit)})
    except Exception as exc:
        errors.append(f"CSV 保存失敗: {exc}")

    # 2. phase0_smoke_log.json
    log_path = WORKING_DIR / "phase0_smoke_log.json"
    try:
        _save_log()
    except Exception as exc:
        errors.append(f"ログ保存失敗: {exc}")

    # 3. phase0_status.txt
    status_path = WORKING_DIR / "phase0_status.txt"
    all_checks = LOG.get("checks", {})
    failed = [k for k, v in all_checks.items() if v["status"] == "FAIL"]
    overall = "FAIL" if failed else "PASS"
    LOG["overall"] = overall

    try:
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(f"Phase 0 Status: {overall}\n")
            f.write(f"Timestamp: {LOG['timestamp_utc']}\n")
            f.write(f"Is Kaggle: {_IS_KAGGLE}\n")
            f.write(f"Answer: {answer_5digit}\n")
            if failed:
                f.write(f"Failed checks: {', '.join(failed)}\n")
    except Exception as exc:
        errors.append(f"status.txt 保存失敗: {exc}")

    if errors:
        _record("CHECK_6_SAVE_OUTPUTS", "FAIL", {
            "message": f"ファイル保存エラー: {errors}",
            "errors": errors,
        })
    else:
        _record("CHECK_6_SAVE_OUTPUTS", "PASS", {
            "message": (
                f"3 ファイル保存成功: "
                f"{csv_path.name}, {log_path.name}, {status_path.name}"
            ),
            "files": [
                str(csv_path),
                str(log_path),
                str(status_path),
            ],
        })


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 0 Kaggle 環境疎通スモークテスト"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "GPU/モデルチェックをスキップしてダミー推論で配管のみ確認する。"
            "ローカル開発環境での構造検証用。"
        ),
    )
    parser.add_argument(
        "--model-path",
        default=DEFAULT_MODEL_PATH,
        help=f"モデル重みのパス (default: {DEFAULT_MODEL_PATH})",
    )
    args = parser.parse_args()

    model_path = args.model_path
    LOG["model_path"] = model_path

    print("=" * 60, flush=True)
    print("AIMO3 Phase 0 — Kaggle 環境疎通スモークテスト", flush=True)
    print(f"  dry_run   : {args.dry_run}", flush=True)
    print(f"  is_kaggle : {_IS_KAGGLE}", flush=True)
    print(f"  model_path: {model_path}", flush=True)
    print(f"  working   : {WORKING_DIR}", flush=True)
    print("=" * 60, flush=True)

    # --- CHECK 1: GPU ---
    check_gpu(args.dry_run)

    # --- CHECK 2: モデル重み ---
    model_weights_ok = check_model_weights(args.dry_run, model_path)

    # --- CHECK 3: import ---
    check_imports(args.dry_run)

    # --- CHECK 4 + 5: 推論 + 5桁出力 ---
    answer_5digit = check_inference_and_output(
        args.dry_run, model_weights_ok, model_path
    )

    # --- CHECK 6: ファイル保存 ---
    check_save_outputs(answer_5digit, args.dry_run)

    # --- 最終ログ書き出し ---
    all_checks = LOG.get("checks", {})
    failed = [k for k, v in all_checks.items() if v["status"] == "FAIL"]
    LOG["overall"] = "FAIL" if failed else "PASS"
    _save_log()

    # --- 結果サマリ ---
    print("\n" + "=" * 60, flush=True)
    print("Phase 0 Summary", flush=True)
    for name, result in all_checks.items():
        symbol = {"PASS": "✓", "FAIL": "✗", "SKIP": "−"}.get(result["status"], "?")
        print(f"  [{symbol}] {name}: {result['status']}", flush=True)

    overall = LOG["overall"]
    print(f"\n>>> Overall: {overall}", flush=True)
    if failed:
        print(f">>> FAILED checks: {failed}", flush=True)
        print(">>> 詰まり箇所: docs/runs/phase0_result.md を参照", flush=True)

    print(f"\n出力ファイル:", flush=True)
    print(f"  {WORKING_DIR}/phase0_smoke_log.json", flush=True)
    print(f"  {WORKING_DIR}/phase0_result.csv", flush=True)
    print(f"  {WORKING_DIR}/phase0_status.txt", flush=True)
    print("=" * 60, flush=True)

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
