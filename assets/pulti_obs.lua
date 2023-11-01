local obs = obslua

local file_path = 'C' .. debug.getinfo(1, "S").source:sub(2):match("^(.*[/\\])") .. "obs.txt"
local timer_interval = 500 
local old_scene = ''


function read_file()
    local file = io.open(file_path, "r")
    if file then
        local content = file:read("*line")
        file:close()
        return content
    else
        print('File not found')
        return ""
    end
end

function switch_scene(scene_name)
    local scene_source = obs.obs_get_source_by_name(scene_name)
    if not scene_source then
        print('Error: Scene not found')
        return
    end
    obs.obs_frontend_set_current_scene(scene_source)
    obs.obs_source_release(scene_source)
end

function on_timer()
    local new_scene = read_file()
    if old_scene ~= new_scene then
        switch_scene(read_file())
        old_scene = new_scene
    end
end

function script_description()
    return "All settings will be configured inside the pulti executable!"
end

function script_load(settings)
    old_scene = read_file()
    switch_scene(old_scene)
    obs.timer_add(on_timer, timer_interval)
end

function script_unload()
    obs.timer_remove(on_timer)
end
