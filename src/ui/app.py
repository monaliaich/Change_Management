import streamlit as st
import pandas as pd
import os
import sys
import time
import threading
import schedule
import random
from datetime import datetime, timedelta
import plotly.express as px
import random

# Add parent directory to path so we can import the agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.identify_change_migration_agent import IdentifyChangeMigrationAgent
from agents.sod_violation_detection_agent import SODViolationDetectionAgent

# Define paths to your data directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")

def schedule_audit(interval_minutes):
    """Schedule the audit to run periodically"""
    if st.session_state.is_running:
        add_log("Cannot schedule while a process is already running")
        return False
    
    # Clear any existing schedule
    schedule.clear()
    
    # Schedule the audit
    schedule.every(interval_minutes).minutes.do(run_scheduled_audit)
    
    # Start the scheduler in a separate thread
    st.session_state.scheduler_thread = threading.Thread(target=run_scheduler)
    st.session_state.scheduler_thread.daemon = True
    st.session_state.scheduler_thread.start()
    
    st.session_state.is_scheduled = True
    st.session_state.schedule_interval = interval_minutes
    
    add_log(f"Audit scheduled to run every {interval_minutes} minutes")
    return True

def run_scheduled_audit():
    """Run the audit as a scheduled task"""
    add_log("Running scheduled audit")
    run_full_audit()
    return schedule.CancelJob  # Don't cancel the job



# Initialize session state
def init_session_state():
    """Initialize session state variables if they don't exist"""
    # Existing session state variables
    if 'population_data' not in st.session_state:
        st.session_state.population_data = None
    if 'violations_data' not in st.session_state:
        st.session_state.violations_data = None
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
    if 'last_run_time' not in st.session_state:
        st.session_state.last_run_time = None
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False
    if 'population_file' not in st.session_state:
        st.session_state.population_file = None
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Population"
    if 'scheduler_enabled' not in st.session_state:
        st.session_state.scheduler_enabled = False
    if 'start_delay' not in st.session_state:
        st.session_state.start_delay = 5  # Default to 5 minutes delay
    if 'next_scheduled_run' not in st.session_state:
        st.session_state.next_scheduled_run = None
    if 'last_check_time' not in st.session_state:
        st.session_state.last_check_time = datetime.now()

def add_log(message):
    """Add a log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"{timestamp} - {message}"
    st.session_state.log_messages.append(log_message)
    if len(st.session_state.log_messages) > 100:
        st.session_state.log_messages.pop(0)
    print(log_message)

def check_scheduled_run():
    """Check if it's time to run a scheduled audit"""
    if not st.session_state.scheduler_enabled or st.session_state.is_running:
        return False
    
    now = datetime.now()
    
    # If next run time is set and we've reached it
    if st.session_state.next_scheduled_run and now >= st.session_state.next_scheduled_run:
        add_log(f"Running scheduled audit at {now.strftime('%H:%M:%S')}")
        
        # Run the audit
        run_full_audit()
        
        # Disable the scheduler after running once
        st.session_state.scheduler_enabled = False
        st.session_state.next_scheduled_run = None
        add_log("Scheduled run completed. Scheduler disabled.")
        
        return True
    
    return False

def toggle_auto_refresh():
    """Toggle auto-refresh on/off"""
    if st.session_state.auto_refresh:
        # Turn off auto-refresh
        st.session_state.auto_refresh = False
        st.session_state.next_run_time = None
        add_log("Auto-refresh disabled")
    else:
        # Turn on auto-refresh
        st.session_state.auto_refresh = True
        st.session_state.next_run_time = datetime.now() + timedelta(minutes=st.session_state.refresh_interval)
        add_log(f"Auto-refresh enabled. Next run at {st.session_state.next_run_time.strftime('%H:%M:%S')}")

def run_population_extraction():
    """Run the population extraction agent"""
    st.session_state.is_running = True
    
    try:
        add_log("Starting IdentifyChangeMigrationAgent")
        
        # Create and run the agent
        identify_agent = IdentifyChangeMigrationAgent(data_dir=DATA_DIR, output_data_dir=OUTPUT_DIR)
        identify_result = identify_agent.run()
        
        if not identify_result:
            add_log("IdentifyChangeMigrationAgent failed")
            st.session_state.is_running = False
            return False
        
        # Get population file
        population_file = identify_agent.save_verified_population_file()
        st.session_state.population_file = population_file
        add_log(f"Population file created: {population_file}")
        
        if identify_agent.migration_data is not None:
            add_log(f"Population contains {len(identify_agent.migration_data)} records")
            # Store population data
            st.session_state.population_data = identify_agent.migration_data
        else:
            add_log("No records found in population")
            st.session_state.is_running = False
            return False
        
        # Update last run time
        st.session_state.last_run_time = datetime.now()
        add_log("Population extraction completed successfully")
        
    except Exception as e:
        add_log(f"Error in population extraction: {str(e)}")
        st.session_state.is_running = False
        return False
    
    st.session_state.is_running = False
    return True

def generate_sample_violations():
    """Generate sample violations for testing"""
    if st.session_state.population_data is None:
        return pd.DataFrame()
    
    # Get a subset of the population data to create violations
    population = st.session_state.population_data
    
    # Select a few random records to create violations for
    if len(population) > 5:
        violation_indices = random.sample(range(len(population)), min(3, len(population)))
    else:
        violation_indices = range(len(population))
    
    violations = []
    
    violation_types = [
        "Same user requested & approved",
        "High risk change with standard approval",
        "Emergency change without proper documentation",
        "Unauthorized developer access"
    ]
    
    for idx in violation_indices:
        record = population.iloc[idx]
        
        # Create a violation record
        violation = {
            'Change_ID': record['Change_ID'] if 'Change_ID' in record else f"CHG{1000+idx}",
            'Title': record['Title'] if 'Title' in record else "Unknown Change",
            'Asset_Name': record['Asset_Name'] if 'Asset_Name' in record else "Unknown Asset",
            'Violation_Type': random.choice(violation_types),
            'Risk_Rating': random.choice(['High', 'Medium', 'Low']),
            'Details': f"Violation details for {record['Change_ID'] if 'Change_ID' in record else f'CHG{1000+idx}'}",
            'Implementation_Timestamp': record['Implementation_Timestamp'] if 'Implementation_Timestamp' in record else "Unknown Date"
        }
        
        violations.append(violation)
    
    return pd.DataFrame(violations)

def run_sod_detection():
    """Run the SOD violation detection agent"""
    if st.session_state.population_file is None:
        add_log("No population file available. Run population extraction first.")
        return False
    
    st.session_state.is_running = True
    
    try:
        add_log("Starting SODViolationDetectionAgent")
        
        # Create and run the agent
        sod_agent = SODViolationDetectionAgent(
            data_dir=DATA_DIR,
            output_data_dir=OUTPUT_DIR,
            verified_population_file=st.session_state.population_file
        )
        sod_result = sod_agent.run()
        
        if not sod_result:
            add_log("SODViolationDetectionAgent failed")
            st.session_state.is_running = False
            return False
        
        # Look for the SOD violations output file
        sod_output_dir = os.path.join(OUTPUT_DIR, "sod_violations")
        sod_output_file = os.path.join(sod_output_dir, "sod_violations.xlsx")
        
        if os.path.exists(sod_output_file):
            add_log(f"Reading SOD violations from {sod_output_file}")
            try:
                # Read the Excel file
                violations_df = pd.read_excel(sod_output_file, sheet_name='SOD Analysis')
                
                if not violations_df.empty:
                    st.session_state.violations_data = violations_df
                    add_log(f"Loaded {len(violations_df)} records from SOD violations file")
                    
                    # Count violations
                    if 'Status' in violations_df.columns:
                        violations_count = len(violations_df[violations_df['Status'] == 'Exception'])
                        add_log(f"Found {violations_count} SOD violations")
                else:
                    add_log("SOD violations file is empty")
                    st.session_state.violations_data = pd.DataFrame()
            except Exception as e:
                add_log(f"Error reading SOD violations file: {str(e)}")
                st.session_state.violations_data = pd.DataFrame()
        else:
            add_log(f"SOD violations file not found at {sod_output_file}")
            
            # If the agent has violations data directly, use that
            if hasattr(sod_agent, 'violations_data') and sod_agent.violations_data is not None:
                st.session_state.violations_data = sod_agent.violations_data
                add_log(f"Using violations data directly from agent ({len(sod_agent.violations_data)} records)")
            else:
                # No violations data available
                st.session_state.violations_data = pd.DataFrame()
                add_log("No violations data available")
        
        # Update last run time
        st.session_state.last_run_time = datetime.now()
        add_log("SOD violation detection completed successfully")
        
    except Exception as e:
        add_log(f"Error in SOD violation detection: {str(e)}")
        st.session_state.is_running = False
        return False
    
    st.session_state.is_running = False
    return True

def run_full_audit():
    """Run both population extraction and SOD detection"""
    if run_population_extraction():
        return run_sod_detection()
    return False

def display_population_metrics():
    """Display metrics for the population data"""
    if st.session_state.population_data is None:
        return
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric("Total Records", len(st.session_state.population_data))
    
    with metric_col2:
        if 'Asset_Name' in st.session_state.population_data.columns:
            unique_assets = st.session_state.population_data['Asset_Name'].nunique()
            st.metric("Unique Assets", unique_assets)
    
    with metric_col3:
        if 'Status' in st.session_state.population_data.columns:
            completed = len(st.session_state.population_data[
                st.session_state.population_data['Status'] == 'Completed'
            ])
            st.metric("Completed Changes", completed)

def display_population_filters():
    """Display and apply filters for population data"""
    if st.session_state.population_data is None:
        return None, None
    
    filter_col1, filter_col2 = st.columns(2)
    
    selected_asset = 'All'
    selected_risk = 'All'
    
    with filter_col1:
        if 'Asset_Name' in st.session_state.population_data.columns:
            asset_options = ['All'] + list(st.session_state.population_data['Asset_Name'].unique())
            selected_asset = st.selectbox("Asset Name", asset_options, key="pop_asset_filter")
    
    with filter_col2:
        if 'Risk_Rating' in st.session_state.population_data.columns:
            risk_options = ['All'] + list(st.session_state.population_data['Risk_Rating'].unique())
            selected_risk = st.selectbox("Risk Rating", risk_options, key="pop_risk_filter")
    
    return selected_asset, selected_risk

def apply_population_filters(selected_asset, selected_risk):
    """Apply filters to population data"""
    if st.session_state.population_data is None:
        return None
    
    filtered_data = st.session_state.population_data.copy()
    
    if selected_asset != 'All':
        filtered_data = filtered_data[filtered_data['Asset_Name'] == selected_asset]
    
    if selected_risk != 'All':
        filtered_data = filtered_data[filtered_data['Risk_Rating'] == selected_risk]
    
    return filtered_data

def display_population_visualizations(filtered_data):
    """Display visualizations for population data"""
    if filtered_data is None or len(filtered_data) == 0:
        return
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Risk distribution chart
        if 'Risk_Rating' in filtered_data.columns:
            risk_counts = filtered_data['Risk_Rating'].value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Distribution"
            )
            st.plotly_chart(fig, width="stretch")
    
    with chart_col2:
        # Change type distribution
        if 'Change_Type' in filtered_data.columns:
            change_counts = filtered_data['Change_Type'].value_counts()
            fig = px.bar(
                x=change_counts.index,
                y=change_counts.values,
                title="Change Types"
            )
            st.plotly_chart(fig, width="stretch")

def show_population_data():
    """Display the population data tab"""
    st.header("Verified Population")
    
    if st.session_state.population_data is None:
        st.info("No population data available. Run the extraction first.")
        return
    
    # Summary metrics
    display_population_metrics()
    
    # Filters
    st.subheader("Filters")
    selected_asset, selected_risk = display_population_filters()
    
    # Apply filters
    filtered_data = apply_population_filters(selected_asset, selected_risk)
    
    # Display data table
    st.subheader("Change Records")
    st.dataframe(filtered_data, width="stretch")
    
    # Download button
    csv = filtered_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download CSV",
        csv,
        "verified_population.csv",
        "text/csv",
        key="download-population-csv"
    )
    
    # Visualization
    st.subheader("Data Visualization")
    display_population_visualizations(filtered_data)

def display_violations_metrics():
    """Display metrics for violations data"""
    if st.session_state.violations_data is None:
        return
    
    # Convert to DataFrame if it's not already
    violations_df = st.session_state.violations_data
    if not isinstance(violations_df, pd.DataFrame):
        try:
            violations_df = pd.DataFrame(violations_df)
        except:
            return
    
    # Create four metrics columns
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    # Total records
    with metric_col1:
        st.metric("Total Records", len(violations_df))
    
    # Actual violations (records with Status = 'Exception')
    with metric_col2:
        if 'Status' in violations_df.columns:
            exception_count = len(violations_df[violations_df['Status'] == 'Exception'])
            st.metric("SOD Violations", exception_count)
        else:
            st.metric("SOD Violations", "N/A")
    
    # High risk violations
    with metric_col3:
        if 'Risk_Rating' in violations_df.columns and 'Status' in violations_df.columns:
            high_risk = len(violations_df[(violations_df['Risk_Rating'] == 'High') & 
                                         (violations_df['Status'] == 'Exception')])
            st.metric("High Risk Violations", high_risk)
        elif 'Risk_Rating' in violations_df.columns:
            high_risk = len(violations_df[violations_df['Risk_Rating'] == 'High'])
            st.metric("High Risk Records", high_risk)
    
    # Violation types
    with metric_col4:
        if 'Violation_Type' in violations_df.columns:
            unique_types = violations_df['Violation_Type'].nunique()
            st.metric("Violation Types", unique_types)

def display_violations_filters():
    """Display and apply filters for violations data"""
    if st.session_state.violations_data is None:
        return None, None, None
    
    # Convert to DataFrame if it's not already
    violations_df = st.session_state.violations_data
    if not isinstance(violations_df, pd.DataFrame):
        try:
            violations_df = pd.DataFrame(violations_df)
        except:
            return None, None, None
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    selected_status = 'All'
    selected_risk = 'All'
    selected_type = 'All'
    
    with filter_col1:
        if 'Status' in violations_df.columns:
            status_options = ['All'] + list(violations_df['Status'].unique())
            selected_status = st.selectbox("Status", status_options, key="viol_status_filter")
    
    with filter_col2:
        if 'Risk_Rating' in violations_df.columns:
            risk_options = ['All'] + list(violations_df['Risk_Rating'].unique())
            selected_risk = st.selectbox("Risk Rating", risk_options, key="viol_risk_filter")
    
    with filter_col3:
        if 'Violation_Type' in violations_df.columns:
            type_options = ['All'] + list(violations_df['Violation_Type'].unique())
            selected_type = st.selectbox("Violation Type", type_options, key="viol_type_filter")
    
    # Add a checkbox to show only violations
    show_only_violations = st.checkbox("Show Only Violations", value=False, key="show_only_violations")
    if show_only_violations and 'Status' in violations_df.columns:
        selected_status = 'Exception'
    
    return selected_status, selected_risk, selected_type

def apply_violations_filters(selected_status, selected_risk, selected_type):
    """Apply filters to violations data"""
    if st.session_state.violations_data is None:
        return None
    
    # Convert to DataFrame if it's not already
    violations_df = st.session_state.violations_data
    if not isinstance(violations_df, pd.DataFrame):
        try:
            violations_df = pd.DataFrame(violations_df)
        except:
            return None
    
    filtered_violations = violations_df.copy()
    
    if selected_status != 'All' and 'Status' in filtered_violations.columns:
        filtered_violations = filtered_violations[filtered_violations['Status'] == selected_status]
    
    if selected_risk != 'All' and 'Risk_Rating' in filtered_violations.columns:
        filtered_violations = filtered_violations[filtered_violations['Risk_Rating'] == selected_risk]
    
    if selected_type != 'All' and 'Violation_Type' in filtered_violations.columns:
        filtered_violations = filtered_violations[filtered_violations['Violation_Type'] == selected_type]
    
    return filtered_violations


def display_violations_visualizations(filtered_violations):
    """Display visualizations for violations data"""
    if filtered_violations is None or len(filtered_violations) == 0:
        return
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Status distribution (Violations vs Compliant)
        if 'Status' in filtered_violations.columns:
            status_counts = filtered_violations['Status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Compliance Status",
                color_discrete_map={'Exception': 'red', 'Compliant': 'green'}
            )
            st.plotly_chart(fig, width="stretch")
        elif 'Risk_Rating' in filtered_violations.columns:
            risk_counts = filtered_violations['Risk_Rating'].value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Distribution"
            )
            st.plotly_chart(fig, width="stretch")
    
    with chart_col2:
        # Violation types
        if 'Violation_Type' in filtered_violations.columns:
            # Filter to only show actual violations
            if 'Status' in filtered_violations.columns:
                violations_only = filtered_violations[filtered_violations['Status'] == 'Exception']
                if len(violations_only) > 0:
                    type_counts = violations_only['Violation_Type'].value_counts()
                    fig = px.bar(
                        x=type_counts.index,
                        y=type_counts.values,
                        title="Violation Types (Exceptions Only)"
                    )
                    st.plotly_chart(fig, width="stretch")
            else:
                type_counts = filtered_violations['Violation_Type'].value_counts()
                fig = px.bar(
                    x=type_counts.index,
                    y=type_counts.values,
                    title="Violation Types"
                )
                st.plotly_chart(fig, width="stretch")

def show_violations_data():
    """Display the SOD violations tab"""
    st.header("SOD Violations")
    
    if st.session_state.violations_data is None:
        st.info("No violations data available. Run the SOD detection first.")
        return
    
    # Check if violations data is empty
    violations_df = st.session_state.violations_data
    if isinstance(violations_df, pd.DataFrame) and violations_df.empty:
        st.success("No SOD violations were found in the population.")
        return
    
    # Convert to DataFrame if it's not already
    if not isinstance(violations_df, pd.DataFrame):
        try:
            violations_df = pd.DataFrame(violations_df)
            st.session_state.violations_data = violations_df
        except Exception as e:
            st.error(f"Error converting violations data to DataFrame: {str(e)}")
            st.write("Raw violations data:", violations_df)
            return
    
    # Summary metrics
    display_violations_metrics()
    
    # Filters
    st.subheader("Filters")
    selected_status, selected_risk, selected_type = display_violations_filters()
    
    # Apply filters
    filtered_violations = apply_violations_filters(selected_status, selected_risk, selected_type)
    
    # Display data table
    st.subheader("Violation Details")
    
    # Define columns to display in the order specified
    display_columns = [
        'Change_ID', 'Asset_Name', 
        'Requestor_ID', 'Requestor_Name', 
        'Developer_ID', 'Developer_Name', 
        'Deployer_ID', 'Deployer_Name', 
        'Approver_ID', 'Approver_Name', 
        'Status', 'Exception_Reason'
    ]
    
    # Filter columns to only include those that exist in the DataFrame
    display_columns = [col for col in display_columns if col in filtered_violations.columns]
    
    # Display the DataFrame with selected columns
    if len(display_columns) > 0:
        st.dataframe(filtered_violations[display_columns], width="stretch")
    else:
        st.dataframe(filtered_violations, width="stretch")
    
    # Download button
    csv = filtered_violations.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download CSV",
        csv,
        "sod_violations.csv",
        "text/csv",
        key="download-violations-csv"
    )
    
    # Visualization
    if len(filtered_violations) > 0:
        st.subheader("Violation Analysis")
        display_violations_visualizations(filtered_violations)


def toggle_scheduler():
    """Toggle scheduler on/off"""
    if st.session_state.scheduler_enabled:
        # Turn off scheduler
        st.session_state.scheduler_enabled = False
        st.session_state.next_scheduled_run = None
        add_log("Scheduler disabled")
    else:
        # Turn on scheduler with delay
        st.session_state.scheduler_enabled = True
        
        # Schedule the run after the specified delay
        scheduled_time = datetime.now() + timedelta(minutes=st.session_state.start_delay)
        st.session_state.next_scheduled_run = scheduled_time
        
        add_log(f"Scheduler enabled. Will run once at {scheduled_time.strftime('%H:%M:%S')} (after {st.session_state.start_delay} minutes)")


def display_sidebar_controls():
    """Display controls in the sidebar"""
    st.sidebar.header("Controls")
    
    # Run buttons
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        if st.button("Extract Population", disabled=st.session_state.is_running):
            run_population_extraction()
    
    with col2:
        if st.button("Detect Violations", disabled=st.session_state.is_running or st.session_state.population_file is None):
            run_sod_detection()
    
    with col3:
        if st.button("Run Full Audit", disabled=st.session_state.is_running):
            run_full_audit()
    
    # Status indicator
    if st.session_state.is_running:
        st.sidebar.warning("Process running...")
    elif st.session_state.last_run_time:
        st.sidebar.success(f"Last run: {st.session_state.last_run_time.strftime('%H:%M:%S')}")
    
    # Scheduler options
    st.sidebar.header("Scheduler")
    
    # Delay setting
    start_delay = st.sidebar.number_input(
        "Delay (minutes)", 
        min_value=1, 
        value=st.session_state.start_delay,
        key="start_delay_input"
    )
    
    # Update the delay if changed
    if start_delay != st.session_state.start_delay:
        st.session_state.start_delay = start_delay
        if st.session_state.scheduler_enabled:
            # Update the scheduled time if scheduler is already running
            scheduled_time = datetime.now() + timedelta(minutes=start_delay)
            st.session_state.next_scheduled_run = scheduled_time
            add_log(f"Delay updated. Will run at {scheduled_time.strftime('%H:%M:%S')}")
    
    # Scheduler control button
    button_label = "Stop Scheduler" if st.session_state.scheduler_enabled else "Start Scheduler"
    button_disabled = st.session_state.is_running and not st.session_state.scheduler_enabled
    
    if st.sidebar.button(button_label, key="toggle_scheduler", disabled=button_disabled):
        toggle_scheduler()
    
    # Show scheduler status
    if st.session_state.scheduler_enabled:
        next_run = st.session_state.next_scheduled_run.strftime('%H:%M:%S') if st.session_state.next_scheduled_run else "Unknown"
        if st.session_state.next_scheduled_run:
            time_left = (st.session_state.next_scheduled_run - datetime.now()).total_seconds()
            minutes_left = max(0, int(time_left / 60))
            seconds_left = max(0, int(time_left % 60))
            st.sidebar.info(f"Scheduled to run at: {next_run} ({minutes_left}m {seconds_left}s remaining)")
        else:
            st.sidebar.info(f"Scheduled to run at: {next_run}")
    
    # Log display
    st.sidebar.subheader("Log")
    log_text = "\n".join(st.session_state.log_messages)
    st.sidebar.text_area(
        label="Log Messages",
        value=log_text,
        height=400,
        label_visibility="collapsed"
    )

def main():
    """Main Streamlit application"""
    # Set page config
    st.set_page_config(
        page_title="Change Management Audit Tool",
        page_icon="📊",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Check for scheduled runs
    check_scheduled_run()
    
    # Page title
    st.title("Change Management Audit Tool")
    
    # Sidebar controls
    display_sidebar_controls()
    
    # Main content - tabs
    tab1, tab2 = st.tabs(["Verified Population", "SOD Violations"])
    
    with tab1:
        show_population_data()
    
    with tab2:
        show_violations_data()
    
    # Auto-refresh the app every few seconds to check for scheduled runs
    if st.session_state.scheduler_enabled:
        time.sleep(1)  # Small delay
        st.rerun()

if __name__ == "__main__":
    main()