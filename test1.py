from openai import OpenAI
import os
import pandas as pd
from pymongo import MongoClient
import pymongo
import riskfolio as rp
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import re
import certifi
import sys  # sys 모듈 추가

# OpenAI API 키 설정 (환경 변수에서 가져오기)
client = OpenAI(
    api_key="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"
)

# 1. MongoDB Atlas 연결
uriCloud = "mongodb+srv://fua990401:Mxl8n9j31X1LILXZ@funddata.es8v3.mongodb.net/?retryWrites=true&w=majority&appName=FundData"
cert = certifi.where()

# 사용할 데이터베이스와 컬렉션 선택
dbclient = MongoClient(uriCloud, tls=True, tlsCAFile=cert, connectTimeoutMS=30000, socketTimeoutMS=30000)
db = dbclient['fund_data']  # 데이터베이스 이름
collectionr = db['fund_rate']  # 수익률 관련 컬렉션
collections = db['fund_sector']  # 섹터 관련 컬렉션

# 실시간 금융 데이터 예시
current_financial_data = {
    "KOSPI": 2631.68,
    "interest_rate": 3.5,
    "exchange_rate": 1335.30
}

user_profile = {
    "age": 30}

data_r = list(collectionr.find())
dfr = pd.DataFrame(data_r)
data_s = list(collections.find())
dfs = pd.DataFrame(data_s)

# '주요 섹터'가 'None' 문자열이나 None 값인 경우는 빈 리스트로 처리하고, 나머지는 쉼표로 구분하여 리스트로 변환
dfus = dfs['주요 섹터'].apply(lambda x: x.split(',') if isinstance(x, str) and x != 'None' else [])

# 빈 리스트와 'None' 문자열을 제외하고 리스트 내부의 섹터를 평평하게(flatten) 만들어 중복 제거
sectors_list = [sublist for sublist in dfus if sublist]  # 빈 리스트가 아닌 경우에만 처리
unique_sectors = set([sector.strip() for sublist in sectors_list for sector in sublist if sector and sector != 'None'])  # 'None' 문자열 제거

def latest_df(df):
    # 기준일자를 datetime 형식으로 변환
    df['기준일자'] = pd.to_datetime(df['기준일자'])
    # 각 펀드별로 최신 기준일자를 기준으로 데이터 선택
    latest_data = df.loc[df.groupby('펀드명')['기준일자'].idxmax()]
    return latest_data

def user_risk(user_profile):
    if user_profile["age"] == 30:
        risk = "R"
    else:
        risk = "S"
    return risk

def classify_sector(user_input):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"넌 펀드 추천 질문에서 섹터를 찾아서 분류할 예정이야. 섹터는 {unique_sectors} 이거야. 섹터를 분류할 수 있으면 그 섹터만 출력하고, 입력된 질문 중에 섹터 내용이 없다면 0을 출력해줘. 예시 답변: 정보기술, 0"},
            {"role": "user", "content": f"이 질문을 펀드 섹터에 맞게 분류해줘.: '{user_input}'"}
        ],
        max_tokens=50,
        temperature=0
    )
    classification = response.choices[0].message.content.strip()
    return classification

def find_top_negative_correlations(df, target_fund_name):
    # 각 펀드별 모든 일자의 데이터 사용
    df['기준일자'] = pd.to_datetime(df['기준일자'])
    df = df.sort_values('기준일자')

    # 월별로 데이터 묶기
    df['year_month'] = df['기준일자'].dt.to_period('M')
    monthly_df = df.groupby(['year_month', '펀드명'])['전일대비\n등락'].mean().reset_index()

    # 수익률을 기준으로 상관계수 계산을 위한 데이터프레임 준비
    pivot_df = monthly_df.pivot(index='year_month', columns='펀드명', values='전일대비\n등락')
    pivot_df = pivot_df.apply(pd.to_numeric, errors='coerce')

    # 결측값 처리 (앞으로 채우기와 뒤로 채우기)
    pivot_df = pivot_df.ffill().bfill()

    # 추가적인 결측치 제거 및 변동성 없는 열 제거
    pivot_df = pivot_df.dropna(axis=1, how='any')
    pivot_df = pivot_df.loc[:, pivot_df.std() != 0]

    correlations = pivot_df.corrwith(pivot_df[target_fund_name])
    correlations_df = correlations.reset_index()
    correlations_df = correlations_df.fillna(0)
    correlations_df.columns = ['펀드명', '상관계수']

    # 상관계수가 음수인 것만 필터링
    negative_correlations_df = correlations_df[correlations_df['상관계수'] < 0].sort_values(by='상관계수')

    # 유사한 펀드 제거를 위해 match_fund_names_by_prefix 함수 활용
    selected_funds = []
    seen_fund_names = []

    for _, row in negative_correlations_df.iterrows():
        fund_name = row['펀드명']

        # match_fund_names_by_prefix를 사용하여 이미 선택된 펀드들과의 유사성을 체크
        if not match_fund_names_by_prefix(pd.DataFrame({'펀드명': [fund_name]}), pd.DataFrame({'펀드명': seen_fund_names})):
            selected_funds.append(row)
            seen_fund_names.append(fund_name)

        # 상위 3개만 선택
        if len(selected_funds) == 3:
            break

    # 최종 선택된 상관계수가 낮은 3개의 펀드 반환
    top_negative_correlations = pd.DataFrame(selected_funds)

    return top_negative_correlations

def classify_question(user_input):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "넌 질문을 정해주는 카테고리 별로 분류해서 정해진 답을 출력할거야. 섹터별 펀드 추천은 R, 경제 관련 질문(예: 금리, 환율, 주가, 투자 전략 등)은 E, 경제 관련 질문이 아니라면 N으로 답해줘. 펀드 추천은 확실하게 분류해야해. {펀드}와 {추천}이 들어가면 무조건 펀드 추천으로 분류해줘"},
            {"role": "user", "content": f"이 질문을 분류해줘: '{user_input}'"}
        ],
        max_tokens=10,
        temperature=0
    )
    classification = response.choices[0].message.content.strip().upper()
    return classification

def chat_with_gpt(user_input, current_financial_data):
    # GPT에게 질문 분류 요청
    classification = classify_question(user_input)
    if classification == "E":
        return economic_q(user_input, current_financial_data)
    elif classification == "R":
        sector = classify_sector(user_input)
        if sector == "0":
            return "조금 더 정확한 포트폴리오 구성을 위해 섹터를 포함해 질문해 주세요."
        else:
            target_fund = recommend_fund(user_profile, sector)
            if target_fund is None:
                return "죄송합니다. 해당 섹터에 대한 펀드를 찾을 수 없습니다."
            cor_funds = find_top_negative_correlations(dfr, target_fund)
            riskfolio(dfr, target_fund, cor_funds)
    else:
        return "저는 경제 관련 질문만 답변할 수 있습니다."

def economic_q(user_input, financial_data):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"넌 실시간 시장 정보를 가지고 경제 및 투자 관련 질문에 답하는 어시스턴트고 답변은 존댓말로 부탁할게. 현재 금융 정보야. {current_financial_data} "},
            {"role": "user", "content": user_input},
        ],
        max_tokens=150,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()

def recommend_fund(user_profile, sector):
    risk = user_risk(user_profile)
    # 펀드 추천 로직을 추가하세요
    return "펀드 추천 예시"  # 실제 펀드 추천 로직으로 수정해야 합니다.

def riskfolio(df, target_fund, cor_funds):
    # 추가적인 로직 구현이 필요함
    print(f"선택한 펀드: {target_fund}")
    print(f"상관관계가 낮은 펀드들: {cor_funds}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python script.py '<사용자 질문>'")
        sys.exit(1)

    user_input = sys.argv[1]
    response = chat_with_gpt(user_input, current_financial_data)
    print("GPT 응답:", response)
