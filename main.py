# main.py
# ==========================================================
# 전국 시군구 고령화 지도 (65세 이상 인구 비율)
#
# Streamlit Cloud용
#
# 필요한 추가 패키지
#   geopandas
#   branca
#
# (streamlit, pandas, numpy, plotly, requests는 이미 설치되어 있다고 가정)
# ==========================================================

import json

import branca.colormap as cm
import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px

# ----------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------
st.set_page_config(
    page_title="전국 시군구 고령화 지도",
    layout="wide",
)

st.title("🗺️ 전국 시군구 고령화 지도")
st.caption("시군구별 65세 이상 인구 비율 (최신 연도 기준)")

# ----------------------------------------------------------
# 데이터 주소
# ----------------------------------------------------------
POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"

GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"


# ----------------------------------------------------------
# 인구 데이터 읽기
# ----------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_population():
    # 코드는 반드시 문자열
    df = pd.read_csv(
        POP_URL,
        compression="gzip",
        dtype={"코드": str},
    )

    df["코드"] = df["코드"].str.zfill(10)
    df["시군구코드"] = df["코드"].str[:5]

    return df


# ----------------------------------------------------------
# GeoJSON 읽기
# ----------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_geo():
    gdf = gpd.read_file(GEO_URL)

    gdf["코드"] = gdf["코드"].astype(str).str.zfill(5)

    return gdf


# ----------------------------------------------------------
# 최신 연도 시군구별 고령화율 계산
# ----------------------------------------------------------
@st.cache_data(show_spinner=False)
def make_sigungu_table(df):
    latest_year = df["연도"].max()

    latest = df[df["연도"] == latest_year].copy()

    # --------------------------
    # 전체 인구 열 찾기
    # --------------------------
    total_cols = [c for c in latest.columns if c.startswith("계_")]

    # --------------------------
    # 65세 이상 열 찾기
    # --------------------------
    elderly_cols = []

    for c in total_cols:
        age = c.replace("계_", "")

        if age == "100세 이상":
            elderly_cols.append(c)
            continue

        if age.endswith("세"):
            try:
                n = int(age.replace("세", ""))
                if n >= 65:
                    elderly_cols.append(c)
            except Exception:
                pass

    # --------------------------
    # 읍면동 -> 시군구 합계
    # --------------------------
    latest["전체"] = latest[total_cols].sum(axis=1)
    latest["고령"] = latest[elderly_cols].sum(axis=1)

    sig = (
        latest.groupby("시군구코드", as_index=False)[["전체", "고령"]]
        .sum()
    )

    sig["고령화율"] = sig["고령"] / sig["전체"] * 100

    return latest_year, sig


# ----------------------------------------------------------
# 데이터 준비
# ----------------------------------------------------------
with st.spinner("데이터 불러오는 중..."):

    pop = load_population()
    latest_year, sig = make_sigungu_table(pop)
    geo = load_geo()

    gdf = geo.merge(
        sig,
        left_on="코드",
        right_on="시군구코드",
        how="left",
    )

# ----------------------------------------------------------
# 단계 구분
# ----------------------------------------------------------
bins = [-np.inf, 19, 23, 28, 38, np.inf]

labels = [
    "19% 미만",
    "19~23%",
    "23~28%",
    "28~38%",
    "38% 이상",
]

gdf["구간"] = pd.cut(
    gdf["고령화율"],
    bins=bins,
    labels=labels,
    include_lowest=True,
)

# 5단계 색
color_map = {
    "19% 미만": "#F2F0F7",
    "19~23%": "#CBC9E2",
    "23~28%": "#9E9AC8",
    "28~38%": "#756BB1",
    "38% 이상": "#54278F",
}

# ----------------------------------------------------------
# Plotly용 GeoJSON
# ----------------------------------------------------------
geojson = json.loads(gdf.to_json())

plot_df = gdf.copy()

plot_df["고령화율표시"] = plot_df["고령화율"].round(1)

# ----------------------------------------------------------
# 지도
# ----------------------------------------------------------
fig = px.choropleth(
    plot_df,
    geojson=geojson,
    locations="코드",
    featureidkey="properties.코드",
    color="구간",
    category_orders={"구간": labels},
    color_discrete_map=color_map,
    hover_name="시군구",
    hover_data={
        "시도": True,
        "고령화율표시": ":.1f",
        "구간": False,
        "코드": False,
    },
)

fig.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>"
    + "시도: %{customdata[0]}<br>"
    + "고령화율: %{customdata[1]:.1f}%<extra></extra>"
)

fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor="rgba(0,0,0,0)",
)

fig.update_layout(
    title=f"{latest_year}년 시군구별 65세 이상 인구 비율",
    legend_title="고령화율",
    margin=dict(l=0, r=0, t=60, b=0),
    paper_bgcolor="white",
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------
# 범례 설명
# ----------------------------------------------------------
st.markdown(
    """
**범례**

🟪 19% 미만 &nbsp;&nbsp;
🟪 19~23% &nbsp;&nbsp;
🟪 23~28% &nbsp;&nbsp;
🟪 28~38% &nbsp;&nbsp;
🟪 38% 이상
"""
)

# ----------------------------------------------------------
# 상위/하위 10개
# ----------------------------------------------------------
rank = (
    gdf[["시도", "시군구", "고령화율"]]
    .copy()
    .sort_values("고령화율", ascending=False)
)

rank["고령화율(%)"] = rank["고령화율"].round(2)

top10 = (
    rank[["시도", "시군구", "고령화율(%)"]]
    .head(10)
    .reset_index(drop=True)
)

bottom10 = (
    rank[["시도", "시군구", "고령화율(%)"]]
    .tail(10)
    .sort_values("고령화율(%)")
    .reset_index(drop=True)
)

st.markdown("---")

c1, c2 = st.columns(2)

with c1:
    st.subheader("고령화율 높은 시군구 TOP 10")
    st.dataframe(
        top10,
        use_container_width=True,
        hide_index=True,
    )

with c2:
    st.subheader("고령화율 낮은 시군구 TOP 10")
    st.dataframe(
        bottom10,
        use_container_width=True,
        hide_index=True,
    )
