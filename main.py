try:
    import ui
    import dialogs
except ImportError:
    print("This script is intended for Pythonista on iOS and requires the 'ui' module.")
    print("It will not run on standard Python environments (Windows/Mac/Linux).")
    # Mock classes for syntax checking/IDE support on Desktop
    class MockUI:
        def View(self): pass
        def NavigationView(self, root_view): pass
        def TableView(self): pass
        def ListDataSource(self, items): pass
        def Button(self): pass
        def Label(self): pass
        def TextField(self): pass
        def Image(self): pass
        def ImageView(self): pass
        def ButtonItem(self): pass
    ui = MockUI()
    dialogs = object()

import database
import datetime

# Initialize DB on load
database.init_db()

class WLogApp:
    def __init__(self):
        self.current_workout_sets = []
        self.main_nav = None
        
    def create_dashboard(self):
        v = ui.View()
        v.name = 'WLog Dashboard'
        v.background_color = '#1c1c1e' # Dark mode background
        
        # Title
        lbl_title = ui.Label(frame=(20, 40, 300, 50))
        lbl_title.text = "WLog"
        lbl_title.font = ('<system-bold>', 32)
        lbl_title.text_color = 'white'
        v.add_subview(lbl_title)
        
        # Streak Card
        streak = database.get_streak()
        card = ui.View(frame=(20, 100, 335, 100))
        card.background_color = '#2c2c2e'
        card.corner_radius = 12
        
        lbl_streak = ui.Label(frame=(10, 10, 300, 30))
        lbl_streak.text = "CURRENT STREAK"
        lbl_streak.font = ('<system-bold>', 14)
        lbl_streak.text_color = '#8e8e93'
        card.add_subview(lbl_streak)
        
        lbl_days = ui.Label(frame=(10, 40, 300, 50))
        lbl_days.text = f"{streak} DAYS"
        lbl_days.font = ('<system-bold>', 36)
        lbl_days.text_color = '#30d158' # iOS Green
        card.add_subview(lbl_days)
        
        v.add_subview(card)
        
        # Start Workout Button
        btn_start = ui.Button(frame=(20, 220, 335, 50))
        btn_start.title = "Start Live Workout"
        btn_start.font = ('<system-bold>', 18)
        btn_start.background_color = '#0a84ff' # iOS Blue
        btn_start.tint_color = 'white'
        btn_start.corner_radius = 12
        btn_start.action = self.open_log_workout
        v.add_subview(btn_start)
        
        # Library Button
        btn_lib = ui.Button(frame=(20, 290, 335, 50))
        btn_lib.title = "Exercise Library"
        btn_lib.font = ('<system-bold>', 18)
        btn_lib.background_color = '#3a3a3c'
        btn_lib.tint_color = 'white'
        btn_lib.corner_radius = 12
        btn_lib.action = self.open_library
        v.add_subview(btn_lib)
        
        # Share Last Workout
        btn_share = ui.Button(frame=(20, 360, 335, 50))
        btn_share.title = "Share Last Workout"
        btn_share.font = ('<system-bold>', 18)
        btn_share.background_color = '#ff9f0a' # iOS Orange
        btn_share.tint_color = 'white'
        btn_share.corner_radius = 12
        btn_share.action = self.share_last_workout
        v.add_subview(btn_share)

        return v

    def open_log_workout(self, sender):
        v = ui.View()
        v.name = 'Live Workout'
        v.background_color = '#1c1c1e'
        
        # Table to show logged sets
        self.workout_table = ui.TableView(frame=(0, 0, 375, 400))
        self.workout_table.flex = 'WH'
        self.workout_table.data_source = ui.ListDataSource([])
        self.workout_table.data_source.tableview_cell_for_row = self.cell_for_set
        v.add_subview(self.workout_table)
        
        # Add Exercise Button (Bottom)
        btn_add = ui.Button(frame=(20, 420, 335, 50))
        btn_add.title = "+ Add Exercise"
        btn_add.flex = 'T' # Stick to bottom roughly
        btn_add.background_color = '#0a84ff'
        btn_add.tint_color = 'white'
        btn_add.corner_radius = 12
        btn_add.action = self.select_exercise_for_log
        v.add_subview(btn_add)
        
        # Finish Button
        btn_finish = ui.ButtonItem(title='Finish')
        btn_finish.action = self.finish_workout
        v.right_button_items = [btn_finish]
        
        self.current_workout_sets = []
        self.update_workout_table()
        
        self.main_nav.push_view(v)

    def cell_for_set(self, tableview, section, row):
        # Custom cell formatting for workout table
        item = tableview.data_source.items[row]
        cell = ui.TableViewCell()
        cell.text_label.text = item['title']
        cell.detail_text_label.text = item['detail']
        return cell

    def update_workout_table(self):
        items = []
        for s in self.current_workout_sets:
            items.append({
                'title': s['name'],
                'detail': f"{s['weight']} lbs x {s['reps']} reps"
            })
        self.workout_table.data_source.items = items
        self.workout_table.reload_data()

    def select_exercise_for_log(self, sender):
        self.open_library(mode='select')

    def open_library(self, sender=None, mode='view'):
        self.all_exercises = database.get_all_exercises()
        
        v = ui.View()
        title = 'Exercise Library' if mode == 'view' else 'Select Exercise'
        v.name = title
        v.background_color = '#1c1c1e'
        
        # Search Bar
        search_field = ui.TextField(frame=(10, 10, 355, 40))
        search_field.placeholder = 'Search Exercises'
        search_field.clear_button_mode = 'always'
        search_field.delegate = self
        search_field.action = self.filter_exercises
        # Store mode to handle tap later
        v.extra_data = {'mode': mode} 
        v.add_subview(search_field)
        
        # TableView
        tv = ui.TableView()
        tv.frame = (0, 60, 375, 607)
        tv.flex = 'WH'
        tv.name = 'table'
        v.add_subview(tv)
        
        self.current_library_view = v
        self.update_library_list(self.all_exercises, mode)
        
        self.main_nav.push_view(v)

    def filter_exercises(self, sender):
        query = sender.text.lower()
        if not query:
            filtered = self.all_exercises
        else:
            filtered = [e for e in self.all_exercises if query in e['name'].lower()]
        
        mode = self.current_library_view.extra_data['mode']
        self.update_library_list(filtered, mode)

    def update_library_list(self, exercises, mode):
        tv = self.current_library_view['table']
        
        # Group by muscle
        groups = {}
        for e in exercises:
            m = e['muscle']
            if m not in groups: groups[m] = []
            groups[m].append(e)
            
        sorted_keys = sorted(groups.keys())
        items = []
        
        # Add "Custom" Section at the extremely top only in 'select' mode or always if preferred
        # User requested "search list", typically relevant for logging.
        if mode == 'select':
            items.append([{
                'title': '+ Create New Exercise',
                'image': 'iob:plus_circled_24',
                'accessory_type': 'disclosure_indicator',
                'action_type': 'custom_add'
            }])
            # Insert a "header" for sections but ListDataSource handles sections via mapping matching indices
            # trick: we will just manage items and sections list parallel
        
        display_sections = []
        if mode == 'select':
            display_sections.append("Actions")

        for k in sorted_keys:
            display_sections.append(k)
            # Sort exercises within muscle
            ex_list = sorted(groups[k], key=lambda x: x['name'])
            # Format: "Muscle - Name" as requested, though header is muscle, we will stick to request
            # "exercises should appear in mussle group - exercise name format"
            # Since we have headers, redundancy is okay or we can flatten. 
            # I will keep headers and format the text as requested.
            section = []
            for x in ex_list:
                section.append({
                    'title': f"{x['muscle']} - {x['name']}",
                    'db_data': x,
                    'accessory_type': 'disclosure_indicator',
                    'action_type': 'exercise'
                })
            items.append(section)
            
        ds = ui.ListDataSource(items)
        ds.sections = display_sections
        ds.font = ('<system>', 18)
        
        ds.action = self.handle_library_selection
            
        tv.data_source = ds
        tv.delegate = ds
        tv.reload_data()
        
    def handle_library_selection(self, sender):
        sec, row = sender.selected_row
        item = sender.items[sec][row]
        
        if item.get('action_type') == 'custom_add':
            self.show_add_custom_exercise_dialog()
            return
            
        # Normal exercise selection
        mode = self.current_library_view.extra_data['mode']
        if mode == 'view':
            self.show_exercise_detail_data(item['db_data'])
        else:
            self.prompt_log_set_data(item['db_data'])

    def show_add_custom_exercise_dialog(self):
        fields = [
            {'type': 'text', 'title': 'Exercise Name', 'key': 'name'},
            {'type': 'text', 'title': 'Muscle Group', 'key': 'muscle', 'value': 'Custom'},
        ]
        result = dialogs.form_dialog(title="New Exercise", fields=fields)
        if result:
            name = result.get('name', '').strip()
            muscle = result.get('muscle', '').strip()
            
            if not name or not muscle:
                dialogs.alert("Error", "Name and Muscle are required.", "OK")
                return
                
            try:
                database.add_custom_exercise(name, muscle)
                dialogs.hud_alert("Exercise Created!")
                # Refresh list
                self.all_exercises = database.get_all_exercises()
                # Reset list with all exercises
                self.update_library_list(self.all_exercises, 'select')
                
            except ValueError as e:
                dialogs.alert("Error", str(e), "OK")

    def show_exercise_detail_data(self, data):
        v = ui.View()
        v.name = data['name']
        v.background_color = 'white'
        
        img = ui.ImageView(frame=(0, 0, 375, 250))
        img.background_color = '#e5e5ea'
        lbl_img = ui.Label(frame=(0,100,375,50))
        lbl_img.text = f"{data['category']} / {data['difficulty']}"
        lbl_img.alignment = ui.ALIGN_CENTER
        img.add_subview(lbl_img)
        v.add_subview(img)
        
        tv = ui.TextView(frame=(20, 270, 335, 300))
        tv.editable = False
        tv.font = ('<system>', 16)
        tv.text = f"Target Muscle: {data['muscle']}\nCategory: {data['category']}\n\nInstructions:\n{data['instructions']}"
        v.add_subview(tv)
        
        self.main_nav.push_view(v)

    def prompt_log_set_data(self, data):
        fields = [
            {'type': 'number', 'title': 'Weight (lbs)', 'key': 'weight'},
            {'type': 'number', 'title': 'Reps', 'key': 'reps'}
        ]
        result = dialogs.form_dialog(title=f"Log {data['name']}", fields=fields)
        
        if result:
            weight = float(result.get('weight', 0))
            reps = int(result.get('reps', 0))
            
            self.current_workout_sets.append({
                'id': data['id'],
                'name': data['name'],
                'weight': weight,
                'reps': reps
            })
            
            self.main_nav.pop_view()
            self.update_workout_table()

    def finish_workout(self, sender):
        if not self.current_workout_sets:
            dialogs.alert("Empty Workout", "No sets logged!", "OK")
            return
            
        total_volume = sum([s['weight'] * s['reps'] for s in self.current_workout_sets])
        
        workout_id = database.create_workout(total_volume)
        
        for idx, s in enumerate(self.current_workout_sets):
            database.log_set(workout_id, s['id'], s['weight'], s['reps'], idx)
            
        dialogs.hud_alert("Workout Saved!")
        self.main_nav.pop_view()
        
        # Refresh dashboard (lazy way: just pop)
        # In real structure, dashboard view would observe DB
        
        # Auto-share prompt
        self.share_last_workout(None)

    def share_last_workout(self, sender):
        data = database.get_last_workout_summary()
        if not data:
            dialogs.alert("No Workouts", "Log a workout first.", "OK")
            return
            
        # Generate Text Summary
        text = f"🏋️ WLog Workout - {data['date']}\n"
        text += f"🔥 Total Volume: {data['volume']:,.0f} lbs\n\n"
        
        exercise_map = {}
        for row in data['sets']: # name, weight, reps
            name = row[0]
            if name not in exercise_map:
                exercise_map[name] = []
            exercise_map[name].append(f"{row[1]}x{row[2]}")
            
        for name, sets in exercise_map.items():
            text += f"• {name}: {', '.join(sets)}\n"
            
        text += "\n#WLog #TrainingStreak"
        
        # Use native iOS share sheet
        dialogs.share_text(text)

    def run(self):
        dashboard = self.create_dashboard()
        self.main_nav = ui.NavigationView(dashboard)
        self.main_nav.present('fullscreen')

if __name__ == '__main__':
    app = WLogApp()
    # Check if running in Pythonista (ui variable is a module)
    if 'MockUI' not in str(type(ui)):
        app.run()
    else:
        print("Code generated. Transfer to Pythonista 3 on iOS to run.")
