from project import Project
import ui.base
import ui.stock
import ui.core
import ui.pos

UII = Project.UI

class Start(ui.core.Stage):
    def start(self):
        UII["test"] = ui.stock.Button(UII, "Click me!", self.clickon_switch)
    def clickon_switch(self, _):
        UII.smanager.switch_stage("stress")
    def cleanup(self):
        del UII["test"]
    
__stage__ = Start