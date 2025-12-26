import pandas as pd
import datetime
import streamlit as st
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Global client cache
_gc = None
_sh = None
DB_NAME = "Google Sheets (WLog_DB)"

def _get_connection():
    global _gc, _sh
    if _gc and _sh:
        return _gc, _sh

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Try getting secrets from Streamlit secrets or local file
    creds_dict = None
    
    # 1. Try Streamlit Secrets (Cloud) - Wrapped to prevent crash if secrets.toml missing
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
    except Exception:
        pass # Secrets file not found or invalid
        
    # 2. Try Local File (Local Dev)
    if not creds_dict:
        if os.path.exists("service_account.json"):
            # Priority: Explicitly named file
            with open("service_account.json") as f:
                creds_dict = json.load(f)
        else:
            # Fallback: Auto-discover any service account JSON
            for f_name in os.listdir("."):
                if f_name.endswith(".json"):
                    try:
                        with open(f_name) as f:
                            temp_data = json.load(f)
                            if temp_data.get("type") == "service_account":
                                creds_dict = temp_data
                                break
                    except:
                        continue
            
    if not creds_dict:
        st.error("Missing Google Sheets Credentials. Add 'service_account.json' locally or 'gcp_service_account' in secrets.")
        st.stop()
        
    # print("Authenticating with Google...")
    _gc = gspread.service_account_from_dict(creds_dict)
    try:
        # print("Opening Spreadsheet 'WLog_DB'...")
        _sh = _gc.open("WLog_DB")
        # print(f"Successfully opened: {_sh.title}")
        st.toast(f"✅ Connected to: {_sh.title}")
    except gspread.SpreadsheetNotFound:
        st.error("Spreadsheet 'WLog_DB' not found. Please create it and share with the service account email.")
        st.stop()
        
    return _gc, _sh

def _get_df(worksheet_name):
    # Cache key
    cache_key = f"gs_cache_{worksheet_name}"
    
    # Return from cache if available
    if cache_key in st.session_state:
        # print(f"DEBUG: Reading '{worksheet_name}' from CACHE")
        return st.session_state[cache_key]

    # print(f"Reading sheet: {worksheet_name} from API")
    _, sh = _get_connection()
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        # Auto-create if missing (failsafe)
        ws = sh.add_worksheet(title=worksheet_name, rows=100, cols=20)
        
    
    # robust read using pandas from values, assuming row 1 is header
    data = ws.get_all_values()
    if not data:
        # print(f"WARNING: Sheet '{worksheet_name}' is completely empty.")
        df = pd.DataFrame()
        # Cache the empty result too
        st.session_state[cache_key] = df
        return df
        
    headers = data[0]
    # print(f"DEBUG: Sheet '{worksheet_name}' RAW HEADERS: {headers}")
    rows = data[1:]
    
    # Handle duplicate headers if they exist by strictly creating DF
    df = pd.DataFrame(rows, columns=headers)
    
    # Clean whitespace from headers just in case
    df.columns = df.columns.str.strip()
    
    # Save to Cache
    st.session_state[cache_key] = df
    
    return df

def _append_row(worksheet_name, row_data):
    _, sh = _get_connection()
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
         # Lowercase fallback
         all_ws = {w.title.lower(): w for w in sh.worksheets()}
         ws = all_ws.get(worksheet_name.lower())
         if not ws:
             raise ValueError(f"Worksheet {worksheet_name} not found")
             
    ws.append_row(row_data)
    
    # Update Cache
    cache_key = f"gs_cache_{worksheet_name}"
    if cache_key in st.session_state:
        df = st.session_state[cache_key]
        if not df.empty:
            # Convert row_data to strings to match WS behavior
            str_row = [str(item) for item in row_data]
            # Create a 1-row DF
            new_row_df = pd.DataFrame([str_row], columns=df.columns)
            # Concat
            st.session_state[cache_key] = pd.concat([df, new_row_df], ignore_index=True)
        else:
            # If df was empty, we can't easily append without headers.
            # Invalidate cache so next read fetches with new headers/data
            del st.session_state[cache_key]

def _replace_sheet_data(worksheet_name, df):
    _, sh = _get_connection()
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=100, cols=20)
        
    ws.clear()
    # Write header and data
    # GSpread update requires list of lists including header
    if not df.empty:
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    else:
        # Just header
        if len(df.columns) > 0:
            ws.update([df.columns.values.tolist()])
            
    # Update Cache
    st.session_state[f"gs_cache_{worksheet_name}"] = df.copy()

# --- Implementation ---

def init_db():
    _, sh = _get_connection()
    # Define schema with default headers
    schema = {
        "exercises": ["id", "name", "target_muscle", "instructions", "difficulty", "category"],
        "workouts": ["id", "timestamp", "total_volume", "session_name", "duration_minutes"],
        "log_entries": ["id", "workout_id", "exercise_id", "set_order", "weight", "reps"],
        "sessions": ["id", "name", "created_at"],
        "session_items": ["id", "session_id", "exercise_id", "item_order"]
    }
    
    # Clean check: Get titles, normalize to lowercase for check
    existing_titles_map = {ws.title.lower(): ws.title for ws in sh.worksheets()}
    
    for table, columns in schema.items():
        if table.lower() not in existing_titles_map:
            # Create new
            ws = sh.add_worksheet(title=table, rows=100, cols=20)
            ws.append_row(columns)
        else:
            # Check if empty, if so write headers
            real_title = existing_titles_map[table.lower()]
            ws = sh.worksheet(real_title)
            if not ws.get_all_values():
                ws.append_row(columns)

def seed_exercises(cursor=None):
    pass

def get_all_exercises():
    df = _get_df("exercises")
    if df.empty: return []
    
    # Rename target_muscle to muscle to match app expectations
    if 'target_muscle' in df.columns:
        df = df.rename(columns={'target_muscle': 'muscle'})
        
    return df.to_dict('records')

def add_custom_exercise(name, muscle, instructions="Custom Exercise", difficulty=1, category='Custom'):
    df = _get_df("exercises")
    
    # Check uniqueness
    if not df.empty and name.lower() in df['name'].str.lower().values:
        raise ValueError("Exercise already exists.")
        
    new_id = 1
    if not df.empty:
        ids = pd.to_numeric(df['id'], errors='coerce')
        if not ids.dropna().empty:
            new_id = ids.max() + 1
    row = [int(new_id), name, muscle, instructions, int(difficulty), category]
    _append_row("exercises", row)

def create_workout(total_volume, session_name=None, duration_minutes=0):
    df = _get_df("workouts")
    new_id = 1
    if not df.empty:
        ids = pd.to_numeric(df['id'], errors='coerce')
        if not ids.dropna().empty:
            new_id = ids.max() + 1
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    row = [int(new_id), timestamp, total_volume, session_name, duration_minutes]
    _append_row("workouts", row)
    return new_id

def log_set(workout_id, exercise_id, weight, reps, set_order):
    df = _get_df("log_entries")
    new_id = 1
    if not df.empty:
        ids = pd.to_numeric(df['id'], errors='coerce')
        if not ids.dropna().empty:
            new_id = ids.max() + 1
    row = [int(new_id), int(workout_id), int(exercise_id), int(set_order), float(weight), int(reps)]
    _append_row("log_entries", row)

def get_last_performance(exercise_id):
    # Slow operation in Sheets: Join LogEntries + Workouts
    logs = _get_df("log_entries")
    workouts = _get_df("workouts")
    
    if logs.empty or workouts.empty:
        return None
        
    # Filter logs for exercise
    ex_logs = logs[logs['exercise_id'] == exercise_id]
    if ex_logs.empty:
        return None
        
    # Merge
    merged = pd.merge(ex_logs, workouts, left_on='workout_id', right_on='id', suffixes=('_log', '_wo'))
    if merged.empty:
        return None
        
    # Sort by workout id desc
    last = merged.sort_values('workout_id', ascending=False).iloc[0]
    return {
        "weight": last['weight'], 
        "reps": last['reps'], 
        "date": str(last['timestamp']).split(" ")[0]
    }

def get_streak():
    workouts = _get_df("workouts")
    if workouts.empty: return 0
    
    dates = pd.to_datetime(workouts['timestamp']).dt.date.unique()
    dates = sorted(dates, reverse=True)
    
    if not dates: return 0
    
    streak = 1
    today = datetime.date.today()
    last = dates[0]
    
    if (today - last).days > 1: return 0
    
    for i in range(len(dates)-1):
        if (dates[i] - dates[i+1]).days == 1:
            streak += 1
        else:
            break
    return streak

def get_last_workout_summary():
    workouts = _get_df("workouts")
    if workouts.empty: return None
    
    last = workouts.sort_values('id', ascending=False).iloc[0]
    w_id = last['id']
    
    logs = _get_df("log_entries")
    exs = _get_df("exercises")
    
    w_logs = logs[logs['workout_id'] == w_id]
    merged = pd.merge(w_logs, exs, left_on='exercise_id', right_on='id')
    
    sets = []
    for _, row in merged.iterrows():
        # Format matching tuple expected by UI (name, weight, reps)
        sets.append((row['name'], row['weight'], row['reps']))
        
    return {
        "date": last['timestamp'],
        "volume": last['total_volume'],
        "sets": sets
    }

# --- Session Management ---

def create_session(name, exercise_ids):
    sess = _get_df("sessions")
    
    # Validation / Self-Healing for Sessions Sheet
    if sess.empty:
         s_new_id = 1
    else:
         if 'id' not in sess.columns:
             # Header corrupt, fix it
             _replace_sheet_data("sessions", pd.DataFrame(columns=["id", "name", "created_at"]))
             sess = _get_df("sessions")
             
         sess['id'] = pd.to_numeric(sess['id'], errors='coerce')
         if sess['id'].dropna().empty:
             s_new_id = 1
         else:
             s_new_id = int(sess['id'].max()) + 1
            
    created_at = datetime.datetime.now().strftime("%Y-%m-%d")
    _append_row("sessions", [int(s_new_id), name, created_at])
    
    # Validation / Self-Healing for Items Sheet
    items = _get_df("session_items")
    if items.empty:
        start_id = 1
    else:
        if 'id' not in items.columns:
            _replace_sheet_data("session_items", pd.DataFrame(columns=["id", "session_id", "exercise_id", "item_order"]))
            items = _get_df("session_items")
            
        items['id'] = pd.to_numeric(items['id'], errors='coerce')
        if items['id'].dropna().empty:
            start_id = 1
        else:
            start_id = int(items['id'].max()) + 1
    
    rows_to_add = []
    for idx, eid in enumerate(exercise_ids):
        rows_to_add.append([int(start_id + idx), int(s_new_id), int(eid), int(idx)])
    
    # Batch add manual
    _, sh = _get_connection()
    ws = sh.worksheet("session_items")
    ws.append_rows(rows_to_add)
    
    # Invalidate Cache for session_items since we did a manual append
    if "gs_cache_session_items" in st.session_state:
        del st.session_state["gs_cache_session_items"]

def get_all_sessions():
    df = _get_df("sessions")
    if df.empty: return []
    
    required = {'id', 'name'}
    if not required.issubset(df.columns):
        # print(f"ERROR: sessions table missing columns. Found: {df.columns.tolist()}")
        # Fallback: Return empty to trigger re-init button in UI
        return []
        
    return tuple(df[['id', 'name']].to_dict('records'))

def get_session_details(session_id):
    s_items = _get_df("session_items")
    exs = _get_df("exercises")
    
    if s_items.empty: return []
    
    items = s_items[s_items['session_id'] == session_id].sort_values('item_order')
    merged = pd.merge(items, exs, left_on='exercise_id', right_on='id')
    
    return merged[['id_y', 'name', 'target_muscle']].rename(columns={'id_y': 'id', 'target_muscle': 'muscle'}).to_dict('records')

def get_session_by_name(name):
    df = _get_df("sessions")
    if df.empty: return None
    row = df[df['name'] == name]
    if row.empty: return None
    return int(row.iloc[0]['id'])

def update_session_by_id(session_id, name, exercise_ids):
    # This involves rewriting sessions and session_items
    # 1. Update name
    sess = _get_df("sessions")
    sess.loc[sess['id'].astype(str) == str(session_id), 'name'] = name
    _replace_sheet_data("sessions", sess)
    
    # 2. Delete old items
    items = _get_df("session_items")
    items = items[items['session_id'].astype(str) != str(session_id)] # Keep others
    
    # 3. Add new items
    start_id = 1
    if not items.empty:
        ids = pd.to_numeric(items['id'], errors='coerce')
        if not ids.dropna().empty:
            start_id = ids.max() + 1
    new_rows = []
    for idx, eid in enumerate(exercise_ids):
        new_rows.append({
            "id": int(start_id + idx),
            "session_id": int(session_id),
            "exercise_id": int(eid),
            "item_order": int(idx)
        })
    
    new_items_df = pd.DataFrame(new_rows)
    final_items = pd.concat([items, new_items_df], ignore_index=True)
    _replace_sheet_data("session_items", final_items)

def delete_session(session_id):
    # Filter out
    sess = _get_df("sessions")
    sess = sess[sess['id'].astype(str) != str(session_id)]
    _replace_sheet_data("sessions", sess)
    
    items = _get_df("session_items")
    items = items[items['session_id'].astype(str) != str(session_id)]
    _replace_sheet_data("session_items", items)

def delete_workout(workout_id):
    w = _get_df("workouts")
    w = w[w['id'].astype(str) != str(workout_id)]
    _replace_sheet_data("workouts", w)
    
    l = _get_df("log_entries")
    l = l[l['workout_id'].astype(str) != str(workout_id)]
    _replace_sheet_data("log_entries", l)

def get_history():
    workouts = _get_df("workouts")
    if workouts.empty: return []
    
    logs = _get_df("log_entries")
    exs = _get_df("exercises")
    
    # Sort workouts desc
    workouts = workouts.sort_values('id', ascending=False)
    
    history = []
    for _, w in workouts.iterrows():
        w_id = w['id']
        w_logs = logs[logs['workout_id'] == w_id].sort_values('set_order')
        
        merged = pd.merge(w_logs, exs, left_on='exercise_id', right_on='id')
        sets_data = []
        for _, r in merged.iterrows():
            sets_data.append({
                "exercise": r['name'],
                "weight": r['weight'],
                "reps": r['reps'],
                "muscle": r['target_muscle']
            })
            
        history.append({
            "id": w_id,
            "date": w['timestamp'],
            "volume": w['total_volume'],
            "session": w['session_name'],
            "duration": w['duration_minutes'],
            "sets": sets_data
        })
    return history

def delete_exercise(exercise_id):
    # This is heavy.
    for table in ["exercises", "session_items", "log_entries"]:
        df = _get_df(table)
        col = 'id' if table == "exercises" else 'exercise_id'
        df = df[df[col].astype(str) != str(exercise_id)]
        _replace_sheet_data(table, df)

def create_default_schedule():
    # Only run if sessions empty
    # Batched Optimized Version
    if not get_all_sessions():
         schedule = {
            "Monday: Upper Body Push": [
                ("Dumbbell Bench Press", "Chest", "Strength", "3 sets x 10–12 reps. Flat or Incline.", 2),
                ("Dumbbell Overhead Press", "Shoulders", "Strength", "3 sets x 10 reps. Standing or Seated.", 2),
                ("Push-Ups", "Chest", "Strength", "3 sets x Failure. Knees if needed for full range.", 1),
                ("Overhead Tricep Extension", "Arms", "Hypertrophy", "3 sets x 12 reps. Use Dumbbell.", 2),
                ("Plank", "Core", "Core", "3 sets x 45 seconds. Core stability.", 1),
                ("Brisk Walk", "Cardio", "Cardio", "20 mins. Incline 5. Keep heart rate moderate.", 1)
            ],
            "Tuesday: Upper Body Pull": [
                ("Lat Pulldowns", "Back", "Hypertrophy", "3 sets x 12 reps. Focus on pulling with elbows.", 1),
                ("Single-Arm Dumbbell Row", "Back", "Hypertrophy", "3 sets x 10 reps per arm. Use bench support. Flat back.", 2),
                ("Dumbbell Bicep Curls", "Arms", "Hypertrophy", "3 sets x 12 reps.", 1),
                ("Dead Hangs", "Back", "Strength", "3 sets x Max time. Hang until hands slip. Grip focus.", 2),
                ("Cycling", "Cardio", "Cardio", "20 mins. Moderate pace.", 1)
            ],
            "Wednesday: Leg Strength": [
                ("Goblet Squats", "Legs", "Strength", "3 sets x 12 reps. Hold DB at chest. Squat deep.", 2),
                ("Dumbbell Walking Lunges", "Legs", "Hypertrophy", "3 sets x 10 steps per leg.", 2),
                ("Dumbbell Romanian Deadlift", "Legs", "Hypertrophy", "3 sets x 12 reps. Hold DBs in front. Hinge hips. Feel hamstring stretch.", 2),
                ("Standing Calf Raises", "Legs", "Isolation", "3 sets x 15 reps. Use DBs.", 1),
                ("Incline Walk", "Cardio", "Cardio", "15 mins. Increase incline to 8-10.", 2)
            ],
            "Thursday: Active Rest": [
                ("Outdoor Walk", "Cardio", "Cardio", "45-min continuous walk outdoors.", 1),
                ("Swimming", "Cardio", "Cardio", "Light swim to flush out soreness.", 2)
            ],
            "Friday: Spartan Circuit": [
                ("Bodyweight Squats", "Legs", "Endurance", "20 reps. Part of Circuit.", 1),
                ("Push-Ups", "Chest", "Strength", "10 reps. Part of Circuit.", 1),
                ("Mountain Climbers", "Core", "Endurance", "20 reps (Total). Part of Circuit.", 2),
                ("Step-Ups", "Legs", "Endurance", "10 reps per leg. Step onto bench.", 2),
                ("Burpees", "Cardio", "Endurance", "5 reps. Smooth motion.", 3),
                ("Cool-down Walk", "Cardio", "Cardio", "10 mins.", 1)
            ],
            "Saturday: Endurance & Carries": [
                ("Farmer’s Carry", "Back", "Strength", "4 sets x 40 meters. Heaviest DBs safely. Good posture.", 2),
                ("Running", "Cardio", "Cardio", "30–45 mins. Constant pace.", 2)
            ]
        }
         
         # Logic to add these
         # Ensure headers correct
         ex_df = _get_df("exercises")
         
         if ex_df.empty and len(ex_df.columns) == 0:
              _replace_sheet_data("exercises", pd.DataFrame(columns=["id", "name", "target_muscle", "instructions", "difficulty", "category"]))
              ex_df = _get_df("exercises")
         
         if 'id' not in ex_df.columns:
             _, sh = _get_connection()
             ws = sh.worksheet("exercises")
             ws.update(range_name='A1', values=[["id", "name", "target_muscle", "instructions", "difficulty", "category"]])
             ex_df = _get_df("exercises")

         if ex_df.empty: 
             next_id = 1
         else:
             ex_df['id'] = pd.to_numeric(ex_df['id'], errors='coerce')
             if ex_df['id'].dropna().empty:
                 next_id = 1
             else:
                 next_id = int(ex_df['id'].max()) + 1
             
         new_exercises_rows = []
         final_schedule_ids = {} # Routine -> [ExIDs]
         existing_names = set(ex_df['name'].str.lower().values) if not ex_df.empty else set()
         
         curr_next_id = next_id
         # Pre-fill map from existing df
         name_to_id = {}
         if not ex_df.empty:
             for _, r in ex_df.iterrows():
                 name_to_id[r['name'].lower()] = int(r['id'])
         
         for routine, exs in schedule.items():
            r_ex_ids = []
            for ex in exs:
                name, muscle, cat, inst, diff = ex
                lower_name = name.lower()
                
                if lower_name in name_to_id:
                    eid = name_to_id[lower_name]
                else:
                    eid = curr_next_id
                    new_exercises_rows.append([int(eid), name, muscle, inst, int(diff), cat])
                    name_to_id[lower_name] = eid
                    curr_next_id += 1
                r_ex_ids.append(eid)
            final_schedule_ids[routine] = r_ex_ids
            
         # BATCH WRITE EXERCISES
         if new_exercises_rows:
             _, sh = _get_connection()
             ws = sh.worksheet("exercises")
             ws.append_rows(new_exercises_rows)
             # print(f"Batch inserted {len(new_exercises_rows)} exercises.")
             
         # Batch create sessions
         # OPTIMIZATION: Do not call create_session() in loop. Batch everything.
         
         # print("Batching sessions and items creation...")
         
         # 1. Prepare Sessions Data
         sess = _get_df("sessions")
         if sess.empty:
             s_next_id = 1
         else:
             if 'id' not in sess.columns:
                 _replace_sheet_data("sessions", pd.DataFrame(columns=["id", "name", "created_at"]))
                 sess = _get_df("sessions")
             
             sess['id'] = pd.to_numeric(sess['id'], errors='coerce')
             if sess['id'].dropna().empty:
                 s_next_id = 1
             else:
                 s_next_id = int(sess['id'].max()) + 1
                 
         # 2. Prepare Items Data
         items = _get_df("session_items")
         if items.empty:
             i_next_id = 1
         else:
             if 'id' not in items.columns:
                 _replace_sheet_data("session_items", pd.DataFrame(columns=["id", "session_id", "exercise_id", "item_order"]))
                 items = _get_df("session_items")
                 
             items['id'] = pd.to_numeric(items['id'], errors='coerce')
             if items['id'].dropna().empty:
                 i_next_id = 1
             else:
                 i_next_id = int(items['id'].max()) + 1
                 
         # 3. Generate Rows
         new_sess_rows = []
         new_item_rows = []
         
         created_at = datetime.datetime.now().strftime("%Y-%m-%d")
         
         for routine_name, ex_ids in final_schedule_ids.items():
             # Session Row
             s_id = s_next_id
             new_sess_rows.append([int(s_id), routine_name, created_at])
             s_next_id += 1
             
             # Item Rows
             for idx, eid in enumerate(ex_ids):
                 new_item_rows.append([int(i_next_id), int(s_id), int(eid), int(idx)])
                 i_next_id += 1
                 
         # 4. Batch Write
         _, sh = _get_connection()
         
         if new_sess_rows:
             ws_s = sh.worksheet("sessions")
             ws_s.append_rows(new_sess_rows)
             # print(f"Batch inserted {len(new_sess_rows)} sessions.")
             
         if new_item_rows:
             ws_i = sh.worksheet("session_items")
             ws_i.append_rows(new_item_rows)
             # print(f"Batch inserted {len(new_item_rows)} session items.")
             
         # print("Schedule initialization complete.")
         
         # Invalidate all caches affected
         for k in ["gs_cache_exercises", "gs_cache_sessions", "gs_cache_session_items"]:
             if k in st.session_state:
                 del st.session_state[k]
