import streamlit as st
import pandas as pd

def show_population():
    """Display the verified population tab content"""
    st.header("Verified Population")
    
    if st.session_state.population_data is None:
        st.info("No population data available. Run an audit first.")
    else:
        # Summary metrics
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
        
        # Filters
        st.subheader("Filters")
        filter_col1, filter_col2 = st.columns(2)
        
        selected_asset = 'All'
        selected_risk = 'All'
        
        with filter_col1:
            if 'Asset_Name' in st.session_state.population_data.columns:
                asset_options = ['All'] + list(st.session_state.population_data['Asset_Name'].unique())
                selected_asset = st.selectbox("Asset Name", asset_options)
        
        with filter_col2:
            if 'Risk_Rating' in st.session_state.population_data.columns:
                risk_options = ['All'] + list(st.session_state.population_data['Risk_Rating'].unique())
                selected_risk = st.selectbox("Risk Rating", risk_options)
        
        # Apply filters
        filtered_data = st.session_state.population_data.copy()
        
        if selected_asset != 'All':
            filtered_data = filtered_data[filtered_data['Asset_Name'] == selected_asset]
        
        if selected_risk != 'All':
            filtered_data = filtered_data[filtered_data['Risk_Rating'] == selected_risk]
        
        # Display data table
        st.subheader("Change Records")
        st.dataframe(filtered_data, use_container_width=True)
        
        # Download button
        csv = filtered_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download CSV",
            csv,
            "verified_population.csv",
            "text/csv",
            key="download-population-csv"
        )