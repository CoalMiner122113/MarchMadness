import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from Madness import getTeam, arr
import numpy as np
from TournamentLayout import tourney

# Set page config
st.set_page_config(
    page_title="March Madness Simulator",
    page_icon="🏀",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .bracket-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .game-result {
        border: 1px solid #ddd;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .winner {
        color: #28a745;
        font-weight: bold;
    }
    .loser {
        color: #dc3545;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("🏀 March Madness Tournament Simulator")
st.markdown("""
This simulator uses advanced analytics from KenPom data to predict March Madness tournament outcomes.
Each simulation takes into account team statistics including:
- Adjusted Efficiency Margin (AdjEM)
- Strength of Schedule (SOS)
- Luck Factor
""")

# Initialize session state for tournament results
if 'tournament_results' not in st.session_state:
    st.session_state.tournament_results = None

# Create regions with current teams
def initialize_regions():
    east = [getTeam("Connecticut"),getTeam("Stetson"),getTeam("Florida Atlantic"),getTeam("Northwestern"),
            getTeam("San Diego St."),getTeam("UAB"),getTeam("Auburn"),getTeam("Yale"),
            getTeam("BYU"),getTeam("Duquesne"),getTeam("Illinois"),getTeam("Morehead St."),
            getTeam("Washington St."),getTeam("Drake"),getTeam("Iowa St."),getTeam("South Dakota St.")]
    
    west = [getTeam("North Carolina"),getTeam("Wagner"),getTeam("Mississippi St."),getTeam("Michigan St."),
            getTeam("Saint Mary's"),getTeam("Grand Canyon"),getTeam("Alabama"),getTeam("Charleston"),
            getTeam("Clemson"),getTeam("New Mexico"),getTeam("Baylor"),getTeam("Colgate"),
            getTeam("Dayton"),getTeam("Nevada"),getTeam("Arizona"),getTeam("Long Beach St.")]
    
    south = [getTeam("Houston"),getTeam("Longwood"),getTeam("Nebraska"),getTeam("Texas A&M"),
             getTeam("Wisconsin"),getTeam("James Madison"),getTeam("Duke"),getTeam("Vermont"),
             getTeam("Texas Tech"),getTeam("N.C. State"),getTeam("Kentucky"),getTeam("Oakland"),
             getTeam("Florida"),getTeam("Colorado"),getTeam("Marquette"),getTeam("Western Kentucky")]
    
    midwest = [getTeam("Purdue"),getTeam("Grambling St."),getTeam("Utah St."),getTeam("TCU"),
               getTeam("Gonzaga"),getTeam("McNeese St."),getTeam("Kansas"),getTeam("Samford"),
               getTeam("South Carolina"),getTeam("Oregon"),getTeam("Creighton"),getTeam("Akron"),
               getTeam("Texas"),getTeam("Colorado St."),getTeam("Tennessee"),getTeam("Saint Peter's")]
    
    return east, west, south, midwest

def display_game_results(games, region=None):
    for game in games:
        winner, loser, probability = game
        st.markdown(f"""
        <div class="game-result">
            <span class="winner">✓ {winner.name}</span> def. 
            <span class="loser">{loser.name}</span>
            <br/>
            <small>Win Probability: {probability:.2%}</small>
        </div>
        """, unsafe_allow_html=True)

# Create columns for the regions
col1, col2 = st.columns(2)

with col1:
    st.subheader("Simulation Controls")
    if st.button("🎲 Run New Simulation", key="run_sim"):
        # Initialize regions
        east, west, south, midwest = initialize_regions()
        
        # Run tournament and store results
        results = tourney(east, west, south, midwest)
        st.session_state.tournament_results = results

with col2:
    st.subheader("Statistics")
    # Add some sample statistics or metrics here
    st.metric(label="Total Games", value="63")
    st.metric(label="Rounds", value="6")

# Display tournament results
if st.session_state.tournament_results:
    st.header("Tournament Results")
    results = st.session_state.tournament_results
    
    # Create tabs for different rounds
    tabs = st.tabs(["Round of 64", "Round of 32", "Sweet 16", "Elite 8", "Final Four", "Championship"])
    
    # Round of 64
    with tabs[0]:
        st.write("### Round of 64")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("#### East Region")
            display_game_results(results['round64']['east'])
        with col2:
            st.write("#### West Region")
            display_game_results(results['round64']['west'])
        with col3:
            st.write("#### South Region")
            display_game_results(results['round64']['south'])
        with col4:
            st.write("#### Midwest Region")
            display_game_results(results['round64']['midwest'])
    
    # Round of 32
    with tabs[1]:
        st.write("### Round of 32")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("#### East Region")
            display_game_results(results['round32']['east'])
        with col2:
            st.write("#### West Region")
            display_game_results(results['round32']['west'])
        with col3:
            st.write("#### South Region")
            display_game_results(results['round32']['south'])
        with col4:
            st.write("#### Midwest Region")
            display_game_results(results['round32']['midwest'])
    
    # Sweet 16
    with tabs[2]:
        st.write("### Sweet 16")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("#### East Region")
            display_game_results(results['sweet16']['east'])
        with col2:
            st.write("#### West Region")
            display_game_results(results['sweet16']['west'])
        with col3:
            st.write("#### South Region")
            display_game_results(results['sweet16']['south'])
        with col4:
            st.write("#### Midwest Region")
            display_game_results(results['sweet16']['midwest'])
    
    # Elite 8
    with tabs[3]:
        st.write("### Elite 8")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("#### East Region")
            display_game_results(results['elite8']['east'])
        with col2:
            st.write("#### West Region")
            display_game_results(results['elite8']['west'])
        with col3:
            st.write("#### South Region")
            display_game_results(results['elite8']['south'])
        with col4:
            st.write("#### Midwest Region")
            display_game_results(results['elite8']['midwest'])
    
    # Final Four
    with tabs[4]:
        st.write("### Final Four")
        col1, col2 = st.columns(2)
        with col1:
            st.write("#### Semifinal 1")
            display_game_results([results['final4'][0]])
        with col2:
            st.write("#### Semifinal 2")
            display_game_results([results['final4'][1]])
    
    # Championship
    with tabs[5]:
        st.write("### Championship")
        st.write("#### National Championship Game")
        display_game_results(results['championship'])
        
        st.markdown(f"""
        <div style="text-align: center; margin-top: 20px; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            <h2>🏆 National Champion 🏆</h2>
            <h3 style="color: #28a745;">{results['champion'].name}</h3>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Python and Streamlit | Data from KenPom") 