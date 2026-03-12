import streamlit as st

def run():
    st.markdown('<h2 style="color:white;">☸️ K8S Workload & Jobs</h2>', unsafe_allow_html=True)
    
    st.subheader("Active Data-Driven Jobs")
    st.markdown("""
        <div style="background-color:#1E293B; padding:15px; border-radius:10px; border-left:5px solid #10B981; margin-bottom:10px;">
            <b>Job ID:</b> model-train-0x12 <br>
            <b>Type:</b> AI Training (PyTorch) <br>
            <b>Target:</b> nessie.sensor.front_camera <br>
            <b>Status:</b> <span style="color:#10B981;">Running (GPU utilized 98%)</span>
        </div>
        <div style="background-color:#1E293B; padding:15px; border-radius:10px; border-left:5px solid #38BDF8; margin-bottom:10px;">
            <b>Job ID:</b> hpc-sim-sky-01 <br>
            <b>Type:</b> HPC Simulation <br>
            <b>Target:</b> weather.history <br>
            <b>Status:</b> <span style="color:#38BDF8;">Pending (Mounting FUSE...)</span>
        </div>
    """, unsafe_allow_html=True)
