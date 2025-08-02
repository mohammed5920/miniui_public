from project import Project
import ui.base
import ui.stock
import ui.core
import ui.pos

UII = Project.UI

class Stress(ui.core.Stage):
    def start(self):
        self.grid = ui.base.UIContainer(UII, ui.pos.BoxLayout('vertical'))
        for i in range(30):
            row = ui.base.UIContainer(UII, ui.pos.BoxLayout('horizontal'))
            for j in range(40):
                row.add_elements({None:ui.stock.Button(UII, str(j+i*40), self.clickon_anything)})
            self.grid.add_elements({i:row})
        UII.add({"stress" : self.grid})

    def clickon_anything(self,_):
        UII.smanager.switch_stage("start")
    
    def cleanup(self):
        self.grid = self.grid.delete()

__stage__ = Stress