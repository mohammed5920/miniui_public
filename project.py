from ui.core import UIEngine
import zutil

class Project:
    UI : UIEngine
    settings = zutil.Settings()
    settings.add("DISPLAY", 0, lambda x : isinstance(x, int) and x >= 0, 
                "<int> which display to render to")