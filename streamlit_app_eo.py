#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit apo (EO): Ilo por kolekti kaj kunigi artikolojn de Pola Retradio
Lanĉo:
    streamlit run GPT5pro/streamlit_app_eo.py
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

st.set_page_config(page_title="Pola Retradio – kolekto kaj kunigo", layout="wide")

st.title("📻 Pola Retradio – ilo por kolekti kaj kunigi artikolojn")
st.markdown(
    """
Ni aŭtomate kolektas la URL-ojn kaj la ĉeftekstojn (en Esperanto) de artikoloj publikigitaj ĉe https://pola-retradio.org/ dum elektita periodo, kaj kunigas ilin en unu dokumento.
- Metodo: uzas ambaŭ RSS/feeds kaj monatajn arkivojn (ŝanĝeblaj laŭbezone)
- Eligo: Markdown / TXT / CSV / JSONL (elŝuteblaj)
- Zorgo: respekti robots.txt, malpliigi servilan ŝargon, hom-simila UA, prokrasto (throttle)
"""
)

min_supported = date(2011, 1, 1)
today = date.today()
default_start = max(min_supported, today - timedelta(days=14))

col1, col2, col3 = st.columns(3)
with col1:
    start = st.date_input(
        "Komenca dato",
        value=default_start,
        min_value=min_supported,
        max_value=today,
    )
with col2:
    end = st.date_input(
        "Fina dato",
        value=today,
        min_value=min_supported,
        max_value=today,
    )
with col3:
    method = st.selectbox("Kolekta metodo", options=["both", "feed", "archive"], index=0)

throttle = st.slider("Interspaco inter petoj (sek.)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
max_pages = st.number_input("Limigo de paĝonumerado (None = senlima)", min_value=0, value=0, step=1)
include_audio = st.checkbox("Aldoni ankaŭ sonligilojn (nedeviga)", value=False)

if st.button("Ekzekuti la kolekton", type="primary"):
    cfg = ScrapeConfig(
        start_date=start,
        end_date=end,
        method=method,
        throttle_sec=throttle,
        max_pages=(None if max_pages == 0 else int(max_pages)),
        include_audio_links=include_audio,
        use_cache=True,
    )
    with st.spinner("Kolektante URL-ojn..."):
        result = collect_urls(cfg)
    urls = result.urls
    st.success(f"Kandidat-URL-oj: {result.total}")
    st.caption(
        f"feed {result.feed_used}/{result.feed_initial}, archive {result.archive_used}/{result.archive_initial}, "
        f"forigitaj duplikatoj {result.duplicates_removed}, ekskluditaj ekster periodo {result.out_of_range_skipped}"
    )
    if result.earliest_date and result.latest_date:
        st.caption(f"Proksimuma intervalo de publikigo: {result.earliest_date} – {result.latest_date}")
    st.write("La akiro de ĉeftekstoj povas postuli iom da tempo. Por redukti la ŝargon, ni enmetas prokraston inter petoj.")

    arts = []
    s = _session(cfg)
    progress = st.progress(0.0, "Elŝutante ĉeftekstojn...")
    failures = []
    for i, u in enumerate(urls, 1):
        try:
            a = fetch_article(u, cfg, s)
            if a.published and not (cfg.start_date <= a.published.date() <= cfg.end_date):
                pass
            else:
                arts.append(a)
        except Exception as e:
            st.warning(f"Malsukcesis akiri: {u} ({e})")
            failures.append(f"{u} ({e})")
        finally:
            time.sleep(cfg.throttle_sec)
            progress.progress(i / len(urls), f"Elŝutante ĉeftekstojn... {i}/{len(urls)}")

    def sort_key(a):
        if a.published:
            pub_naive = a.published.replace(tzinfo=None) if a.published.tzinfo else a.published
            return (pub_naive, a.url)
        return (datetime.max, a.url)

    arts.sort(key=sort_key)
    st.success(f"Pretigita: {len(arts)} artikoloj")
    if not arts:
        st.stop()
    if failures:
        with st.expander("Ne akiritaj eroj (indas reprovi)"):
            for failure in failures:
                st.write(failure)

    df = pd.DataFrame(
        [
            {
                "publikigita": (a.published.strftime("%Y-%m-%d") if a.published else ""),
                "titolo": a.title,
                "URL": a.url,
                "aŭtoro": a.author or "",
                "kategorioj": ", ".join(a.categories or []),
            }
            for a in arts
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    md = to_markdown(arts, cfg)
    txt = to_text(arts)
    csv_str = to_csv(arts)
    jsonl = to_jsonl(arts)

    st.download_button("📄 Elŝuti Markdown", md, file_name=f"pola_retradio_{start}_{end}.md", mime="text/markdown")
    st.download_button("🗒️ Elŝuti TXT", txt, file_name=f"pola_retradio_{start}_{end}.txt", mime="text/plain")
    st.download_button("🧾 Elŝuti CSV", csv_str, file_name=f"pola_retradio_{start}_{end}.csv", mime="text/csv")
    st.download_button("🧰 Elŝuti JSONL", jsonl, file_name=f"pola_retradio_{start}_{end}.jsonl", mime="application/json")
else:
    st.info("Elektu komencan kaj finan datojn, poste alklaku ‘Ekzekuti la kolekton’.")
