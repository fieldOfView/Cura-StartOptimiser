# Cura Startup Optimiser

This plugin lets the user optimise starting Cura by not loading configuration files that will not be used.

By default Cura loads and parses close to 2000 files on startup related to printers and profiles for many known printers. Most users will not need all of these files. The plugin checks what configuration files are used by currently configured printers, and lets the user disable loading of files for other printers.