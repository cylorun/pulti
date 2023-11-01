import config
import threading, sys, json, os
import tkinter as tk

from pulti import Util
from pulti import WindowManager
from tkinter import ttk
from tkinter import Scale
from tkinter import messagebox

settings = config.settings
if not os.path.exists('assets'):
        os.makedirs('assets')
        messagebox.showinfo("Pulti Info", "Downloading assets, this might take a bit")
        threading.Thread(target=Util.download_assets, daemon=True)

def load_settings():
    try:
        with open("config.json", "r") as json_file:
            data = json.load(json_file)
            for key in settings:
                if key in data:
                    settings[key] = data[key]
    except FileNotFoundError:
        pass

def save_settings():
    settings["bypass"] = bypass_var.get()
    settings["mode"] = mode_var.get()
    settings["window_mode"] = window_mode_var.get()
    settings["rows"] = row_var.get()
    settings["cols"] = col_var.get()
    settings["wide"] = slider_var.get()
    
    for key, value in textboxes.items():
        settings[key] = value.get()
    
    with open("config.json", "w") as json_file:
        json.dump(settings, json_file)

def add_textbox(text:str, value, i):
    tk.Label(hotkeys_panel, text=text.capitalize().replace('_',' ')).grid(row=i,column=0)
    textbox = tk.Entry(hotkeys_panel)
    textbox.grid(row=i,column=1)
    textboxes[text] = textbox
    textbox.insert(0, value)

def on_close():
    root.destroy()
    sys.exit()

textboxes = {}
root = tk.Tk()

notebook = ttk.Notebook(root)
options_panel = ttk.Frame(notebook)
hotkeys_panel = ttk.Frame(notebook)
main_panel = ttk.Frame(notebook)

notebook.pack(fill='both', expand=True)
notebook.add(hotkeys_panel,text="Hotkeys")
notebook.add(options_panel, text="Options")
notebook.add(main_panel, text="Pulti")

root.title("Settings")
root.iconbitmap("assets\\pulti.ico")
root.resizable(False,False)
root.geometry('300x400')

load_settings()
mode_var = tk.StringVar(value=settings["mode"])
tk.Label(options_panel, text="Mode").grid(row=1,column=0)
ttk.Combobox(options_panel, textvariable=mode_var, values=["Wall", "Grid"]).grid(row=2,column=0)

window_mode_var = tk.StringVar(value=settings["window_mode"])
tk.Label(options_panel, text="Window Mode").grid(row=3,column=0)
ttk.Combobox(options_panel, textvariable=window_mode_var, values=["Fullscreen", "Borderless","Windowed"]).grid(row=4,column=0)

bypass_var = tk.BooleanVar(value=settings["bypass"])
tk.Checkbutton(options_panel, text="Bypass wall", variable=bypass_var).grid(row=5,column=0)


row_var = tk.IntVar(value=settings["rows"])
tk.Label(options_panel, text="Rows").grid(row=6,column=0)
tk.Spinbox(options_panel, from_=1, to=99, textvariable=row_var).grid(row=7,column=0)

col_var = tk.IntVar(value=settings["cols"])
tk.Label(options_panel, text="Cols").grid(row=8,column=0)
tk.Spinbox(options_panel, from_=1, to=99, textvariable=col_var).grid(row=9,column=0)


slider_var = tk.DoubleVar(value=settings['wide'])
tk.Label(options_panel, text="Width multiplier").grid(row=10,column=0)
Scale(options_panel, from_=1, to=5, resolution=0.1, variable=slider_var, orient='horizontal').grid(row=11,column=0)
tk.Button(options_panel, text="Save", command=save_settings).grid(row=13,column=0)
tk.Button(hotkeys_panel, text="Save", command=save_settings).grid(row=9,column=0)

ts = ['inst_format_obs','wall_scene','reset_all','play','focus_reset','reset_single','exitworld','lock']
for i,s in enumerate(ts):
    add_textbox(s,settings[s],i)

tk.Button(main_panel, text="Redetect Instances", command= Util.redetect_instances).grid(row=1,column=1)
tk.Button(main_panel,text="Set Titles", command=WindowManager.set_titles).grid(row=2,column=1)
tk.Button(main_panel,text="Close Instances",command=Util.close_instances).grid(row=3,column=1)

threading.Thread(target=Util.init, daemon=True).start() # daemon thread so the program can instantly shut down when wanted, instead of having to wait

root.protocol("WM_DELETE_WINDOW", on_close)
notebook.select(main_panel)
root.mainloop()
