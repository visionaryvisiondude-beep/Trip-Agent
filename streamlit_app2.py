import streamlit as st
import requests
from datetime import datetime, date
import json
import time

# Page configuration
st.set_page_config(
    page_title="VacAIgent - AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .trip-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_response' not in st.session_state:
    st.session_state.api_response = None
if 'loading' not in st.session_state:
    st.session_state.loading = False

# Main header
st.markdown('<h1 class="main-header">✈️ VacAIgent</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your AI-Powered Travel Planning Assistant</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API endpoint configuration
    api_base_url = st.text_input(
        "API Base URL",
        value="https://trip-agent.onrender.com/",
        help="The base URL of your VacAIgent API"
    )
    
    # Health check button
    if st.button("🔍 Check API Health"):
        try:
            health_response = requests.get(f"{api_base_url}/api/v1/health", timeout=10)
            if health_response.status_code == 200:
                health_data = health_response.json()
                st.success(f"✅ API is healthy!\nStatus: {health_data.get('status', 'N/A')}")
            else:
                st.error(f"❌ API health check failed: {health_response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Failed to connect to API: {str(e)}")
    
    st.divider()
    
    # About section
    st.header("ℹ️ About")
    st.markdown("""
    **VacAIgent** uses advanced AI to create personalized travel itineraries based on:
    - 🌍 Your destination preferences
    - 📅 Travel dates
    - 🎯 Personal interests
    - 💰 Budget considerations
    """)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🗺️ Plan Your Trip")
    
    # Trip planning form
    with st.form("trip_form"):
        # Origin and Destination
        col_orig, col_dest = st.columns(2)
        with col_orig:
            origin = st.text_input(
                "From (Origin)",
                placeholder="e.g., Bangalore, India",
                help="Enter your departure city"
            )
        
        with col_dest:
            destination = st.text_input(
                "To (Destination)",
                placeholder="e.g., Krabi, Thailand",
                help="Enter your desired destination"
            )
        
        # Date selection
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "Start Date",
                value=date.today(),
                min_value=date.today(),
                help="Select your departure date"
            )
        
        with col_end:
            end_date = st.date_input(
                "End Date",
                value=date.today(),
                min_value=date.today(),
                help="Select your return date"
            )
        
        # Interests and preferences
        interests = st.text_area(
            "Travel Interests & Preferences",
            placeholder="e.g., 2 adults who love swimming, hiking, local food, and water sports.",
            height=100,
            help="Describe your group size, interests, and what you'd like to do during your trip"
        )
        
        # Submit button
        submitted = st.form_submit_button("🚀 Generate Trip Plan", use_container_width=True)
        
        if submitted:
            # Validation
            if not all([origin, destination, interests]):
                st.error("❌ Please fill in all required fields.")
            elif end_date <= start_date:
                st.error("❌ End date must be after start date.")
            else:
                # Prepare API request
                trip_data = {
                    "origin": origin,
                    "destination": destination,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "interests": interests
                }
                
                st.session_state.loading = True
                st.session_state.api_response = None

with col2:
    st.header("📋 Trip Summary")
    
    # Display current form values
    if any([origin, destination, interests]):
        st.markdown('<div class="trip-card">', unsafe_allow_html=True)
        st.markdown("**🎯 Current Selection:**")
        if origin:
            st.markdown(f"**From:** {origin}")
        if destination:
            st.markdown(f"**To:** {destination}")
        try:
            if 'start_date' in locals() and 'end_date' in locals():
                if start_date and end_date and end_date > start_date:
                    duration = (end_date - start_date).days
                    st.markdown(f"**Duration:** {duration} days")
                    st.markdown(f"**Dates:** {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}")
        except:
            pass
        if interests:
            st.markdown(f"**Interests:** {interests[:100]}{'...' if len(interests) > 100 else ''}")
        st.markdown('</div>', unsafe_allow_html=True)

# Handle API call and display results
if st.session_state.loading:
    with st.spinner("🤖 AI is crafting your perfect trip... This may take a few minutes."):
        try:
            # Make API request
            response = requests.post(
                f"{api_base_url}/api/v1/plan-trip",
                json=trip_data,
                timeout=300  # 5 minutes timeout
            )
            
            if response.status_code == 200:
                st.session_state.api_response = response.json()
                st.session_state.loading = False
                st.rerun()
            else:
                st.session_state.loading = False
                error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
                st.error(f"❌ API Error ({response.status_code}): {error_detail}")
                
        except requests.exceptions.Timeout:
            st.session_state.loading = False
            st.error("⏰ Request timed out. The AI is taking longer than expected. Please try again.")
        except requests.exceptions.RequestException as e:
            st.session_state.loading = False
            st.error(f"❌ Connection Error: {str(e)}")
        except Exception as e:
            st.session_state.loading = False
            st.error(f"❌ Unexpected Error: {str(e)}")

# Display API response
if st.session_state.api_response:
    response_data = st.session_state.api_response
    
    if response_data.get('status') == 'success':
        st.markdown('<div class="success-message">✅ Trip plan generated successfully!</div>', unsafe_allow_html=True)
        
        # Display the itinerary
        st.header("🗓️ Your Personalized Trip Itinerary")
        
        itinerary = response_data.get('itinerary', '')
        if itinerary:
            # Create tabs for better organization
            tab1, tab2 = st.tabs(["📖 Full Itinerary", "💾 Export Options"])
            
            with tab1:
                st.markdown(itinerary)
            
            with tab2:
                col_download1, col_download2 = st.columns(2)
                
                with col_download1:
                    # Download as text file
                    st.download_button(
                        label="📄 Download as Text",
                        data=itinerary,
                        file_name=f"trip_itinerary_{destination.replace(' ', '_')}_{start_date}.txt",
                        mime="text/plain"
                    )
                
                with col_download2:
                    # Download as JSON
                    json_data = json.dumps(response_data, indent=2)
                    st.download_button(
                        label="📊 Download as JSON",
                        data=json_data,
                        file_name=f"trip_data_{destination.replace(' ', '_')}_{start_date}.json",
                        mime="application/json"
                    )
                
                # Copy to clipboard option
                st.markdown("**💡 Tip:** You can select and copy the itinerary text above to save it elsewhere.")
        
        # Clear results button
        if st.button("🗑️ Clear Results"):
            st.session_state.api_response = None
            st.rerun()
            
    else:
        error_msg = response_data.get('error', response_data.get('message', 'Unknown error'))
        st.markdown(f'<div class="error-message">❌ Error: {error_msg}</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>Powered by VacAIgent API | Built with ❤️ using Streamlit</p>
        <p>🤖 AI-generated itineraries are suggestions. Please verify details before booking.</p>
    </div>
    """,
    unsafe_allow_html=True
)
