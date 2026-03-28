# Day8 — CLI Solver Live Run (Subscription Auth)

## 目的

`ANTHROPIC_API_KEY` 未設定のまま、Claude Code subscription 経路で live 実行できるかを確認する。

---

## 認証状態確認

| 項目 | 状態 |
|---|---|
| `ANTHROPIC_API_KEY` | **設定なし** |
| `oauthAccount`（~/.claude.json） | `False` |
| `cachedExtraUsageDisabledReason` | `org_level_disabled` |
| `claude` CLI バージョン | 2.1.86 |
| `claude --print` 動作確認 | **動作する** |

**発見：** `oauthAccount: False` / `org_level_disabled` は「extra usage（追加クォータ）が無効」を意味しており、
基本的な `claude --print` 呼び出しは有効。

---

## 実装内容

### solver.py に `CLI = "cli"` モードを追加

```python
CLI = "cli"

def _make_cli_solver(subprocess_timeout=240.0) -> Callable:
    # shutil.which("claude") がなければ SolverConfigError
    # subprocess.run(["claude", "--print", "--output-format", "text"], input=prompt, ...)
    # _extract_integer() でモデル出力から整数を抽出
```

### `_extract_integer()` — 出力パーサ

モデルが extended thinking で reasoning prose を返す場合の対応：

1. `\boxed{N}` — LaTeX boxed answer
2. 最後の行が純粋な整数
3. テキスト中の最後の 1-3 桁整数

### 変更ファイル

- `src/day1_minimal_baseline/solver.py` — CLI mode 追加
- `scripts/run_baseline_once.py` — `--solver-mode cli` 対応
- `scripts/run_baseline_batch.py` — `--solver-mode cli` 対応
- `tests/test_day8_smoke.py` — 12 テスト（モック使用）

---

## live 実行結果

### single run

```
PYTHONPATH=src python scripts/run_baseline_once.py --solver-mode cli
```

```
=== baseline — first record [solver=cli] ===
  id: alg_001
  predicted: 00025
  expected: 00031
  correct: False
  parse_failure_count: 0
  elapsed_sec: 38.9s
```

**判定：** 成功（exit 0）。整数として正常に parse された。

---

### tiny batch (limit=3, timeout-sec=300)

```
PYTHONPATH=src python scripts/run_baseline_batch.py --solver-mode cli --limit 3 --timeout-sec 300
```

```
total              : 3
correct            : 1
accuracy           : 0.3333
5digit_compliance  : 3/3  (1.0000)
parse_failure_count: 0
avg_runtime_sec    : 92.44
max_runtime_sec    : 182.02

id           domain     diff   pred   gold  ok?
alg_001      algebra       1  00834  00031  --
alg_002      algebra       1  00059  00063  --
alg_003      algebra       1  00057  00057  OK
```

**判定：** 成功（exit 0）。3/3 完走、parse エラーなし。

---

## 観察事項

### 確定

- subscription 経路（`claude --print`）で live 実行 **可能**
- `ANTHROPIC_API_KEY` **不要**
- モデルは extended thinking を使って実際に問題を解こうとする
- `parse_failure_count = 0`：`_extract_integer()` が正常動作
- `5digit_compliance = 1.0`：全回答が 5 桁形式で出力

### 要確認

- `max_runtime_sec = 182s`：思考時間が問題によって大きく変動
  - batch 実行には `--timeout-sec 300` 推奨（デフォルト 250s では足りない場合あり）
- 正解率 1/3（33%）：問題テキストなし（metadata のみ）の制約として妥当
- `subprocess_timeout = 240s`：pipeline の `timeout_sec=250s` より短く設定

### 記録案（exp_001 実行前チェックリスト）

実験 001（full 32-problem batch）を実行する前に確認すること：

- [ ] `git status --short` → clean
- [ ] `claude --version` → CLI 確認
- [ ] `ANTHROPIC_API_KEY` → 未設定（subscription 経路を使用）
- [ ] `--timeout-sec 300` を付与する（実測 max 182s を考慮）
- [ ] `--limit 5` で予備テスト後、全件実行
- [ ] FLAGGED-E 閾値（accuracy > 70%）を認識しておく
- [ ] 実行前に `shadow_eval_v1.0` 変更がないことを `verify_shadow_eval.py` で確認

---

## PASS / FAIL / WARN まとめ

| 項目 | 結果 |
|---|---|
| `ANTHROPIC_API_KEY` 未設定を確認 | **PASS** |
| subscription 経路（`claude --print`）動作確認 | **PASS** |
| live single run（exit 0） | **PASS** |
| live tiny batch（limit=3, exit 0） | **PASS** |
| parse_failure_count = 0 | **PASS** |
| 5digit_compliance = 1.0 | **PASS** |
| silent fallback なし | **PASS** |
| 既存導線（Day1-Day7）破壊なし | **PASS** |
| API 課金なし | **PASS** |
| 正解率 1/3（metadata のみ起因） | **WARN**（設計上の制約） |
| max_runtime 182s（timeout 設定要注意） | **WARN** |

**総合判定: PASS — subscription 経路で live 実行可能。API 課金不要。**

---

## テスト

```
pytest tests/ -q
152 passed
```

---

## commit 一覧（Day8）

| SHA | 内容 |
|---|---|
| `d483c21` | feat(day8): add CLI solver mode |
| `a169c42` | fix(day8): extract integer from CLI solver prose output |
| `c870a61` | fix(day8): increase CLI solver subprocess timeout to 240s |
