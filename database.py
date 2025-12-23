# ... (Previous imports and init_db remain unchanged)
import sqlite3
import datetime

DB_NAME = "wlog.db"

def init_db():
    # ... (Same as before)
    """Initialize the database tables and handle migrations."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if exercises table exists to handle migration
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exercises'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Create new schema
        cursor.execute('''
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_muscle TEXT,
                instructions TEXT,
                difficulty INTEGER DEFAULT 1,
                category TEXT DEFAULT 'Strength'
            )
        ''')
        seed_exercises(cursor)
    else:
        # Migration: Check for new columns
        cursor.execute("PRAGMA table_info(exercises)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'difficulty' not in columns:
            cursor.execute("ALTER TABLE exercises ADD COLUMN difficulty INTEGER DEFAULT 1")
        if 'category' not in columns:
            cursor.execute("ALTER TABLE exercises ADD COLUMN category TEXT DEFAULT 'Strength'")
            
    # Workouts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_volume REAL
        )
    ''')
    
    # Check for total_volume column in workouts migration
    cursor.execute("PRAGMA table_info(workouts)")
    w_columns = [info[1] for info in cursor.fetchall()]
    if 'total_volume' not in w_columns:
        cursor.execute("ALTER TABLE workouts ADD COLUMN total_volume REAL DEFAULT 0")
        
    if 'session_name' not in w_columns:
        cursor.execute("ALTER TABLE workouts ADD COLUMN session_name TEXT")
        
    if 'duration_minutes' not in w_columns:
        cursor.execute("ALTER TABLE workouts ADD COLUMN duration_minutes INTEGER DEFAULT 0")

    # Sessions (Routines) Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            exercise_id INTEGER,
            item_order INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (exercise_id) REFERENCES exercises (id)
        )
    ''')
    
    # LogEntries table (Sets)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            exercise_id INTEGER,
            set_order INTEGER,
            weight REAL,
            reps INTEGER,
            FOREIGN KEY (workout_id) REFERENCES workouts (id),
            FOREIGN KEY (exercise_id) REFERENCES exercises (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def seed_exercises(cursor):
    """Populates the database with the curated list of exercises."""
    # List format: (Name, Muscle, Instructions, Difficulty, Category)
    exercises = [
        # Chest
        ("Barbell Bench Press", "Chest", "Lower bar to mid-chest; keep feet planted; drive bar up.", 2, "Strength"),
        ("Dumbbell Incline Press", "Chest", "Set bench to 30°; press weights up; focus on the upper chest.", 2, "Hypertrophy"),
        ("Chest Dips", "Chest", "Lean forward slightly; lower body until elbows are at 90°; push back up.", 2, "Strength"),
        ("Cable Crossover", "Chest", "Bring handles together in a 'hugging' motion; squeeze chest at the center.", 1, "Hypertrophy"),
        ("Dumbbell Flyes", "Chest", "Lie flat; open arms wide with slight elbow bend; hug weights back to center.", 1, "Hypertrophy"),
        ("Push-Ups", "Chest", "Maintain a straight line from head to toe; chest nearly touches the floor.", 1, "Strength"),
        
        # Back
        ("Pull-Ups", "Back", "Wide grip; pull chest to bar; drive elbows toward your ribs.", 2, "Strength"),
        ("Bent-Over Barbell Row", "Back", "Hinge at hips; pull bar to lower stomach; squeeze shoulder blades.", 2, "Strength"),
        ("Lat Pulldowns", "Back", "Pull bar to upper chest; lean back slightly; avoid using momentum.", 1, "Hypertrophy"),
        ("Seated Cable Row", "Back", "Pull handle to waist; keep back straight; squeeze shoulder blades.", 1, "Hypertrophy"),
        ("Deadlift", "Back", "Keep bar close to shins; flat back; drive through heels to stand upright.", 3, "Strength"),
        ("Single-Arm Dumbbell Row", "Back", "One hand on bench for support; pull weight to hip; keep elbow tucked.", 1, "Hypertrophy"),
        
        # Legs
        ("Back Squats", "Legs", "Bar on traps; sit back into heels; keep chest up; hips below knees.", 3, "Strength"),
        ("Leg Press", "Legs", "Feet shoulder-width on platform; lower until knees are at 90°; don't lock knees.", 2, "Hypertrophy"),
        ("Romanian Deadlift", "Legs", "Hinge hips back; feel stretch in hamstrings; keep back flat.", 2, "Hypertrophy"),
        ("Bulgarian Split Squat", "Legs", "One foot back on bench; drop back knee; keep front shin vertical.", 2, "Hypertrophy"),
        ("Leg Extensions", "Legs", "Sit upright; kick legs out straight; squeeze quads at the top.", 1, "Isolation"),
        ("Seated Calf Raises", "Legs", "Sit with weight on knees; lift heels as high as possible; slow descent.", 1, "Isolation"),
        
        # Shoulders
        ("Military Press", "Shoulders", "Stand tall; press bar from chin to overhead; lock out at the top.", 2, "Strength"),
        ("Dumbbell Lateral Raise", "Shoulders", "Lift weights to the side until level with shoulders; lead with elbows.", 1, "Hypertrophy"),
        ("Front Raises", "Shoulders", "Lift dumbbells forward to eye level; keep arms straight; control the descent.", 1, "Isolation"),
        ("Face Pulls", "Shoulders", "Pull rope toward forehead; pull ends apart; focus on rear shoulders.", 1, "Mobility"),
        ("Dumbbell Shrugs", "Shoulders", "Hold weights at sides; lift shoulders toward ears; don't roll shoulders.", 1, "Hypertrophy"),
        ("Reverse Flyes", "Shoulders", "Bend forward; lift weights out to the side; focus on upper back/rear delts.", 1, "Hypertrophy"),
        
        # Arms
        ("Barbell Curls", "Arms", "Palms up; curl bar to shoulders; keep elbows pinned to sides.", 1, "Hypertrophy"),
        ("Hammer Curls", "Arms", "Palms facing in; curl dumbbells; targets forearms and biceps.", 1, "Hypertrophy"),
        ("Skull Crushers", "Arms", "Lie flat; lower weight to forehead by bending elbows; extend back up.", 2, "Hypertrophy"),
        ("Tricep Pushdowns", "Arms", "Use rope; pull down until arms are straight; squeeze triceps.", 1, "Isolation"),
        ("Preacher Curls", "Arms", "Arms rested on pad; curl weight up; prevents cheating with momentum.", 1, "Isolation"),
        ("Overhead Tricep Extension", "Arms", "Hold one dumbbell with both hands; lower behind head; press up.", 1, "Hypertrophy"),
        
        # Core
        ("Plank", "Core", "Forearms on floor; body straight; squeeze glutes and core; hold.", 1, "Core"),
        ("Hanging Leg Raises", "Core", "Hang from bar; lift legs to 90°; avoid swinging.", 2, "Core"),
        ("Russian Twists", "Core", "Sit with feet up; rotate torso side to side; touch floor with hands.", 1, "Core"),
        ("Ab Wheel Rollouts", "Core", "Kneel; roll wheel forward as far as possible; pull back using abs.", 3, "Core"),
        ("Cable Crunches", "Core", "Kneeling; pull rope down toward floor using abs; round the back.", 1, "Core"),
        ("Bicycle Crunches", "Core", "Opposite elbow to opposite knee; keep a steady rhythm.", 1, "Core")
    ]
    
    for ex in exercises:
        cursor.execute("SELECT id FROM exercises WHERE name = ?", (ex[0],))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO exercises (name, target_muscle, instructions, difficulty, category) 
                VALUES (?, ?, ?, ?, ?)
            ''', ex)

def add_custom_exercise(name, muscle, instructions="Custom Exercise", difficulty=1, category='Custom'):
    """Adds a custom exercise to the database. Raises ValueError if name exists."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check uniqueness
    cursor.execute("SELECT id FROM exercises WHERE name = ? COLLATE NOCASE", (name,))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Exercise already exists.")
        
    cursor.execute('''
        INSERT INTO exercises (name, target_muscle, instructions, difficulty, category)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, muscle, instructions, difficulty, category))
    conn.commit()
    conn.close()

def get_all_exercises():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, target_muscle, instructions, difficulty, category FROM exercises ORDER BY name")
    data = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "muscle": r[2], "instructions": r[3], "difficulty": r[4], "category": r[5]} for r in data]

def create_workout(total_volume, session_name=None, duration_minutes=0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO workouts (timestamp, total_volume, session_name, duration_minutes) VALUES (?, ?, ?, ?)", 
                  (timestamp, total_volume, session_name, duration_minutes))
    workout_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return workout_id

def create_session(name, exercise_ids):
    """Creates a new routine/session with a list of exercise IDs."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("INSERT INTO sessions (name, created_at) VALUES (?, ?)", (name, created_at))
    session_id = cursor.lastrowid
    
    for idx, ex_id in enumerate(exercise_ids):
        cursor.execute("INSERT INTO session_items (session_id, exercise_id, item_order) VALUES (?, ?, ?)",
                      (session_id, ex_id, idx))
                      
    conn.commit()
    conn.close()

def update_session(name, exercise_ids):
    """Updates the exercises in a session."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get ID
    cursor.execute("SELECT id FROM sessions WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    s_id = row[0]
    
    # Clear existing items
    cursor.execute("DELETE FROM session_items WHERE session_id = ?", (s_id,))
    
    # Add new items
    for idx, ex_id in enumerate(exercise_ids):
        cursor.execute("INSERT INTO session_items (session_id, exercise_id, item_order) VALUES (?, ?, ?)",
                      (s_id, ex_id, idx))
                      
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM sessions")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

def get_session_details(session_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, e.name, e.target_muscle
        FROM session_items si
        JOIN exercises e ON si.exercise_id = e.id
        WHERE si.session_id = ?
        ORDER BY si.item_order
    ''', (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "muscle": r[2]} for r in rows]

def get_session_by_name(name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sessions WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_last_performance(exercise_id):
    """Gets the last weight/reps logged for this exercise."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.weight, l.reps, w.timestamp
        FROM log_entries l
        JOIN workouts w ON l.workout_id = w.id
        WHERE l.exercise_id = ?
        ORDER BY w.id DESC
        LIMIT 1
    ''', (exercise_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"weight": row[0], "reps": row[1], "date": row[2].split(" ")[0]}
    return None

def log_set(workout_id, exercise_id, weight, reps, set_order):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO log_entries (workout_id, exercise_id, weight, reps, set_order)
        VALUES (?, ?, ?, ?, ?)
    ''', (workout_id, exercise_id, weight, reps, set_order))
    conn.commit()
    conn.close()

def get_streak():
    """Calculates the current training streak in consecutive days."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get distinct dates of workouts sorted descending
    cursor.execute("SELECT DISTINCT date(timestamp) FROM workouts ORDER BY date(timestamp) DESC")
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not dates:
        return 0
        
    streak = 1 if len(dates) > 0 else 0
    # Check if the most recent workout was today or yesterday to keep streak alive
    today = datetime.date.today()
    last_workout = datetime.datetime.strptime(dates[0], "%Y-%m-%d").date()
    
    if (today - last_workout).days > 1:
        return 0 # Streak broken
    
    # Iterate to find consecutive days
    for i in range(len(dates) - 1):
        d1 = datetime.datetime.strptime(dates[i], "%Y-%m-%d").date()
        d2 = datetime.datetime.strptime(dates[i+1], "%Y-%m-%d").date()
        diff = (d1 - d2).days
        if diff == 1:
            streak += 1
        else:
            break
            
    return streak

def get_last_workout_summary():
    """Fetches summary of the last workout for sharing."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, total_volume FROM workouts ORDER BY id DESC LIMIT 1")
    workout = cursor.fetchone()
    
    if not workout:
        conn.close()
        return None
        
    w_id = workout[0]
    date = workout[1]
    volume = workout[2]
    
    cursor.execute('''
        SELECT e.name, l.weight, l.reps
        FROM log_entries l
        JOIN exercises e ON l.exercise_id = e.id
        WHERE l.workout_id = ?
    ''', (w_id,))
    sets = cursor.fetchall()
    conn.close()
    
    return {
        "date": date,
        "volume": volume,
        "sets": sets
    }

def get_history():
    """Returns a list of all workouts with their detailed sets."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get all workouts ordered by date descending
    cursor.execute("SELECT id, timestamp, total_volume, session_name, duration_minutes FROM workouts ORDER BY id DESC")
    workouts_raw = cursor.fetchall()
    
    workouts = []
    for row in workouts_raw:
        w_id = row[0]
        timestamp = row[1]
        vol = row[2]
        s_name = row[3] if len(row) > 3 else None
        dur = row[4] if len(row) > 4 else 0
        
        cursor.execute('''
            SELECT e.name, l.weight, l.reps, e.target_muscle, l.set_order
            FROM log_entries l
            JOIN exercises e ON l.exercise_id = e.id
            WHERE l.workout_id = ?
            ORDER BY l.set_order
        ''', (w_id,))
        sets_raw = cursor.fetchall()
        
        sets_data = []
        for s in sets_raw:
            sets_data.append({
                "exercise": s[0],
                "weight": s[1],
                "reps": s[2],
                "muscle": s[3]
            })
            
        workouts.append({
            "id": w_id,
            "date": timestamp,
            "volume": vol,
            "session": s_name,
            "duration": dur,
            "sets": sets_data
        })
        
    conn.close()
    return workouts

def delete_session(session_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM session_items WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def delete_workout(workout_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM log_entries WHERE workout_id = ?", (workout_id,))
    cursor.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()

def delete_exercise(exercise_id):
    """Deletes exercise and all associated logs/session items."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM session_items WHERE exercise_id = ?", (exercise_id,))
    cursor.execute("DELETE FROM log_entries WHERE exercise_id = ?", (exercise_id,))
    cursor.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
    conn.commit()
    conn.close()
