import streamlit as st
import plotly.graph_objects as go

def run():
    # 상단 3개 카드 레이아웃
    col1, col2, col3 = st.columns([4, 3, 3])

    with col1:
        st.markdown("""
            <div class="card">
                <div class="card-header">📊 Storage Total</div>
        """, unsafe_allow_html=True)
        
        # 원형 게이지 차트 생성
        fig = go.Figure(go.Pie(
            values=[70, 30],
            labels=["Used", "Free"],
            hole=.7,
            marker_colors=['#38BDF8', '#1E293B'],
            textinfo='none',
            hoverinfo='label+percent'
        ))
        fig.update_layout(
            showlegend=False, margin=dict(t=0, b=0, l=0, r=0),
            height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(text='70%<br><span style="font-size:12px; color:#64748B;">Used</span>', 
                         x=0.5, y=0.5, font_size=24, font_color="white", showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("""
                <div style="text-align:center; color:#94A3B8; font-size:0.8rem;">
                    🔵 Ceph: 3PB &nbsp; 🔵 Weka: 0.5PB
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="card" style="height:318px;">
                <div class="card-header">📦 Data Map Stats</div>
                <div style="margin-top:20px;">
                    <div class="metric-label">Milvus Vectors</div>
                    <div class="metric-value">15.4M</div>
                </div>
                <div style="margin-top:30px; border-top:1px solid #1E293B; padding-top:20px;">
                    <div class="metric-label">Redis Keys</div>
                    <div class="metric-value">54.0M</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="card" style="height:318px; text-align:center;">
                <div class="card-header">🚀 Active Mounts</div>
                <div style="margin-top:40px;">
                    <div class="metric-value" style="font-size:4rem; color:#FACC15;">12 ⚡</div>
                    <div class="metric-label">HPC Nodes Active</div>
                </div>
                <div style="margin-top:40px;">
                    <div class="status-badge">✔ All Systems GO</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 하단 로그 섹션
    st.markdown("""
        <div class="card">
            <div class="card-header">🗒 Recent Activities</div>
            <div class="activity-log">
                <span class="log-time">[13:45]</span> User_K <span class="log-highlight">mounted</span> 'autonomous_driving_v2' to Node #04<br>
                <span class="log-time">[12:30]</span> New Iceberg Table <span class="log-highlight">'weather_sensor_kr'</span> ingested.<br>
                <span class="log-time">[11:10]</span> Keycloak Policy updated for 'AI_Research_Group'.<br>
                <span class="log-time">[10:05]</span> <span style="color:#F87171;">WARN:</span> Latency spike detected in Cluster B.<br>
                <span class="log-time">[09:00]</span> Trident Data Plane v1.2 Heartbeat OK.
            </div>
        </div>
    """, unsafe_allow_html=True)
