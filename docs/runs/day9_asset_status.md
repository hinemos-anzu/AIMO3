# Day9 — 資産固定状況

## 目的

認証 YES / NO のどちらでも止まらないように、live 非依存の資産を commit 可能な形に固める。

---

## 資産状況マップ

### 確定（実装 + テスト済み）

| 資産 | 実装ファイル | テスト | 備考 |
|---|---|---|---|
| 5桁強制パース（`format_answer()`） | `pipeline.py` | `test_day4_smoke.py` | ValueError on non-numeric, 確定 |
| `\boxed{N}` 抽出 | `solver.py:_extract_integer()` | `test_day9_smoke.py` | 優先順位 1 |
| stdout 最終行キャッチ | `solver.py:_extract_integer()` | `test_day9_smoke.py` | 優先順位 2 |
| 最終整数フォールバック | `solver.py:_extract_integer()` | `test_day9_smoke.py` | 優先順位 3 |
| retry 設定注入（`max_retries=` param） | `pipeline.py` | `test_day5_run2_smoke.py` | solver= に依存しない |
| timeout poll（`timeout_sec=`） | `pipeline.py` | `test_day5_run2_smoke.py` | attempt 開始前に elapsed チェック |
| candidate 集約（`generate_candidates` + `select_by_majority`） | `pipeline.py` | `test_day5_run3_smoke.py` | tie-break: 辞書順最小 |
| solver injection（`solver=` param） | `pipeline.py` | `test_day6_smoke.py` | None → placeholder |
| CLI モード（`claude --print`） | `solver.py` | `test_day8_smoke.py` | subscription auth |
| E2E dry-run（echo dummy solver） | — | `test_day9_smoke.py` | live 不要で full stack 確認 |

---

### 要確認

| 項目 | 現状 | 影響 |
|---|---|---|
| `subprocess.TimeoutExpired` の分類 | `except Exception` で捕捉 → retry される | max_retries=0 なら RuntimeError に化ける（許容範囲） |
| timeout_sec は attempt 間チェックのみ | attempt 実行中の solver ハング未対応 | CLI solver の `subprocess_timeout=240s` が内部ガード |
| `_extract_integer()` の 4桁 AIME 答 | `\b\d{1,3}\b` は 1-3桁のみマッチ | AIME 答は 0-999 なので 4桁は存在しない（仕様上 OK） |
| `boxed{1000}` など範囲外 | boxed path では不一致 → 後続 path に fallback | `format_answer()` が 1000 → "01000" (6桁) → 正しく ValueError |

---

### 提案差分（要実装ではなく検討候補）

| 提案 | 効果 | 優先度 |
|---|---|---|
| `subprocess.TimeoutExpired` → `ExecTimeoutError` に変換 | retry されなくなる（timeout は fatal 扱い） | 低（現状動作に問題なし） |
| `_extract_integer()` を `pipeline.py` に移動 | solver 非依存に | 低（今は CLI 専用として問題なし） |
| `timeout_sec` を subprocess に伝播 | attempt 内ハングを kill できる | 中（大規模 batch で有用） |

---

## YES / NO 次手整理

### YES — subscription 認証が使える（Day8 で確認済み）

| ステップ | コマンド | 備考 |
|---|---|---|
| exp_001 準備確認 | `python scripts/verify_shadow_eval.py` | shadow_eval_v1.0 未変更確認 |
| 予備 5件 | `--solver-mode cli --limit 5 --timeout-sec 300` | max_runtime 確認 |
| 全 32件実行 | `--solver-mode cli --timeout-sec 300` | FLAGGED-E 閾値（>70%）注意 |
| 結果記録 | `docs/runs/exp_001_full_run.md` | accuracy, parse_failure_count 記録 |

### NO — 認証不可 or 環境制約

| ステップ | 対応 | 備考 |
|---|---|---|
| placeholder baseline 取得 | `--solver-mode placeholder` | accuracy=0.0、比較基準として記録 |
| dummy solver E2E 確認 | `test_day9_smoke.py` 実行 | live 不要で pipeline stack 確認済み |
| 代替 solver 方針検討 | 下記参照 | |

**代替 solver 方針メモ（NO 時）：**

```
現在の solver.py が提供する 3 モード:
  placeholder — 常に "00000" 返す
  llm         — ANTHROPIC_API_KEY 必須
  cli         — claude --print 必須（今回 YES）

追加可能な方向（実装スコープ外）:
  subprocess 経由で別 LLM CLI（ollama 等）を呼ぶ "subprocess" モード
    → _make_cli_solver() の claude コマンドを差し替えるだけ
    → solver.py の設計変更なし、コマンド名を引数化するだけ
```

---

## E2E Dry-Run 最小手順

**前提：** `claude` CLI 不要、API key 不要、OSS モデル不要。

```bash
# 1. echo ベース dummy を使った full stack 確認（test_day9 に含まれる）
PYTHONPATH=src python -m pytest tests/test_day9_smoke.py::test_e2e_dummy_solver_returns_answer -v

# 2. 手動確認（何かを確かめたい場合）
mkdir /tmp/fake_claude_dir
cat > /tmp/fake_claude_dir/claude << 'EOF'
#!/bin/sh
echo "42"
EOF
chmod +x /tmp/fake_claude_dir/claude

PATH=/tmp/fake_claude_dir:$PATH \
  PYTHONPATH=src python scripts/run_baseline_once.py --solver-mode cli
# → expected: predicted=00042, parse_failure_count=0

# 3. tiny batch dry-run
PATH=/tmp/fake_claude_dir:$PATH \
  PYTHONPATH=src python scripts/run_baseline_batch.py \
    --solver-mode cli --limit 3 --timeout-sec 60
# → expected: 3/3 完走、全て predicted=00042、parse_failure_count=0
```

---

## commit 分割方針（確定）

| commit | 内容 | サイズ |
|---|---|---|
| feat(day9): `_extract_integer` unit tests + E2E dry-run | `test_day9_smoke.py` | 小 |
| docs(day9): asset status and YES/NO next steps | `day9_asset_status.md` | 小 |

---

## テスト状況

```
pytest tests/ -q
175 passed (Day1-Day9)
```

| ファイル | テスト数 |
|---|---|
| test_day1_smoke.py | 12 |
| test_day2_smoke.py | 15 |
| test_day3_smoke.py | 17 |
| test_day4_smoke.py | 18 |
| test_day5_run2_smoke.py | 24 |
| test_day5_run3_smoke.py | 31 |
| test_day6_smoke.py | 23 |
| test_day8_smoke.py | 12 |
| test_day9_smoke.py | **23** |
| **合計** | **175** |

---

## PASS / FAIL / WARN

| 項目 | 結果 |
|---|---|
| `_extract_integer()` 全 path テスト | **PASS** |
| E2E dummy solver dry-run | **PASS** |
| 既存 Day1-Day8 導線 | **PASS** |
| `subprocess.TimeoutExpired` は retry される | **WARN**（既知制約、許容範囲） |
| timeout_sec は attempt 内未対応 | **WARN**（CLI の内部 timeout でカバー） |
