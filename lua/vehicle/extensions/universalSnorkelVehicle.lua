-- Universal Snorkel — vehicle-side extension
--
-- Gives EVERY vehicle with a combustion engine a functional snorkel without
-- editing any jbeam.
--
-- Background (see docs/HOW_IT_WORKS.md for the full write-up):
--   BeamNG floods/hydrolocks an engine when ALL nodes of its "engine_intake"
--   engineGroup are underwater ("waterDamage" property in the engine jbeam).
--   The flooding state is accumulated frame by frame in the combustion engine
--   powertrain device (vehicle Lua VM). This extension prevents that
--   accumulator from ever reaching the hydrolock threshold while the virtual
--   snorkel opening is above the waterline.
--
-- Modes:
--   off    — stock behaviour, engine floods as usual
--   small  — snorkel opening at ~hood height (55% of the vehicle's height)
--   medium — snorkel opening at ~mirror height (75% of the vehicle's height)
--   tall   — snorkel opening at the vehicle's highest point (roof line)
--   max    — intake is fully waterproof, engine never hydrolocks
--
-- In small/medium/tall the engine keeps running while the water is below the
-- snorkel opening; once the water reaches or passes it, vanilla flooding
-- takes over and the engine starts hydrolocking exactly like stock.
--
-- The mode is global for all vehicles and is coordinated by the GE-side
-- extension (lua/ge/extensions/universalSnorkel.lua).

local M = {}

local huge = math.huge
local abs = math.abs

local MODE_ORDER = {"off", "small", "medium", "tall", "max"}
local VALID_MODES = {off = true, small = true, medium = true, tall = true, max = true}
local MODE_LABELS = {
  off = "OFF — stock air intake",
  small = "SMALL — hood-height snorkel",
  medium = "MEDIUM — mirror-height snorkel",
  tall = "TALL — roof-height snorkel",
  max = "MAX — fully waterproof intake"
}
-- snorkel opening height as a fraction of the vehicle's total height
local MODE_HEIGHT_FRACTION = {small = 0.55, medium = 0.75, tall = 1.0}

local logTag = "universalSnorkelVehicle"

local mode = "off" -- real mode is pushed in by the GE extension right after load
local engines = {} -- { {device = <table>, floodKeys = {"floodLevel", ...}}, ... }
local sensorCids = {} -- mode -> node cid used as the snorkel opening
local snorkelUnderwater = false
local warnedNoFloodField = false
local rescanTimer = 0

-- Engine discovery -----------------------------------------------------------

-- Collect every numeric field on the engine device whose name contains
-- "flood". As of game version 0.36 this is the flood accumulator
-- (e.g. floodLevel); matching by pattern keeps the mod working if the exact
-- name changes between game versions.
local function collectFloodKeys(device)
  local keys = {}
  for key, value in pairs(device) do
    if type(key) == "string" and type(value) == "number" and key:lower():find("flood", 1, true) then
      keys[#keys + 1] = key
    end
  end
  return keys
end

local function scanEngines()
  engines = {}
  local devices = {}

  -- Preferred: all combustion engines (also covers multi-engine mods)
  local ok, result = pcall(function()
    if powertrain and powertrain.getDevicesByType then
      return powertrain.getDevicesByType("combustionEngine")
    end
  end)
  if ok and type(result) == "table" then
    for _, dev in pairs(result) do
      devices[#devices + 1] = dev
    end
  end

  -- Fallback 1: walk all powertrain devices and filter by type
  if #devices == 0 then
    local ok2, all = pcall(function()
      return powertrain and powertrain.getDevices and powertrain.getDevices()
    end)
    if ok2 and type(all) == "table" then
      for _, dev in pairs(all) do
        if type(dev) == "table" and dev.type == "combustionEngine" then
          devices[#devices + 1] = dev
        end
      end
    end
  end

  -- Fallback 2: the conventional main engine name
  if #devices == 0 then
    local ok3, dev = pcall(function()
      return powertrain and powertrain.getDevice and powertrain.getDevice("mainEngine")
    end)
    if ok3 and type(dev) == "table" then
      devices[1] = dev
    end
  end

  for _, dev in ipairs(devices) do
    if type(dev) == "table" then
      local floodKeys = collectFloodKeys(dev)
      engines[#engines + 1] = {device = dev, floodKeys = floodKeys}
      if #floodKeys == 0 and not warnedNoFloodField then
        warnedNoFloodField = true
        log("W", logTag, "No flood accumulator field found on engine '" .. tostring(dev.name)
          .. "'. Hydrolock protection may not work on this game version — please report this.")
      end
    end
  end
end

-- Pick one sensor node per snorkel height: the node whose design-space Z is
-- closest to the target height (bottom + fraction * vehicle height). For
-- "tall" this is simply the highest node of the vehicle (roof / rollcage).
local function findSensorNodes()
  sensorCids = {}
  local ok, err = pcall(function()
    if not (v and v.data and v.data.nodes) then return end
    local minZ, maxZ = huge, -huge
    for _, node in pairs(v.data.nodes) do
      local p = node.pos
      if p and type(p.z) == "number" then
        if p.z < minZ then minZ = p.z end
        if p.z > maxZ then maxZ = p.z end
      end
    end
    if maxZ <= minZ then return end

    for modeName, fraction in pairs(MODE_HEIGHT_FRACTION) do
      local targetZ = minZ + fraction * (maxZ - minZ)
      local bestCid, bestDist = nil, huge
      for cid, node in pairs(v.data.nodes) do
        local p = node.pos
        if p and type(p.z) == "number" then
          local dist = abs(p.z - targetZ)
          if dist < bestDist then
            bestDist = dist
            bestCid = node.cid or cid
          end
        end
      end
      sensorCids[modeName] = bestCid
    end
  end)
  if not ok then
    log("W", logTag, "Failed to find snorkel sensor nodes: " .. tostring(err))
  end
end

-- Public API ------------------------------------------------------------------

-- silent = true suppresses the UI message (used for initial sync on spawn and
-- for broadcasts, so the message is only shown once, on the vehicle that
-- triggered the change).
local function setMode(newMode, silent)
  if newMode == "high" then newMode = "tall" end -- pre-1.1 name
  if not VALID_MODES[newMode] then return end
  local changed = newMode ~= mode
  mode = newMode
  if changed and not silent and guihooks then
    guihooks.message("Snorkel: " .. MODE_LABELS[mode], 5, "universalSnorkel.mode")
  end
end

-- Bound to a key via Options > Controls > Vehicle > "Cycle snorkel mode".
local function cycleMode()
  local index = 1
  for i, m in ipairs(MODE_ORDER) do
    if m == mode then index = i end
  end
  local nextMode = MODE_ORDER[(index % #MODE_ORDER) + 1]

  -- Apply locally right away (shows the UI message)…
  setMode(nextMode, false)
  -- …then let the GE extension persist it and sync every other vehicle.
  obj:queueGameEngineLua(string.format(
    "if extensions.universalSnorkel then extensions.universalSnorkel.setGlobalMode(%q) end",
    nextMode))
end

local function getMode()
  return mode
end

-- Per-frame protection --------------------------------------------------------

local function updateGFX(dt)
  if mode == "off" or #engines == 0 then
    snorkelUnderwater = false
    return
  end

  -- Late rescan: some engines are initialised after the extension loads, or
  -- flood fields may be created lazily. Retry every 2 s until found.
  local needRescan = false
  for _, entry in ipairs(engines) do
    if #entry.floodKeys == 0 then needRescan = true break end
  end
  if needRescan then
    rescanTimer = rescanTimer + dt
    if rescanTimer > 2 then
      rescanTimer = 0
      for _, entry in ipairs(engines) do
        if #entry.floodKeys == 0 then
          entry.floodKeys = collectFloodKeys(entry.device)
        end
      end
    end
  end

  local protecting = true
  local sensorCid = sensorCids[mode]
  if sensorCid then -- small / medium / tall: check the snorkel opening
    local underwater = obj:inWater(sensorCid) and true or false
    if underwater ~= snorkelUnderwater then
      snorkelUnderwater = underwater
      if guihooks then
        if underwater then
          guihooks.message("Snorkel submerged — engine is flooding!", 5, "vehicle.damage.flood")
        else
          guihooks.message("Snorkel above water — engine protected", 5, "vehicle.damage.flood")
        end
      end
    end
    protecting = not underwater
  end

  if not protecting then return end

  -- Keep the flood accumulator(s) at zero so the engine can never reach the
  -- hydrolock threshold. Flooding fills over multiple seconds, so a
  -- once-per-frame reset fully suppresses it regardless of update order.
  for _, entry in ipairs(engines) do
    local device = entry.device
    for _, key in ipairs(entry.floodKeys) do
      local value = device[key]
      if type(value) == "number" and value > 0 then
        device[key] = 0
      end
    end
  end
end

-- Lifecycle hooks ---------------------------------------------------------------

local function onExtensionLoaded()
  scanEngines()
  findSensorNodes()
  log("I", logTag, string.format(
    "Universal Snorkel active on this vehicle — %d engine(s), sensors: small=%s medium=%s tall=%s",
    #engines, tostring(sensorCids.small), tostring(sensorCids.medium), tostring(sensorCids.tall)))
end

local function onReset()
  -- Powertrain state is rebuilt on vehicle reset (Ctrl+R / recovery)
  scanEngines()
  snorkelUnderwater = false
end

M.setMode = setMode
M.cycleMode = cycleMode
M.getMode = getMode
M.updateGFX = updateGFX
M.onExtensionLoaded = onExtensionLoaded
M.onReset = onReset

return M
