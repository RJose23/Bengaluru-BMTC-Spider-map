import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import math
from typing import List, Tuple
import os

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Bangalore Bus Stop Spider Map",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
    <style>
        :root {
            --primary-color: #ff9500;
            --background-color: #1a1a1a;
            --secondary-bg: #222222;
            --text-color: #ffffff;
            --border-color: #333333;
        }
        
        .main {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        
        .sidebar .sidebar-content {
            background-color: var(--secondary-bg);
        }
        
        .metric-card {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        
        .stop-item {
            background-color: var(--secondary-bg);
            border-left: 4px solid var(--primary-color);
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
        }
        
        .spider-info {
            background-color: rgba(255, 149, 0, 0.1);
            border: 1px solid var(--primary-color);
            border-radius: 6px;
            padding: 12px;
            margin: 10px 0;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING & CACHING
# ============================================================================
@st.cache_data
def load_stops_data(filepath: str = "stops.txt") -> pd.DataFrame:
    """Load bus stops from CSV file"""
    try:
        df = pd.read_csv(filepath)
        # Ensure proper column names
        df.columns = ['stop_name', 'stop_id', 'stop_lat', 'stop_lon']
        df = df.dropna(subset=['stop_lat', 'stop_lon'])
        df['stop_lat'] = pd.to_numeric(df['stop_lat'], errors='coerce')
        df['stop_lon'] = pd.to_numeric(df['stop_lon'], errors='coerce')
        df = df.dropna(subset=['stop_lat', 'stop_lon'])
        st.success(f"✅ Loaded {len(df)} bus stops from Bangalore")
        return df
    except FileNotFoundError:
        st.error(f"❌ File not found: {filepath}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()

# ============================================================================
# DISTANCE CALCULATIONS
# ============================================================================
def euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Euclidean distance in kilometers"""
    scale = 111.0  # km per degree at equator
    dlat = (lat2 - lat1) * scale
    dlon = (lon2 - lon1) * scale * math.cos(math.radians(lat1))
    return math.sqrt(dlat**2 + dlon**2)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance (great-circle distance) in km"""
    R = 6371  # Earth's radius in kilometers
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def find_nearest_stops(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    num_stops: int = 6,
    distance_mode: str = "euclidean"
) -> pd.DataFrame:
    """Find N nearest bus stops from a given coordinate"""
    if df.empty:
        return pd.DataFrame()
    
    # Calculate distances
    if distance_mode == "euclidean":
        distances = df.apply(
            lambda row: euclidean_distance(lat, lon, row['stop_lat'], row['stop_lon']),
            axis=1
        )
    else:  # haversine
        distances = df.apply(
            lambda row: haversine_distance(lat, lon, row['stop_lat'], row['stop_lon']),
            axis=1
        )
    
    df_with_distances = df.copy()
    df_with_distances['distance_km'] = distances
    
    # Sort and get top N
    nearest = df_with_distances.nsmallest(num_stops, 'distance_km').copy()
    nearest['distance_km'] = nearest['distance_km'].round(3)
    
    return nearest

# ============================================================================
# MAP VISUALIZATION
# ============================================================================
def create_spider_map(
    query_lat: float,
    query_lon: float,
    nearest_stops: pd.DataFrame,
    distance_mode: str = "euclidean"
) -> folium.Map:
    """Create interactive spider map with Folium"""
    
    # Initialize map centered on query location
    m = folium.Map(
        location=[query_lat, query_lon],
        zoom_start=14,
        tiles="CartoDB dark_matter"
    )
    
    # Add query location marker (center point)
    folium.CircleMarker(
        location=[query_lat, query_lon],
        radius=8,
        popup=f"Query Location<br>Lat: {query_lat:.4f}, Lon: {query_lon:.4f}",
        color="white",
        fill=True,
        fillColor="#ff9500",
        fillOpacity=0.9,
        weight=2,
        tooltip="Your Location"
    ).add_to(m)
    
    # Add spider legs and stop markers
    for idx, stop in nearest_stops.iterrows():
        stop_lat = stop['stop_lat']
        stop_lon = stop['stop_lon']
        distance = stop['distance_km']
        stop_name = stop['stop_name']
        stop_id = stop['stop_id']
        
        # Draw line from query point to stop (spider leg)
        folium.PolyLine(
            locations=[[query_lat, query_lon], [stop_lat, stop_lon]],
            color="#ff9500",
            weight=2,
            opacity=0.7,
            dash_array="5, 5"
        ).add_to(m)
        
        # Add stop marker
        popup_text = f"""
        <div style="font-family: Arial; font-size: 12px; width: 200px;">
            <b style="color: #ff9500;">🚌 {stop_name}</b><br>
            <hr style="margin: 5px 0; border-color: #ff9500;">
            <b>Stop ID:</b> {stop_id}<br>
            <b>Distance:</b> {distance:.3f} km<br>
            <b>Latitude:</b> {stop_lat:.6f}<br>
            <b>Longitude:</b> {stop_lon:.6f}
        </div>
        """
        
        folium.CircleMarker(
            location=[stop_lat, stop_lon],
            radius=6,
            popup=folium.Popup(popup_text, max_width=250),
            color="white",
            fill=True,
            fillColor="#ff9500",
            fillOpacity=0.8,
            weight=1,
            tooltip=f"{stop_name} ({distance:.2f} km)"
        ).add_to(m)
    
    return m

# ============================================================================
# MAIN APP
# ============================================================================
def main():
    # Title and description
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🕷️ Bangalore Bus Spider Map")
        st.markdown("**Interactive visualization of nearest bus stops using spider-leg mapping**")
    
    # Load data
    stops_df = load_stops_data("stops.txt")
    
    if stops_df.empty:
        st.error("Cannot proceed without bus stop data. Please check that stops.txt exists in the app directory.")
        return
    
    # ========================================================================
    # SIDEBAR CONTROLS
    # ========================================================================
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Number of stops
        num_stops = st.slider(
            "Number of Nearest Stops",
            min_value=5,
            max_value=8,
            value=6,
            step=1,
            help="Select how many nearest bus stops to display (5-8)"
        )
        
        # Distance mode
        st.markdown("---")
        st.subheader("Distance Calculation Mode")
        distance_mode = st.radio(
            "Choose distance metric:",
            options=["euclidean", "haversine"],
            format_func=lambda x: "📏 Euclidean Distance" if x == "euclidean" else "🗺️ Haversine (Walking Network)",
            help="Euclidean: straight-line distance | Haversine: great-circle distance (more accurate)"
        )
        
        # Information
        st.markdown("---")
        st.subheader("📊 Dataset Info")
        st.metric("Total Bus Stops", f"{len(stops_df):,}")
        st.metric("City", "Bangalore, India")
        st.metric("Lat Range", f"{stops_df['stop_lat'].min():.2f} to {stops_df['stop_lat'].max():.2f}")
        st.metric("Lon Range", f"{stops_df['stop_lon'].min():.2f} to {stops_df['stop_lon'].max():.2f}")
        
        # Sample locations
        st.markdown("---")
        st.subheader("🎯 Sample Locations")
        sample_locations = {
            "MG Road": (12.9352, 77.6245),
            "Indiranagar": (13.0011, 77.6448),
            "Whitefield": (12.9698, 77.7499),
            "Yeshwanthpur": (13.0386, 77.5769),
            "Marathahalli": (12.9698, 77.6959),
            "HSR Layout": (12.9176, 77.6348)
        }
        
        selected_sample = st.selectbox(
            "Quick Location Select",
            options=[None] + list(sample_locations.keys()),
            format_func=lambda x: "-- Custom Input --" if x is None else x
        )
    
    # ========================================================================
    # MAIN CONTENT AREA
    # ========================================================================
    # Location input
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Enter Location")
        if selected_sample:
            query_lat, query_lon = sample_locations[selected_sample]
            st.info(f"✓ Using sample location: **{selected_sample}**")
        else:
            query_lat = st.number_input(
                "Latitude",
                value=12.9352,
                min_value=-90.0,
                max_value=90.0,
                step=0.0001,
                format="%.6f"
            )
            query_lon = st.number_input(
                "Longitude",
                value=77.6245,
                min_value=-180.0,
                max_value=180.0,
                step=0.0001,
                format="%.6f"
            )
    
    with col2:
        st.subheader("📈 Query Info")
        st.markdown(f"""
        <div class="spider-info">
            <b>Query Location:</b><br>
            Lat: {query_lat:.6f}<br>
            Lon: {query_lon:.6f}<br>
            <br>
            <b>Search Radius:</b> Top {num_stops} stops<br>
            <b>Distance Mode:</b> {distance_mode.title()}
        </div>
        """, unsafe_allow_html=True)
    
    # Find nearest stops
    nearest_stops = find_nearest_stops(
        stops_df,
        query_lat,
        query_lon,
        num_stops=num_stops,
        distance_mode=distance_mode
    )
    
    # ========================================================================
    # MAP AND RESULTS
    # ========================================================================
    st.markdown("---")
    
    map_col, results_col = st.columns([2, 1])
    
    with map_col:
        st.subheader("🗺️ Spider Map Visualization")
        
        # Create and display map
        spider_map = create_spider_map(
            query_lat,
            query_lon,
            nearest_stops,
            distance_mode=distance_mode
        )
        
        st_folium(spider_map, width=800, height=600)
    
    with results_col:
        st.subheader("🚌 Nearest Bus Stops")
        
        if not nearest_stops.empty:
            # Summary stats
            st.markdown(f"""
            <div class="metric-card">
                <b>Total Found:</b> {len(nearest_stops)}<br>
                <b>Closest:</b> {nearest_stops.iloc[0]['distance_km']:.3f} km<br>
                <b>Farthest:</b> {nearest_stops.iloc[-1]['distance_km']:.3f} km<br>
                <b>Avg Distance:</b> {nearest_stops['distance_km'].mean():.3f} km
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # List of stops
            for idx, (i, stop) in enumerate(nearest_stops.iterrows(), 1):
                st.markdown(f"""
                <div class="stop-item">
                    <b>#{idx} {stop['stop_name']}</b><br>
                    <small>
                        ID: {stop['stop_id']} | 
                        Distance: {stop['distance_km']:.3f} km<br>
                        Lat: {stop['stop_lat']:.6f} | Lon: {stop['stop_lon']:.6f}
                    </small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No stops found for the given location.")
    
    # ========================================================================
    # EXPORT DATA
    # ========================================================================
    st.markdown("---")
    st.subheader("📥 Export Results")
    
    if not nearest_stops.empty:
        # Prepare export data
        export_df = nearest_stops[['stop_name', 'stop_id', 'stop_lat', 'stop_lon', 'distance_km']].copy()
        export_df['rank'] = range(1, len(export_df) + 1)
        export_df = export_df[['rank', 'stop_name', 'stop_id', 'stop_lat', 'stop_lon', 'distance_km']]
        
        # CSV download
        csv_data = export_df.to_csv(index=False)
        st.download_button(
            label="📄 Download as CSV",
            data=csv_data,
            file_name=f"nearest_stops_{query_lat:.4f}_{query_lon:.4f}.csv",
            mime="text/csv"
        )
        
        # Display table
        st.dataframe(
            export_df.style.format({
                'distance_km': '{:.3f}',
                'stop_lat': '{:.6f}',
                'stop_lon': '{:.6f}'
            }),
            use_container_width=True
        )
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">
        🕷️ <b>Bangalore Bus Spider Map</b> | Built with Streamlit + Folium<br>
        Data Source: stops.txt | Visualization: Interactive Folium Maps
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
