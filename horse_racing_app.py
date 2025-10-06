import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="🐎 KimiK2 Horse Racing Predictor",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #1f4788;
    text-align: center;
    margin-bottom: 2rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}
.sub-header {
    font-size: 1.5rem;
    color: #4a90e2;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

class HorseRacingPredictor:
    def __init__(self):
        self.weights = {
            'speed_figure': 0.25,
            'recent_form': 0.20,
            'class_level': 0.15,
            'jockey_skill': 0.12,
            'trainer_stats': 0.12,
            'post_position': 0.08,
            'track_condition': 0.05,
            'distance_fitness': 0.03
        }
        
        self.track_variants = {
            'fast': 1.0, 'good': 1.02, 'sloppy': 1.05, 
            'muddy': 1.08, 'turf_firm': 0.98, 'turf_good': 1.0
        }
        
        self.post_position_weights = {
            1: 0.85, 2: 0.90, 3: 0.92, 4: 0.95, 5: 0.97,
            6: 1.0, 7: 0.98, 8: 0.95, 9: 0.92, 10: 0.90,
            11: 0.85, 12: 0.80, 13: 0.75, 14: 0.70, 15: 0.65
        }

    def calculate_speed_score(self, horse_data):
        base_speed = horse_data.get('beyer_speed_figure', 70)
        track_adj = self.track_variants.get(horse_data.get('track_condition', 'fast'), 1.0)
        distance = horse_data.get('race_distance', 6.0)
        distance_factor = 1.0 if distance <= 6.5 else 0.95
        
        recent_speeds = horse_data.get('recent_beyer_figures', [base_speed])
        trend_factor = 1.0
        if len(recent_speeds) >= 3:
            trend = (recent_speeds[-1] - recent_speeds[-3]) / recent_speeds[-3]
            trend_factor = 1.0 + (trend * 0.5)
        
        adjusted_speed = base_speed * track_adj * distance_factor * trend_factor
        return min(adjusted_speed, 120)

    def calculate_form_score(self, horse_data):
        recent_finishes = horse_data.get('recent_finishes', [5, 5, 5])
        total_races = len(recent_finishes)
        
        if total_races == 0:
            return 0.5
            
        weighted_sum = 0
        total_weight = 0
        
        for i, finish in enumerate(reversed(recent_finishes)):
            weight = (i + 1) / total_races
            position_score = max(0, (10 - finish) / 10)
            weighted_sum += position_score * weight
            total_weight += weight
            
        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def calculate_class_score(self, horse_data):
        current_class = horse_data.get('race_class', 'claiming')
        horse_class = horse_data.get('horse_class', 'claiming')
        
        class_hierarchy = {
            'maiden': 1, 'claiming': 2, 'allowance': 3, 
            'stakes': 4, 'graded_stakes': 5, 'grade_1': 6
        }
        
        race_level = class_hierarchy.get(current_class, 2)
        horse_level = class_hierarchy.get(horse_class, 2)
        
        if horse_level > race_level:
            return 1.2
        elif horse_level == race_level:
            return 1.0
        else:
            return 0.8

    def calculate_connection_score(self, horse_data):
        jockey_win_pct = horse_data.get('jockey_win_percentage', 0.10)
        trainer_win_pct = horse_data.get('trainer_win_percentage', 0.12)
        
        jockey_score = min(jockey_win_pct / 0.25, 1.0)
        trainer_score = min(trainer_win_pct / 0.25, 1.0)
        
        combo_success = horse_data.get('jockey_trainer_combo_win_pct', 0.10)
        combo_bonus = min(combo_success / 0.30, 0.2)
        
        return jockey_score + (combo_bonus * 0.5), trainer_score + (combo_bonus * 0.5)

    def calculate_post_position_score(self, horse_data):
        post = horse_data.get('post_position', 5)
        field_size = horse_data.get('field_size', 10)
        
        if field_size <= 6:
            return 1.0
        elif field_size <= 10:
            return self.post_position_weights.get(post, 0.90)
        else:
            large_field_weights = {i: max(0.5, 1.0 - (i-6)*0.05) for i in range(1, 21)}
            return large_field_weights.get(post, 0.60)

    def calculate_overall_score(self, horse_data):
        speed_score = self.calculate_speed_score(horse_data)
        form_score = self.calculate_form_score(horse_data)
        class_score = self.calculate_class_score(horse_data)
        jockey_score, trainer_score = self.calculate_connection_score(horse_data)
        post_score = self.calculate_post_position_score(horse_data)
        
        total_score = (
            speed_score * self.weights['speed_figure'] +
            form_score * 100 * self.weights['recent_form'] +
            class_score * 100 * self.weights['class_level'] +
            jockey_score * 100 * self.weights['jockey_skill'] +
            trainer_score * 100 * self.weights['trainer_stats'] +
            post_score * 100 * self.weights['post_position']
        )
        
        return total_score

    def predict_race(self, horses_data):
        results = []
        
        for horse in horses_data:
            score = self.calculate_overall_score(horse)
            probability = self.score_to_probability(score, horses_data)
            
            results.append({
                'Horse': horse.get('name', 'Unknown'),
                'Score': round(score, 2),
                'Win_Probability': round(probability * 100, 1),
                'Beyer_Figure': round(self.calculate_speed_score(horse), 1),
                'Form_Score': round(self.calculate_form_score(horse), 3),
                'Class_Score': round(self.calculate_class_score(horse), 3),
                'Jockey_Score': round(self.calculate_connection_score(horse)[0], 3),
                'Trainer_Score': round(self.calculate_connection_score(horse)[1], 3),
                'Post_Advantage': round(self.calculate_post_position_score(horse), 3)
            })
        
        results_df = pd.DataFrame(results).sort_values('Score', ascending=False)
        
        total_prob = results_df['Win_Probability'].sum()
        if total_prob > 0:
            results_df['Win_Probability'] = (results_df['Win_Probability'] / total_prob * 100).round(1)
        
        return results_df

    def score_to_probability(self, score, all_horses):
        all_scores = [self.calculate_overall_score(horse) for horse in all_horses]
        exp_scores = [np.exp(s / 10) for s in all_scores]
        exp_score = np.exp(score / 10)
        return exp_score / sum(exp_scores)

def main():
    st.markdown('<h1 class="main-header">🏇 KimiK2 Horse Racing Predictor</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">AI-Powered Race Analysis & Predictions</h2>', unsafe_allow_html=True)

    # Initialize session state
    if 'horses' not in st.session_state:
        st.session_state.horses = []

    # Sidebar for race setup
    with st.sidebar:
        st.header("🎯 Race Setup")
        
        race_name = st.text_input("Race Name", "KimiK2 Challenge Stakes")
        track_name = st.text_input("Track Name", "Virtual Downs")
        distance = st.number_input("Distance (furlongs)", 6.0, 12.0, 8.5, 0.5)
        surface = st.selectbox("Surface", ["Dirt", "Turf", "All-Weather"])
        track_condition = st.selectbox("Track Condition", 
                                     ["Fast", "Good", "Sloppy", "Muddy", "Turf-Firm", "Turf-Good"])
        field_size = st.number_input("Field Size", 4, 16, 8)

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("🐎 Horse Information")
        
        with st.expander("➕ Add Horse", expanded=True):
            horse_name = st.text_input("Horse Name", key="horse_name")
            
            col_h1, col_h2, col_h3 = st.columns(3)
            
            with col_h1:
                beyer_figure = st.number_input("Beyer Speed Figure", 50, 120, 85, key="beyer")
                recent_beyer = st.text_input("Recent Beyer Figures", "82,84,85", key="recent_beyer")
                recent_finishes = st.text_input("Recent Finishes", "2,1,3", key="recent_finishes")
            
            with col_h2:
                race_class = st.selectbox("Race Class", ["Maiden", "Claiming", "Allowance", "Stakes", "Graded Stakes"], key="race_class")
                horse_class = st.selectbox("Horse Class", ["Maiden", "Claiming", "Allowance", "Stakes", "Graded Stakes"], key="horse_class")
                post_position = st.number_input("Post Position", 1, field_size, 1, key="post_position")
            
            with col_h3:
                jockey_win_pct = st.number_input("Jockey Win %", 0.0, 50.0, 12.0, 0.1, key="jockey_pct") / 100
                trainer_win_pct = st.number_input("Trainer Win %", 0.0, 50.0, 15.0, 0.1, key="trainer_pct") / 100
                combo_win_pct = st.number_input("Jockey-Trainer Combo Win %", 0.0, 100.0, 20.0, 0.1, key="combo_pct") / 100

            if st.button("🐎 Add Horse to Race"):
                try:
                    recent_beyer_list = [int(x.strip()) for x in recent_beyer.split(',')]
                    recent_finishes_list = [int(x.strip()) for x in recent_finishes.split(',')]
                    
                    horse_data = {
                        'name': horse_name,
                        'beyer_speed_figure': beyer_figure,
                        'recent_beyer_figures': recent_beyer_list,
                        'recent_finishes': recent_finishes_list,
                        'race_class': race_class.lower().replace(' ', '_'),
                        'horse_class': horse_class.lower().replace(' ', '_'),
                        'jockey_win_percentage': jockey_win_pct,
                        'trainer_win_percentage': trainer_win_pct,
                        'jockey_trainer_combo_win_pct': combo_win_pct,
                        'post_position': post_position,
                        'field_size': field_size,
                        'race_distance': distance,
                        'track_condition': track_condition.lower().replace('-', '_')
                    }
                    
                    st.session_state.horses.append(horse_data)
                    st.success(f"✅ Added {horse_name} to the race!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error adding horse: {str(e)}")

    with col2:
        st.header("📊 Race Summary")
        
        if st.session_state.horses:
            st.metric("Horses Entered", len(st.session_state.horses))
            st.metric("Field Size", field_size)
            
            st.subheader("🐎 Current Entries:")
            for i, horse in enumerate(st.session_state.horses, 1):
                st.write(f"{i}. {horse['name']}")
        else:
            st.info("👆 Add horses using the form above")

    # Prediction section
    if st.session_state.horses and len(st.session_state.horses) >= 2:
        st.header("🔮 AI Predictions")
        
        predictor = HorseRacingPredictor()
        predictions = predictor.predict_race(st.session_state.horses)
        
        # Display top 5
        st.subheader("🏆 Top 5 Predictions")
        
        col_pred1, col_pred2 = st.columns([1, 1])
        
        with col_pred1:
            st.dataframe(predictions.head(5)[['Horse', 'Win_Probability', 'Score', 'Beyer_Figure']])
        
        with col_pred2:
            fig = go.Figure(data=[
                go.Bar(x=predictions.head(5)['Horse'], 
                      y=predictions.head(5)['Win_Probability'],
                      marker_color=['gold', 'silver', '#CD7F32', 'lightblue', 'lightgreen'])
            ])
            fig.update_layout(
                title="Win Probabilities (%)",
                xaxis_title="Horse",
                yaxis_title="Win Probability (%)",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed analysis
        with st.expander("📈 Detailed Analysis"):
            for idx, (_, horse) in enumerate(predictions.head(5).iterrows(), 1):
                st.subheader(f"{idx}. {horse['Horse']} ({horse['Win_Probability']}% win probability)")
                
                col_det1, col_det2 = st.columns(2)
                
                with col_det1:
                    st.write("**Speed & Performance:**")
                    st.write(f"• Beyer Figure: {horse['Beyer_Figure']:.1f}")
                    st.write(f"• Recent Form: {horse['Form_Score']:.3f}")
                    st.write(f"• Class Score: {horse['Class_Score']:.3f}")
                
                with col_det2:
                    st.write("**Connections & Setup:**")
                    st.write(f"• Jockey Score: {horse['Jockey_Score']:.3f}")
                    st.write(f"• Trainer Score: {horse['Trainer_Score']:.3f}")
                    st.write(f"• Post Advantage: {horse['Post_Advantage']:.3f}")
        
        # Betting recommendations
        st.header("💰 Betting Strategy")
        
        col_bet1, col_bet2, col_bet3 = st.columns(3)
        
        with col_bet1:
            st.metric("Favorite", predictions.iloc[0]['Horse'], 
                     f"{predictions.iloc[0]['Win_Probability']}%")
        
        with col_bet2:
            best_value = predictions.iloc[1] if len(predictions) > 1 else predictions.iloc[0]
            st.metric("Value Play", best_value['Horse'], 
                     f"{best_value['Win_Probability']}%")
        
        with col_bet3:
            longshot = predictions.iloc[-1] if len(predictions) >= 3 else predictions.iloc[0]
            st.metric("Longshot", longshot['Horse'], 
                     f"{longshot['Win_Probability']}%")
        
        # Export functionality
        st.header("📁 Export Results")
        csv = predictions.to_csv(index=False)
        st.download_button(
            label="📊 Download Predictions CSV",
            data=csv,
            file_name=f"horse_racing_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Clear button
        if st.button("🗑️ Clear All Horses"):
            st.session_state.horses = []
            st.rerun()
        
    elif len(st.session_state.horses) < 2 and len(st.session_state.horses) > 0:
        st.info("🐎 Add at least 2 horses to generate predictions")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🏇 Powered by KimiK2 AI Horse Racing Analysis System</p>
        <p>Remember: This is for entertainment purposes. Always gamble responsibly.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
