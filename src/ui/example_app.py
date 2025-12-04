import streamlit as st
import os
import sys
import time
from datetime import datetime
import threading

# Add parent directory to path so we can import the agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import tab modules
from dashboard import show_dashboard
from population import show_population
from violations import show_violations
from audit_engine import run_audit_once, start_scheduler, stop_scheduler, add_log, get_scheduler_status

# Define paths to your data directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")

# Initialize session state variables if they don't exist
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'last_run_time' not in st.session_state:
    st.session_state.last_run_time = None
if 'next_run_time' not in st.session_state:
    st.session_state.next_run_time = None
if 'population_data' not in st.session_state:
    st.session_state.population_data = None
if 'violations_data' not in st.session_state:
    st.session_state.violations_data = None
if 'mode' not in st.session_state:
    st.session_state.mode = "Run Once"
if 'interval' not in st.session_state:
    st.session_state.interval = 5
if 'duration' not in st.session_state:
    st.session_state.duration = 60
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = datetime.now()

def start_audit():
    """Start the audit process based on selected mode"""
    if st.session_state.is_running:
        st.warning("Audit is already running")
        return
    
    mode = st.session_state.mode
    interval = st.session_state.interval
    duration = st.session_state.duration
    
    # Validate inputs
    if interval < 1:
        st.error("Interval must be at least 1 minute")
        return
    
    if mode == "Run Once":
        # Run once
        add_log("Running audit once")
        st.session_state.is_running = True
        run_audit_once(DATA_DIR, OUTPUT_DIR)
        st.session_state.is_running = False
    else:
        # Run periodically
        add_log(f"Starting periodic audit with interval={interval} minutes, duration={duration} minutes")
        start_scheduler(interval, duration, DATA_DIR, OUTPUT_DIR)

def stop_audit():
    """Stop the running audit process"""
    if not st.session_state.is_running:
        st.warning("No audit is currently running")
        return
    
    stop_scheduler()

def update_status():
    """Update the UI status from the scheduler"""
    if st.session_state.is_running:
        status = get_scheduler_status()
        
        # Update next run time if changed
        if status["next_run_time"] and status["next_run_time"] != st.session_state.next_run_time:
            st.session_state.next_run_time = status["next_run_time"]
        
        # If scheduler stopped but UI thinks it's running
        if not status["is_running"] and st.session_state.is_running:
            st.session_state.is_running = False
        
        # Force a rerun every 5 seconds to update the UI
        now = datetime.now()
        if (now - st.session_state.last_update_time).total_seconds() > 5:
            st.session_state.last_update_time = now
            st.rerun()

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Change Management Audit Tool",
        page_icon="📊",
        layout="wide"
    )
    
    # Update status from scheduler
    update_status()
    
    st.title("Change Management Audit Tool")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Verified Population", "SOD Violations"])
    
    # Tab 1: Dashboard
    with tab1:
        show_dashboard(start_audit, stop_audit)
    
    # Tab 2: Verified Population
    with tab2:
        show_population()
    
    # Tab 3: SOD Violations
    with tab3:
        show_violations()

if __name__ == "__main__":
    main()