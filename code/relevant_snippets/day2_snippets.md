# Day2 Relevant Code Snippets

実行可能な統合版は `code/kaggle_aimo3_v2_runner.py` に実装。

## `predict()`
- `run_kaggle_inference()` 内で `predict()` を定義し、`AIMO3InferenceServer` に渡しています。

## `_process_attempt`
- `AIMO3Solver._process_attempt()` で style/tir/python使用有無・python_error・entropy を収集。

## `_select_answer`
- `AIMO3Solver._select_answer()` は全候補に対して verifier を実行し、加点型 `composite_score` で最終選択。
- early `break` はありません。

## `inference_server.serve()` path
- `if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):` で `serve()`、それ以外は `run_local_gateway()` を実行。

## Exception handling / fallback / logging
- Verifier は `VALID / INVALID / UNVERIFIED` 三値。
- `logs/recall_eval/recall_summary.jsonl`
- `logs/ranker_eval/per_problem_candidate_scores.jsonl`
- `logs/style_eval/per_attempt_style.csv`
