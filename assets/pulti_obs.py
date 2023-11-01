import obspython as obs
import time, os

def switch_scene(scene_name):
    scene_source = obs.obs_get_source_by_name(scene_name)
    if scene_source:
        obs.obs_frontend_set_current_scene(scene_source)
        obs.obs_source_release(scene_source)

def script_description():
    return "Switches scenes based on the content of 'obs.txt'."

def script_update(settings):
    pass

def script_load(settings):
    obs.script_log(obs.LOG_INFO, "Script loaded")

def script_save(settings):
    pass

def script_tick(seconds):
    f =os.getcwd().replace('\\assets','\\obs.txt')
    print(f)
    return
    with open(f, 'r') as file:
        new_scene = file.read()
    current_scene = obs.obs_frontend_get_current_scene()
    
    if new_scene != current_scene:
        switch_scene(new_scene)


obs.timer_add(script_tick, 3000)  
