# AIMO3 Day1 Repo Review Report

## 対象
- repository: `hinemos-anzu/AIMO3`
- branch: `codex/prepare-repo-for-aimo3-day-1`

---

## 確定

### 1. 主要ファイル一覧

#### 存在確認できたファイル
- `README.md`
- `data/shadow_eval.jsonl`
- `scripts/run_baseline_once.py`
- `src/aimo3/__init__.py`
- `src/aimo3/pipeline.py`
- `tests/test_run_baseline_once.py`
- `docs/shadow_eval_spec.md`
- `docs/executor_policy.md`
- `docs/verifier_policy.md`
- `docs/experiment_template.md`
- `docs/submission_checklist.md`

#### 不在確認したファイル
- `run.py`
- `tools/precheck_exp001.py`

### 2. 実行導線
現時点の baseline 実行導線は README の Quick start に記載された 1 本です。

```bash
python scripts/run_baseline_once.py
```

README には、Day1 の目標は「max accuracy ではなく comparable baseline foundation」と記載されています。

### 3. `scripts/run_baseline_once.py` の実態
このスクリプトは以下の動作です。

- デフォルトで `data/shadow_eval.jsonl` を読む
- JSONL の先頭の有効行だけを読む
- `id` と `problem` を取得
- `src/aimo3/pipeline.py` の `solve_once()` を呼ぶ
- `{"id": ..., "answer": ..., "answer_digits": 5}` を標準出力に JSON 1行で出す

### 4. `data/shadow_eval.jsonl` の現在スキーマ
現在の実ファイルは次の2行です。

- `{"id":"shadow-0001","problem":"Compute 1+1."}`
- `{"id":"shadow-0002","problem":"Compute 2+3."}`

したがって、現時点で実際に使われているスキーマは少なくとも下記です。

- `id: string`
- `problem: string`

`docs/shadow_eval_spec.md` でも Day1 の format は JSONL で `id` と `problem` の2項目と定義されています。

### 5. `src/aimo3/pipeline.py` の実態
現在の baseline 実装は最小骨格です。

- `SimpleGenerator.generate(problem)`
  - `problem.strip()` を返す
- `SimpleExecutor.execute(generated_text)`
  - 文字コードの総和を返す
- `SimpleVerifierSelector.select(executor_value, digits)`
  - 値を 5 桁ゼロ埋めで文字列化する
- `solve_once()`
  - generator → executor → verifier/selector の単一路線で処理する

### 6. tests の実態
`tests/test_run_baseline_once.py` では、スクリプト実行結果に対して以下のみを検証しています。

- `id` が存在する
- `answer` が文字列
- `answer` が 5 桁
- `answer` が数字のみ

### 7. toy/mock 痕跡
toy/mock/placeholder の痕跡は明確です。

- shadow eval の中身が `Compute 1+1.` などの toy 問題
- README に baseline が intentionally minimal / placeholder と明記
- `docs/executor_policy.md` に tiny deterministic executor placeholder と明記
- `docs/verifier_policy.md` に single candidate / Day2 で verification 追加予定と明記

---

## 要確認

### 1. baseline 正本方針との整合
前提では baseline 正本は `verifier_mode="none"` 原則ですが、現行コードは `SimpleVerifierSelector` を必ず通します。

ただし中身は multi-candidate verifier ではなく、実質は 5 桁フォーマッタです。
よって、現状は次のどちらかに整理すべきです。

- `verifier` という名前をやめて `formatter` などへ変更する
- `verifier_mode="none"` を明示し、Day1 では verification 不使用と固定する

### 2. shadow eval の固定版として十分か
現時点の `shadow_eval.jsonl` は toy 2問だけです。
配線確認には十分ですが、Day1 の比較可能 baseline 用 shadow eval としては未完成です。

### 3. real / toy の境界
README や docs では placeholder と明記されていますが、実行時の引数・出力・メタ情報に real/toy 区別は入っていません。
このままだと後で混同しやすいです。

---

## 実行導線の要約

### 現在の最小実行コマンド
```bash
python scripts/run_baseline_once.py
```

### 完了条件
- JSON 1行が出る
- `id` が入る
- `answer` が 5 桁数字で出る

### 確認方法
- 標準出力を目視確認
- または `tests/test_run_baseline_once.py` を実行し、5桁数字出力を確認する

---

## Day1 のボトルネック

### 1. shadow eval が toy のまま
比較可能 baseline の土台としては弱いです。
今は「配線確認用データ」であり、「固定評価セット」ではありません。

### 2. verifier none 方針がコードで明文化されていない
現状は verification ではなく formatting に近い処理なのに、名前上は verifier が存在します。

### 3. 全件実行導線がない
現状は先頭1問のみです。Day1 の比較可能性を担保するには、固定 shadow eval 全件を流す最小実行導線が必要です。

### 4. toy / real / mode の明示不足
README には placeholder とありますが、コード・出力・テストにはその境界がまだ弱いです。

---

## 次に触るべきファイル優先順位

1. `data/shadow_eval.jsonl`
   - 理由: Day1 比較土台の中核。toy から固定 shadow eval に更新が必要。

2. `docs/shadow_eval_spec.md`
   - 理由: shadow eval の正本仕様を先に固定しないと実験比較が崩れる。

3. `src/aimo3/pipeline.py`
   - 理由: `verifier none` 方針と責務名の整理が必要。

4. `scripts/run_baseline_once.py`
   - 理由: 1問導線から Day1 baseline 固定確認導線へ拡張候補。

5. `tests/test_run_baseline_once.py`
   - 理由: 現在は 5 桁確認のみ。将来的に schema/mode/dataset 契約も見るべき。

---

## 次アクション

### 次アクション1: shadow eval 正本仕様の固定
#### 依頼内容
`shadow_eval` を toy から Day1 固定版へ移行するための仕様を明文化する。

#### 完了条件
- `data/shadow_eval.jsonl` の intended schema が明文化されている
- toy / real 区別が明記されている
- contamination 回避方針が記載されている
- 行数または作成基準が定義されている

#### 確認方法
- `docs/shadow_eval_spec.md` と `data/shadow_eval.jsonl` の整合レビュー

### 次アクション2: verifier none 方針のコード反映
#### 依頼内容
Day1 baseline 正本を `verifier none` 原則に合わせて命名・責務を整理する。

#### 完了条件
- `verifier` が本当に verifier なら mode 明示
- formatter なら命名変更
- README / docs / code が同じ意味で揃っている

#### 確認方法
- `pipeline.py` を見て責務が曖昧でない
- README / docs の記述と実装が一致している

### 次アクション3: Day1 比較用の最小実行導線の整備
#### 依頼内容
1問配線確認用と Day1 baseline 比較用の実行を分離する。

#### 完了条件
- 配線確認用コマンドと比較用コマンドが区別されている
- silent fallback がない
- 出力に最低限の mode 情報がある

#### 確認方法
- README の実行手順と実際の出力例が一致する
- テストが追加されている

---

## Codex への短い結論

この branch は、**AIMO3 Day1 の「配線確認用 minimal baseline repo」としては使える**状態です。
一方で、**Day1 の比較可能 baseline 正本として固定するには未完成**です。主因は以下です。

- shadow eval が toy 2問のまま
- verifier none 方針がコードに明示されていない
- 全件実行導線がない
- toy / real の境界が弱い

したがって、次は **shadow eval 仕様固定 → pipeline の責務整理 → baseline 比較導線整備** の順で進めるのが妥当です。
