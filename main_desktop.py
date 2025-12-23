from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import ThreeLineListItem, OneLineListItem
from kivy.properties import ObjectProperty, StringProperty
from kivymd.toast import toast
from kivy.core.window import Window
from kivy.metrics import dp
from kivymd.uix.menu import MDDropdownMenu
import database

# Ensure DB is initialized
database.init_db()

KV = '''
<DashboardScreen>:
    name: "dashboard"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(20)
        
        MDLabel:
            text: "WLog (Windows Test)"
            font_style: "H4"
            halign: "center"
            size_hint_y: None
            height: dp(50)
            
        MDCard:
            orientation: "vertical"
            padding: dp(20)
            size_hint: None, None
            size: "280dp", "120dp"
            pos_hint: {"center_x": .5}
            radius: [12]
            md_bg_color: app.theme_cls.bg_darkest
            
            MDLabel:
                text: "CURRENT STREAK"
                theme_text_color: "Custom"
                text_color: 0.5, 0.5, 0.5, 1
                font_style: "Caption"
            
            MDLabel:
                id: streak_label
                text: "0 DAYS"
                theme_text_color: "Custom"
                text_color: 0, 1, 0, 1
                font_style: "H3"
                bold: True

        MDFillRoundFlatButton:
            text: "START LIVE WORKOUT"
            font_size: "18sp"
            size_hint_x: 0.8
            pos_hint: {"center_x": .5}
            on_release: app.sm.current = "workout_screen"

        MDFillRoundFlatButton:
            text: "EXERCISE LIBRARY"
            md_bg_color: 0.3, 0.3, 0.3, 1
            font_size: "18sp"
            size_hint_x: 0.8
            pos_hint: {"center_x": .5}
            on_release: 
                app.sm.current = "library_screen"
                root.load_library()
        
        MDFillRoundFlatButton:
            text: "SHARE LAST WORKOUT"
            md_bg_color: 1, 0.6, 0, 1
            font_size: "18sp"
            size_hint_x: 0.8
            pos_hint: {"center_x": .5}
            on_release: root.share_mockup()

        Widget:

<LibraryScreen>:
    name: "library_screen"
    
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "Exercise Library"
            left_action_items: [["arrow-left", lambda x: app.go_home()]]
            elevation: 2

        MDScrollView:
            MDList:
                id: library_list

<WorkoutScreen>:
    name: "workout_screen"
    
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "Live Workout"
            left_action_items: [["arrow-left", lambda x: app.go_home()]]
            right_action_items: [["check", lambda x: root.finish_workout()]]

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(20)
            spacing: dp(10)
            size_hint_y: None
            height: dp(200)

            MDBoxLayout:
                spacing: dp(10)
                MDTextField:
                    id: exercise_input
                    hint_text: "Select Exercise"
                    mode: "rectangle"
                
                MDIconButton:
                    icon: "magnify"
                    on_release: root.open_search_menu()

            MDBoxLayout:
                spacing: dp(10)
                MDTextField:
                    id: weight_input
                    hint_text: "Weight"
                    input_filter: "float"
                    mode: "rectangle"
                MDTextField:
                    id: reps_input
                    hint_text: "Reps"
                    input_filter: "int"
                    mode: "rectangle"

            MDRaisedButton:
                text: "ADD SET"
                pos_hint: {"center_x": .5}
                on_release: root.add_set()

        MDScrollView:
            MDList:
                id: workout_list

ScreenManager:
    DashboardScreen:
        id: dashboard
    LibraryScreen:
        id: library_screen
    WorkoutScreen:
        id: workout_screen
'''

from kivy.clock import Clock

class DashboardScreen(MDScreen):
    def on_enter(self):
        Clock.schedule_once(self.update_streak)

    def update_streak(self, dt):
        streak = database.get_streak()
        if 'streak_label' in self.ids:
            self.ids.streak_label.text = f"{streak} DAYS"
        
    def load_library(self):
        # We trigger loading in the library screen, 
        # but to keep it simple we can access it via app
        lib_screen = MDApp.get_running_app().sm.get_screen('library_screen')
        lib_screen.refresh_list()
        
    def share_mockup(self):
        data = database.get_last_workout_summary()
        if not data:
            toast("No workout to share")
            return
        print("--- SHARED TEXT ---")
        print(f"Workout Date: {data['date']}")
        print(f"Volume: {data['volume']}")
        toast("Summary printed to console (Mock Share)")

class LibraryScreen(MDScreen):
    def refresh_list(self):
        self.ids.library_list.clear_widgets()
        exercises = database.get_all_exercises()
        
        # Group by muscle
        groups = {}
        for e in exercises:
            m = e['muscle']
            if m not in groups: groups[m] = []
            groups[m].append(e)
            
        for muscle in sorted(groups.keys()):
            # Header
            self.ids.library_list.add_widget(
                OneLineListItem(text=f"-- {muscle} --", divider=None, theme_text_color="Primary")
            )
            for e in groups[muscle]:
                self.ids.library_list.add_widget(
                    ThreeLineListItem(
                        text=e['name'],
                        secondary_text=f"Difficulty: {e['difficulty']} | Category: {e['category']}",
                        tertiary_text=e['instructions'][:50] + "..."
                    )
                )

class WorkoutScreen(MDScreen):
    current_sets = []
    current_exercise_id = None
    menu = None

    def open_search_menu(self):
        exercises = database.get_all_exercises()
        # Sort by muscle then name for cleaner list
        exercises.sort(key=lambda x: (x['muscle'], x['name']))
        
        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": "+ Add Custom Exercise",
                "height": dp(56),
                "on_release": self.add_custom_exercise_dialog,
            }
        ] + [
            {
                "viewclass": "OneLineListItem",
                "text": f"{e['muscle']} - {e['name']}",
                "height": dp(56),
                "on_release": lambda x=e: self.set_exercise(x),
            } for e in exercises
        ]
        self.menu = MDDropdownMenu(
            caller=self.ids.exercise_input,
            items=menu_items,
            width_mult=5,
            max_height=dp(400),
        )
        self.menu.open()

    def add_custom_exercise_dialog(self):
        self.menu.dismiss()
        print("--- ADD CUSTOM EXERCISE (Mock) ---")
        print("On iOS this opens a Form Dialog.")
        # For desktop test, we can just insert a Dummy one to prove DB logic works
        try:
            database.add_custom_exercise("Custom Press", "Shoulders")
            toast("Created 'Custom Press' (Shoulders)")
            # Reopen menu to show it
            self.open_search_menu()
        except ValueError as e:
            toast(str(e))

    def set_exercise(self, exercise_data):
        self.ids.exercise_input.text = exercise_data['name']
        self.current_exercise_id = exercise_data['id']
        self.menu.dismiss()

    def add_set(self):
        w = self.ids.weight_input.text
        r = self.ids.reps_input.text
        if not w or not r or not self.current_exercise_id:
            toast("Fill all fields")
            return
            
        self.current_sets.append({
            'exercise_id': self.current_exercise_id,
            'name': self.ids.exercise_input.text,
            'weight': float(w),
            'reps': int(r)
        })
        
        self.ids.workout_list.add_widget(
            OneLineListItem(text=f"{self.ids.exercise_input.text}: {w} x {r}")
        )
        self.ids.weight_input.text = ""
        self.ids.reps_input.text = ""

    def finish_workout(self):
        if not self.current_sets:
            toast("Empty workout")
            return
            
        vol = sum([s['weight'] * s['reps'] for s in self.current_sets])
        w_id = database.create_workout(vol)
        
        for idx, s in enumerate(self.current_sets):
            database.log_set(w_id, s['exercise_id'], s['weight'], s['reps'], idx)
            
        toast("Workout Saved!")
        self.current_sets = []
        self.ids.workout_list.clear_widgets()
        MDApp.get_running_app().go_home()

class WLogDesktopApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.sm = Builder.load_string(KV)
        return self.sm

    def go_home(self):
        self.sm.current = "dashboard"

if __name__ == "__main__":
    Window.size = (400, 750)
    WLogDesktopApp().run()
