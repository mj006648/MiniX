import streamlit as st
import pandas as pd

def run():
    st.markdown('<h2 style="color:white;">🧊 Apache Iceberg Table Management</h2>', unsafe_allow_html=True)
    
    # 가상의 테이블 데이터
    data = {
        "Table Name": ["sensor.front_camera", "sensor.lidar_raw", "traffic.log", "weather.history"],
        "Type": ["Binary (Video)", "Binary (npy)", "Structured (Parquet)", "Structured (Parquet)"],
        "Status": ["Ready", "Compacting", "Ready", "Ready"],
        "Records/Files": ["45,000 files", "120,000 files", "4.2B rows", "150M rows"]
    }
    df = pd.DataFrame(data)
    
    st.subheader("Registered Iceberg Tables")
    st.dataframe(df, use_container_width=True)

    st.markdown("### Iceberg Maintenance (Storage Optimization)")
    col1, col2, col3 = st.columns(3)
    if col1.button("Run Data Compaction"): st.info("Optimizing small files...")
    if col2.button("Cleanup Orphan Files"): st.info("Deleting unreferenced objects...")
    if col3.button("Expire Snapshots"): st.info("Removing old metadata history...")
