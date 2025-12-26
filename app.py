import streamlit as st
import database_gsheets as database
import pandas as pd
from datetime import datetime
import time

# Page Config
st.set_page_config(page_title="WLog", page_icon="🏋️", layout="wide")

# Initialize DB
database.init_db()

# Session State
if 'workout_log' not in st.session_state:
    st.session_state.workout_log = []
if 'current_session_name' not in st.session_state:
    st.session_state.current_session_name = None
if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = None

def main():
    st.sidebar.title("WLog 🏋️")
    menu = ["Dashboard", "Log Workout", "Routines", "Exercise Library", "History"]
    choice = st.sidebar.radio("Navigate", menu)

    if choice == "Dashboard":
        show_dashboard()
    elif choice == "Log Workout":
        show_log_workout()
    elif choice == "Routines":
        show_routines()
    elif choice == "Exercise Library":
        show_library()
    elif choice == "History":
        show_history()

def show_dashboard():
    st.title("Dashboard")
    streak = database.get_streak()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Current Streak 🔥", value=f"{streak} Days")
    
    last_wo = database.get_last_workout_summary()
    if last_wo:
        with col2:
            st.metric(label="Last Workout Volume", value=f"{last_wo['volume']:,.0f} kg")
            st.caption(f"Date: {last_wo['date']}")

def show_routines():
    st.title("Custom Routines")
    
    # Initialize Edit State
    if "edit_routine_id" not in st.session_state:
        st.session_state.edit_routine_id = None
        
    # Check for empty DB
    sessions = database.get_all_sessions()
    if not sessions:
        st.warning("No routines found.")
        if st.button("📥 Initialize Heart & Hustle Schedule"):
            with st.spinner("Initializing Database..."):
                database.create_default_schedule()
            st.success("Schedule Created!")
            time.sleep(1)
            st.rerun()

    # --- Edit Mode ---
    if st.session_state.edit_routine_id:
        st.subheader("Edit Routine")
        
        # Fetch current routine data to prepopulate
        s_id = st.session_state.edit_routine_id
        sessions = database.get_all_sessions()
        target_session = next((s for s in sessions if s['id'] == s_id), None)
        
        if not target_session:
            st.error("Routine not found.")
            st.session_state.edit_routine_id = None
            if st.button("Back"):
                st.rerun()
            return

        # Edit Form
        new_name = st.text_input("Routine Name", value=target_session['name'])
        
        # Pre-select existing exercises
        current_details = database.get_session_details(s_id)
        current_ex_ids = [d['id'] for d in current_details]
        
        all_ex = database.get_all_exercises()
        options = {f"{e['muscle']} - {e['name']}": e['id'] for e in all_ex}
        sorted_opts = sorted(options.keys())
        
        # Map IDs back to Option Strings for default value
        id_to_opt = {v: k for k, v in options.items()}
        defaults = [id_to_opt[eid] for eid in current_ex_ids if eid in id_to_opt]
        
        selected_ex = st.multiselect("Select Exercises", sorted_opts, default=defaults)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("💾 Save Changes", type="primary"):
                if new_name and selected_ex:
                    ids = [options[s] for s in selected_ex]
                    database.update_session_by_id(s_id, new_name, ids)
                    st.success(f"Routine '{new_name}' Updated!")
                    st.session_state.edit_routine_id = None
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Name and Exercises required")
                    
        with c2:
            if st.button("Cancel"):
                st.session_state.edit_routine_id = None
                st.rerun()

    else:
        # --- Create / View Mode ---
        with st.expander("Create New Routine", expanded=False):
            r_name = st.text_input("Routine Name (e.g., Upper Body)")
            
            all_ex = database.get_all_exercises()
            options = {f"{e['muscle']} - {e['name']}": e['id'] for e in all_ex}
            sorted_opts = sorted(options.keys())
            
            selected_ex = st.multiselect("Select Exercises", sorted_opts)
            
            if st.button("Save Routine"):
                if r_name and selected_ex:
                    ids = [options[s] for s in selected_ex]
                    database.create_session(r_name, ids)
                    st.success(f"Routine '{r_name}' Created!")
                    st.rerun()
                else:
                    st.error("Name and Exercises required")
        
        st.divider()
        st.subheader("Your Routines")
        sessions = database.get_all_sessions()
        
        if not sessions:
            st.info("No routines created yet.")
            
        for s in sessions:
            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                with st.expander(s['name']):
                    details = database.get_session_details(s['id'])
                    for d in details:
                        st.text(f"• {d['name']} ({d['muscle']})")
            
            # Edit Button
            with c2:
                if st.button("✏️", key=f"edit_sess_{s['id']}", help="Edit Routine"):
                    st.session_state.edit_routine_id = s['id']
                    st.rerun()
            
            # Delete Button
            with c3:
                confirm_key = f"confirm_del_sess_{s['id']}"
                if st.session_state.get(confirm_key):
                    st.warning("Delete?")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("✅", key=f"yes_sess_{s['id']}", help="Confirm"):
                        database.delete_session(s['id'])
                        st.success(f"Deleted")
                        del st.session_state[confirm_key]
                        time.sleep(0.5)
                        st.rerun()
                    if col_no.button("❌", key=f"no_sess_{s['id']}", help="Cancel"):
                        del st.session_state[confirm_key]
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"del_sess_{s['id']}", help=f"Delete {s['name']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()

def show_log_workout():
    st.title("Log Workout")
    
    # Routine Selector / Start Logic
    if not st.session_state.workout_log and not st.session_state.session_start_time:
        st.subheader("Start Session")
        sessions = database.get_all_sessions()
        session_opts = ["New Workout"] + [s['name'] for s in sessions]
        
        selected_session = st.selectbox("Choose Routine or start a New Workout", session_opts)
        
        if st.button("Start Workout ⏱️"):
            st.session_state.session_start_time = datetime.now()
            st.session_state.current_session_name = None if selected_session == "New Workout" else selected_session
            
            if selected_session != "New Workout":
                # Pre-fill
                s_id = next(s['id'] for s in sessions if s['name'] == selected_session)
                details = database.get_session_details(s_id)
                for d in details:
                    last = database.get_last_performance(d['id'])
                    st.session_state.workout_log.append({
                        "id": d['id'],
                        "name": d['name'],
                        "muscle": d['muscle'],
                        "weight": last['weight'] if last else 0.0,
                        "reps": last['reps'] if last else 0,
                        "last_perf": f"{last['weight']}kg x {last['reps']} ({last['date']})" if last else "New",
                        "is_session_item": True
                    })
            st.rerun()

    # If session is active (either logs exist OR start time is set)
    if st.session_state.session_start_time:
        import streamlit.components.v1 as components
        
        # Header with Timer (JS based for live updates)
        c1, c2 = st.columns([3, 1])
        c1.subheader(f"Current Session: {st.session_state.current_session_name or 'Freestyle'}")
        
        # Pass start time as timestamp for JS
        start_ts = st.session_state.session_start_time.timestamp() * 1000
        
        timer_html = f"""
        <div style="text-align: center;">
            <div style="font-size: 14px; color: #555; margin-bottom: 4px;">Time Elapsed</div>
            <div id="timer" style="font-size: 24px; font-weight: bold; font-family: monospace; color: #111;">00:00:00</div>
        </div>
        <script>
        function updateTimer() {{
            const start = {start_ts};
            const now = new Date().getTime();
            const diff = Math.floor((now - start) / 1000);
            
            if (diff < 0) return; // Prevent negative on weird sync
            
            const h = Math.floor(diff / 3600);
            const m = Math.floor((diff % 3600) / 60);
            const s = diff % 60;
            
            document.getElementById("timer").innerHTML = 
                (h < 10 ? "0" + h : h) + ":" + 
                (m < 10 ? "0" + m : m) + ":" + 
                (s < 10 ? "0" + s : s);
        }}
        setInterval(updateTimer, 1000);
        updateTimer();
        </script>
        """
        
        with c2:
            components.html(timer_html, height=80)
        
        # Main Logger Interface
        current_session = st.session_state.current_session_name
        exercises = database.get_all_exercises()
        all_ex_map = {f"{e['muscle']} - {e['name']}": e for e in exercises}
        
        options = []
        session_ex_ids = []
        if current_session:
            s_id = database.get_session_by_name(current_session)
            if s_id:
                session_details = database.get_session_details(s_id)
                session_ex_ids = [d['id'] for d in session_details]
                session_options = [k for k, v in all_ex_map.items() if v['id'] in session_ex_ids]
                session_options.sort()
                options = session_options + ["---", "➕ Add from Database", "✨ Create New Exercise"]
        else:
            options = sorted(list(all_ex_map.keys())) + ["---", "✨ Create New Exercise"]
        
        st.divider()
        with st.container():
            st.write("### Add Set")
            selected_option = st.selectbox("Select Exercise", options)
            target_exercise = None
            
            if selected_option == "---":
                st.info("Select an option above.")
            elif selected_option == "➕ Add from Database":
                all_opts = sorted(list(all_ex_map.keys()))
                full_select = st.selectbox("Search All Exercises", all_opts)
                target_exercise = all_ex_map[full_select]
            elif selected_option == "✨ Create New Exercise":
                with st.expander("New Exercise Details", expanded=True):
                    c_name = st.text_input("Name")
                    c_muscle = st.selectbox("Muscle", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Cardio", "Other"])
                    c_cat = st.selectbox("Category", ["Strength", "Hypertrophy", "Endurance", "Mobility", "Cardio", "Custom"])
                    if st.button("Create & Use"):
                        if c_name:
                            try:
                                database.add_custom_exercise(c_name, c_muscle, category=c_cat)
                                st.success(f"Created {c_name}!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
            else:
                target_exercise = all_ex_map[selected_option]

            if target_exercise:
                # Show Info Box for Instructions
                if target_exercise.get('instructions'):
                    st.info(f"ℹ️ **{target_exercise['name']}**: {target_exercise['instructions']}")
                
                last = database.get_last_performance(target_exercise['id'])
                if last:
                    st.caption(f"Last Log: {last['weight']}kg x {last['reps']} ({last['date']})")
                col_w, col_r, col_btn = st.columns([1, 1, 1])
                with col_w:
                    weight = st.number_input("Kg", min_value=0.0, step=1.25, key="w_input")
                with col_r:
                    reps = st.number_input("Reps", min_value=0, step=1, value=0, key="r_input")
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("Add Set", type="primary"):
                        if reps > 0:
                            st.session_state.workout_log.append({
                                "id": target_exercise['id'],
                                "name": target_exercise['name'],
                                "muscle": target_exercise['muscle'],
                                "weight": weight,
                                "reps": reps,
                                "last_perf": f"{last['weight']}kg x {last['reps']}" if last else "New"
                            })
                            st.success(f"Added {target_exercise['name']}")
                            st.rerun()
                        else:
                            st.error("Reps > 0 required")

        # View/Edit Log
        if st.session_state.workout_log:
            display_data = []
            unique_logged_ids = set()
            for l in st.session_state.workout_log:
                unique_logged_ids.add(l['id'])
                display_data.append({
                    "Exercise": l['name'],
                    "Weight": l['weight'],
                    "Reps": l['reps'],
                    "Last": l.get('last_perf', '-')
                })
            
            st.dataframe(display_data, width='stretch')
            
            # Check for Routine Update
            update_routine = False
            if current_session and session_ex_ids:
                new_ids = [ids for ids in unique_logged_ids if ids not in session_ex_ids]
                if new_ids:
                    st.info(f"You added {len(new_ids)} new exercise(s) to this session.")
                    update_routine = st.checkbox(f"Update '{current_session}' to include these new exercises?", value=True)
            
            cols = st.columns(3)
            if cols[1].button("Finish & Save", type="primary", width='stretch'):
                save_routine(update_session_bool=update_routine)
                
            if cols[2].button("Cancel & Clear"):
                st.session_state.workout_log = []
                st.session_state.current_session_name = None
                st.session_state.session_start_time = None
                st.rerun()
        else:
            if st.button("Cancel Session"):
                st.session_state.session_start_time = None
                st.session_state.current_session_name = None
                st.rerun()

def save_routine(update_session_bool=False):
    logs = st.session_state.workout_log
    s_name = st.session_state.get('current_session_name')
    start = st.session_state.get('session_start_time')
    
    if not logs:
        return
        
    duration = 0
    if start:
        delta = datetime.now() - start
        duration = int(delta.total_seconds() / 60)
    
    total_vol = sum(l['weight'] * l['reps'] for l in logs)
    
    w_id = database.create_workout(total_vol, session_name=s_name, duration_minutes=duration)
    
    logged_ex_ids = []
    seen = set()
    for idx, item in enumerate(logs):
        database.log_set(w_id, item['id'], item['weight'], item['reps'], idx)
        if item['id'] not in seen:
            logged_ex_ids.append(item['id'])
            seen.add(item['id'])
            
    if update_session_bool and s_name:
        database.update_session(s_name, logged_ex_ids)
        st.toast(f"Updated routine '{s_name}'!")
        
    st.session_state.workout_log = []
    st.session_state.current_session_name = None
    st.session_state.session_start_time = None
    st.balloons()
    st.success(f"Workout Saved! Duration: {duration} mins")

def show_library():
    st.title("Exercise Library")
    
    tab1, tab2, tab3 = st.tabs(["View Exercises", "Add Custom", "Manage"])
    
    with tab1:
        exercises = database.get_all_exercises()
        df = pd.DataFrame(exercises)
        if not df.empty:
            df = df[["muscle", "name", "category", "difficulty", "instructions"]]
            
            search = st.text_input("Search Library", "")
            if search:
                df = df[df["name"].str.contains(search, case=False)]
                
            st.dataframe(df, width='stretch')
        else:
            st.warning("Database empty.")
            
    with tab2:
        st.subheader("Create New Exercise")
        with st.form("custom_ex"):
            name = st.text_input("Exercise Name")
            muscle = st.selectbox("Target Muscle", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Cardio", "Other"])
            category = st.selectbox("Category", ["Strength", "Hypertrophy", "Endurance", "Mobility", "Cardio", "Custom"])
            diff = st.slider("Difficulty", 1, 5, 1)
            inst = st.text_area("Instructions", "Enter execution details...")
            
            submitted = st.form_submit_button("Create Exercise")
            if submitted:
                if name:
                    try:
                        database.add_custom_exercise(name, muscle, inst, diff, category)
                        st.success(f"Created {name}!")
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.error("Name is required")

    with tab3:
        st.subheader("Delete Exercises")
        st.warning("⚠️ Deleting an exercise will remove it from all History and Routines.")
        exercises = database.get_all_exercises()
        ex_map = {f"{e['muscle']} - {e['name']}": e['id'] for e in exercises}
        
        to_del = st.selectbox("Select Exercise to Delete", sorted(ex_map.keys()))
        if st.button("Delete Permanently", type="primary"):
            st.session_state.delete_target_name = to_del
            st.rerun()
            
        if st.session_state.get("delete_target_name"):
            target = st.session_state.delete_target_name
            st.warning(f"Are you sure you want to delete '{target}'? This cannot be undone.")
            c1, c2 = st.columns([1,4])
            if c1.button("Yes, Delete", type="primary"):
                # Check if it still exists (map keys might have changed if we didn't refresh, 
                # but we're relying on ex_map which is fresh from this run)
                # However, if target isn't in ex_map (e.g. somehow changed), we handle it.
                if target in ex_map:
                    eid = ex_map[target]
                    database.delete_exercise(eid)
                    st.success(f"Deleted {target}!")
                else:
                    st.error("Exercise not found.")
                
                del st.session_state.delete_target_name
                time.sleep(0.7)
                st.rerun()
            
            if c2.button("Cancel"):
                del st.session_state.delete_target_name
                st.rerun()

def show_history():
    st.title("Workout History")
    history = database.get_history()
    
    if not history:
        st.info("No workouts found.")
        return
        
    for w in history:
        dur = w.get('duration', 0)
        title = f"{w['date']} - {w['session'] or 'Freestyle'} | ⏱️ {dur}m | Vol: {w['volume']:,.0f}kg"
        
        c1, c2 = st.columns([6, 1])
        with c1:
            with st.expander(title):
                df = pd.DataFrame(w['sets'])
                if not df.empty:
                    st.dataframe(df[['muscle', 'exercise', 'weight', 'reps']], width='stretch')
        with c2:
            confirm_key = f"confirm_del_wo_{w['id']}"
            if st.session_state.get(confirm_key):
                st.warning("Delete?")
                col_yes, col_no = st.columns(2)
                if col_yes.button("✅", key=f"yes_wo_{w['id']}", help="Confirm Delete"):
                    database.delete_workout(w['id'])
                    st.success("Workout Deleted")
                    del st.session_state[confirm_key]
                    time.sleep(0.7)
                    st.rerun()
                if col_no.button("❌", key=f"no_wo_{w['id']}", help="Cancel"):
                    del st.session_state[confirm_key]
                    st.rerun()
            else:
                if st.button("🗑️", key=f"del_wo_{w['id']}", help="Delete Workout"):
                    st.session_state[confirm_key] = True
                    st.rerun()

if __name__ == "__main__":
    main()
