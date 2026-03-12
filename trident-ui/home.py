import streamlit as st
from styles import apply_login_styles, apply_dashboard_styles
from modules import status, data_sense, iceberg, bi_dashboard, k8s_jobs

# 페이지 설정
st.set_page_config(page_title="TRIDENT | GIST NetAi", page_icon="🔱", layout="wide")

# 세션 상태 초기화
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    apply_login_styles()
    
    # 로고
    st.markdown("""
        <div class="brand-box">
            <span class="brand-logo">🔱</span>
            <span class="brand-text">TRIDENT</span>
        </div>
    """, unsafe_allow_html=True)

    # 버튼
    if st.button("Login with Keycloak"):
        st.session_state.auth = True
        st.session_state.user_id = "GIST_Researcher"
        st.rerun()

    # 문구들
    st.markdown('<div class="subtitle-text">Cloud-Native Data Lakehouse for Scale-Across Infrastructure</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer-reserved">© 2026 GIST NetAi Lab. All rights reserved.</div>', unsafe_allow_html=True)

else:
    apply_dashboard_styles()
    
    with st.sidebar:
        st.markdown("<h2 style='color:white; margin-bottom:30px;'>🔱 TRIDENT</h2>", unsafe_allow_html=True)
        page = st.radio("MENU", ["Infrastructure", "Data Sense", "Table Catalog", "SQL Analytics", "Workloads"], label_visibility="collapsed")
        st.divider()
        st.markdown(f"👤 **{st.session_state.user_id}**")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # 라우팅 로직
    if page == "Infrastructure": status.run()
    elif page == "Data Sense": data_sense.run()
    elif page == "Table Catalog": iceberg.run()
    elif page == "SQL Analytics": bi_dashboard.run()
    elif page == "Workloads": k8s_jobs.run()
