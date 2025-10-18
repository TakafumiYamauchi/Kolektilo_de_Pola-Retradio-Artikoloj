# -*- coding: utf-8 -*-
"""
Streamlit アプリ：Pola Retradio の記事を期間指定で収集・統合し、ワンクリックでダウンロード
起動:
    streamlit run streamlit_app.py
"""
import time
import pandas as pd
import streamlit as st
from datetime import date, timedelta, datetime

from retradio_lib import (
    ScrapeConfig,
    collect_urls,
    fetch_article,
    _session,
    to_markdown,
    to_text,
    to_csv,
    to_jsonl,
)

st.set_page_config(page_title="Pola Retradio 期間収集ツール", layout="wide")

st.title("📻 Pola Retradio 記事収集・統合ツール")
st.markdown("""
指定した期間内に https://pola-retradio.org/ で公開された記事の URL と本文（エスペラント）を自動収集し、1つの文書へ統合します。
- **方法**: RSS/Feed と 月別アーカイブの HTML を併用（必要に応じて切替）
- **出力**: Markdown / TXT / CSV / JSONL（ダウンロード可能）
- **配慮**: robots.txt・低負荷・人間 UA、遅延（throttle）
""")

col1, col2, col3 = st.columns(3)
with col1:
    start = st.date_input("開始日", value=(date.today() - timedelta(days=14)))
with col2:
    end = st.date_input("終了日", value=date.today())
with col3:
    method = st.selectbox("収集方法", options=["both","feed","archive"], index=0)

throttle = st.slider("リクエスト間隔（秒）", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
max_pages = st.number_input("ページ送りの上限（None=制限なし）", min_value=0, value=0, step=1)
include_audio = st.checkbox("音声リンクも併記する（任意）", value=False)

if st.button("収集を実行する", type="primary"):
    cfg = ScrapeConfig(
        start_date=start, end_date=end, method=method,
        throttle_sec=throttle, max_pages=(None if max_pages==0 else int(max_pages)),
        include_audio_links=include_audio, use_cache=True
    )
    with st.spinner("URL を収集中..."):
        result = collect_urls(cfg)
    urls = result.urls
    st.success(f"候補 URL: {result.total} 件")
    st.caption(
        f"feed {result.feed_used}/{result.feed_initial}, archive {result.archive_used}/{result.archive_initial}, "
        f"duplicates removed {result.duplicates_removed}, out-of-range skipped {result.out_of_range_skipped}"
    )
    if result.earliest_date and result.latest_date:
        st.caption(f"推定公開日範囲: {result.earliest_date} ～ {result.latest_date}")
    st.write("（本文取得には少し時間がかかります。低負荷のため遅延を入れています。）")

    arts = []
    s = _session(cfg)
    progress = st.progress(0.0, "本文を取得中...")
    failures = []
    for i, u in enumerate(urls, 1):
        try:
            a = fetch_article(u, cfg, s)
            if a.published and not (cfg.start_date <= a.published.date() <= cfg.end_date):
                # 範囲外は除外
                pass
            else:
                arts.append(a)
        except Exception as e:
            st.warning(f"取得失敗: {u} ({e})")
            failures.append(f"{u} ({e})")
        finally:
            time.sleep(cfg.throttle_sec)
            progress.progress(i/len(urls), f"本文を取得中... {i}/{len(urls)}")

    # タイムゾーンを削除して比較
    def sort_key(a):
        if a.published:
            pub_naive = a.published.replace(tzinfo=None) if a.published.tzinfo else a.published
            return (pub_naive, a.url)
        return (datetime.max, a.url)
    arts.sort(key=sort_key)
    st.success(f"抽出完了: {len(arts)} 本")
    if not arts:
        st.stop()
    if failures:
        with st.expander("取得できなかった記事（要再試行）"):
            for failure in failures:
                st.write(failure)

    # 表示
    df = pd.DataFrame([{
        "published": (a.published.strftime("%Y-%m-%d") if a.published else ""),
        "title": a.title, "url": a.url,
        "author": a.author or "", "categories": ", ".join(a.categories or [])
    } for a in arts])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ダウンロード
    md = to_markdown(arts, cfg)
    txt = to_text(arts)
    csv_str = to_csv(arts)
    jsonl = to_jsonl(arts)

    st.download_button("📄 Markdown をダウンロード", md, file_name=f"pola_retradio_{start}_{end}.md", mime="text/markdown")
    st.download_button("🗒️ TXT をダウンロード", txt, file_name=f"pola_retradio_{start}_{end}.txt", mime="text/plain")
    st.download_button("🧾 CSV をダウンロード", csv_str, file_name=f"pola_retradio_{start}_{end}.csv", mime="text/csv")
    st.download_button("🧰 JSONL をダウンロード", jsonl, file_name=f"pola_retradio_{start}_{end}.jsonl", mime="application/json")
else:
    st.info("開始日・終了日を選んで「収集を実行する」をクリックしてください。")
