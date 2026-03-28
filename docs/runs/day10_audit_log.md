# Day10 — 品質保証・実行監査ログ

作成日: 2026-03-28
Branch: `codex/restart-clean` HEAD `933ac85`
監査担当: Day10 QA

---

## 1. 監査対象

| 対象 | ファイル / 証跡 |
|---|---|
| solver adapter 実装 | `src/day1_minimal_baseline/solver.py` |
| mode 切替スクリプト | `scripts/run_baseline_once.py`, `scripts/run_baseline_batch.py` |
| pipeline fail-fast 挙動 | `src/day1_minimal_baseline/pipeline.py` |
| oracle 精度=1.0 検証 | `tests/test_day6_smoke.py:190-216` |
| E2E dummy dry-run | `tests/test_day9_smoke.py` |
| live 実行記録 | `docs/runs/day8_cli_live_run.md` |
| placeholder baseline 記録 | `docs/runs/20260327_placeholder.md` |
| shadow_eval 凍結状態 | `data/shadow_eval.jsonl`, `scripts/verify_shadow_eval.py` |
| 認証状態 | `~/.claude.json`, env `ANTHROPIC_API_KEY` |
| exp_001 実施状態 | ファイル不存在 |
| テストスイート | `tests/` (175 tests) |

---

## 2. 確定してよい事実

以下はすべて実行済みの事実であり、証跡が commit に存在する。

### コード・テスト

| 事実 | 証跡 |
|---|---|
| `solver.py` に PLACEHOLDER / LLM / CLI の 3 mode が実装されている | `solver.py:32-34`, commit `d483c21` |
| `SolverConfigError` は key 未設定時に即座に例外を上げる（silent fallback なし） | `solver.py:65-70`, `test_day6_smoke.py` |
| `_extract_integer()` の 3 path（boxed / last-line / last-int）が実装されテスト済み | `solver.py:161-191`, `test_day9_smoke.py` |
| `format_answer()` は非数値 / 負値で `ValueError` を上げる | `pipeline.py:36-48`, `test_day4_smoke.py` |
| `ExecTimeoutError` は retry されない | `pipeline.py:179-180`, `test_timeout_error_not_retried` |
| `MemoryError` は retry されない | `pipeline.py:378`, `test_memory_error_not_retried` |
| retry 枯渇は `RuntimeError` であり silent fallback ではない | `pipeline.py:391-393`, `test_retry_exhausted_raises` |
| oracle solver inject → `accuracy == 1.0`（3 テスト） | `test_day6_smoke.py:190-216` |
| E2E dummy solver dry-run は pipeline 全 stack を通過する | `test_day9_smoke.py::test_e2e_dummy_solver_returns_answer` |
| dummy WRONG 答は WRONG として記録される | `test_day9_smoke.py::test_e2e_dummy_solver_wrong_answer` |
| 175 tests が全て pass している | `pytest tests/ -q` 実行確認済み |

### 認証・環境

| 事実 | 証跡 |
|---|---|
| `ANTHROPIC_API_KEY` は現在未設定 | `env` 確認済み |
| `~/.claude.json` に `apiKey` / `oauthAccount` は存在しない | `json` 調査結果 |
| `cachedExtraUsageDisabledReason: org_level_disabled` | `~/.claude.json` |
| `claude --print` は現時点で動作する（exit 0, "3" 返却確認） | 本監査内で実行確認 |

### 過去実行記録

| 事実 | 証跡 |
|---|---|
| placeholder solver 全 32 問: accuracy=0.0000, 5digit_compliance=1.0000 | `docs/runs/20260327_placeholder.md` |
| CLI solver limit=3: total=3, correct=1, accuracy=0.3333, parse_failure_count=0 | `docs/runs/day8_cli_live_run.md` |
| CLI solver single run (alg_001): predicted=00025, expected=00031, correct=False | `docs/runs/day8_cli_live_run.md` |

### データ

| 事実 | 証跡 |
|---|---|
| `shadow_eval.jsonl` は 32 問、凍結済み | `scripts/verify_shadow_eval.py` PASS, commit `378c52a` |
| 4 domain × 8、difficulty 1×16 / 2×16 の分布は確認済み | `docs/shadow_eval_v1.0_freeze.md` |

---

## 3. 未完了として残すべき事実

以下は「存在しない」「実施されていない」「未確認」のまま記録する。補完しない。

| 未完了項目 | 理由 |
|---|---|
| **exp_001 は未実施** | `docs/runs/exp_001_*.md` が存在しない |
| **CLI solver 全 32 問の live baseline が未取得** | Day8 は limit=3 のみ。全件スコアは存在しない |
| **全 32 問の accuracy / domain breakdown / parse_failure_count が不明** | 未実行のため数値なし |
| **score_is_deterministic が未確認** | 同一問題を 2 回実行した記録がない |
| **max_runtime_sec (全 32 問) が不明** | limit=3 の max=182s のみ記録済み |
| **exp_001.yaml が存在しない** | 作成・記入されていない |
| **verify_shadow_eval.py の pytest カバレッジがない** | `tests/test_verify_shadow_eval.py` が存在しない |

---

## 4. 認証 YES 時の通過条件

現時点で `claude --print` は動作している（認証 YES 相当）。
ただし `org_level_disabled` の状態が変化する可能性を考慮し、以下を exp_001 実行前後で順序通りに確認すること。

**exp_001 実行前チェック（順序厳守）:**

```
1. git status --short → clean（uncommitted changes なし）
2. python scripts/verify_shadow_eval.py → PASS
3. claude --print で echo 確認 → exit 0
4. --limit 5 予備テスト → exit 0, 5digit_compliance=1.0
5. 上記 PASS 後に --limit 32（全件）を実行
```

**exp_001 実行後 quality check（この順序でしか前進させない）:**

| ステップ | チェック内容 | 合格条件 |
|---|---|---|
| 1 | `score_is_deterministic` | 同一問題を 2 回実行し predicted が一致するか確認 |
| 2 | `baseline_above_70pct` | accuracy ≤ 0.70 なら PASS。> 0.70 なら FLAGGED-E |
| 3 | `domain_bias / geometry_nonzero` | 4 domain の accuracy が全て 0 でないか確認 |
| 4 | `parse_failure_count` | 0 が理想。> 0 の場合は exec_errors を確認して分類 |
| 5 | `avg_runtime_sec_per_problem` | 全件 avg / max を確認し timeout 設定の妥当性を評価 |
| 6 | `exp_001.yaml 記入・DONE化` | 上記 1-5 を全て通過後にのみ DONE とする |

---

## 5. 認証 NO 時の通過条件

`claude --print` が将来的に動作しなくなった場合 または API key 非設定のまま実行不可になった場合:

| 条件 | 扱い |
|---|---|
| `SolverConfigError` 発生 | **fail-fast の正常動作**。code failure ではない |
| `claude --print` exit 非 0 | **環境条件未達（blocked）**。code failure ではない |
| 認証状態不明 | **環境条件未達として記録**。推測しない |

**認証 NO 時に Day10 の成果として認めるもの:**

- 175 tests pass（live 不要の全資産）
- `_extract_integer()` の 3 path テスト（`test_day9_smoke.py`）
- E2E dummy solver dry-run（pipeline 配管テスト）
- `experiment_log_template.md` の拡張（`6248c8e`）
- `day10_status_check.md` / 本監査ログ

**認証 NO 時に進んではいけないもの:**

- verifier / reranker 本実装
- temperature / retry / N の固定値決定
- exp_001 の実施（認証が確認できない状態での実行は不可）

---

## 6. FLAG 条件

以下のいずれかが発生した場合、その時点で作業を止め、理由を明記すること。

| FLAG | 条件 | 対応 |
|---|---|---|
| **FLAGGED-E** | exp_001 accuracy > 0.70 | 全件結果を保存し、cross-validate 未実施のまま性能評価に進まない |
| **FLAGGED-BLOCK** | `claude --print` が連続 3 回 exit 非 0 | blocked として記録し、実行を止める |
| **FLAGGED-PARSE** | exp_001 の parse_failure_count > 5 | `_extract_integer()` の出力例を採取し、regex の見直しを検討 |
| **FLAGGED-TIMEOUT** | exp_001 の max_runtime_sec > 280 | timeout_sec=300 の設定が不足している可能性。全件完走できていない可能性 |
| **FLAGGED-SILENT** | predicted が全件同一値（例: 全て "00000"）| solver が silent fallback している疑い。即座に調査 |
| **FLAGGED-NOEXIT** | run_baseline_batch.py が exit 0 以外で終了 | RuntimeError / ExecTimeoutError が uncaught になっている可能性 |

---

## 7. Day10 で禁止する逸脱

| 禁止事項 | 理由 |
|---|---|
| dummy / placeholder の結果を live の精度根拠として使うこと | dummy の完走は配管テストであり精度評価ではない |
| limit=3 の accuracy=0.3333 を "baseline score" として採用すること | n=3 はサンプルであり baseline 取得ではない |
| exp_001 未実施のまま「性能が良い/悪い」と判断すること | baseline スコアがない間は評価不能 |
| blocked（認証未達）を "API 障害" や "code failure" と誤表現すること | blocked は環境条件未達であり code defect ではない |
| SolverConfigError 発生を "バグ" として扱うこと | fail-fast の正常動作である |
| 認証状態不明なまま "subscription で動く" と断定すること | 現時点では動作しているが、保証はない |
| verifier / reranker の設計に着手すること | baseline スコア未取得の段階ではスコープ外 |
| temperature / retry / N の固定値を決定すること | exp_001 結果なしに決定できない |
| fail-fast（ExecTimeoutError / MemoryError）を緩める変更 | 品質保証の根幹を壊す |
| `shadow_eval_v1.0` のレコードを変更・追加・削除すること | 凍結済み |

---

## 8. PM に返すべき判定文

```
Day10 開始時点の判定:

【実行状態】
  exp_001: 未実施
  baseline (full 32問 live): 未取得
  認証: claude --print 動作確認済み（2026-03-28 本監査内）
        ただし ANTHROPIC_API_KEY 未設定 / oauthAccount: False のまま

【成果として確定できるもの】
  - 175 tests pass（live 非依存の全資産）
  - CLI solver + _extract_integer() + E2E dry-run の実装・テスト定着
  - experiment_log_template の全フィールド拡張
  - 実行ガイド・品質チェック手順の文書化

【現時点で判断できないこと】
  - CLI solver の全 32 問精度（未取得）
  - score_is_deterministic（未確認）
  - geometry / domain_bias（未実行）
  - exp_001 に基づく採否判断（未実施）

【次に必要なアクション（順序厳守）】
  1. verify_shadow_eval.py PASS 確認
  2. limit=5 予備実行（exit 0 確認）
  3. exp_001 全件実行（--solver-mode cli --timeout-sec 300）
  4. quality check 6 ステップ通過
  5. exp_001.yaml 記入・DONE

【blocked 条件】
  claude --print が使用不可になった場合は blocked として記録する。
  これは code failure ではなく環境条件未達である。
```

---

## 9. 追加で記録すべき監査ログ

exp_001 実行時に以下を必ず採取・記録すること。

### 採取必須（実行ログ）

```bash
# 実行コマンドをそのまま記録すること
PYTHONPATH=src python scripts/run_baseline_batch.py \
  --solver-mode cli --timeout-sec 300 \
  2>&1 | tee docs/runs/exp_001_raw_output.txt
```

### 記録必須フィールド（`experiment_log_template.md` 準拠）

| フィールド | 採取方法 |
|---|---|
| 実行日時・commit SHA | `git log -1 --oneline` |
| `total` | summary 出力 |
| `correct` | summary 出力 |
| `accuracy` | summary 出力（FLAGGED-E 判定に使用） |
| `5digit_compliance.rate` | summary 出力 |
| `parse_failure_count` | parse stats 出力 |
| `avg_runtime_sec` | retry stats 出力 |
| `max_runtime_sec` | retry stats 出力 |
| `exec_error_count` | retry stats 出力 |
| `retry_count_used` | retry stats 出力 |
| `breakdown_domain` (4 domain) | summary 出力 |
| `breakdown_difficulty` (2 levels) | summary 出力 |
| per-record 全 32 行（id / domain / diff / pred / gold / ok） | batch 末尾出力 |
| exit code | `echo "exit=$?"` |
| 総経過時間 | `time` コマンド |

### 採取必須（環境スナップショット）

```bash
git log -1 --oneline
if [ -z "${ANTHROPIC_API_KEY}" ]; then echo "ANTHROPIC_API_KEY: 未設定"; fi
claude --version
python scripts/verify_shadow_eval.py
```

### FLAGGED-E 発火時の追加採取

accuracy > 0.70 の場合、以下を追加で採取する。
（採取のみ。この時点で性能評価・採否判断を行ってはならない。）

- 正解した問題の ID・domain・difficulty 一覧
- 正解答が `answer_raw` の偶然一致か、実際の推論による正解か（例: 全て "00042" など固定値でないか確認）
- per-record の predicted 列を全件記録

---

*本監査ログは `docs/runs/day10_audit_log.md` として commit する。*
