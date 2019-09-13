import os
import toga
from toga.style import Pack 
from toga.style.pack import COLUMN, ROW
from cwl_airflow.app.launch import Launcher


class App(toga.App):

    __airflow_home_default = "~/airflow"
    __launcher = None

    def load(self, widget):
        self.__launcher.load()

    def unload(self, widget):
        self.__launcher.unload()

    def startup(self):
        # Create Launcher
        self.__launcher = Launcher(self.__airflow_home_default)
        self.__launcher.configure()

        # Create a main window with a name matching the app
        self.main_window = toga.MainWindow(title=self.name, size=(250,100))

        # Create a main content box
        main_box = toga.Box()
        main_box.style.update(direction=ROW, padding=20)

        # Add load button
        load_button = toga.Button("Load", on_press=self.load)
        load_button.style.padding = 25
        main_box.add(load_button)

        # Add unload button
        unload_button = toga.Button("Unload", on_press=self.unload)
        unload_button.style.padding = 25
        main_box.add(unload_button)

        # Add the content on the main window
        self.main_window.content = main_box

        # Show the main window
        self.main_window.show()

def main():
    return App('CWL-Airflow Control Panel', 'com.biowardrobe')
