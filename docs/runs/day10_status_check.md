# Day10 — 実装証跡確認 (開始時点スナップショット)

## 調査日時 / branch

- 調査日: 2026-03-28
- Branch: `codex/restart-clean`
- HEAD: `0e4d1c5` (docs(day9): asset status, YES/NO next steps)
- Tests: 175 passed, 0 failed

---

## 1. すでに commit / 定着済みの要素

### solver adapter

| 要素 | 実装場所 | commit | テスト |
|---|---|---|---|
| `PLACEHOLDER = "placeholder"` | `solver.py:32` | `e8bef03` | `test_day6_smoke.py` |
| `LLM = "llm"` | `solver.py:33` | `e8bef03` | `test_day6_smoke.py` |
| `CLI = "cli"` | `solver.py:34` | `d483c21` | `test_day8_smoke.py` |
| `VALID_MODES = (PLACEHOLDER, LLM, CLI)` | `solver.py:36` | `d483c21` | `test_day8_smoke.py` |
| `SolverConfigError` — key 未設定時に例外 | `solver.py:39` | `e8bef03` | `test_day6_smoke.py` |
| `create_solver(mode, model)` — factory | `solver.py:194` | `e8bef03` / `d483c21` | 両テスト |
| `_make_placeholder_solver()` | `solver.py:46` | `e8bef03` | `test_day6_smoke.py` |
| `_make_llm_solver(model)` — API key 専用 | `solver.py:53` | `e8bef03` | `test_day6_smoke.py` (monkeypatch) |
| `_make_cli_solver(subprocess_timeout)` | `solver.py:114` | `d483c21` / `c870a61` | `test_day8_smoke.py` |
| `_extract_integer(text)` — 3 path | `solver.py:161` | `a169c42` | **`test_day9_smoke.py`** |

### mode 切替

| 要素 | 証跡 |
|---|---|
| `--solver-mode placeholder/llm/cli` 引数 | `scripts/run_baseline_once.py`, `scripts/run_baseline_batch.py` |
| LLM / CLI 失敗時 exit 1（silent fallback なし） | `run_baseline_once.py:46-52`, `run_baseline_batch.py:92-99` |
| unknown mode → `ValueError` | `solver.py:202`, `test_day8_smoke.py::test_unknown_mode_still_raises_value_error` |

### oracle 検証

| 要素 | commit | テスト |
|---|---|---|
| `oracle_solver` inject → `accuracy == 1.0` | `e8bef03` | `test_day6_smoke.py:190-216` |
| oracle で `run_batch_with_retry` accuracy=1.0 | `e8bef03` | `test_day6_smoke.py:212-216` |
| oracle で `run_batch_with_candidates` accuracy=1.0 | `e8bef03` | `test_day6_smoke.py:193-198` |

### retry 設定注入

| 要素 | 実装場所 | テスト |
|---|---|---|
| `max_retries=0` デフォルト（retry なし） | `pipeline.py:110` | `test_day5_run2_smoke.py` |
| retry on RuntimeError / generic Exception | `pipeline.py:154-189` | `test_retry_fires_on_runtime_error` |
| retry 枯渇 → `RuntimeError`（silent fallback なし） | `pipeline.py:191-195` | `test_retry_exhausted_raises` |
| `retries_used`, `exec_error_count` 記録 | `pipeline.py:173-178` | `test_result_has_retry_keys` |
| `parse_failure_count` — ValueError/TypeError を別計上 | `pipeline.py:151, 182-185` | `test_day6_smoke.py` |

### timeout kill

| 要素 | 実装場所 | テスト |
|---|---|---|
| `timeout_sec=250.0` デフォルト | `pipeline.py:113` | — |
| attempt 開始前 elapsed チェック | `pipeline.py:154-160` | `test_day5_run2_smoke.py` |
| `ExecTimeoutError` — never retried | `pipeline.py:179-180` | `test_timeout_error_not_retried` |
| `subprocess_timeout=240.0` — CLI solver 内部 kill | `solver.py:114`, `c870a61` | `test_subprocess_timeout_classified_as_exec_error` |

**既知制約:**
- pipeline `timeout_sec` は attempt「間」のみチェック（attempt「中」は CLI の `subprocess_timeout` でカバー）
- `subprocess.TimeoutExpired` は `except Exception` で捕捉 → retry される（max_retries=0 なら RuntimeError）

### candidate 集約

| 要素 | 実装場所 | テスト |
|---|---|---|
| `generate_candidates(record, N, solver=None)` | `pipeline.py:260` | `test_day5_run3_smoke.py` |
| `select_by_majority(candidates)` — tie は辞書順最小 | `pipeline.py:285` | `test_select_majority_tie_lexicographic` |
| `candidate_diversity = unique / N` | `pipeline.py:361-362` | `test_run_one_candidates_diversity_range` |
| `MemoryError` never retried (OOM は fatal) | `pipeline.py:378` | `test_memory_error_not_retried` |
| `num_candidates_setting` 記録 | `pipeline.py:374` | `test_run_one_candidates_count_recorded` |

### parser 周り

| 要素 | 実装場所 | テスト |
|---|---|---|
| `format_answer(raw)` — 5桁ゼロ埋め | `pipeline.py:36-48` | `test_day1_smoke.py`, `test_day4_smoke.py` |
| 負値 → `ValueError` | `pipeline.py:44-46` | `test_format_answer_invalid` |
| 非数値 → `ValueError` | `pipeline.py:42-45` | `test_format_answer_invalid` |
| `_extract_integer(text)` path 1: `\boxed{N}` | `solver.py:175-178` | `test_extract_boxed_*` (6テスト) |
| `_extract_integer(text)` path 2: 最終行が純整数 | `solver.py:181-184` | `test_extract_last_line_*` (4テスト) |
| `_extract_integer(text)` path 3: 最終整数 fallback | `solver.py:187-189` | `test_extract_last_standalone_*` (3テスト) |
| 抽出失敗 → stripped text 返却 → `format_answer` が `ValueError` | `solver.py:191` | `test_format_answer_raises_when_no_integer_in_text` |

### fail-fast 挙動

| 要素 | 実装場所 | テスト |
|---|---|---|
| `ExecTimeoutError` は retry しない | `pipeline.py:179-180` | `test_timeout_error_not_retried` |
| `MemoryError` は retry しない | `pipeline.py:378` | `test_memory_error_not_retried` |
| `SolverConfigError` → exit 1（script 側） | `run_baseline_once.py:49-51` | 手動確認 (Day6.5) |
| `load_jsonl` — empty / missing field → `ValueError` | `io.py:23-45` | `test_day1_smoke.py` |
| `silent fallback なし` — retry 枯渇 → `RuntimeError` | `pipeline.py:391-393` | `test_retry_exhausted_raises` |

### offline evaluation 集計

| 要素 | 実装場所 | テスト |
|---|---|---|
| `run_batch()` — total/correct/accuracy | `pipeline.py:73` | `test_day2_smoke.py` |
| `format_summary()` — 5digit_compliance | `pipeline.py:488` | `test_day3_smoke.py`, `test_day4_smoke.py` |
| `breakdown_domain` / `breakdown_difficulty` | `pipeline.py:526-532` | `test_day3_smoke.py` |
| `retry_stats` / `candidate_stats` / `parse_stats` (conditional) | `pipeline.py:534-558` | `test_day3_smoke.py` |
| `FLAGGED-E 閾値` accuracy > 70% 文書化 | `docs/shadow_eval_v1.0_freeze.md:57-59` | なし（docs のみ） |

### E2E 空回し確認用テスト

| 要素 | commit | テスト |
|---|---|---|
| echo dummy solver (`/tmp/fake_claude_dir/claude`) | `cedec9d` | `test_e2e_dummy_solver_returns_answer` |
| dummy → WRONG answer 確認 | `cedec9d` | `test_e2e_dummy_solver_wrong_answer` |
| dummy → prose + `\boxed{}` 抽出確認 | `cedec9d` | `test_e2e_dummy_solver_prose_with_boxed` |
| dummy non-zero exit → exec error | `cedec9d` | `test_e2e_dummy_solver_nonzero_exit_becomes_exec_error` |
| `subprocess.TimeoutExpired` → RuntimeError (known constraint) | `cedec9d` | `test_subprocess_timeout_classified_as_exec_error` |

### docs / runs / decisions

| ファイル | 内容 | commit |
|---|---|---|
| `docs/shadow_eval_v1.0_freeze.md` | 32問凍結宣言、FLAGGED-E 方針 | `378c52a` |
| `docs/experiment_log_template.md` | 実行記録テンプレート | `8506a01` |
| `docs/runs/20260327_placeholder.md` | placeholder baseline 記録 | `8506a01` |
| `docs/runs/day5_run2_retry.md` | retry 変更記録 | `d773440` |
| `docs/runs/day5_run3_candidates.md` | candidate N 変更記録 | `2915197` |
| `docs/runs/day6_real_solver.md` | solver adapter 設計記録 | `e8bef03` |
| `docs/runs/day6_live_attempt.md` | live 実行試行 → API key なし停止 | `2a1ff2c` |
| `docs/runs/day7_auth_check.md` | 認証経路確認 → 未認証 | `cbaed34` |
| `docs/runs/day8_cli_live_run.md` | CLI live run 成功記録 | `43daca2` |
| `docs/runs/day9_asset_status.md` | 資産固定状況 + YES/NO 次手 | `0e4d1c5` |

---

## 2. まだ文書整理のみで commit 固定が必要な要素

### A. `experiment_log_template.md` フィールド不足

`run_batch_with_candidates` の出力フィールドが template に未記載。

**現 template に不足しているフィールド:**

| フィールド | 出力元 |
|---|---|
| `parse_failure_count` | `run_batch_with_retry`, `run_batch_with_candidates` |
| `avg_runtime_sec` | 同上 |
| `max_runtime_sec` | 同上 |
| `retry_count_used` | 同上 |
| `exec_error_count` | 同上 |
| `avg_candidate_diversity` | `run_batch_with_candidates` |
| `num_candidates_setting` | 同上 |

**対応:** `docs/experiment_log_template.md` を拡張して commit する。

### B. `verify_shadow_eval.py` に pytest テストがない

`scripts/verify_shadow_eval.py` の `verify_transform_consistency()` は実行確認済み（PASS）だが、
pytest テストカバレッジが存在しない。

**対応:** `tests/test_verify_shadow_eval.py` を追加する。（任意、優先度低）

### C. `shadow_eval_v1.0` タグの SHA 不整合

| | SHA |
|---|---|
| local tag (`git tag -l`) | `378c52a` (commit SHA) |
| GitHub tag (MCP `list_tags`) | `daf8cf0` (annotated tag object SHA) |

**解釈:** annotated tag は tag オブジェクト自体の SHA を持つ（commit SHA とは別）。
GitHub 上のタグは proxy が作成した annotated tag。
`git show shadow_eval_v1.0` → commit `378c52a` を指しており、データ整合性は問題なし。

**対応:** 不要（tag は正常、SHA 種別の違いのみ）。

### D. live baseline (full 32問) 未取得

| 実行 | 状態 |
|---|---|
| placeholder 全件 (32問) | `docs/runs/20260327_placeholder.md` に記録済み |
| CLI solver 3件 (`--limit 3`) | `docs/runs/day8_cli_live_run.md` に記録済み |
| **CLI solver 全件 (32問)** | **未取得** |

---

## 3. live baseline 実行時に必ず採取すべきログ

```
# 採取コマンド
PYTHONPATH=src python scripts/run_baseline_batch.py \
  --solver-mode cli \
  --timeout-sec 300 \
  2>&1 | tee docs/runs/exp_001_raw_output.txt
```

**採取必須フィールド（format_summary 出力より）:**

| フィールド | 採取理由 |
|---|---|
| `total` | 全件処理確認 |
| `correct` | 精度計算の分子 |
| `accuracy` | FLAGGED-E 判定（>0.70 要注意） |
| `5digit_compliance.rate` | format_answer 動作確認 |
| `parse_stats.parse_failure_count` | `_extract_integer()` 失敗回数 |
| `parse_stats.parse_success_count` | 正常 parse 回数 |
| `retry_stats.retry_count_used` | 実際に retry が発生したか |
| `retry_stats.exec_error_count` | exec error 件数 |
| `retry_stats.avg_runtime_sec` | 平均思考時間 |
| `retry_stats.max_runtime_sec` | 最大思考時間（timeout 設定の妥当性確認） |
| `candidate_stats.avg_candidate_diversity` | 多様性（N=1 なら 1.0 固定） |
| `breakdown_domain` | 4 domain 別正解率 |
| `breakdown_difficulty` | 難易度別正解率 |
| 実行日時 / commit SHA / solver mode | 再現性 |

**採取必須: per-record ログ（batch の最後の行一覧）**

```
id           domain         diff   pred   gold  ok?
```

→ 全 32 行を記録。FLAGGED-E 発火時の検証に使用。

---

## 4. baseline 後に確認する品質項目の順序

1. **exit code = 0** — RuntimeError / ExecTimeoutError が発生していないか
2. **total == 32** — 全件処理されたか
3. **5digit_compliance.rate == 1.0** — 全回答が 5 桁整数か
4. **parse_failure_count** — 0 なら `_extract_integer()` が全件成功
5. **max_runtime_sec < timeout_sec(300)** — timeout 未発生確認
6. **accuracy** — FLAGGED-E 閾値 0.70 と比較
7. **breakdown_domain** — 4 domain 均一か、特定 domain に偏りがないか
8. **breakdown_difficulty** — difficulty 1 vs 2 に逆転がないか（易しい方が低いのは異常）
9. **per-record の predicted 列** — 全て `"00000"` または同一値なら fallback 疑い
10. **exec_error_count > 0** なら exec_errors を確認して分類

---

## 5. commit を分けるなら どう分けるべきか

Day10 で必要な commit は以下の 2 つに分割する：

| commit # | 内容 | ファイル |
|---|---|---|
| 1 | `experiment_log_template.md` の拡張（フィールド追加） | `docs/experiment_log_template.md` |
| 2 | この証跡確認 doc | `docs/runs/day10_status_check.md` |

**分ける理由:**
- テンプレート変更は今後の全 run doc に影響する（独立した変更）
- 証跡確認 doc は記録であり、テンプレート変更に依存しない

**Day10 でコード変更が生じた場合の追加 commit:**

| commit # | 内容 | 条件 |
|---|---|---|
| 3 | `test_verify_shadow_eval.py` | verify script のテストを追加する場合 |
| 4 | exp_001 実行記録 | full 32問 live run を実行した場合 |

---

## 6. Day10 でまだやらないこと

| 項目 | 理由 |
|---|---|
| verifier / reranker 設計 | 禁止事項 |
| temperature / retry / N の固定値決定 | 禁止事項 |
| fail-fast 緩和 | 禁止事項 |
| shadow_eval_v1.0 変更 | 凍結済み |
| `subprocess.TimeoutExpired` → `ExecTimeoutError` 変換 | 優先度低、現状動作に問題なし |
| `timeout_sec` を attempt 内まで伝播 | 大改造、スコープ外 |
| OSS / 他 LLM への solver 追加 | スコープ外（ユーザー確認が先） |
| exp_001 全件実行の自動スケジューリング | スコープ外 |

---

## PASS / FAIL / WARN サマリー

| 確認項目 | 判定 |
|---|---|
| solver adapter 3 mode 全て commit | **PASS** |
| mode 切替 + SolverConfigError | **PASS** |
| oracle 精度=1.0 テスト | **PASS** |
| retry 設定注入（params + tests） | **PASS** |
| timeout poll（attempt 前） | **PASS** |
| CLI solver 内部 subprocess_timeout | **PASS** |
| candidate 集約（majority vote + tie-break） | **PASS** |
| parser 全 path テスト | **PASS** |
| fail-fast（ExecTimeoutError / MemoryError 非 retry） | **PASS** |
| offline 集計（breakdown / compliance / parse_stats） | **PASS** |
| E2E dummy solver dry-run | **PASS** |
| shadow_eval_v1.0 凍結 + verify PASS | **PASS** |
| GitHub に tag 存在 | **PASS**（annotated tag object SHA、内容一致） |
| live 全件 baseline 取得 | **WARN（未取得）** |
| experiment_log_template フィールド完備 | **WARN（拡張が必要）** |
| verify_shadow_eval.py pytest カバレッジ | **WARN（なし）** |
| subprocess.TimeoutExpired は retry される | **WARN（既知制約）** |
