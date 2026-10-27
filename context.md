# context.md

## Key points
- Notebookは**1セルのみ**に制限し、実行状態は**メッセージ（print/log）で確認可能**にする
- 実行環境は **Local / Google Colab を自動判定**し、clone 先の `yaml/ data/ output/` を使う。GitHub 更新ではこの3つを消さない
- **Localは venv 前提**も明記（Python3.12固定、再現性担保）
- データは `data/` に **ケース毎=CSVファイル名**で保存（拡張子除く=case_id）
- CLIは **case指定あり→1件 / 指定なし→data/全CSVを一括図化**
- 図の **縦横比・解像度・フォント（title/axis/legend別）** は `yaml/base.yaml` で調整（ケースyamlで上書き可）
- 出力は**ファイル保存のみ**、`output/{case_id}/...` にケース別整理

---

## 1. Project Overview
### 1.1 Goal
間隙水圧計（＋必要なら変位計）CSVを入力として、ケース単位で以下を自動生成して保存する：
- 水頭（補正前/補正後）
- 圧力勾配（P1基準、外水位基準）
- 変位（任意）
- 指標（例：指定時刻の勾配抽出など）
- 実行ログ、使用設定（YAML）

### 1.2 Non-Goals
- 対話GUI、ノートブック多セル運用
- 画面表示前提（`plt.show()` 依存）
- 手作業でパスを書き換える運用（環境判定で吸収）

---

## 2. Inputs / File convention
### 2.1 Data directory rule
- 入力は `data/` 直下にCSVを配置
- **case_id = CSVファイル名（拡張子除く）**
  - 例：`data/CaseA.csv` → `case_id: "CaseA"`
- `--case` 未指定の場合、`data/*.csv` を全件処理（globはbase.yamlで制御）

### 2.2 CSV read assumptions (from reference notebook)
- `pd.read_csv(..., encoding='shift-jis', skiprows=?, skipfooter=?, engine='python')` 等
- こういう癖は**YAMLへ逃がす**（コードに埋めない）

---

## 3. Outputs
### 3.1 Output policy
- 生成物は全て `output/{case_id}/` 配下に保存
- 同一ケースは再実行で上書き（ログや `config_used.yml` は残す方針でも可）

### 3.2 Output structure
output/
  {case_id}/
    figures/
      waterhead.png
      gradient_from_p1.png
      gradient_from_outside.png
      displacement.png
      combined_4panel.png
    data/
      waterhead.csv
      waterhead_approx.csv
      gradient_from_p1.csv
      gradient_from_outside.csv
      displacement.csv
      metrics.json
    logs/
      run.log
      config_used.yml

---

## 4. Configuration (YAML)
### 4.0 Config layering
- `yaml/base.yaml`（共通：入出力・環境・図化スタイル。無ければ `templates/yaml` から作る）
- `yaml/{case_id}.yaml` または `yaml/cases/{case_id}.yaml`（ケース固有）
- マージ順：**base → case（caseが上書き）**

### 4.1 base.yaml（必須）
- 図の縦横比（width/height or ratio）
- dpi
- フォントサイズ（title/axis/legend）
- data_dir / output_dir / params_dir / src_dir 等（環境で切替）

#### base.yaml schema（概念）
project:
  env: "auto"            # auto / local / colab
  paths:
    local:
      root: "."
      data_dir: "./data"
      params_dir: "./params"
      src_dir: "./src"
      output_dir: "./output"
      venv_dir: "./.venv"
    colab:
      root: "/content"
      data_dir: "/content/data"
      params_dir: "/content/params"
      src_dir: "/content/src"
      output_dir: "/content/output"

io:
  encoding: "shift-jis"
  read_csv:
    skiprows: 69
    skipfooter: 7
    engine: "python"

plot_style:
  figure:
    aspect:
      mode: "width_height"    # width_height / ratio
      width_in: 12.0
      height_in: 6.0
      # ratio: 2.0
    dpi: 200
    constrained_layout: true
  fonts:
    family: "DejaVu Sans"
    title: 14
    axis_label: 12
    tick_label: 10
    legend: 10
  save:
    format: "png"
    transparent: false

---

## 5. Architecture
### 5.1 Directory layout
.
├─ context.md
├─ pyproject.toml
├─ params/
│   ├─ base.yaml
│   └─ cases/
│       └─ *.yaml
├─ src/
│   └─ poreviz/
│       ├─ __init__.py
│       ├─ env.py          # Local/Colab判定・パス解決
│       ├─ config.py       # base+caseのロードとdeep-merge
│       ├─ io.py           # CSV読取
│       ├─ processing.py   # 変換/補正/勾配
│       ├─ plotting.py     # 保存専用
│       ├─ pipeline.py     # run_case / run_all
│       └─ cli.py          # CLI
├─ notebooks/
│   └─ run.ipynb           # 1セルのみ（後述）
├─ tests/
│   ├─ test_env.py
│   ├─ test_processing.py
│   └─ test_pipeline.py
└─ output/                 # gitignore

### 5.2 Environment auto-detection
- 判定は `env.py` に集約
- ルール（例）：
  - `import google.colab` が通る、または環境変数/パスでColab判定
  - それ以外は local
- 判定結果で `base.yaml` の `project.paths.{local|colab}` を選び、以後は **絶対パス化**して扱う

---

## 6. Local environment (venv) policy（追加）
### 6.1 Python version
- Localは **Python 3.12** を使用する（`python3.12` を明示）

### 6.2 venv creation & usage
- venvはプロジェクト直下の `./.venv/` を標準とする
- 依存は `pyproject.toml` を単一の正とし、以下を許容：
  - `python -m venv .venv` + `pip install -e .`
  - もしくは uv/poetry等（採用ツールはプロジェクトで固定）

### 6.3 Minimal local commands（例）
- 作成：
  - `python3.12 -m venv .venv`
  - `source .venv/bin/activate`
  - `python -m pip install -U pip`
  - `python -m pip install -e ".[dev]"`
- 実行：
  - `poreviz run`（全件）
  - `poreviz run --case CaseA`（単体）
- テスト：
  - `pytest -q`

---

## 7. CLI Spec
- `poreviz run`
  - `--case <case_id>`：`data/<case_id>.csv` のみ処理
  - 未指定：`data/*.csv` を全件処理
  - `--base params/base.yaml`（既定値あり）
  - `--case-config params/cases/<case_id>.yaml`（存在すれば自動適用）
- `poreviz validate`
  - baseとcaseのスキーマ整合（キー不足/型不一致は即エラー）
- `poreviz list`
  - `data/` 内CSVから case一覧

終了コード（例）：
- 0 success
- 2 config error
- 3 io error
- 4 processing error

---

## 8. Notebook policy（重要：1セル運用）
### 8.1 Notebook constraints
- Notebookは **1セルのみ**
- セル内は「CLI呼び出し」か「pipelineエントリ」を1発実行するだけ
- 実行状態は **メッセージで確認**できること（例：開始/終了、対象case数、出力先）

### 8.2 Expected notebook behavior
- 実行時に必ず出すメッセージ（例）：
  - 実行環境（local/colab）
  - 読み込んだbase.yamlパス
  - case指定の有無、処理対象ケース数
  - 出力ディレクトリ
  - 成功/失敗（失敗時は例外要約）

---

## 9. Testing (pytest)
- `env` 判定（local/colab相当をモック）
- `discover_cases()` が `data/` のCSV数と一致
- `run_all()` が output/{case_id}/ を全件生成
- 画像のpixelサイズが `width_in * dpi` に概ね一致（許容誤差つき）

---

## 10. Definition of Done
- `data/` にCSVを置くだけで、指定なし実行で全件図化できる
- `--case` で単体実行できる
- 図の見た目は `params/base.yaml` で統制できる（縦横比/dpi/フォント別）
- Notebookは1セル、ログで状態確認できる
- Local/Colabでパスを自動切替できる
- Localはvenvで再現可能
- pytestが通る