# AIMO3 Day4 exp_001 実行前チェック結果

## 判定サマリ
- CHECK-01 (shadow_eval.jsonl の内容確認): **FAIL**
  - 原因: `data/shadow_eval.jsonl` がリポジトリ内に存在しない
  - 影響: real shadow 評価データ不在のため `exp_001` 実行可否の確認ができない
  - 対応: fail-fast の事前チェック `tools/precheck_exp001.py` を追加（silent fallback 防止）

## 実行コマンド
```bash
python tools/precheck_exp001.py
```

## 出力
```text
FAIL: data/shadow_eval.jsonl が存在しません。real用評価データを配置してください。
```

## 最小差分修正内容
- `tools/precheck_exp001.py` を追加し、以下を自動検証
  - ファイル存在
  - JSONL 妥当性
  - `domain` / `difficulty`
  - `problem_id` or `id` の欠損・重複
  - toy/mock/dummy/test 文字列混入
- 入力不足時は必ず終了コード `1` で停止（silent fallback 防止）

## 次アクション
1. real データ `data/shadow_eval.jsonl` を配置
2. 再度 `python tools/precheck_exp001.py` を実行
3. PASS を確認後に `python run.py baseline` を実行
