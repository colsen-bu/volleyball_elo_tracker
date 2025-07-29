import streamlit as st
import pandas as pd
import numpy as np
import io

# ELO calculation functions
def calculate_expected_score(rating_a, rating_b):
    """Calculate expected score for player A against player B"""
    return 1 / (1 + 10**((rating_b - rating_a) / 400))

def update_elo_ratings(rating_a, rating_b, score_a, k=32):
    """
    Update ELO ratings based on match result
    score_a: 1 if player A wins, 0 if player A loses, 0.5 for draw
    """
    expected_a = calculate_expected_score(rating_a, rating_b)
    expected_b = 1 - expected_a
    
    new_rating_a = rating_a + k * (score_a - expected_a)
    new_rating_b = rating_b + k * ((1 - score_a) - expected_b)
    
    return round(new_rating_a), round(new_rating_b)

# Initialize session state
if 'players' not in st.session_state:
    st.session_state.players = {}
if 'match_history' not in st.session_state:
    st.session_state.match_history = []
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

# Admin password (in production, use environment variable)
ADMIN_PASSWORD = st.secrets.get("admin_password", "volleyball2024")

st.title("🏐 Volleyball ELO Ladder Tracker")
st.markdown("Track ELO ratings for our volleyball nights!")

# Sidebar for current standings
with st.sidebar:
    st.header("🏆 Current Ladder")
    if st.session_state.players:
        # Sort players by ELO rating
        sorted_players = sorted(st.session_state.players.items(), key=lambda x: x[1], reverse=True)
        
        st.markdown("### Rankings")
        for i, (player, rating) in enumerate(sorted_players, 1):
            if i == 1:
                st.write(f"🥇 **{player}** - {rating}")
            elif i == 2:
                st.write(f"🥈 **{player}** - {rating}")
            elif i == 3:
                st.write(f"🥉 **{player}** - {rating}")
            else:
                st.write(f"{i}. **{player}** - {rating}")
        
        # Show total matches played
        st.markdown("---")
        st.write(f"**Total matches:** {len(st.session_state.match_history)}")
        
    else:
        st.info("No matches recorded yet!")

# Main content tabs
tab1, tab2, tab3 = st.tabs(["🏐 Ladder", "📊 Stats", "⚙️ Admin"])

with tab1:
    st.header("Current Standings")
    
    if st.session_state.players:
        # Create a nice standings table
        standings_data = []
        sorted_players = sorted(st.session_state.players.items(), key=lambda x: x[1], reverse=True)
        
        for i, (player, rating) in enumerate(sorted_players, 1):
            # Calculate matches played and win rate
            player_matches = [m for m in st.session_state.match_history 
                            if m['Player1'] == player or m['Player2'] == player]
            matches_played = len(player_matches)
            wins = len([m for m in player_matches if m['Winner'] == player])
            win_rate = (wins / matches_played * 100) if matches_played > 0 else 0
            
            standings_data.append({
                'Rank': i,
                'Player': player,
                'ELO Rating': rating,
                'Matches': matches_played,
                'Wins': wins,
                'Win Rate %': f"{win_rate:.1f}%"
            })
        
        standings_df = pd.DataFrame(standings_data)
        st.dataframe(standings_df, use_container_width=True, hide_index=True)
        
    else:
        st.info("No players in the ladder yet. Check back after some matches are recorded!")

with tab2:
    st.header("Match Statistics")
    
    if st.session_state.match_history:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Matches", len(st.session_state.match_history))
            st.metric("Active Players", len(st.session_state.players))
        
        with col2:
            if st.session_state.players:
                highest_rated = max(st.session_state.players.items(), key=lambda x: x[1])
                st.metric("Highest Rated", f"{highest_rated[0]} ({highest_rated[1]})")
        
        # Recent matches
        st.subheader("Recent Matches")
        recent_matches = st.session_state.match_history[-10:]
        
        for match in reversed(recent_matches):
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 2])
                with col1:
                    st.write(f"**{match['Player1']}**")
                    st.write(f"Rating: {match['Player1_Before']} → {match['Player1_After']} ({match['Player1_Change']:+d})")
                with col2:
                    st.write("**VS**")
                    winner_emoji = "🏐" if match['Winner'] == match['Player1'] else ""
                    st.write(winner_emoji)
                with col3:
                    st.write(f"**{match['Player2']}**")
                    st.write(f"Rating: {match['Player2_Before']} → {match['Player2_After']} ({match['Player2_Change']:+d})")
                st.markdown("---")
    else:
        st.info("No match history available yet.")

with tab3:
    st.header("Admin Panel")
    
    # Authentication
    if not st.session_state.admin_authenticated:
        st.warning("🔒 Admin access required to update match results")
        password = st.text_input("Enter admin password:", type="password")
        if st.button("Login"):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("✅ Admin access granted!")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    else:
        st.success("✅ Admin access active")
        
        if st.button("Logout", type="secondary"):
            st.session_state.admin_authenticated = False
            st.rerun()
        
        st.markdown("---")
        
        # File uploader (only for admin)
        st.subheader("Upload Match Results")
        
        uploaded_file = st.file_uploader(
            "Choose a CSV file with columns: Player1, Player2, Result",
            type="csv",
            help="Result should be '1' if Player1 wins, '2' if Player2 wins"
        )
        
        # Show expected CSV format
        with st.expander("Expected CSV Format"):
            sample_data = pd.DataFrame({
                'Player1': ['Alice', 'Bob', 'Charlie'],
                'Player2': ['Bob', 'Charlie', 'Alice'],
                'Result': ['1', '2', '1']
            })
            st.write("Example CSV format:")
            st.dataframe(sample_data)
            st.write("- **Result '1'**: Player1 wins")
            st.write("- **Result '2'**: Player2 wins")
        
        if uploaded_file is not None:
            try:
                # Read the CSV
                df = pd.read_csv(uploaded_file)
                
                # Validate columns
                required_columns = ['Player1', 'Player2', 'Result']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"CSV must contain columns: {required_columns}")
                else:
                    st.success(f"Loaded {len(df)} matches from CSV")
                    
                    # Show preview
                    st.subheader("Match Results Preview")
                    st.dataframe(df)
                    
                    # Process matches button
                    if st.button("Process Matches and Update ELO"):
                        processed_matches = []
                        
                        for _, row in df.iterrows():
                            player1 = str(row['Player1']).strip()
                            player2 = str(row['Player2']).strip()
                            result = str(row['Result']).strip()
                            
                            # Initialize players if new (starting ELO: 1400)
                            if player1 not in st.session_state.players:
                                st.session_state.players[player1] = 1400
                            if player2 not in st.session_state.players:
                                st.session_state.players[player2] = 1400
                            
                            # Get current ratings
                            rating1_before = st.session_state.players[player1]
                            rating2_before = st.session_state.players[player2]
                            
                            # Determine match outcome (score_a for player1)
                            if result == '1':
                                score_a = 1  # Player1 wins
                                winner = player1
                            elif result == '2':
                                score_a = 0  # Player2 wins
                                winner = player2
                            else:
                                st.warning(f"Invalid result '{result}' for match {player1} vs {player2}. Skipping.")
                                continue
                            
                            # Update ELO ratings
                            new_rating1, new_rating2 = update_elo_ratings(rating1_before, rating2_before, score_a)
                            
                            # Store updated ratings
                            st.session_state.players[player1] = new_rating1
                            st.session_state.players[player2] = new_rating2
                            
                            # Track match for history
                            match_info = {
                                'Player1': player1,
                                'Player2': player2,
                                'Winner': winner,
                                'Player1_Before': rating1_before,
                                'Player2_Before': rating2_before,
                                'Player1_After': new_rating1,
                                'Player2_After': new_rating2,
                                'Player1_Change': new_rating1 - rating1_before,
                                'Player2_Change': new_rating2 - rating2_before
                            }
                            processed_matches.append(match_info)
                            st.session_state.match_history.append(match_info)
                        
                        st.success(f"Processed {len(processed_matches)} matches successfully!")
                        
                        # Show rating changes
                        if processed_matches:
                            st.subheader("Rating Changes")
                            changes_df = pd.DataFrame(processed_matches)
                            st.dataframe(changes_df)
                        
                        # Refresh the sidebar by rerunning
                        st.rerun()
            
            except Exception as e:
                st.error(f"Error processing CSV: {str(e)}")
        
        # Management section
        st.markdown("---")
        st.subheader("Data Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Reset All Data", type="secondary"):
                if st.checkbox("I understand this will delete all data"):
                    st.session_state.players = {}
                    st.session_state.match_history = []
                    st.success("All data has been reset!")
                    st.rerun()
        
        with col2:
            if st.session_state.players:
                # Export current standings
                standings_df = pd.DataFrame([
                    {'Player': player, 'ELO_Rating': rating} 
                    for player, rating in sorted(st.session_state.players.items(), key=lambda x: x[1], reverse=True)
                ])
                
                csv_buffer = io.StringIO()
                standings_df.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="📥 Download Standings",
                    data=csv_buffer.getvalue(),
                    file_name="volleyball_standings.csv",
                    mime="text/csv"
                )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        🏐 Volleyball ELO Tracker | Built with Streamlit
    </div>
    """, 
    unsafe_allow_html=True
)

# Instructions (collapsed by default)
with st.expander("ℹ️ How the ELO System Works"):
    st.markdown("""
    **ELO Rating System:**
    - All players start at **1400 ELO rating**
    - K-factor is set to **32**
    - When a higher-rated player loses to a lower-rated player, they lose more points
    - When a lower-rated player beats a higher-rated player, they gain more points
    - The system automatically balances over time to reflect true skill levels
    
    **For Admins:**
    1. Prepare a CSV file with columns: `Player1`, `Player2`, `Result`
    2. Use '1' if Player1 wins, '2' if Player2 wins
    3. Upload via the Admin tab (password required)
    4. All ratings update automatically
    
    **For Players:**
    - View current standings in the Ladder tab
    - Check your stats and recent matches in the Stats tab
    - The sidebar always shows live rankings
    """)