import streamlit as st
import plotly.express as px

def show_dashboard(start_audit_func, stop_audit_func):
    """Display the dashboard tab content"""
    st.header("Audit Control Panel")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Execution Settings")
        
        # Mode selection
        st.radio(
            "Execution Mode",
            ["Run Once", "Run Periodically"],
            key="mode",
            format_func=lambda x: x
        )
        
        # Periodic settings
        if st.session_state.mode == "Run Periodically":
            st.number_input(
                "Interval (minutes)",
                min_value=1,
                value=5,
                key="interval"
            )
            
            st.number_input(
                "Duration (minutes, 0 for indefinite)",
                min_value=0,
                value=60,
                key="duration"
            )
        else:
            # Set default values even when not shown
            st.session_state.interval = 5
            st.session_state.duration = 60
        
        # Control buttons
        col1a, col1b = st.columns(2)
        with col1a:
            st.button(
                "Start Audit",
                on_click=start_audit_func,
                disabled=st.session_state.is_running
            )
        
        with col1b:
            st.button(
                "Stop Audit",
                on_click=stop_audit_func,
                disabled=not st.session_state.is_running
            )
    
    with col2:
        st.subheader("Status")
        
        # Status indicators
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            st.metric(
                "Current Status",
                "Running" if st.session_state.is_running else "Stopped"
            )
            
            if st.session_state.last_run_time:
                st.metric(
                    "Last Run",
                    st.session_state.last_run_time.strftime("%H:%M:%S")
                )
        
        with status_col2:
            if st.session_state.next_run_time and st.session_state.is_running:
                st.metric(
                    "Next Run",
                    st.session_state.next_run_time.strftime("%H:%M:%S")
                )
            
            if st.session_state.population_data is not None:
                st.metric(
                    "Records Processed",
                    len(st.session_state.population_data)
                )
            
            if st.session_state.violations_data is not None:
                st.metric(
                    "Violations Found",
                    len(st.session_state.violations_data)
                )
    
    # Log output
    st.subheader("Log Output")
    log_container = st.container()
    
    # Fix: Add a label to the text_area
    log_container.text_area(
        label="Log Messages",  # Added a label here
        value="\n".join(st.session_state.log_messages),
        height=300,
        key="log_display",
        label_visibility="collapsed"  # Hide the label visually but keep it for accessibility
    )
    
    # Summary charts (if data available)
    if st.session_state.population_data is not None:
        st.subheader("Audit Summary")
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Risk distribution chart
            if 'Risk_Rating' in st.session_state.population_data.columns:
                risk_counts = st.session_state.population_data['Risk_Rating'].value_counts()
                fig = px.pie(
                    values=risk_counts.values,
                    names=risk_counts.index,
                    title="Risk Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with chart_col2:
            # Change type distribution
            if 'Change_Type' in st.session_state.population_data.columns:
                change_counts = st.session_state.population_data['Change_Type'].value_counts()
                fig = px.bar(
                    x=change_counts.index,
                    y=change_counts.values,
                    title="Change Types"
                )
                st.plotly_chart(fig, use_container_width=True)