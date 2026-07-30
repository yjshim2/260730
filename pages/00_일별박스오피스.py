import streamlit as st
import pandas as pd
import requests
import plotly.express as px

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ----------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------

st.set_page_config(
    page_title="박스오피스 분석 대시보드",
    layout="wide"
)

st.title("🎬 어제의 박스오피스 분석")


# ----------------------------------------------------------
# KOBIS API 키
# ----------------------------------------------------------

KOBIS_KEY = st.secrets["KOBIS_KEY"]


# ----------------------------------------------------------
# 한국 시간 기준 어제 날짜
# ----------------------------------------------------------

yesterday = (
    datetime.now(ZoneInfo("Asia/Seoul"))
    - timedelta(days=1)
)

target_dt = yesterday.strftime("%Y%m%d")


st.caption(
    f"조회 기준일 : {yesterday.strftime('%Y-%m-%d')}"
)


# ----------------------------------------------------------
# KOBIS API 호출
# ----------------------------------------------------------

url = (
    "https://www.kobis.or.kr/"
    "kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


res = requests.get(
    url,
    params={
        "key": KOBIS_KEY,
        "targetDt": target_dt
    },
    timeout=10
)


if res.status_code != 200:
    st.error(
        f"API 요청 실패 : {res.status_code}"
    )
    st.stop()


data = res.json()


# 인증 오류 확인

if "faultInfo" in data:
    st.error(
        "API 인증키 오류입니다. "
        "Streamlit Secrets의 KOBIS_KEY를 확인하세요."
    )
    st.stop()



box_list = (
    data
    .get("boxOfficeResult", {})
    .get("dailyBoxOfficeList", [])
)


if not box_list:
    st.warning(
        "조회 데이터가 없습니다."
    )
    st.stop()



# ----------------------------------------------------------
# 데이터 정리
# ----------------------------------------------------------

df = pd.DataFrame(box_list)


number_cols = [
    "rank",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]


for col in number_cols:
    df[col] = pd.to_numeric(
        df[col]
    )



# ----------------------------------------------------------
# 1위 카드
# ----------------------------------------------------------

top = (
    df
    .sort_values("rank")
    .iloc[0]
)


c1, c2, c3 = st.columns(3)


c1.metric(
    "🥇 어제 1위",
    top["movieNm"]
)


c2.metric(
    "👥 어제 관객수",
    f"{top['audiCnt']:,}명"
)


c3.metric(
    "🎞 누적 관객",
    f"{top['audiAcc']:,}명"
)



# ----------------------------------------------------------
# TOP10 표
# ----------------------------------------------------------

table = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()


table.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


table = (
    table
    .sort_values("순위")
    .reset_index(drop=True)
)


st.subheader(
    "📋 박스오피스 TOP 10"
)


st.dataframe(
    table,
    use_container_width=True,
    hide_index=True
)



# ----------------------------------------------------------
# TOP5 관객 점유율
# ----------------------------------------------------------

st.subheader(
    "🥧 전체 TOP5 관객 점유율"
)


top5 = (
    table
    .sort_values(
        "관객수",
        ascending=False
    )
    .head(5)
)


fig_pie = px.pie(
    top5,
    values="관객수",
    names="영화명",
    hole=0.45
)


fig_pie.update_traces(
    textinfo="percent+label"
)


fig_pie.update_layout(
    height=450
)


st.plotly_chart(
    fig_pie,
    use_container_width=True
)



# ----------------------------------------------------------
# 애니메이션 분석
# ----------------------------------------------------------

st.markdown("---")


st.header(
    "🎨 애니메이션 영화 분석"
)


# 영화명 기반 애니메이션 검색
# KOBIS에는 장르 정보가 없기 때문에 키워드 방식 사용

animation_keywords = [
    "애니",
    "극장판",
    "짱구",
    "도라에몽",
    "코난",
    "픽사",
    "디즈니",
    "토이",
    "모아나",
    "귀멸",
]


animation_df = table[
    table["영화명"]
    .str.contains(
        "|".join(animation_keywords),
        na=False
    )
].copy()



if animation_df.empty:

    st.info(
        "현재 TOP10 안에 애니메이션 영화가 없습니다."
    )


else:


    animation_df = (
        animation_df
        .sort_values(
            "관객수",
            ascending=False
        )
        .reset_index(drop=True)
    )


    # ------------------------------------------------------
    # 애니메이션 최고작 카드
    # ------------------------------------------------------

    ani_top = animation_df.iloc[0]


    a1, a2, a3 = st.columns(3)


    a1.metric(
        "🎨 최고 흥행 애니",
        ani_top["영화명"]
    )


    a2.metric(
        "👥 관객수",
        f"{ani_top['관객수']:,}명"
    )


    a3.metric(
        "🎬 스크린수",
        f"{ani_top['스크린수']}개"
    )



    # ------------------------------------------------------
    # 애니메이션 관객 점유율
    # ------------------------------------------------------

    st.subheader(
        "🥧 애니메이션 관객 점유율"
    )


    ani_pie = px.pie(
        animation_df.head(5),
        values="관객수",
        names="영화명",
        hole=0.45
    )


    ani_pie.update_traces(
        textinfo="percent+label"
    )


    st.plotly_chart(
        ani_pie,
        use_container_width=True
    )



    # ------------------------------------------------------
    # 애니메이션 관객 비교
    # ------------------------------------------------------

    st.subheader(
        "📈 애니메이션 관객 비교"
    )


    ani_bar = px.bar(
        animation_df.head(5),
        x="관객수",
        y="영화명",
        orientation="h",
        text="관객수"
    )


    ani_bar.update_layout(
        height=400,
        yaxis_title="",
        xaxis_title="관객수"
    )


    st.plotly_chart(
        ani_bar,
        use_container_width=True
    )
