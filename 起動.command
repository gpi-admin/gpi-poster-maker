#!/bin/bash
# GPI Poster Maker 起動スクリプト
# ダブルクリックで実行できます

# このスクリプトのディレクトリに移動
cd "$(dirname "$0")"

echo "================================================"
echo "  GPI Poster Maker を起動しています..."
echo "================================================"

# Python が利用可能か確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3 が見つかりません。"
    echo "https://www.python.org からインストールしてください。"
    read -p "Enterキーを押して終了..."
    exit 1
fi

# 仮想環境が存在する場合は有効化
if [ -d ".venv" ]; then
    echo "仮想環境を有効化..."
    source .venv/bin/activate
fi

# 依存パッケージのインストール（初回のみ時間がかかります）
echo "依存パッケージを確認中..."
pip3 install -r requirements.txt -q

echo ""
echo "ブラウザが自動で開きます..."
echo "終了するには このウィンドウで Ctrl+C を押してください"
echo "================================================"

# Streamlit 起動
python3 -m streamlit run app.py --server.headless false

read -p "Enterキーを押して終了..."
