# Nedaka. — Backend (FastAPI)

睡眠記録を株価チャートに見立てて可視化するアプリ「Nedaka.（寝高）」のバックエンドAPIです。

- フロントエンド: [nedaka-frontend](https://github.com/yukisatodev/nedaka-frontend)
- デモ（ログイン不要）: https://gregarious-pony-811702.netlify.app/demo

## 作った背景

Site Checkに続く3つ目の制作物として、「本格的なユーザー認証」と「独自のデータ可視化ロジック」を持つプロダクトを作りたいと考えて着手しました。

睡眠記録という地味になりがちなテーマを、株式相場のメタファー（ローソク足・移動平均線・アナリストコメント）で表現することで、単なるデータ可視化の実装だけでなく、「ドメインロジックを自分で設計する」経験を積むことを意識しています。

## 仕組み

各日の記録は、前日のスコア（終値）を起点に、目標睡眠時間との差と中途覚醒回数によって増減する「株価」に変換されます。

- **Open（始値）**: 前日のClose
- **Close（終値）**: 睡眠時間・中途覚醒から計算したその日のスコア
- **High/Low（高値・安値）**: その日の値動きの振れ幅
- **MA7 / MA30**: 直近7日・30日の移動平均線
- **アナリストコメント**: 直近の平均と、その前の期間の平均を比較し、「強気相場」「弱気相場」「もみ合い」を自動判定

## エンドポイント

- `POST /api/auth/register` / `POST /api/auth/login` — JWT認証によるアカウント登録・ログイン
- `POST /api/entries` — 睡眠記録の登録・更新（同じ日付ならupsert）
- `GET /api/entries` — 全期間のローソク足データ・移動平均・アナリストコメント
- `GET /api/report` — 決算レポートPDFのダウンロード
- `GET /api/demo` / `GET /api/demo/report` — ログイン不要のサンプルデータ（デモ用）

## 使用技術

FastAPI / SQLAlchemy / SQLite / python-jose（JWT） / passlib（bcrypt） / reportlab

PDFの日本語表示には、Site Checkと同じくNoto Sans JPを必要な文字だけサブセット化して埋め込む手法を使っています。

## ローカルで動かす

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`http://127.0.0.1:8000/docs` でAPIを直接確認できます。
