#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 앱(KR): Pola Retradio 기사 수집·통합
실행:
    streamlit run GPT5pro/streamlit_app_ko.py
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

st.set_page_config(page_title="Pola Retradio 기사 수집·통합", layout="wide")

st.title("📻 Pola Retradio 기사 수집·통합 도구")
st.markdown(
    """
지정한 기간 동안 https://pola-retradio.org/ 에 공개된 글의 URL과 본문(에스페란토)을 자동으로 수집하여 하나의 문서로 통합합니다.
- 방법: RSS/피드와 월별 아카이브 HTML을 병행 사용(필요 시 전환)
- 출력: Markdown / TXT / CSV / JSONL (다운로드 가능)
- 배려: robots.txt 준수, 서버 부하 최소화, 사람용 UA, 요청 간 지연(throttle)
"""
)

min_supported = date(2011, 1, 1)
today = date.today()
default_start = max(min_supported, today - timedelta(days=14))

col1, col2, col3 = st.columns(3)
with col1:
    start = st.date_input(
        "시작일",
        value=default_start,
        min_value=min_supported,
        max_value=today,
    )
with col2:
    end = st.date_input(
        "종료일",
        value=today,
        min_value=min_supported,
        max_value=today,
    )
with col3:
    method = st.selectbox("수집 방법", options=["both", "feed", "archive"], index=0)

throttle = st.slider("요청 간 간격(초)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
max_pages = st.number_input("페이지 넘김 상한(None=제한 없음)", min_value=0, value=0, step=1)
include_audio = st.checkbox("오디오 링크도 함께 표기(선택)", value=False)

if st.button("수집 실행", type="primary"):
    cfg = ScrapeConfig(
        start_date=start,
        end_date=end,
        method=method,
        throttle_sec=throttle,
        max_pages=(None if max_pages == 0 else int(max_pages)),
        include_audio_links=include_audio,
        use_cache=True,
    )
    with st.spinner("URL 수집 중..."):
        result = collect_urls(cfg)
    urls = result.urls
    st.success(f"후보 URL: {result.total}건")
    st.caption(
        f"feed {result.feed_used}/{result.feed_initial}, archive {result.archive_used}/{result.archive_initial}, "
        f"중복 제거 {result.duplicates_removed}, 기간 외 제외 {result.out_of_range_skipped}"
    )
    if result.earliest_date and result.latest_date:
        st.caption(f"추정 공개일 범위: {result.earliest_date} ~ {result.latest_date}")
    st.write("본문 수집에는 시간이 조금 걸립니다. 서버 부하를 줄이기 위해 지연을 두었습니다.")

    arts = []
    s = _session(cfg)
    progress = st.progress(0.0, "본문을 수집 중...")
    failures = []
    for i, u in enumerate(urls, 1):
        try:
            a = fetch_article(u, cfg, s)
            if a.published and not (cfg.start_date <= a.published.date() <= cfg.end_date):
                pass
            else:
                arts.append(a)
        except Exception as e:
            st.warning(f"수집 실패: {u} ({e})")
            failures.append(f"{u} ({e})")
        finally:
            time.sleep(cfg.throttle_sec)
            progress.progress(i / len(urls), f"본문을 수집 중... {i}/{len(urls)}")

    def sort_key(a):
        if a.published:
            pub_naive = a.published.replace(tzinfo=None) if a.published.tzinfo else a.published
            return (pub_naive, a.url)
        return (datetime.max, a.url)

    arts.sort(key=sort_key)
    st.success(f"추출 완료: {len(arts)}건")
    if not arts:
        st.stop()
    if failures:
        with st.expander("가져오지 못한 글(재시도 필요)"):
            for failure in failures:
                st.write(failure)

    df = pd.DataFrame(
        [
            {
                "공개일": (a.published.strftime("%Y-%m-%d") if a.published else ""),
                "제목": a.title,
                "URL": a.url,
                "작성자": a.author or "",
                "카테고리": ", ".join(a.categories or []),
            }
            for a in arts
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    md = to_markdown(arts, cfg)
    txt = to_text(arts)
    csv_str = to_csv(arts)
    jsonl = to_jsonl(arts)

    st.download_button("📄 Markdown 다운로드", md, file_name=f"pola_retradio_{start}_{end}.md", mime="text/markdown")
    st.download_button("🗒️ TXT 다운로드", txt, file_name=f"pola_retradio_{start}_{end}.txt", mime="text/plain")
    st.download_button("🧾 CSV 다운로드", csv_str, file_name=f"pola_retradio_{start}_{end}.csv", mime="text/csv")
    st.download_button("🧰 JSONL 다운로드", jsonl, file_name=f"pola_retradio_{start}_{end}.jsonl", mime="application/json")
else:
    st.info("시작일·종료일을 선택한 뒤 ‘수집 실행’을 클릭하세요.")
