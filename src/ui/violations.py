import streamlit as st
import pandas as pd
import plotly.express as px

def show_violations():
    """Display the SOD violations tab content"""
    st.header("SOD Violations")
    
    if st.session_state.violations_data is None or len(st.session_state.violations_data) == 0:
        st.info("No violations data available. Run an audit first.")
    else:
        # Summary metrics
        violations_df = st.session_state.violations_data
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric("Total Violations", len(violations_df))
        
        with metric_col2:
            if 'Risk_Rating' in violations_df.columns:
                high_risk = len(violations_df[violations_df['Risk_Rating'] == 'High'])
                st.metric("High Risk Violations", high_risk)
        
        with metric_col3:
            if 'Violation_Type' in violations_df.columns:
                unique_types = violations_df['Violation_Type'].nunique()
                st.metric("Violation Types", unique_types)
        
        # Filters
        st.subheader("Filters")
        filter_col1, filter_col2 = st.columns(2)
        
        selected_risk = 'All'
        selected_type = 'All'
        
        with filter_col1:
            if 'Risk_Rating' in violations_df.columns:
                risk_options = ['All'] + list(violations_df['Risk_Rating'].unique())
                selected_risk = st.selectbox("Risk Rating", risk_options)
        
        with filter_col2:
            if 'Violation_Type' in violations_df.columns:
                type_options = ['All'] + list(violations_df['Violation_Type'].unique())
                selected_type = st.selectbox("Violation Type", type_options)
        
        # Apply filters
        filtered_violations = violations_df.copy()
        
        if selected_risk != 'All':
            filtered_violations = filtered_violations[filtered_violations['Risk_Rating'] == selected_risk]
        
        if selected_type != 'All':
            filtered_violations = filtered_violations[filtered_violations['Violation_Type'] == selected_type]
        
        # Display data table
        st.subheader("Violation Details")
        st.dataframe(filtered_violations, use_container_width=True)
        
        # Visualization
        if len(filtered_violations) > 0:
            st.subheader("Violation Analysis")
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                if 'Risk_Rating' in filtered_violations.columns:
                    risk_counts = filtered_violations['Risk_Rating'].value_counts()
                    fig = px.pie(
                        values=risk_counts.values,
                        names=risk_counts.index,
                        title="Violations by Risk Level"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with chart_col2:
                if 'Violation_Type' in filtered_violations.columns:
                    type_counts = filtered_violations['Violation_Type'].value_counts()
                    fig = px.bar(
                        x=type_counts.index,
                        y=type_counts.values,
                        title="Violations by Type"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Download button
        csv = filtered_violations.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download CSV",
            csv,
            "sod_violations.csv",
            "text/csv",
            key="download-violations-csv"
        )