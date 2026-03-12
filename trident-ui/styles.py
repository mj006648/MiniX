import streamlit as st

def apply_login_styles():
    st.markdown("""
        <style>
        /* 1. 레이아웃 초기화 */
        [data-testid="stHeader"], [data-testid="stToolbar"] {display: none;}
        
        /* 2. 배경 그라데이션 */
        .stApp {
            background-color: #060b13 !important;
            background-image: radial-gradient(circle at center, #0a1628 0%, #060b13 100%) !important;
            overflow: hidden;
        }

        /* 3. 중앙 상단 배치 (15vh 위로) */
        .main .block-container {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            height: 100vh !important;
            padding-bottom: 15vh !important; 
            max-width: 100% !important;
        }

        /* 4. 브랜드 섹션 */
        .brand-box {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 40px;
        }
        .brand-logo { font-size: 100px; color: #fbbf24; margin-right: 25px; line-height: 1; }
        .brand-text { 
            color: white; 
            font-size: 90px; 
            font-weight: 800; 
            letter-spacing: 6px; 
            margin: 0; 
            line-height: 1;
        }

        /* 5. 거대한 키클락 버튼 */
        [data-testid="stButton"] {
            display: flex;
            justify-content: center;
            width: 100%;
            margin-bottom: 30px;
        }
        [data-testid="stButton"] > button {
            background-color: #3182ce !important;
            color: white !important;
            font-size: 1.8rem !important; /* 폰트 확대 */
            font-weight: 700 !important;
            padding: 25px 0px !important;
            border-radius: 12px !important;
            border: none !important;
            width: 620px !important; /* 너비 확대 */
            height: 85px !important;  /* 높이 확대 */
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
        }
        [data-testid="stButton"] > button:hover {
            background-color: #2b6cb0 !important;
            transform: scale(1.02);
        }

        /* 6. 설명 문구 */
        .subtitle-text {
            color: #ffffff;
            font-size: 1.5rem;
            font-weight: 400;
            opacity: 0.9;
            text-align: center;
            letter-spacing: 0.5px;
        }

        /* 7. 하단 카피라이트 고정 */
        .footer-reserved {
            position: fixed;
            bottom: 40px;
            left: 0;
            width: 100%;
            text-align: center;
            color: #4a5568;
            font-size: 1.1rem;
            font-weight: 500;
        }
        </style>
    """, unsafe_allow_html=True)

def apply_dashboard_styles():
    st.markdown("""
        <style>
        [data-testid="stHeader"] {visibility: hidden;}
        .stApp { background-color: #0b111a; }
        [data-testid="stSidebar"] { background-color: #0e1621; border-right: 1px solid #1e293b; }
        .dashboard-card {
            background-color: #161e2e;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }
        .metric-val { font-size: 2rem; font-weight: 800; color: #38bdf8; }
        .card-label { color: #94a3b8; font-size: 0.9rem; margin-bottom: 10px; }
        .log-card {
            background-color: #020617;
            border-radius: 8px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            color: #10b981;
            font-size: 0.9rem;
        }
        </style>
    """, unsafe_allow_html=True)
