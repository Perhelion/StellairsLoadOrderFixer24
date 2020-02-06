# StellairsLoadOrderFixer25
Sort Stellaris mods in *reverse* alphabetical order (2.4's mod load order is different from 2.3.3)

2.5: Changes the `game_data.json` for the visible order (at the PDX launcher).
 - Now supports sorting by mod dependencies

The `dlc_load.json` is the load order for enabled mods (used by the game instead of `game_data.json`, which is stored in *reverse* order to `game_data.json`).
~~2.4: Force load all incompatible mods (you can disable them manually in the launcher)~~

## How to use
Download [load_order_stellaris24.exe](https://github.com/haifengkao/StellairsLoadOrderFixer24/releases/download/1.2/load_order_stellaris24.exe)

Then double click it

If you see "done", the load order has been succesfully sorted

If you see “mod_registry” not found, please run the exe inside local mod folder

![demo](https://github.com/haifengkao/StellairsLoadOrderFixer24/blob/master/demo.jpg)
