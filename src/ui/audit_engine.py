import streamlit as st
import time
from datetime import datetime
import pandas as pd
import os
import sys
import threading
import json

# Add parent directory to path so we can import the agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.identify_change_migration_agent import IdentifyChangeMigrationAgent
from agents.sod_violation_detection_agent import SODViolationDetectionAgent

# Global variables for thread communication
_is_running = False
_next_run_time = None
_log_messages = []
_population_data = None
_violations_data = None
_last_run_time = None

def add_log(message):
    """Add a log message with timestamp to the log list"""
    global _log_messages
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"{timestamp} - {message}"
    
    # Add to global log list
    _log_messages.append(log_message)
    if len(_log_messages) > 100:
        _log_messages.pop(0)
    
    # Also print to console
    print(log_message)
    
    # Update session state if possible
    if hasattr(st, 'session_state') and 'log_messages' in st.session_state:
        st.session_state.log_messages = _log_messages.copy()

def sync_to_session_state():
    """Sync global variables to session state"""
    if hasattr(st, 'session_state'):
        st.session_state.is_running = _is_running
        st.session_state.next_run_time = _next_run_time
        st.session_state.last_run_time = _last_run_time
        st.session_state.log_messages = _log_messages.copy()
        
        if _population_data is not None:
            st.session_state.population_data = _population_data
        
        if _violations_data is not None:
            st.session_state.violations_data = _violations_data

def run_audit_once(data_dir, output_dir):
    """Run a single audit cycle with both agents"""
    global _population_data, _violations_data, _last_run_time
    
    add_log("Starting audit process")
    
    try:
        # Run identify agent
        add_log("Starting IdentifyChangeMigrationAgent")
        identify_agent = IdentifyChangeMigrationAgent(data_dir=data_dir, output_data_dir=output_dir)
        identify_result = identify_agent.run()
        
        if not identify_result:
            add_log("IdentifyChangeMigrationAgent failed")
            return False
        
        # Get population file
        population_file = identify_agent.save_verified_population_file()
        add_log(f"Population file created: {population_file}")
        
        if identify_agent.migration_data is not None:
            add_log(f"Population contains {len(identify_agent.migration_data)} records")
            # Store population data
            _population_data = identify_agent.migration_data
        else:
            add_log("No records found in population")
            return False
        
        # Run SOD agent
        add_log("Starting SODViolationDetectionAgent")
        sod_agent = SODViolationDetectionAgent(
            data_dir=data_dir,
            output_data_dir=output_dir,
            verified_population_file=population_file
        )
        sod_result = sod_agent.run()
        
        if not sod_result:
            add_log("SODViolationDetectionAgent failed")
            return False
        
        # Store results
        _last_run_time = datetime.now()
        
        # Get violations data
        if hasattr(sod_agent, 'violations') and sod_agent.violations is not None:
            _violations_data = sod_agent.violations
            add_log(f"Found {len(sod_agent.violations)} violations")
        else:
            _violations_data = pd.DataFrame()
            add_log("No violations found")
        
        # Sync to session state
        sync_to_session_state()
        
        add_log("Audit completed successfully")
        return True
    
    except Exception as e:
        add_log(f"Error in audit process: {str(e)}")
        return False

def scheduler_function(interval, duration, data_dir, output_dir):
    """Function to run in a separate thread for periodic execution"""
    global _is_running, _next_run_time
    
    # Set the global running flag
    _is_running = True
    sync_to_session_state()
    
    start_time = time.time()
    end_time = start_time + (duration * 60) if duration > 0 else float('inf')
    
    try:
        while _is_running and time.time() < end_time:
            # Run the audit
            run_audit_once(data_dir, output_dir)
            
            # Calculate next run time
            next_run = time.time() + (interval * 60)
            _next_run_time = datetime.fromtimestamp(next_run)
            sync_to_session_state()
            
            add_log(f"Next run scheduled for {_next_run_time.strftime('%H:%M:%S')}")
            
            # Sleep until next run
            sleep_interval = 10  # Check every 10 seconds
            sleep_count = int((interval * 60) / sleep_interval)
            
            for _ in range(sleep_count):
                if not _is_running:
                    break
                time.sleep(sleep_interval)
    
    except Exception as e:
        add_log(f"Error in scheduler: {str(e)}")
    
    finally:
        # Clean up
        _is_running = False
        sync_to_session_state()
        add_log("Scheduler stopped")

def start_scheduler(interval, duration, data_dir, output_dir):
    """Start the scheduler in a separate thread"""
    global _is_running
    
    if _is_running:
        add_log("Scheduler is already running")
        return False
    
    # Set the session state
    st.session_state.is_running = True
    _is_running = True
    
    # Create and start scheduler thread
    scheduler_thread = threading.Thread(
        target=scheduler_function,
        args=(interval, duration, data_dir, output_dir)
    )
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    return True

def stop_scheduler():
    """Stop the running scheduler"""
    global _is_running
    
    if not _is_running:
        add_log("Scheduler is not running")
        return False
    
    # Set the flags to stop the scheduler
    _is_running = False
    st.session_state.is_running = False
    add_log("Stopping scheduler...")
    
    return True

def get_scheduler_status():
    """Get the current status of the scheduler"""
    global _is_running, _next_run_time
    
    return {
        "is_running": _is_running,
        "next_run_time": _next_run_time
    }