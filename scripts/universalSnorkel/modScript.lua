-- Universal Snorkel — mod bootstrap
-- This file is executed by BeamNG.drive when the mod is activated.
-- It loads the game-engine (GE) side extension and registers it as a core
-- module so it survives Lua reloads and level changes.

load("universalSnorkel")
registerCoreModule("universalSnorkel")
