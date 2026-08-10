# Site Check — Backend (FastAPI)

Webサイト診断ツール「Site Check」のバックエンドAPIです。
URLを受け取り、SEO・セキュリティ・パフォーマンス（PageSpeed Insights連携時）を診断し、
結果を保存・PDFレポート化します。

- フロントエンド: [site-check-frontend](https://github.com/yukisatodev/site-check-frontend-)
- 公開URL（フロントエンド経由で利用）: https://effulgent-dodol-5d27d4.netlify.app/
- 制作の背景・経緯: [ポートフォリオサイト内の紹介ページ](https://yukisatodev.github.io/)

## 作った背景

フリーランスとして企業のDX推進・業務改善を支援する中で、「提案するだけでなく、自分の手で仕組みを形にできるようになりたい」という思いが強くなり、その最初の実践としてこのツールを作りました。

Webサイト診断ツールというテーマは、これまで建設・不動産会社向けに自社Webサイトの構築を担当してきた経験と直結しています。企業のサイトが抱えがちな基本的なSEO・セキュリティ上の課題を、URLを入れるだけで自動的に洗い出し、単なる指摘で終わらせず「何をどう直せばいいか」まで返すことを目指しました。

バックエンドをPython/FastAPIで組んだのは、これまでフロントエンド寄りの学習が中心だったため、意識的にバックエンド・クラウド領域の実装経験を積むためです。実際にRenderへデプロイする過程では、Pythonのバージョン差異、フォルダ構成、PDF生成ライブラリがサーバー環境で動かない、といった「ローカルでは気づかない」問題に何度も直面しました。それを一つずつ切り分けて解決していったプロセス自体が、このプロジェクトで一番の学びになっています。

## エンドポイント

- `POST /api/diagnose` — URLを診断し、前回結果との差分つきで返す
- `GET /api/report/{result_id}` — 診断結果をPDFでダウンロード
- `GET /api/history/{url}` — 指定URLの診断履歴を取得

## 診断項目と改善提案

- **SEO**: title タグ / meta description / h1 タグ / 画像の alt 属性
- **セキュリティ**: HTTPS化 / Strict-Transport-Security / X-Content-Type-Options / X-Frame-Options
- **パフォーマンス**: Google PageSpeed Insights API（`PAGESPEED_API_KEY`環境変数を設定した場合のみ計測）

いずれの項目も、問題があった場合は「なぜ問題か」「どう直せばいいか」を含む改善提案文を返します。単なるチェックツールで終わらせず、次のアクションにつながる出力を意識しました。

## 技術選定の理由

| 技術 | 採用理由 |
|---|---|
| FastAPI | 型安全なリクエスト/レスポンス定義と、`/docs`でのAPIドキュメント自動生成が開発効率に直結するため |
| SQLAlchemy + SQLite | まずシンプルな構成で確実に動かすことを優先。`DATABASE_URL`環境変数を差し替えるだけで、Turso等のクラウドDBにも移行できる設計にしてある |
| BeautifulSoup | 取得したHTMLからSEO関連タグ(title・meta description・h1・alt属性)を解析するために使用 |
| reportlab | 当初はWeasyPrintでPDFを生成していたが、Renderの標準Python環境にはPango/Cairo等のシステムライブラリが無く動作しなかったため、pure PythonのreportLabに切り替え。日本語フォント(Noto Sans JP)は必要な文字だけをサブセット化して埋め込み、軽量かつ確実に日本語が表示されるようにした |

## ローカルで動かす

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`http://127.0.0.1:8000/docs` でAPIを直接確認できます。
パフォーマンス計測をしたい場合は、環境変数`PAGESPEED_API_KEY`にGoogle PageSpeed Insights APIキーを設定してください（未設定でもSEO・セキュリティ診断は動作します）。

## 今後やりたいこと

- 診断項目の追加（robots.txt / sitemap.xml の有無など）
- 履歴データをもとにしたスコア推移グラフ
- クラウドDB(Turso等)への移行
