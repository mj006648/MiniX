import streamlit as st

def run():
    st.markdown('<h2 style="color:white;">📊 HPDA BI Dashboard (Trino)</h2>', unsafe_allow_html=True)
    
    st.markdown("""<div class="dashboard-card" style="height:150px;">
        <p style="color:#38BDF8; font-size:1.5rem; font-weight:700;">Query Engine: Trino (Active)</p>
        <p style="color:#94A3B8;">Connected to Trident Metadata Accelerator</p>
    </div>""", unsafe_allow_html=True)

    query = st.text_area("SQL Query Editor", value="SELECT weather, count(*) FROM nessie.sensor.front_camera GROUP BY weather")
    if st.button("Execute Query"):
        st.write("Result Set (Sample):")
        st.table({"weather": ["Rainy", "Sunny", "Cloudy"], "count(*)": [15402, 22010, 7588]})
