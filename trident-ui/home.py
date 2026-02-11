import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(
    page_title="TRIDENT | Data Lakehouse",
    page_icon="🔱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [상태 관리] ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'page' not in st.session_state:
    st.session_state.page = "Trident Status"

# --- [CSS 고도화: 정밀 간격 및 Active 메뉴 스타일] ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    [data-testid="stSidebar"] {display: none !important;}
    .stApp { background-color: #0F172A; }

    /* 화면 전체 중앙 정렬 (로그인용) */
    .main .block-container {
        max-width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 100vh !important;
        padding: 0 !important;
    }

    /* [로그인 스타일] */
    div[data-testid="stForm"] {
        background-color: white !important; padding: 3rem 4rem !important; border-radius: 8px !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important; width: 500px !important; margin: 0 auto !important;
    }

    /* [네비게이션 바] 버튼 텍스트화 및 정밀 간격 */
    .nav-sep { color: #334155; margin: 0 1px; font-weight: 300; font-size: 0.9rem; }
    
    /* 일반 메뉴 버튼 스타일 */
    div.stButton > button {
        background: none !important; border: none !important; 
        color: #FFFFFF !important; /* 기본 흰색 */
        padding: 0 2px !important; font-size: 0.92rem !important; font-weight: 500 !important;
        transition: 0.2s; width: auto !important;
    }
    
    /* [핵심] 선택된(Active) 메뉴 버튼 스타일 - 파란색 강조 */
    div.stButton > button:focus, div.stButton > button:active {
        color: #38BDF8 !important;
    }

    /* 타이틀 섹션 (아이콘 제거) */
    .dashboard-title { color: white; font-size: 2.5rem; font-weight: 700; margin-bottom: -10px; }

    /* 대시보드 카드 및 로그박스 */
    .dashboard-card {
        background-color: #1E293B; border: 1px solid #334155; border-radius: 12px;
        padding: 25px; height: 420px; display: flex; flex-direction: column;
        justify-content: center; align-items: center; position: relative;
    }
    .card-label {
        position: absolute; top: 20px; left: 25px; color: white; font-size: 1rem;
        font-weight: 700; border-bottom: 1px solid #334155; padding-bottom: 8px; width: calc(100% - 50px);
    }
    .log-card {
        background-color: #1E293B; border: 1px solid #334155; border-radius: 12px;
        padding: 25px; width: 100%; margin-top: 30px; text-align: left;
    }
    .log-scroll-area {
        height: 280px; overflow-y: scroll; padding-right: 15px; color: #475569; 
        font-family: 'Inter', sans-serif; line-height: 2;
    }

    .footer-center {
        position: fixed; bottom: 15px; left: 0; width: 100%;
        text-align: center; color: #475569; font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [함수: 메뉴 버튼 생성 (Active 강조 포함)] ---
def nav_button(label, key):
    # 현재 페이지와 버튼 라벨이 일치하면 파란색 스타일 적용
    is_active = st.session_state.page == label
    color = "#38BDF8" if is_active else "#FFFFFF"
    
    # 인라인 스타일 주입하여 강제 색상 변경
    style = f"<style>div:has(> button[key='{key}']) button {{ color: {color} !important; font-weight: {'700' if is_active else '500'} !important; }}</style>"
    st.markdown(style, unsafe_allow_html=True)
    
    if st.button(label, key=key):
        st.session_state.page = label
        st.rerun()

# --- [로직 시작] ---

if not st.session_state.auth:
    # --- [1. 로그인 화면] ---
    st.markdown("""
        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 80px; vertical-align: middle;">🔱</span>
            <span style="color: white; font-size: 60px; font-weight: 800; letter-spacing: 2px; vertical-align: middle;"> TRIDENT</span>
            <div style="color: #94A3B8; font-size: 1.25rem; margin-top: 15px;">Cloud-Native Data Lakehouse for Scale-Across Infrastructure</div>
        </div>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 1.5, 1])
    with center_col:
        with st.form("login_form"):
            st.markdown('<div style="color:#1F2937; font-size:2rem; text-align:center; margin-bottom:2.5rem;">Sign in to your account</div>', unsafe_allow_html=True)
            user = st.text_input("Username or email", placeholder="Enter your username")
            pw = st.text_input("Password", type="password", placeholder="Enter your password")
            if st.form_submit_button("Sign In"):
                if user and pw:
                    st.session_state.auth = True
                    st.session_state.user_id = user
                    st.rerun()

    st.markdown('<div class="footer-center">© 2026 GIST NetAi Lab. All rights reserved.</div>', unsafe_allow_html=True)

else:
    # --- [2. 메인 대시보드 화면] ---
    st.markdown("""<style>.main .block-container { justify-content: flex-start !important; padding: 1rem 4rem !important; }</style>""", unsafe_allow_html=True)
    
    # 상단 메뉴 (간격을 극도로 좁힌 10개 이상의 컬럼 레이아웃)
    nav_l, nav_r = st.columns([7.5, 2.5])
    
    with nav_l:
        # 비율을 0.0x 단위로 쪼개어 글자들 사이의 간격을 거의 없앰
        n = st.columns([0.1, 0.01, 0.09, 0.01, 0.1, 0.01, 0.1, 0.01, 0.08, 1])
        with n[0]: nav_button("Trident Status", "btn_status")
        with n[1]: st.markdown('<span class="nav-sep">|</span>', unsafe_allow_html=True)
        with n[2]: nav_button("Data Sense", "btn_sense")
        with n[3]: st.markdown('<span class="nav-sep">|</span>', unsafe_allow_html=True)
        with n[4]: nav_button("Iceberg Table", "btn_table")
        with n[5]: st.markdown('<span class="nav-sep">|</span>', unsafe_allow_html=True)
        with n[6]: nav_button("BI Dashboard", "btn_bi")
        with n[7]: st.markdown('<span class="nav-sep">|</span>', unsafe_allow_html=True)
        with n[8]: nav_button("K8S Jobs", "btn_jobs")

    with nav_r:
        # 오른쪽 메뉴: User 옆에만 아이콘 배치
        nr = st.columns([4, 0.2, 1.5])
        with nr[0]:
            st.markdown(f'<div style="text-align:right; margin-top:4px; color:white; font-size:0.9rem;">👤 <span style="color:#38BDF8; font-weight:600;">User: {st.session_state.user_id}</span></div>', unsafe_allow_html=True)
        with nr[1]:
            st.markdown('<div style="margin-top:4px; text-align:center;"><span class="nav-sep">|</span></div>', unsafe_allow_html=True)
        with nr[2]:
            if st.button("Logout", key="btn_logout"):
                st.session_state.auth = False
                st.rerun()

    st.markdown('<div style="width:100%; max-width:1450px; margin-top:20px;">', unsafe_allow_html=True)
    
    if st.session_state.page == "Trident Status":
        # 타이틀 (아이콘 제거)
        st.markdown('<div class="dashboard-title">Trident Data Lakehouse Status</div>', unsafe_allow_html=True)
        st.markdown("<hr style='border-color: #334155; margin-top: 15px; margin-bottom: 2.5rem;'>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class="dashboard-card"><div class="card-label">Storage Capacity</div><div style="color:#334155; font-size:4.5rem; font-weight:900;">N/A</div><div style="color:#475569; margin-top:15px;">Infrastructure Disconnected</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="dashboard-card">
                    <div class="card-label">Metadata Registry</div>
                    <div style="width:100%; padding:0 10px; margin-top:40px;">
                        <div style="color:#94A3B8; font-size:0.8rem; font-weight:600; margin-bottom:5px;">MILVUS VECTORS</div>
                        <div style="color:#334155; font-size:2.8rem; font-weight:900;">N/A</div>
                        <div style="margin-top:30px; color:#94A3B8; font-size:0.8rem; font-weight:600; margin-bottom:5px;">REDIS KEYS</div>
                        <div style="color:#334155; font-size:2.8rem; font-weight:900;">N/A</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="dashboard-card"><div class="card-label">Active Workloads</div><div style="color:#334155; font-size:4.5rem; font-weight:900;">N/A</div><div style="color:#475569; margin-top:15px;">No Nodes Detected</div></div>""", unsafe_allow_html=True)

        # 로그 섹션
        st.markdown(f"""
            <div class="log-card">
                <div style="color:white; font-size:1.2rem; font-weight:700; border-bottom:1px solid #334155; padding-bottom:12px; margin-bottom:20px;">Recent Activity Log</div>
                <div class="log-scroll-area">
                    • [14:45] Security: Keycloak authentication token refreshed for session 0xAF31.<br>
                    • [14:22] System check: Primary storage interface unreachable (Timeout).<br>
                    • [13:05] Metadata Sense: Awaiting handshake with Milvus cluster...<br>
                    • [12:40] Authentication: User {st.session_state.user_id} established secure session.<br>
                    • [11:15] Warning: Redundancy nodes are in standby mode.<br>
                    • [10:00] Boot: TRIDENT Data Plane initiated by GIST NetAi.<br>
                    • [09:30] Network: RDMA interface initialized (100G).<br>
                    • [08:00] Analytics: Nightly batch job completed.<br>
                    • [System] No active data streams detected.
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown(f"<h1 style='color: white;'>{st.session_state.page}</h1>", unsafe_allow_html=True)
        st.info(f"Navigating to {st.session_state.page} subsystem...")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer-center">© 2026 GIST NetAi Lab. All rights reserved.</div>', unsafe_allow_html=True)

