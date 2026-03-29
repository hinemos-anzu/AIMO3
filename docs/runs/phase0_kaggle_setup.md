# Phase 0 — Kaggle 環境疎通セットアップ手順

作成日: 2026-03-29
Branch: `claude/aimo3-phase0-baseline-V2vbK`
担当: 実装・配管担当

---

## 1. 実施内容

`notebooks/phase0_kaggle_smoke.py` を作成し、ローカル dry-run で配管を確認した。

### ローカル dry-run 実行コマンド

```bash
python3 notebooks/phase0_kaggle_smoke.py --dry-run
```

### ローカル dry-run 結果

| CHECK | Status | 備考 |
|---|---|---|
| CHECK_1_GPU | SKIP | dry-run につきスキップ |
| CHECK_2_MODEL_WEIGHTS | SKIP | dry-run につきスキップ |
| CHECK_3_IMPORTS | SKIP | torch/transformers/accelerate 未インストール（期待通り） |
| CHECK_4_INFERENCE | SKIP | dry-run: ダミー推論 |
| CHECK_5_5DIGIT_OUTPUT | SKIP | dry-run: 5桁ダミー出力=99999 |
| CHECK_6_SAVE_OUTPUTS | **PASS** | 3ファイル保存成功 |
| Overall | **PASS** | |

配管（ファイル保存・ログ・CSV出力）は正常に動作することを確認。

---

## 2. Kaggle 上での実行手順

### 2-1. Kaggle Notebook の作成

1. `File → New Notebook` → `Python` を選択
2. Accelerator を **GPU T4 x2** または **GPU P100** → 本番前に **H100** へ変更
3. Internet アクセスを **OFF** に設定

### 2-2. モデル Kaggle Dataset の追加

Phase 0 では以下のいずれかを使用する（未決定の場合は DeepSeek-R1-Distill-Qwen-7B を推奨）:

| モデル | Kaggle Dataset 名 (例) | VRAM |
|---|---|---|
| DeepSeek-R1-Distill-Qwen-7B | `deepseek-r1-distill-qwen-7b` | ~16 GB |
| Qwen2.5-Math-7B-Instruct | `qwen25-math-7b-instruct` | ~16 GB |
| DeepSeek-R1-Distill-Qwen-14B | `deepseek-r1-distill-qwen-14b` | ~30 GB |

Dataset を Notebook に追加すると `/kaggle/input/<dataset-name>/` にマウントされる。

### 2-3. スクリプトのアップロード

以下のどちらかの方法でスクリプトをノートブックに取り込む:

**方法 A: Notebook にコードを直接貼る**
- `notebooks/phase0_kaggle_smoke.py` の内容をセルにコピー

**方法 B: Code Dataset として追加**
- `phase0_kaggle_smoke.py` を Kaggle Dataset として公開
- Notebook に追加して `!python /kaggle/input/<dataset>/phase0_kaggle_smoke.py`

### 2-4. 実行コマンド (Kaggle Notebook セル)

```python
# セル 1: 環境確認
import subprocess, sys
result = subprocess.run(
    [sys.executable, "/kaggle/working/phase0_kaggle_smoke.py",
     "--model-path", "/kaggle/input/<dataset-name>/transformers/default/1"],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print("[STDERR]", result.stderr)
```

または直接セルに貼って末尾に `main()` を呼ぶ:

```python
import sys
sys.argv = [
    "phase0_kaggle_smoke.py",
    "--model-path", "/kaggle/input/<dataset-name>/transformers/default/1"
]
# phase0_kaggle_smoke.py の内容をここに貼る
# ...
main()
```

### 2-5. 確認すべき出力

```
[✓] CHECK_1_GPU: PASS  NVIDIA H100 80GB HBM3 (80.0 GB)
[✓] CHECK_2_MODEL_WEIGHTS: PASS  model_type=qwen2 arch=Qwen2ForCausalLM
[✓] CHECK_3_IMPORTS: PASS  torch=2.x.x, transformers=4.x.x, accelerate=x.x.x
[✓] CHECK_4_INFERENCE: PASS  推論完了 (load+infer=xx.xs, new_tokens=xxx)
[✓] CHECK_5_5DIGIT_OUTPUT: PASS  5桁出力生成成功: 00113
[✓] CHECK_6_SAVE_OUTPUTS: PASS  3 ファイル保存成功

>>> Overall: PASS
```

---

## 3. 詰まりやすい箇所と対処

| 箇所 | 症状 | 対処 |
|---|---|---|
| CHECK_2_MODEL_WEIGHTS FAIL | `MODEL_PATH not found` | Dataset のマウントパスを確認。`!ls /kaggle/input/` で確認 |
| CHECK_2_MODEL_WEIGHTS FAIL | `config.json not found` | モデルの格納ディレクトリ階層を確認。`/transformers/default/1` まで必要な場合あり |
| CHECK_3_IMPORTS FAIL | `torch` not found | Kaggle 標準 GPU ノートブックには torch は入っているはず。ランタイムを確認 |
| CHECK_4_INFERENCE FAIL | CUDA OOM | モデルが H100 に収まらない。7B→4B に縮小するか量子化を検討 |
| CHECK_4_INFERENCE FAIL | `trust_remote_code` エラー | `trust_remote_code=True` が既に設定されているはず。コードを確認 |
| CHECK_5_5DIGIT_OUTPUT FAIL | 整数抽出失敗 | `raw_output_preview` をログで確認。`\\boxed{}` に入っているか |
| CHECK_6_SAVE_OUTPUTS FAIL | 書き込み権限エラー | `/kaggle/working/` 以外に書こうとしていないか確認 |

---

## 4. Phase 0 成功判定基準

| 条件 | 判定 |
|---|---|
| 全 6 CHECK が PASS または SKIP (dry-run のみ) | Phase 0 PASS |
| FAIL が 1 件以上 | Phase 0 FAIL → 詰まり箇所を記録して次アクションへ |
| `phase0_smoke_log.json` が `/kaggle/working/` に存在する | 証跡確認 |
| `phase0_result.csv` に 5 桁整数が 1 行出力されている | 5桁出力確認 |

**重要: Phase 0 の結果 (99999 等のダミー値) は精度評価に使わない。**
Phase 0 は「通るか通らないか」の配管テストである。

---

## 5. 次アクション (Phase 0 PASS 後)

1. Phase 0 の実行ログ (`phase0_smoke_log.json`) を `docs/runs/` に保存
2. 詰まり箇所の修正リストを確定
3. Phase 1 (shadow_eval 全 32 問 baseline) に進む
   - `shadow_eval.jsonl` の問題テキストを Kaggle Dataset として追加
   - `run_baseline_batch.py` 相当のバッチ推論スクリプトを作成
4. exp_001 (CLI solver 全 32 問) と比較できる状態にする

---

## 6. まだやってはいけないこと

- Phase 0 未完了のまま精度改善実験を始めること
- `99999` (dry-run 出力) を正解率の分母/分子に使うこと
- モデル選定・ハイパラ調整 (temperature / top-p / N) を決定すること
- verifier / reranker の実装に着手すること
- Phase 0 FAIL のまま Phase 1 に進むこと

---

*Phase 0 実行後、このファイルに実際の CHECK 結果を追記すること。*
