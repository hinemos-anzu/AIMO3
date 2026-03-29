# Phase 0 完了記録

**Status: PASS**
実行日時: 2026-03-29
Branch: `claude/aimo3-phase0-baseline-V2vbK`
Commit at run: `3735125`

---

## 実行コマンド

```bash
python notebooks/phase0_kaggle_smoke.py \
  --model-path /kaggle/input/models/qwen-lm/qwen-3-5/transformers/qwen3.5-35b-a3b/1
# dry_run=False, is_kaggle=True
```

---

## CHECK 結果

| CHECK | Status | 詳細 |
|---|---|---|
| CHECK_1_GPU | **PASS** | NVIDIA H100 80GB HBM3 (79.2 GB) |
| CHECK_2_MODEL_WEIGHTS | **PASS** | model_type=qwen3_5_moe, arch=Qwen3_5MoeForConditionalGeneration |
| CHECK_3_IMPORTS | **PASS** | torch=2.10.0+cu128, transformers=5.4.0, accelerate=1.12.0 |
| CHECK_4_INFERENCE | **PASS** | load+infer=1294.1s, new_tokens=512 |
| CHECK_5_5DIGIT_OUTPUT | **PASS** | 5桁出力: `00004` |
| CHECK_6_SAVE_OUTPUTS | **PASS** | /kaggle/working/ に3ファイル保存 |
| **Overall** | **PASS** | |

---

## 確定した環境情報

| 項目 | 値 |
|---|---|
| GPU | NVIDIA H100 80GB HBM3 |
| VRAM | 79.2 GB |
| CUDA | 12.8 (torch+cu128) |
| torch | 2.10.0+cu128 |
| transformers | 5.4.0 |
| accelerate | 1.12.0 |

---

## 確定したモデル情報

| 項目 | 値 |
|---|---|
| モデル名 | Qwen3.5-35B-A3B (MoE) |
| Kaggle path | `/kaggle/input/models/qwen-lm/qwen-3-5/transformers/qwen3.5-35b-a3b/1` |
| model_type | `qwen3_5_moe` |
| architecture | `Qwen3_5MoeForConditionalGeneration` |
| 総パラメータ | ~35B |
| アクティブパラメータ | ~3B (MoE: expert 選択) |
| dtype | bf16 (device_map=auto) |

---

## タイミング計測 (Phase 0 スモーク1問)

| 区間 | 時間 |
|---|---|
| モデルロード | **1261.6s (約21分)** ← 重大 |
| 推論 (512 new_tokens) | ~32.5s |
| 合計 | 1294.1s |
| 重みファイル数 | 693 ファイル |

**⚠ 警告: モデルロード 21 分は Phase 1 (shadow_eval 32問) で致命的な制約になる。**
Kaggle セッション上限 9 時間のうち 21 分がロードだけで消費される。
shadow_eval 全 32 問 × 推論時間を加えた合計が 9 時間に収まるか確認が必要。

---

## Phase 0 中に観測された警告 (精度評価対象外)

```
`torch_dtype` is deprecated! Use `dtype` instead!
```
→ `phase0_kaggle_smoke.py` の `torch_dtype=torch.bfloat16` を `dtype=torch.bfloat16` に修正が必要。

```
The fast path is not available because one of the required library is not installed.
Falling back to torch implementation.
To install follow https://github.com/fla-org/flash-linear-attention#installation
```
→ flash_linear_attention / causal_conv1d 未インストール。
  インストールすれば推論速度が改善する可能性あり (internet OFF 環境では Kaggle dataset 経由で対応)。

```
The following generation flags are not valid and may be ignored: ['top_p', 'top_k']
```
→ `do_sample=False` (greedy) のときに `top_p`, `top_k` を渡しているため。
  greedy 時はこれらのパラメータを渡さないよう修正が必要。

---

## Phase 0 で確認した事実 (精度評価に使ってはいけない)

- output `00004` は「スモーク問題が通過した」という配管確認の証跡であり、正解率評価ではない。
- `00004` の正誤は記録しない。Phase 0 は accuracy を評価対象としない。

---

## Phase 0 で未確認のまま残すこと

| 項目 | 状態 |
|---|---|
| shadow_eval.jsonl 32問の accuracy | 未取得 (Phase 1 以降) |
| 推論の決定論性 (同一問題2回) | 未確認 |
| モデルロードの高速化 (キャッシュ等) | 未検討 |
| flash_linear_attention の効果 | 未計測 |
| GPT-OSS-120B の動作確認 | 未試験 |

---

## Phase 1 に進む前に必要な最小確認

1. モデルロード時間の対策を検討する (9時間制限に対して21分ロードは許容できるか)
2. shadow_eval.jsonl の問題テキストを Kaggle Dataset に追加する (現在は metadata のみ)
3. `torch_dtype` / `top_p`/`top_k` 警告を修正する

---

## Day10 完了ゲート 最終判定

| GATE | 判定 | 証跡 |
|---|---|---|
| GATE1 モデル確定 | **PASS** | Qwen3.5-35B-A3B, path確定 |
| GATE2 切替条件 | **PASS** | コード明文化済み |
| GATE3 offline/CUDA | **PASS** | torch+cu128, transformers=5.4.0 |
| GATE4 1問読み取り | **PASS** | alg_001 0.3ms 取得 |
| GATE5 1問完走 | **PASS** | load+infer=1294.1s 完走 |
| GATE6 0〜99999 整数 | **PASS** | 00004 (int=4, in_range=True) |
| GATE7 /kaggle/working/ 保存 | **PASS** | 3ファイル確認 |
| GATE8 silent fallback なし | **PASS** | 明示的 raise 確認済み |

**Day10 完了ゲート: 8/8 PASS**
