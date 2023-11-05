local obs = obslua

local timer_interval = 500 
local pulti_dir = os.getenv("UserProfile"):gsub("\\", "/") .. "/.Pulti/"
local old_scene  = ''

function read_file()
    local file = io.open(pulti_dir..'obs.txt', "r")
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
        print('Scene not found: '.. scene_name)
        return
    end
    obs.obs_frontend_set_current_scene(scene_source)
    obs.obs_source_release(scene_source)
end

function on_timer()
    local new_scene = read_file()
    if  old_scene ~= new_scene then
        switch_scene(new_scene)
        old_scene = new_scene
    end
end

function script_description()
    return "Everything is configured in the Pulti executable :)"
end

function script_load(settings)
    old_scene = read_file()
    switch_scene(old_scene)
    obs.timer_add(on_timer, timer_interval)
end

function script_unload()
    obs.timer_remove(on_timer)
end
