-- Universal Snorkel — game-engine (GE) side extension
--
-- Responsibilities:
--   * Remember the global snorkel mode ("off" / "high" / "max") and persist it
--     to the user folder so it survives game restarts.
--   * Inject the vehicle-side extension (universalSnorkelVehicle) into every
--     vehicle: the ones already spawned when the mod loads, and every vehicle
--     spawned afterwards (onVehicleSpawned hook).
--   * Broadcast mode changes to all spawned vehicles.
--
-- The actual hydrolock protection happens in the vehicle Lua VM, see:
--   lua/vehicle/extensions/universalSnorkelVehicle.lua

local M = {}

local logTag = "universalSnorkel"
local settingsPath = "settings/universalSnorkel.json"

local state = {
  -- default OFF: visible snorkel parts (e.g. the D-Series ones) decide the
  -- wading depth on their own; enable a universal mode via the keybind or
  -- console when you want an invisible snorkel on any other car.
  mode = "off"
}

local VALID_MODES = {off = true, small = true, medium = true, tall = true, max = true}

local function sanitizeMode(mode)
  if mode == "high" then return "tall" end -- pre-1.1 name
  if VALID_MODES[mode] then
    return mode
  end
  return "off"
end

local function loadSettings()
  if type(jsonReadFile) ~= "function" then return end
  local ok, data = pcall(jsonReadFile, settingsPath)
  if ok and type(data) == "table" then
    state.mode = sanitizeMode(data.mode)
  end
end

local function saveSettings()
  if type(jsonWriteFile) ~= "function" then return end
  pcall(jsonWriteFile, settingsPath, state, true)
end

-- Command queued into a vehicle's Lua VM. Loading an already loaded extension
-- is a no-op, so this is safe to send repeatedly.
local function buildVehicleCommand(silent)
  return string.format(
    "extensions.load('universalSnorkelVehicle') if extensions.universalSnorkelVehicle then extensions.universalSnorkelVehicle.setMode(%q, %s) end",
    state.mode, silent and "true" or "false")
end

local function forEachVehicle(callback)
  local ok, err = pcall(function()
    if type(getAllVehicles) == "function" then
      for _, veh in ipairs(getAllVehicles()) do
        if veh then callback(veh) end
      end
    elseif be then
      for i = 0, be:getObjectCount() - 1 do
        local veh = be:getObject(i)
        if veh then callback(veh) end
      end
    end
  end)
  if not ok then
    log("W", logTag, "Failed to enumerate vehicles: " .. tostring(err))
  end
end

local function applyToAllVehicles(silent)
  local cmd = buildVehicleCommand(silent)
  forEachVehicle(function(veh)
    veh:queueLuaCommand(cmd)
  end)
end

-- Public API ---------------------------------------------------------------

-- Called from the vehicle-side extension when the player cycles the mode,
-- and usable from the console, e.g.:
--   extensions.universalSnorkel.setGlobalMode("tall")
-- Valid modes: "off", "small", "medium", "tall", "max"
local function setGlobalMode(newMode)
  state.mode = sanitizeMode(newMode)
  saveSettings()
  -- silent = true: the vehicle that initiated the change already showed a UI
  -- message; other vehicles pick the mode up quietly.
  applyToAllVehicles(true)
  log("I", logTag, "Global snorkel mode set to '" .. state.mode .. "'")
end

local function getMode()
  return state.mode
end

-- Game hooks ---------------------------------------------------------------

local function onVehicleSpawned(vehicleId)
  if not be then return end
  local veh = be:getObjectByID(vehicleId)
  if veh then
    veh:queueLuaCommand(buildVehicleCommand(true))
  end
end

local function onExtensionLoaded()
  loadSettings()
  applyToAllVehicles(true)
  log("I", logTag, "Universal Snorkel loaded — current mode: '" .. state.mode .. "'")
end

M.setGlobalMode = setGlobalMode
M.getMode = getMode
M.onVehicleSpawned = onVehicleSpawned
M.onExtensionLoaded = onExtensionLoaded

return M
