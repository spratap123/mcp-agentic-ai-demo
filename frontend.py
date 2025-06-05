# ui.py
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("AI-powered MCP Agent Dashboard")

incident_text = st.text_area("Enter Incident Description:")

if st.button("Submit Incident"):
    if incident_text.strip() == "":
        st.warning("Please enter an incident description.")
    else:
        try:
            resp = requests.post(f"{API_URL}/incident/", json={"description": incident_text})
            if resp.status_code == 200:
                data = resp.json()
                st.success("Incident submitted!")
                st.markdown("### Agent has started processing the incident in the background.")
            else:
                st.error(f"Failed to submit incident. Status code: {resp.status_code}")
        except Exception as e:
            st.error(f"Error submitting incident: {e}")

st.markdown("---")
st.header("Incident History")

try:
    resp = requests.get(f"{API_URL}/history/")
    if resp.status_code == 200:
        data = resp.json()
        incidents = data.get("incidents", [])
        solutions = data.get("solutions", [])
        fix_statuses = data.get("fix_status", [])

        for i, (inc, sol, status) in enumerate(zip(incidents, solutions, fix_statuses)):
            with st.expander(f"Incident {i+1}: {inc}"):
                st.write(sol if sol else "No solution yet.")
                st.markdown(f"**Status:** {status}")
                if status != "executed":
                    if st.button(f"Execute Fix for Incident {i+1}", key=f"exec_{i}"):
                        try:
                            exec_resp = requests.post(f"{API_URL}/execute_fix/", params={"index_param": i})
                            if exec_resp.status_code == 200:
                                st.success("Fix executed (simulated).")
                            else:
                                st.error(f"Failed to execute fix. Status code: {exec_resp.status_code}")
                        except Exception as e:
                            st.error(f"Error executing fix: {e}")
    else:
        st.error(f"Failed to load history. Status code: {resp.status_code}")
except Exception as e:
    st.error(f"Error loading history: {e}")
