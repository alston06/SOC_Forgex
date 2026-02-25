import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


def render(client):
    st.title("Hunting")

    st.write("Query logs by actor, service, resource, and time range.")

    # Query builder
    col1, col2 = st.columns(2)
    
    with col1:
        actor = st.text_input("Actor (user/service)", value="")
        service_name = st.text_input("Service Name", value="")
    
    with col2:
        normalized_path = st.text_input("Resource Path (e.g., /api/users/{id})", value="")
    
    col3, col4 = st.columns(2)
    with col3:
        time_from = st.datetime_input("From", value=datetime.utcnow() - timedelta(hours=1))
    
    with col4:
        time_to = st.datetime_input("To", value=datetime.utcnow())
    
    limit = st.slider("Limit results", 10, 1000, 100)

    if st.button("Search Logs"):
        try:
            result = client.hunt_logs(
                actor=actor if actor else None,
                service_name=service_name if service_name else None,
                normalized_path=normalized_path if normalized_path else None,
                time_from=time_from.isoformat() + "Z" if time_from else None,
                time_to=time_to.isoformat() + "Z" if time_to else None,
                limit=limit
            )
            
            events = result.get("events", [])
            
            if events:
                st.subheader(f"Found {len(events)} events")
                
                events_df = pd.DataFrame(events)
                
                # Select display columns
                display_cols = [col for col in ["timestamp", "event_type", "actor", "resource", "action", "ip", "service_name", "risk_score"] if col in events_df.columns]
                
                if display_cols:
                    st.dataframe(events_df[display_cols], use_container_width=True)
                else:
                    st.dataframe(events_df, use_container_width=True)
                
                # Export option
                csv = events_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="hunt_results.csv",
                    mime="text/csv"
                )
            else:
                st.info("No events found matching the query.")
        
        except Exception as e:
            st.error(f"Error hunting logs: {str(e)}")
