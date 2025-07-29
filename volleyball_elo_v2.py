import streamlit as st
import pandas as pd
import numpy as np
import io

# ELO calculation functions
def calculate_expected_score(rating_a, rating_b):
    """Calculate expected score for team A against team B"""
    return 1 / (1 + 10**((rating_b - rating_a) / 400))

def calculate_team_rating(player_ratings):
    """Calculate average team rating from individual player ratings"""
    return sum(player_ratings) / len(player_ratings)

def update_elo_ratings(team_a_ratings, team_b_ratings, team_a_wins, k=32):
    """
    Update ELO ratings based on team match result
    team_a_ratings: list of ratings for team A players
    team_b_ratings: list of ratings for team B players
    team_a_wins: True if team A wins, False if team B wins
    """
    # Calculate team averages
    avg_rating_a = calculate_team_rating(team_a_ratings)
    avg_rating_b = calculate_team_rating(team_b_ratings)
    
    # Calculate expected scores
    expected_a = calculate_expected_score(avg_rating_a, avg_rating_b)
    
    # Determine actual score
    score_a = 1 if team_a_wins else 0
    
    # Calculate rating change
    rating_change = k * (score_a - expected_a)
    
    # Apply change to all players
    new_ratings_a = [round(rating + rating_change) for rating in team_a_ratings]
    new_ratings_b = [round(rating - rating_change) for rating in team_b_ratings]
    
    return new_ratings_a, new_ratings_b, round(rating_change)

def parse_team_string(team_str):
    """Parse team string like 'Alice,Bob,Charlie' into list of players"""
    return [player.strip() for player in team_str.split(',') if player.strip()]

# Initialize session state
if 'players' not in st.session_state:
    st.session_state.players = {}
if 'match_history' not in st.session_state:
    st.session_state.match_history = []
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

# Admin password (in production, use environment variable)
ADMIN_PASSWORD = st.secrets.get("admin_password", "volleyball2024")

st.title("🏐 Volleyball Team ELO Ladder")
st.markdown("Track ELO ratings for team-based volleyball matches!")

# Sidebar for current standings
with st.sidebar:
    st.header("🏆 Current Ladder")
    if st.session_state.players:
        # Sort players by ELO rating
        sorted_players = sorted(st.session_state.players.items(), key=lambda x: x[1], reverse=True)
        
        st.markdown("### Individual Rankings")
        for i, (player, rating) in enumerate(sorted_players, 1):
            if i <= 10:  # Show top 10 in sidebar
                if i == 1:
                    st.write(f"🥇 **{player}** - {rating}")
                elif i == 2:
                    st.write(f"🥈 **{player}** - {rating}")
                elif i == 3:
                    st.write(f"🥉 **{player}** - {rating}")
                else:
                    st.write(f"{i}. **{player}** - {rating}")
        
        if len(sorted_players) > 10:
            st.write(f"... and {len(sorted_players) - 10} more players")
        
        # Show total matches played
        st.markdown("---")
        st.write(f"**Total matches:** {len(st.session_state.match_history)}")
        st.write(f"**Active players:** {len(st.session_state.players)}")
        
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
            player_matches = []
            wins = 0
            
            for match in st.session_state.match_history:
                team_a_players = parse_team_string(match['Team_A'])
                team_b_players = parse_team_string(match['Team_B'])
                
                if player in team_a_players or player in team_b_players:
                    player_matches.append(match)
                    
                    # Check if player was on winning team
                    if ((player in team_a_players and match['Winner'] == 'Team_A') or 
                        (player in team_b_players and match['Winner'] == 'Team_B')):
                        wins += 1
            
            matches_played = len(player_matches)
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
        
        # Add download button for public standings
        csv_buffer = io.StringIO()
        standings_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Current Standings",
            data=csv_buffer.getvalue(),
            file_name="volleyball_standings.csv",
            mime="text/csv"
        )
        
    else:
        st.info("No players in the ladder yet. Check back after some matches are recorded!")

with tab2:
    st.header("Match Statistics & History")
    
    if st.session_state.match_history:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Matches", len(st.session_state.match_history))
        with col2:
            st.metric("Active Players", len(st.session_state.players))
        with col3:
            if st.session_state.players:
                highest_rated = max(st.session_state.players.items(), key=lambda x: x[1])
                st.metric("Top Player", f"{highest_rated[0]} ({highest_rated[1]})")
        
        # Team composition analysis
        st.subheader("Team Size Distribution")
        team_sizes = []
        for match in st.session_state.match_history:
            team_a_size = len(parse_team_string(match['Team_A']))
            team_b_size = len(parse_team_string(match['Team_B']))
            team_sizes.extend([team_a_size, team_b_size])
        
        if team_sizes:
            size_counts = pd.Series(team_sizes).value_counts().sort_index()
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Players per team:**")
                for size, count in size_counts.items():
                    st.write(f"{size} players: {count} teams")
        
        # Recent matches
        st.subheader("Recent Matches")
        recent_matches = st.session_state.match_history[-10:]
        
        for match in reversed(recent_matches):
            with st.container():
                st.markdown(f"**Match:** {match['Team_A']} vs {match['Team_B']}")
                
                col1, col2, col3 = st.columns([2, 1, 2])
                with col1:
                    st.write(f"**Team A:** {match['Team_A']}")
                    if 'Team_A_Rating_Change' in match:
                        change = match['Team_A_Rating_Change']
                        st.write(f"Rating change: {change:+d}")
                
                with col2:
                    winner_display = "Team A 🏐" if match['Winner'] == 'Team_A' else "Team B 🏐"
                    st.write(f"**Winner:** {winner_display}")
                
                with col3:
                    st.write(f"**Team B:** {match['Team_B']}")
                    if 'Team_B_Rating_Change' in match:
                        change = match['Team_B_Rating_Change']
                        st.write(f"Rating change: {change:+d}")
                
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
        
        # Manual match entry
        st.subheader("Quick Match Entry")
        with st.form("manual_match"):
            col1, col2 = st.columns(2)
            with col1:
                team_a = st.text_input("Team A Players (comma separated)", 
                                      placeholder="Alice,Bob,Charlie")
            with col2:
                team_b = st.text_input("Team B Players (comma separated)", 
                                      placeholder="David,Eve,Frank")
            
            winner = st.selectbox("Winner", ["Team A", "Team B"])
            
            if st.form_submit_button("Add Match"):
                if team_a and team_b:
                    team_a_players = parse_team_string(team_a)
                    team_b_players = parse_team_string(team_b)
                    
                    if len(team_a_players) == 0 or len(team_b_players) == 0:
                        st.error("Both teams must have at least one player")
                    else:
                        # Initialize new players
                        all_players = team_a_players + team_b_players
                        for player in all_players:
                            if player not in st.session_state.players:
                                st.session_state.players[player] = 1400
                        
                        # Get current ratings
                        team_a_ratings = [st.session_state.players[p] for p in team_a_players]
                        team_b_ratings = [st.session_state.players[p] for p in team_b_players]
                        
                        # Update ratings
                        team_a_wins = (winner == "Team A")
                        new_ratings_a, new_ratings_b, rating_change = update_elo_ratings(
                            team_a_ratings, team_b_ratings, team_a_wins
                        )
                        
                        # Apply new ratings
                        for i, player in enumerate(team_a_players):
                            st.session_state.players[player] = new_ratings_a[i]
                        for i, player in enumerate(team_b_players):
                            st.session_state.players[player] = new_ratings_b[i]
                        
                        # Record match
                        match_info = {
                            'Team_A': team_a,
                            'Team_B': team_b,
                            'Winner': 'Team_A' if team_a_wins else 'Team_B',
                            'Team_A_Rating_Change': rating_change if team_a_wins else -rating_change,
                            'Team_B_Rating_Change': -rating_change if team_a_wins else rating_change
                        }
                        st.session_state.match_history.append(match_info)
                        
                        st.success(f"Match added! Rating change: ±{abs(rating_change)}")
                        st.rerun()
                else:
                    st.error("Please enter players for both teams")
        
        st.markdown("---")
        
        # File uploader (for bulk upload)
        st.subheader("Bulk Upload Match Results")
        
        uploaded_file = st.file_uploader(
            "Choose a CSV file with columns: Team_A, Team_B, Winner",
            type="csv",
            help="Team_A and Team_B should contain comma-separated player names. Winner should be 'Team_A' or 'Team_B'"
        )
        
        # Show expected CSV format
        with st.expander("Expected CSV Format"):
            sample_data = pd.DataFrame({
                'Team_A': ['Alice,Bob', 'Charlie,David,Eve', 'Alice,Frank'],
                'Team_B': ['Charlie,David', 'Alice,Bob', 'Bob,Charlie,Eve'],
                'Winner': ['Team_A', 'Team_B', 'Team_B']
            })
            st.write("Example CSV format:")
            st.dataframe(sample_data)
            st.write("- **Team_A/Team_B**: Comma-separated player names")
            st.write("- **Winner**: Either 'Team_A' or 'Team_B'")
            st.write("- Teams can have different numbers of players")
        
        if uploaded_file is not None:
            try:
                # Read the CSV
                df = pd.read_csv(uploaded_file)
                
                # Validate columns
                required_columns = ['Team_A', 'Team_B', 'Winner']
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
                            team_a = str(row['Team_A']).strip()
                            team_b = str(row['Team_B']).strip()
                            winner = str(row['Winner']).strip()
                            
                            # Parse teams
                            team_a_players = parse_team_string(team_a)
                            team_b_players = parse_team_string(team_b)
                            
                            if len(team_a_players) == 0 or len(team_b_players) == 0:
                                st.warning(f"Skipping match with empty team: {team_a} vs {team_b}")
                                continue
                            
                            # Initialize new players (starting ELO: 1400)
                            all_players = team_a_players + team_b_players
                            for player in all_players:
                                if player not in st.session_state.players:
                                    st.session_state.players[player] = 1400
                            
                            # Get current ratings
                            team_a_ratings = [st.session_state.players[p] for p in team_a_players]
                            team_b_ratings = [st.session_state.players[p] for p in team_b_players]
                            
                            # Determine winner
                            if winner not in ['Team_A', 'Team_B']:
                                st.warning(f"Invalid winner '{winner}' for match {team_a} vs {team_b}. Skipping.")
                                continue
                            
                            team_a_wins = (winner == 'Team_A')
                            
                            # Update ELO ratings
                            new_ratings_a, new_ratings_b, rating_change = update_elo_ratings(
                                team_a_ratings, team_b_ratings, team_a_wins
                            )
                            
                            # Apply new ratings
                            for i, player in enumerate(team_a_players):
                                st.session_state.players[player] = new_ratings_a[i]
                            for i, player in enumerate(team_b_players):
                                st.session_state.players[player] = new_ratings_b[i]
                            
                            # Track match for history
                            match_info = {
                                'Team_A': team_a,
                                'Team_B': team_b,
                                'Winner': winner,
                                'Team_A_Rating_Change': rating_change if team_a_wins else -rating_change,
                                'Team_B_Rating_Change': -rating_change if team_a_wins else rating_change
                            }
                            processed_matches.append(match_info)
                            st.session_state.match_history.append(match_info)
                        
                        st.success(f"Processed {len(processed_matches)} matches successfully!")
                        
                        # Show summary of changes
                        if processed_matches:
                            st.subheader("Rating Changes Summary")
                            for match in processed_matches:
                                st.write(f"**{match['Team_A']}** vs **{match['Team_B']}** - Winner: {match['Winner']}")
                                st.write(f"Rating change: ±{abs(match['Team_A_Rating_Change'])}")
                        
                        # Refresh the app
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
            if st.session_state.match_history:
                # Export match history
                history_df = pd.DataFrame(st.session_state.match_history)
                csv_buffer = io.StringIO()
                history_df.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="📥 Download Match History",
                    data=csv_buffer.getvalue(),
                    file_name="volleyball_match_history.csv",
                    mime="text/csv"
                )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        🏐 Volleyball Team ELO Tracker | Built with Streamlit
    </div>
    """, 
    unsafe_allow_html=True
)

# Instructions (collapsed by default)
with st.expander("ℹ️ How the Team ELO System Works"):
    st.markdown("""
    **Team ELO Rating System:**
    - All players start at **1400 ELO rating**
    - K factor is set at 32
    - Team rating is calculated as the **average** of all players on the team
    - When teams play, the **expected outcome** is based on team rating difference
    - **All players** on the winning team gain the same number of points
    - **All players** on the losing team lose the same number of points
    - Rating changes are larger when the outcome is unexpected (upset wins)
    
    **Team Formation:**
    - Teams can have **different numbers of players** (2v2, 3v3, 2v3, etc.)
    - Players can form different team combinations across matches
    - The system tracks individual ratings regardless of team compositions
    
    **For Admins:**
    - **Quick Entry**: Add single matches using the form
    - **Bulk Upload**: Use CSV for multiple matches
    - CSV format: `Team_A`, `Team_B`, `Winner`
    - Team columns should contain comma-separated player names
    - Winner should be either 'Team_A' or 'Team_B'
    
    **Examples:**
    - Team_A: "Alice,Bob,Charlie" (3 players)
    - Team_B: "David,Eve" (2 players)  
    - Winner: "Team_A"
    
    This creates a 3v2 match where Team A (Alice, Bob, Charlie) beats Team B (David, Eve).
    """)