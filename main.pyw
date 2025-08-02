import sys

import pygame

import zutil
from ui.core import UIEngine
from project import Project

# try:  #close the splash image in the pyinstaller build
#     import pyi_splash  # type: ignore
#     pyi_splash.close()
# except ImportError:
#     pass

sys.excepthook = zutil.crash_handler
Project.settings.read()
Project.UI = UIEngine((600, 600), display_idx=Project.settings.DISPLAY)
Project.UI.smanager.parse_stages()

try: #launch program
    Project.UI.loop(pygame.display.get_current_refresh_rate())
except Exception as e:
    zutil.crash_handler(*sys.exc_info())
finally: #after program
    Project.settings.save()
    pygame.quit()
    sys.exit(0)