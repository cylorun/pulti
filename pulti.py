import wmi, win32gui, win32con,  psutil, threading, pythoncom, subprocess
import time, re, ahk, math, keyboard, os, json, logging, datetime, requests,sys,ctypes
import config 
from pygame import mixer 
from macro import Window
from tkinter import messagebox

VERSION = '0.3.0'

PULTI_DIR = f'{os.environ['USERPROFILE']}\\.Pulti'
CURRENT_LOG = f'{PULTI_DIR}\\logs\\{datetime.date.today()}.log'

THREADS = os.cpu_count()
INST_WIDTH = config.res[0]
INST_HEIGHT = config.res[1] 
RESETTING_HEIGHT = int(config.res[1] // float(config.settings['wide']))

PREVIEW_LOAD_PERCENT = 15
AFFINITY_DELAY = 0.1
RESET_DELAY = 0.1

DIRT_THREADS = THREADS
LOCK_THREADS = THREADS
PLAYING_THREADS = int(THREADS*0.6)
PREVIEW_THREADS = int(THREADS*0.5)
BACKGROUND_THREADS = int(THREADS*0.3)
INWORLD_THREADS = int(THREADS*0.1)

ahk = ahk.AHK()


instances = []
running = True

media_urls = ['https://cdn.discordapp.com/attachments/961288757410148433/1168621698627686420/lock.wav',
            'https://cdn.discordapp.com/attachments/1006684003409072279/1169207873604173904/ready.wav',
            'https://cdn.discordapp.com/attachments/961288757410148433/1168623957272956998/reset.wav',
            'https://cdn.discordapp.com/attachments/1006684003409072279/1169204149502619679/pulti.ico'
            ]


class MinecraftInstance:

    def __init__(self, window):
        self.hwnd = Window.get_hwnd(window)
        self.pid = Window.get_pid(window)
        self.locked = False
        self.path =  self.get_inst_path()
        self.num = int(re.sub(r'[^0-9]', '', self.path))
        self.create_new_world_key = self.get_from_settings('key_Create New World:')
        self.fullscreen_key = self.get_from_settings('key_key.fullscreen:')

        self.preview_paused = False
        self.inworld_paused = False
        logging.info(f'Instance {self.num} detected')



    def get_inst_path(self) -> str:
        try:
            pythoncom.CoInitialize()
            return str(wmi.WMI().Win32_Process(ProcessId=self.pid)[0].CommandLine).split('.path=')[1].split()[0].replace('natives','.minecraft').replace('/','\\')
        except wmi.x_wmi_uninitialised_thread as e:  # ^^ should work with any java version
            logging.error(e)
        finally:
            pythoncom.CoUninitialize()

    def get_from_settings(self, setting) -> str: 
        file = open(f'{self.path}\\config\\standardoptions.txt').read().splitlines()
        if '.txt' in file[0]: 
            file = open(file[0]).read().splitlines()

        for line in file:
            if setting in line:
                return line[len(setting)+13:] # +13 for "key.keyboard."
                        
    def get_wp_state(self) -> str:
        return open(f'{self.path}\\wpstateout.txt').read()
    
    def reset(self) -> None:
        self.preview_paused = False
        self.inworld_paused = False
        WindowManager.set_reset(self)
        ahk.run_script(f'ControlSend, , {{{self.create_new_world_key}}}, ahk_id {str(self.hwnd)}')

            
    def enter(self) -> None:
        if 'inworld' in self.get_wp_state():
            WindowManager.set_playing(self.hwnd)
            ObsManager.update_obs(str(self.num))
            if self.get_wp_state() == 'inworld,paused':
                ahk.run_script(f'ControlSend, , {{ESC}}, ahk_id {str(self.hwnd)}') # ! double pauses sometimes(more like double pauses every fucking time :/)

    def set_title(self, title = None) -> None:
        if title is None:
            win32gui.SetWindowText(self.hwnd, f'Minecraft* - Instance {self.num}')
        else:
            win32gui.SetWindowText(self.hwnd, title)

    def exit_world(self) -> None:  # ! why does this function take 13 years to run :/
        self.locked = False
        if Util.get_wall_mode() == 'g':
            WindowManager.set_instance_in_grid(self.hwnd,self.num)
        else: 
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, INST_WIDTH, RESETTING_HEIGHT, win32con.SWP_FRAMECHANGED)

        if config.settings['bypass'] and not len(Util.get_locked_instances()) == 0:
                Util.bypass()
        elif Util.get_wall_mode() == 'w':
                ObsManager.open_projector()

        Util.reset_instance(self)

        

            
class Util:

    @staticmethod
    def init() -> None:
        logging.basicConfig(
        level=logging.DEBUG, 
        format='[%(asctime)s] [%(levelname)s] %(message)s', 
        datefmt='%H:%M:%S', 
        handlers=[logging.FileHandler(CURRENT_LOG), logging.StreamHandler()]
        )
        logging.info(f'------------- Pulti v{VERSION} -------------')
        Util.redetect_instances()
        logging.info(f'Current settings:\n {str(config.settings).replace(',','\n')}')
        threading.Thread(target=Util.reset_helper, daemon=True).start()
        threading.Thread(target=Util.affinity_helper, daemon=True).start()
        logging.info('Ready!')
        Util.play_sound('ready.wav')
        Util.set_hotkeys()

    @staticmethod
    def redetect_instances():
        instances.clear()
        for mc in Window.find_by_title('Minecraft*'):
            instances.append(MinecraftInstance(mc))
        instances.sort(key=lambda x: x.num)
        Util.set_instance_positions()
        WindowManager.set_titles()

    @staticmethod
    def set_instance_positions():
        if Util.get_wall_mode() == 'w':
            for inst in instances:
                WindowManager.set_reset(inst)
        elif Util.get_wall_mode() == 'g':
            WindowManager.make_instance_grid(instances)

    @staticmethod
    def get_resets(file) -> int:
        try:
            file_path = f'{PULTI_DIR}\\{file}'
            if not os.path.exists(file_path):
                print(f"File {file_path} does not exist.")
                return 0

            with open(file_path, 'r') as resets_file:
                r = resets_file.read().strip()
                if not r:
                    print(f"File {file_path} is empty.")
                    return 0
                return int(r)
        except Exception as e:
            print(f"An error occurred: {e}")
            return 0


    @staticmethod
    def update_reset_count(count=1) -> None:
        with open(f'{PULTI_DIR}\\resets.txt', 'w') as resets, open(f'{PULTI_DIR}\\session_resets.txt', 'w') as session_resets:
            v = Util.get_resets('resets.txt') + count
            resets.write(str(v))
            session_resets.write(str(Util.get_resets('session_resets.txt') + count))

    @staticmethod
    def get_wall_mode() -> str:
        match config.settings['mode']:
            case 'Wall': return 'w'
            case 'Grid': return 'g'

    @staticmethod
    def get_window_mode() -> str:
        match config.settings['window_mode']:
            case 'Fullscreen': return 'f'
            case 'Borderless': return 'b'
            case 'Windowed': return 'w'

    @staticmethod
    def set_hotkeys()-> None:
        keyboard.add_hotkey(config.settings['reset_single'], Util.reset_from_projector)
        keyboard.add_hotkey(config.settings['play'], Util.join_world_from_projector)
        keyboard.add_hotkey(config.settings['reset_all'], Util.reset_all)
        keyboard.add_hotkey(config.settings['exitworld'], Util.exit_world)
        keyboard.add_hotkey(config.settings['focus_reset'], Util.reset_focus)
        keyboard.add_hotkey(config.settings['lock'], Util.lock_instance)
        keyboard.wait('f9')

    @staticmethod
    def mouse_pos_to_inst_num() -> int:
        mx, my = win32gui.GetCursorPos()
        return (math.floor(my / (INST_HEIGHT / config.settings['rows'])) * config.settings['cols']) + math.floor(mx / (INST_WIDTH / config.settings['cols']))

    @staticmethod
    def projector_active() -> bool:
        return 'Projector' in Window.get_current().get_title()

    @staticmethod
    def mc_active() -> bool:
        return 'Minecraft*' in Window.get_current().get_title()

    @staticmethod
    def get_playing_instance() -> object:
        hwnd = Window.get_current().get_hwnd()
        for inst in instances:
            if hwnd == inst.hwnd:
                return inst

    @staticmethod
    def reset_instance(inst) -> None:  
        Util.play_sound('reset.wav')
        threading.Thread(target=inst.reset).start()  

    @staticmethod
    def reset_all()-> None:
        Util.update_reset_count(len(instances)-len(Util.get_locked_instances()))
        if Util.allow_hotkey():
            for inst in instances:
                if not inst.locked:
                    Util.reset_instance(inst)

    @staticmethod
    def exit_world() -> None:
        if Util.mc_active():
            inst = Util.get_playing_instance()
            inst.exit_world()

    @staticmethod
    def reset_focus() -> None:
        if Util.allow_hotkey():
            inst = instances[Util.mouse_pos_to_inst_num()]
            Util.lock_instance()
            Util.reset_all()
            if 'inworld' in inst.get_wp_state():
                inst.enter()

    @staticmethod
    def lock_instance() -> None:
        if Util.allow_hotkey():
            inst = instances[Util.mouse_pos_to_inst_num()]
            inst.locked = True
            Util.play_sound('lock.wav')
            
    @staticmethod
    def get_locked_instances() -> list:
        locked = []
        for inst in instances:
            if inst.locked == True:
                locked.append(inst)
        return locked
    
    
    @staticmethod
    def reset_from_projector()-> None:
        Util.update_reset_count()
        if Util.allow_hotkey():
            Util.reset_instance(instances[Util.mouse_pos_to_inst_num()])

    @staticmethod
    def join_world_from_projector()-> None:
        if Util.allow_hotkey():
            instances[Util.mouse_pos_to_inst_num()].enter()
    
    @staticmethod
    def bypass() -> None:
        locked = Util.get_locked_instances()
        if len(locked) >= 1:
            locked[0].enter()

    @staticmethod
    def set_threads(pid, count_threads) -> None:
        cores = list(range(count_threads))
        psutil.Process(pid).cpu_affinity(cores)

    @staticmethod
    def play_sound(audio_file) -> None:
        try:
            mixer.init()
            mixer.music.load(f'{PULTI_DIR}\\media\\{audio_file}')
            mixer.music.play()
        except Exception:
            logging.error(f'Audio` file not founnd, {audio_file.split('\\')[-1]}')
            Util.download_assets()


    @staticmethod
    def allow_hotkey() -> bool:
        if Util.get_wall_mode() == 'w': 
            return Util.projector_active()
        elif Util.get_wall_mode() == 'g': 
            if Util.mc_active():
                inst = Util.get_playing_instance()
                state = inst.get_wp_state()
                if  'inworld,paused' or 'previewing' or 'generating' in state:
                    return True
                else:
                    return False
            else: 
                return False
            
    @staticmethod
    def close_instances() -> None:
        for inst in instances:
            os.kill(inst.pid, 15) 

    
    def save_instance_paths() -> None: # wip
        paths = {}
        for inst in instances:
            paths[inst.num] = inst.path
            with open("paths.json", "w") as json_file:
                json.dump(paths, json_file)

    def load_instance_paths() -> None:
        try: 
            with open("paths.json", "r") as json_file:
                data = json.load(json_file)
                for inst in instances:
                    inst.path = data[inst.num]
        except FileNotFoundError:
            pass

    @staticmethod
    def get_resetting() -> list:
        li = []
        for inst in instances:
            if 'generating' or 'previewing' in inst.get_wp_state():
                li.append(inst)
        return li
    

    def reset_helper() -> None:
        while running:
            for inst in Util.get_resetting():
                if not inst.preview_paused and 'previewing' in inst.get_wp_state():
                    ahk.run_script(f'ControlSend, , {{F3 down}}{{Esc down}}{{F3 up}}{{Esc up}}, ahk_id {str(inst.hwnd)}')
                    inst.preview_paused = True
                elif inst.get_wp_state() == 'inworld,unpaused' and not inst.inworld_paused:
                    ahk.run_script(f'ControlSend, , {{F3 down}}{{Esc down}}{{F3 up}}{{Esc up}}, ahk_id {str(inst.hwnd)}')
                    if inst.get_wp_state() == 'inworld,paused':
                        inst.inworld_paused = True
            time.sleep(RESET_DELAY)

    def affinity_helper():
        while running:
            for inst in instances:
                if inst.locked:
                    Util.set_threads(inst.pid, LOCK_THREADS)
                else:
                    state = inst.get_wp_state()
                    if 'previewing' in state: 
                        progress = int(re.sub(r'[^0-9]', '', state))
                        if progress < PREVIEW_LOAD_PERCENT:
                            Util.set_threads(inst.pid, DIRT_THREADS)
                        else:
                            Util.set_threads(inst.pid, PREVIEW_THREADS)
                    else:
                        match state:
                            case 'generating': Util.set_threads(inst.pid, DIRT_THREADS)
                            case 'inworld': Util.set_threads(inst.pid, INWORLD_THREADS)
            time.sleep(AFFINITY_DELAY)
    
    def download_assets(path, a_li):
        # logging.info('Downloading assets')
        for url in a_li:
            try:
                response = requests.get(url)
                file_name = url.split('/')[-1]

                with open(f'{path}\\{file_name}', "wb") as file:
                    file.write(response.content)
                    # logging.info(f'Downloaded {file_name}, to {os.getcwd()}/assets')

            except FileExistsError as e:
                # logging.error(f'File already exists \n {e}')
                print(e)
        # logging.info('Finished downloading all assets')


    def make_pulti_dir():
        if not os.path.exists(PULTI_DIR):
            threading.Thread(target=messagebox.showinfo,args=("Pulti Info", "Downloading assets, this might take a bit")).start()
            os.makedirs(f'{PULTI_DIR}\\media')
            os.makedirs(f'{PULTI_DIR}\\scripts')
            os.makedirs(f'{PULTI_DIR}\\logs')
            Util.download_assets(f'{PULTI_DIR}\\media', media_urls)
            Util.download_assets(f'{PULTI_DIR}\\scripts',['https://gist.github.com/cylorun/4fc69762a138f8ad88fb509d3d24bf73/raw/8d6995f5dbc8f0e667d0acb3a3b81b25963a2d8c/pulti_obs.lua'])
    
    def open_exporer(path):
        subprocess.Popen(f'explorer {path}')
        messagebox.showinfo('Tutorial','Go to OBS > Tools > Scripts press the " + " and add this script there!')

class WindowManager:

    @staticmethod
    def set_playing(hwnd):
        if Util.get_window_mode() == 'b':
            WindowManager.set_borderless_pos(hwnd, 0, 0, INST_WIDTH, INST_HEIGHT)
        elif Util.get_window_mode() == 'w':
            WindowManager.set_windowed_pos(hwnd, 0, 0, INST_WIDTH, INST_HEIGHT)
        WindowManager.maximize_window(hwnd)
        WindowManager.activate_window(hwnd)

    @staticmethod
    def set_windowed_pos(hwnd, x, y, w, h) -> None:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) | win32con.WS_CAPTION | win32con.WS_THICKFRAME
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_FRAMECHANGED)

    @staticmethod
    def set_borderless_pos(hwnd,x, y, w , h) -> None:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_FRAMECHANGED)

    @staticmethod
    def set_instance_in_grid(hwnd, num) -> None:
        num = num - 1
        w = INST_WIDTH // config.settings['cols']
        h = (INST_HEIGHT - int(config.settings['taskbar_height'])) // config.settings['rows']
        x = (num % config.settings['cols'])
        y = (num // config.settings['cols'])  # Divide by the number of columns, not rows

        if Util.get_window_mode() == 'b':
            WindowManager.set_borderless_pos(hwnd, x*w, y*h , w, h) 
        elif Util.get_window_mode() == 'w':
            WindowManager.set_windowed_pos(hwnd, x*w ,y*h , w, h) 

    @staticmethod
    def make_instance_grid(inst_list) -> None:
        for inst in inst_list:
            WindowManager.set_instance_in_grid(inst.hwnd, inst.num)

    @staticmethod    
    def set_reset(inst):
        if Util.get_wall_mode() == 'w':
            match Util.get_window_mode():
                case 'b': WindowManager.set_borderless_pos(inst.hwnd, 0, 0, INST_WIDTH, RESETTING_HEIGHT)
                case 'w': WindowManager.set_windowed_pos(inst.hwnd, 0, 0, INST_WIDTH, RESETTING_HEIGHT)
        else:
            WindowManager.set_instance_in_grid(inst.hwnd, inst.num)


    @staticmethod
    def maximize_window(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        
    @staticmethod
    def activate_window(hwnd):
        user32 = ctypes.windll.user32
        user32.SwitchToThisWindow(hwnd, True)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)

    @staticmethod
    def set_titles():
        for inst in instances:
            inst.set_title()

class ObsManager:

    @staticmethod
    def update_obs(scene):
        if not Util.get_wall_mode == 'g':
            with open(f'{PULTI_DIR}\\obs.txt','w') as file:
                if scene == 'w':
                    s = config.settings['wall_scene']
                else:
                    s =f'{config.settings['inst_format_obs'].replace('*', scene)}'
                file.write(s)
            logging.info(f'Obs cmd: {s}')

    @staticmethod
    def get_projector_hwnd():
        win = Window.find_by_title('Projector')
        return Window.get_hwnd(win[0])

    @staticmethod
    def open_projector() -> None:  #! shit doesnt work :/, sometimes instances seem to be put in "always on top"
        try:
            ObsManager.update_obs('w')
            WindowManager.activate_window(ObsManager.get_projector_hwnd())
        except Exception as e:
            logging.error(f'Projector not found, {e}')


if __name__ == '__main__':
    print('runnin the roon one!')
    Util.update_reset_count(14)
