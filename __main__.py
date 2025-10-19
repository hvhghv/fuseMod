import asyncio
from fuseMod_py.FuseModManager import FuseModManager
from fuseMod_py.VF_Tui import Panel
from fuseMod_py.tui_menu import register_menu
import fuseMod_py.register_module as register_module
import sys
import os
import curses

def tui_main(config_dir, data_dir, stdscr: curses.window):
    # 创建面板
    panel = Panel(config_dir, data_dir, "main", "系统设置")
    register_menu(panel)
    panel.handle_input(stdscr)

# 运行示例
async def main() -> None:
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    debug = False
    
    if len(sys.argv) == 1:
        curses.wrapper(lambda stdscr: tui_main(config_dir, data_dir, stdscr))
        return
    
    elif len(sys.argv) == 3 and sys.argv[2] != '--debug':
        print("Usage: python __main__.py <mount_point> [--debug]")
        return
    
    elif len(sys.argv) == 3 and sys.argv[2] == '--debug':
        debug = True
    
    elif len(sys.argv) > 3:
        print("Usage: python __main__.py <mount_point> [--debug]")
        return



    Manager = FuseModManager(config_dir, data_dir, debug)

    await Manager.init(sys.argv[1])
    register_module.register_modules(Manager, Manager.get_global_table())
    
    try:
        await Manager.run()
    except KeyboardInterrupt:
        await Manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())