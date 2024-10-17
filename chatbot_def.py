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

# OpenAI API 키 설정 (환경 변수에서 가져오기)
client = OpenAI(
    api_key = "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"
 )

# 1. MongoDB Atlas 연결
uriCloud="mongodb+srv://fua990401:Mxl8n9j31X1LILXZ@funddata.es8v3.mongodb.net/?retryWrites=true&w=majority&appName=FundData"
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
    if(user_profile["age"] == 30):
        risk = "R"
    else:
        risk = "S"
    return risk

def classify_sector(user_input):
    response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "넌 펀드 추천 질문에서 섹터를 찾아서 분류할 예정이야. 섹터는 {unique_sectors} 이거야. 섹터를 분류할 수 있으면 그 섹터만 출력하고, 입력된 질문 중에 섹터 내용이 없다면 0을 출력해줘. 예시 답변: 정보기술, 0"},
        {"role": "user", "content": f"이 질문을 펀드 섹터에 맞게 분류해줘.: '{user_input}'"}
    ],
    max_tokens=50,
    temperature=0
    )
    classification = response.choices[0].message.content.strip()
    print(classification)

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
        if(sector == 0):
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
    gpt_response = response.choices[0].message.content
    return gpt_response

def standardize_fund_name(fund_name):
    if isinstance(fund_name, str):
        # 모든 공백 제거 및 특수 문자 제거, 작은 따옴표 등 제거
        fund_name = re.sub(r'\s+', '', fund_name)  # 모든 공백 제거
        fund_name = re.sub(r'[\'\"]', '', fund_name)  # 작은따옴표, 큰따옴표 제거
        return fund_name.lower().strip()  # 소문자로 변환하고 앞뒤 공백 제거
    return ''


dfs['펀드명'] = dfs['펀드명'].apply(standardize_fund_name)
dfr['펀드명'] = dfr['펀드명'].apply(standardize_fund_name)

def match_fund_names_by_prefix(df1, df2, fund_column_1='펀드명', fund_column_2='펀드명', prefix_length=10):
    matched_indices = []  # df2에서 매칭된 인덱스를 저장할 리스트

    # df1의 펀드명을 하나씩 순회하면서 df2에서 앞글자가 동일한 펀드명을 찾음
    for idx, fund_name in df1[fund_column_1].items():
        fund_prefix = fund_name[:prefix_length]  # 정규화된 펀드명의 앞부분 추출

        for idx2, fund_name_2 in df2[fund_column_2].items():
            if fund_name_2.startswith(fund_prefix):  # 앞글자 비교
                matched_indices.append(idx2)  # 매칭된 df2의 인덱스를 리스트에 저장
                break

    return matched_indices

# 사용자 프로필과 섹터 정보를 이용하여 펀드 추천 함수
def recommend_fund(user_profile, sector):
    # 특정 섹터에 해당하는 펀드 필터링
    filtered_funds = dfs[dfs['주요 섹터'].apply(lambda x: sector in x)]
    filtered_fund_names = filtered_funds[['펀드명']].copy()

    # 최신 수익률 데이터프레임 가져오기 및 펀드명 정규화 적용
    latest_return_df = latest_df(dfr)  # 최신 데이터프레임 가져오기

    # 앞글자 매칭을 통해 필터링된 펀드와 최신 수익률 데이터프레임 매칭
    matched_indices = match_fund_names_by_prefix(filtered_fund_names, latest_return_df)

    # 필터링된 데이터가 비어 있지 않은 경우 수익률이 가장 높은 펀드 선택
    if matched_indices:
        matched_returns = latest_return_df.loc[matched_indices]
        matched_returns['기준일자'] = pd.to_datetime(matched_returns['기준일자'])
        matched_returns = matched_returns.sort_values('기준일자', ascending=False)
        recent_6_months = matched_returns.groupby('펀드명').head(6)  # 각 펀드의 최근 6개월 데이터 선택
        average_returns = recent_6_months.groupby('펀드명')['전일대비\n등락'].mean()  # 6개월 평균 계산

        # print("Matched '전일대비\n등락' 6개월 평균 (first 5):")
        # print(average_returns.head(5))  # 매칭된 펀드 상위 5개의 6개월 평균 등락 정보 출력

        if user_risk(user_profile) == "R":  # 리스크를 선호하는 경우
            top_fund_name = average_returns.sort_values(ascending=False).head(1).index[0]
#        elif user_risk(user_profile) == "S":  # 안정성을 선호하는 경우
#            top_fund_name = matched_returns.groupby('펀드명')['기준가격'].mean().sort_values(ascending=False).head(1).index[0]
        else:
            top_fund_name = None
    else:
            top_fund_name = None

    # 최종 추천 펀드 반환
    if top_fund_name is not None:
        top_fund = matched_returns[matched_returns['펀드명'] == top_fund_name].iloc[0]
        print(top_fund['펀드명'])
        return top_fund['펀드명']
    else:
        return None

def riskfolio(dfr, topfund, corfunds):
    # topfund와 threefunds에 있는 펀드명 추출
    funds = [topfund] + corfunds['펀드명'].tolist()

    # dfr에서 해당 펀드명들만 필터링
    filtered_funds = dfr[dfr['펀드명'].isin(funds)]

    # 기준일자를 datetime 형식으로 변환하고 내림차순 정렬
    filtered_funds.loc[:, '기준일자'] = pd.to_datetime(filtered_funds['기준일자'])
    filtered_funds = filtered_funds.sort_values('기준일자', ascending=False)

    # 펀드명별로 그룹화하고 각 펀드의 최근 6개월 데이터 선택
    recent_6_months = filtered_funds.groupby('펀드명').head(6)

    # 기준일자를 년월 형식으로 변환
    filtered_funds.loc[:, '기준년월'] = pd.to_datetime(filtered_funds['기준일자']).dt.to_period('M')

    # 피벗 테이블을 생성하여 기준일자를 인덱스로, 펀드명을 열로, 수익률을 값으로 변환
    fund_returns_6_months = recent_6_months.pivot_table(index='기준일자', columns='펀드명', values='전일대비\n등락').dropna()

    # Riskfolio-Lib을 사용하여 최적화
    port = rp.Portfolio(returns=fund_returns_6_months)

    # 자산 수익률 및 공분산 계산 (평균 수익률 및 공분산 계산)
    port.assets_stats(method_mu='hist', method_cov='ewma1')

    # 최소 및 최대 가중치 설정
    port.lowerret = [0.05] * len(funds)  # 최소 가중치 5%
    port.upperret = [0.4] * len(funds)   # 최대 가중치 40%

    # 최적화 수행 (샤프 비율 최대화)
    w = port.optimization(model='Classic', rm='MV', obj='Sharpe', hist=True)

    # 포트폴리오 가중치 파이차트 시각화

    # 이후 plt.pie()로 다시 차트 생성 (레전드 없이)
    plt.figure(figsize=(10, 8))  # 차트 크기 설정
    plt.pie(w['weights'], labels=w.index, autopct='%1.1f%%', startangle=90, labeldistance=1.1)

    # 폰트 설정
    plt.rc('font', family='NanumGothic')


    # 제목 추가
    plt.title('Optimized Portfolio Weights')

    # 차트 보여주기
    plt.show()

    # 사용자 질문
user_input = "정보기술 펀드 추천해줘"

# GPT와 대화 후 질문 분류 및 답변
response = chat_with_gpt(user_input, current_financial_data)
print(response)