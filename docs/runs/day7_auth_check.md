# Day7 — 認証経路確認

## 目的

`ANTHROPIC_API_KEY` 未設定のまま、Claude subscription 経路で live 実行できるか確認する。

---

## 事前確認結果

### git 状態

```
branch:  codex/restart-clean
remote:  http://local_proxy@127.0.0.1:.../git/hinemos-anzu/AIMO3
status:  clean (uncommitted changes: none)
```

### 環境変数

| 変数 | 状態 |
|---|---|
| `ANTHROPIC_API_KEY` | **設定なし** |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` |

### Claude Code 認証設定（`~/.claude.json` 調査）

| 項目 | 値 |
|---|---|
| `oauthAccount` | `False`（subscription OAuth 未リンク） |
| `apiKey`（config 内） | 空（未設定） |
| `primaryApiKey`（config 内） | 空（未設定） |
| `userID` | 存在する |
| `cachedExtraUsageDisabledReason` | `org_level_disabled` |

**解釈：**
- Claude Code のユーザー ID は存在するが、org レベルで使用が無効化されている
- OAuth/subscription アカウントはリンクされていない（`oauthAccount: False`）
- config 内にも API key は存在しない
- つまり、Claude Code は **未認証状態** に相当する

---

## solver.py の認証設計調査

`src/day1_minimal_baseline/solver.py` の `_make_llm_solver()`:

```python
api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if not api_key:
    raise SolverConfigError("ANTHROPIC_API_KEY environment variable is not set.")
client = anthropic.Anthropic(api_key=api_key)
```

**判定：** `solver.py` は `ANTHROPIC_API_KEY` 環境変数 **のみ** を確認する設計。
OAuth/subscription 経路は持たない。

---

## live 実行可否判定

live 実行を阻む独立したブロッカーが **2 つ** 存在する：

| # | ブロッカー | 分類 |
|---|---|---|
| 1 | `ANTHROPIC_API_KEY` 未設定 | 環境制約 |
| 2 | `solver.py` が API key 専用設計（subscription 経路なし） | コード設計制約 |

ブロッカー 2 を解消するには `solver.py` の設計変更が必要。
これは「大改造しない」「変更は最小限」方針に照らし、今 Day で行うスコープ外。

---

## 中止条件発火

```
中止条件:
  solver 側が API key 固定で、設計変更なしには進めない
  → 無理に進めず停止し、理由を明記する
```

中止条件が発火したため、live 実行は行わない。

---

## subscription 経路で動かすための条件（参考）

将来的に subscription 経路で live 実行するには、以下が必要：

1. Claude Code で subscription アカウントをリンクする（`claude auth login` 等）
2. `solver.py` の `_make_llm_solver()` を subscription 認証に対応させる
   - `anthropic.Anthropic()` は `api_key=None` + `auth_token` または別クライアント経由で OAuth に対応可能
   - または、`claude` CLI の `--print` フラグ経由でサブプロセス実行する別アーキテクチャ

---

## テスト（認証不要）

```
pytest tests/ -q
140 passed
```

140 テストはすべて monkeypatch ベースで API key 不要。変更なし。

---

## 結果まとめ

| 項目 | 結果 |
|---|---|
| `ANTHROPIC_API_KEY` 未設定を確認 | **PASS** |
| Claude Code の認証方式を整理 | **PASS**（未認証 + org_level_disabled） |
| subscription OAuth リンク確認 | **FAIL**（リンクなし） |
| solver.py の subscription 対応確認 | **FAIL**（API key 専用設計） |
| live 実行 | **BLOCKED**（中止条件発火） |
| placeholder fallback 使用 | なし（silent fallback なし） |
| 既存導線破壊 | なし |
| コード変更 | なし |

**総合判定: WARN（設計・環境の両方が未整備、live 実行不可）**
