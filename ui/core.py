import random
import time
import importlib
import os
from typing import Callable, NoReturn

import numpy as np
import pygame

import ui.base
import ui.stock
import ui.util
import ui.pos
from ui.style import Style
import ui.util

class Stage:
    """splits up the flow of the program into distinct 'stages' that can be activated and that have clear entry/exit points
    \n none of the class methods are designed to be executed directly by user code
    \n instead, flow is to be directed with StageManager.transfer_stage(), StageManager.switch_stage(), StageManager.return_stage()"""
    def __init__(self):
        self._return_func = None
    
    def start(self): 
        """executed when first entering the stage"""
        pass

    def handle_events(self, events : list[pygame.Event]) -> list[pygame.Event]:
        """executed every frame the stage is active"""
        return events

    def update(self, dt):
        """executed every frame the stage is active"""
        pass

    def pause(self): 
        """executed when suspending the stage with the possibility of returning to it later with Stage.resume()"""
        pass
    def cleanup(self): 
        """executed when the stage cannot be returned to without re-initialising with Stage.start()"""
        pass

    def resume(self):
        """executed when returning from a suspended state (Stage.pause())""" 
        if self._return_func:
            self._return_func(self)

class StageManager:
    def __init__(self):
        self.stages : dict[str, Stage] = dict() 
        self.current_stage : Stage = None
        self.previous_stages : list[Stage] = []

    def parse_stages(self, start_key="start"):
        for file in [file for file in os.listdir("stages/") if file.endswith(".py") and not file.startswith("__")]:
            mod = importlib.import_module(f"stages.{file[:-3]}")
            try: self.stages[file[:-3]] = getattr(mod, "__stage__")()
            except: continue
        self.switch_stage(start_key)

    def switch_stage(self, stage_key : str, start_args=()):
        """switch to an entirely new stage, 
        ensuring all data from last stages are cleaned up 
        and no state is left lingering"""
        for stage in self.previous_stages: stage.cleanup()
        self.previous_stages = []
        if self.current_stage: self.current_stage.cleanup()
        self.current_stage = self.stages[stage_key]
        self.current_stage.start(*start_args)

    def transfer_stage(self, stage_key : str, return_func = None, start_args=()):
        """suspend a stage and run a new one, 
        keeping the last stage loaded in to return from
        \n additional argument: return_func (no arguments) ->
        a function that is executed once the stage being transferred from is returned to again"""
        self.current_stage._return_func = return_func
        self.previous_stages.append(self.current_stage)
        self.current_stage.pause()
        self.current_stage = self.stages[stage_key]
        self.current_stage.start(*start_args)

    def return_stage(self):
        """returns to the last suspended stage and executes its resume funcs
          if it exists else returns false"""
        if not self.previous_stages: return False
        self.current_stage.cleanup()
        self.current_stage = self.previous_stages.pop()
        self.current_stage.resume()
        return True

class UIEngine:
    def __getitem__(self, key):
        return self.root.__getitem__(key)
    def __setitem__(self, key, value):
        return self.root.__setitem__(key, value)
    def __contains__(self, key : str):
        return self.root.__contains__(key)
    def __delitem__(self, key : str):
        return self.root.__delitem__(key)

    def __init__(self, display_size, display_idx=0, caption="", **kwargs):
        pygame.init()
        self.display = pygame.display.set_mode(display_size, pygame.RESIZABLE | pygame.DOUBLEBUF, display=display_idx, vsync=1)
        self.display.fill(Style.COLOURS.BACKGROUND)
        pygame.display.flip()
        pygame.display.set_caption(caption or "MiniUI - you, and i.")
    
        self.clock = pygame.Clock()
        self.tracker = set()
        self.detracker = dict() #has to preserve insertion orders
        self.focused_element : ui.base.UIElement = None
        self.fonts = ui.util.Wrappers.FontWrapper()
        self.root = ui.base.UIContainer(self, ui.pos.StackLayout(), enable_bg=False)
        self.smanager = StageManager()
        self.running = True
        self.bg_threads : set[ui.util.Wrappers.ThreadWrapper] = set()

        self.event_listeners = {
            "rmb_down" : set(), #called with global coords
            "lmb_up" : set(), #called with global coords
            "key_down" : set(), #called with key event
            "resize" : set() #called with new window size
        }

    def track(self, element):
        """called whenever a new element is created, tracks elements so a unique id is always issued and for debugging"""
        self.tracker.add(element)            
    def add(self, element_dict : dict[str, ui.base.UIElement]):
        """shorthand for adding an element to root node"""
        self.root.add_elements(element_dict)
    def queue_deletion(self, element : ui.base.UIElement):
        """called whenever an element requests to be deleted, actual deletion always happens at the end of the frame"""
        if element._parent() in self.detracker: raise ui.util.Exceptions.UILayoutException("Tried to delete child of a parent that's already marked for deletion!")
        self.detracker[element] = None

    def get_kb_focus(self, element : ui.base.UIElement):
        if self.focused_element:
            self.focused_element.istate.is_kb_focused = False
            self.focused_element.on_kb_defocus()
        element.istate.is_kb_focused = True
        self.focused_element = element
        self.focused_element.on_kb_focus()

    def get_unique_id(self):
        used = {element._id for element in self.tracker}
        while True:
            colour = [random.randint(0, 96) for _ in range(3)]
            colour_key = colour[0] << 16 | colour[1] << 8 | colour[2]
            if colour_key not in used:
                return colour_key
            
    def add_event_listener(self, event_type : str, handler : Callable):
        """do NOT use lambdas as event listeners because they will cause the element to not get deleted properly"""
        if handler.__name__ == "<lambda>": raise ui.util.Exceptions.UIException("do NOT use lambdas as event listeners because they will cause the element to not get deleted properly")
        self.event_listeners[event_type].add(handler)
    def remove_event_listener(self, event_type : str, handler : Callable):
        self.event_listeners[event_type].remove(handler)
            
    def df_traverse(self, root : ui.base.UIContainer, post=False):
        """utility generator to perform depth-first traversal on a root note in either pre or post order"""
        stack = [(root, False)]
        while stack:
            element, visited = stack.pop()
            if visited or not post: yield element
            if not visited:
                if post: 
                    stack.append((element, True))
                    [stack.append((child, False)) for child in element._elements.values()]
                else:
                    [stack.append((child, False)) for child in reversed(element._elements.values())]

    def start_job(self, func, cb=None, args=(), daemon=True):
        """start func(*args) on a separate thread, then after it's done or errors out, calls cb(err, result) on the main thread"""
        thread = ui.util.Wrappers.ThreadWrapper(func, args, cb)
        if daemon: thread.daemon = True
        self.bg_threads.add(thread)
        thread.start()
        return thread

    ###################################################################################
    #split each frame step into its own function so the scope isn't littered with vars#
    ###################################################################################

    def handle_events(self):
        #how it works:
        #-> boil down all pygame events incoming for the frame into a bunch of vars
        #-> use those vars to traverse the entire tree and fire the respective handler depending on the state
        #-> implements first hit detection for top-most elements - only hits one element
        #-> after all elements have had a chance to handle the events, then fire event listeners 

        #event aggregation
        lmb_down = lmb_up = rmb_down = resize = False
        scroll_up = keystroke = None
        mouse_pos = pygame.mouse.get_pos()
        events =  pygame.event.get() if self.smanager.current_stage is None else self.smanager.current_stage.handle_events(pygame.event.get())
        for event in events:
            if event.type == pygame.QUIT: #save settings file and shutdown gracefully
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.root.reflow()
                resize = event.size
            elif event.type == pygame.KEYDOWN and self.focused_element:
                self.focused_element.on_keystroke(event)
                keystroke = event
            elif event.type == pygame.MOUSEBUTTONDOWN:
                match event.button:
                    case 1: lmb_down = True
                    case 3: rmb_down = True
                    case 4: scroll_up = True
                    case 5: scroll_up = False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                lmb_up = True

        #event handling
        first_hit = False
        for element in self.df_traverse(self.root, post=True):
            if element._rect is None: continue #child hasn't been laid out yet
            translated_mouse = np.subtract(mouse_pos, element._rect.topleft)
            #mouse is on child
            if not first_hit and element._rect.collidepoint(mouse_pos):
                first_hit = True
                element.istate.translated_mouse = translated_mouse
                if not element.istate.is_hovered:
                    element.on_enter()
                    element.istate.is_hovered = True
                element.while_hovered(translated_mouse)
                if element.istate.is_clicked:
                    element.while_clicked(translated_mouse)
                if lmb_down:
                    element.on_down(translated_mouse)
                    element.istate.is_clicked = True
                elif lmb_up and element.istate.is_clicked:
                    element.on_click(translated_mouse)
                elif rmb_down:
                    if element.on_right(): 
                        self.add({None : ui.stock.ContextMenu(self, element.on_right()).place(ui.pos.Alignment.TOP_LEFT, offset=(mouse_pos))}) #TODO add some logic here to spawn a right mouse handler 
                elif scroll_up is not None:
                    element.on_scroll(scroll_up, not scroll_up)
            #mouse is off child
            else:
                element.istate.translated_mouse = None
                if element.istate.is_hovered:
                    element.on_exit()
                    element.istate.is_hovered = False
                if element.istate.is_kb_focused and not element.istate.keep_kb_focus and lmb_up:
                    element.istate.is_kb_focused = False
                    element.on_kb_defocus()
                    self.focused_element = None
            #regardless of whether or not its on the child
            if lmb_up and element.istate.is_clicked: 
                element.on_up()
                element.istate.is_clicked = False

        if rmb_down: [listener(mouse_pos) for listener in self.event_listeners["rmb_down"]]
        if lmb_up: [listener(mouse_pos) for listener in self.event_listeners["lmb_up"]]
        if keystroke: [listener(keystroke) for listener in self.event_listeners["key_down"]]
        if resize: [listener(resize) for listener in self.event_listeners["resize"]]

    def update(self):
        #how it works
        #-> traverse all components and update
        #-> loop over all background threads and check if they're done
        #-> fire the callback on the main thread with the (err, result) tuple

        if self.smanager.current_stage is not None: self.smanager.current_stage.update(self.clock.get_rawtime())
        for element in self.df_traverse(self.root):
            element.update(self.clock.get_rawtime())
        
        if not self.bg_threads: return
        for thread in self.bg_threads.copy():
            if not thread.is_alive():
                self.bg_threads.remove(thread)
                if thread.callback is not None:
                    thread.callback(thread.error, thread.result)

    def handle_reflow(self):
        #how it works
        #-> checks if any ancestor has called reflow()
        #-> recalculates the entire layout once
        #-> repositions everything (redundantly in some cases) <- TODO see if becomes an issue

        if self.root._reflow_flag:
            self.root.distribute(pygame.Rect((0,0), self.display.size))
            #print(self.display.size)

    def render(self):
        #how it works
        #-> traverse the entire tree
        #-> check if element is visible on screen and tell the element to place its surface on the UI display 

        for element in self.df_traverse(self.root):
            if element._rect.colliderect(self.root._rect):
                element.render(self.display)

    def cleanup(self):
        #how it works
        #-> loop over all elements that have been scheduled for deletion in order of deletion (guaranteed to delete child before parent and not vice versa)
        #-> defocus if necessary
        #-> traverse all of its kids recursively
        #-> for every ancestor, remove from global tracker, call cleanup, delete parent reference to child, delete child reference to parent
        #-> maintain a set of living parents of dead children and call reflow() on those 

        parents = set()
        for el in self.detracker.copy():
            if self.focused_element and el == self.focused_element: 
                self.focused_element = None
            self.detracker.pop(el)
            for kid in self.df_traverse(el, post=True): #traverse will also return el itself 
                self.tracker.remove(kid)
                kid.cleanup()
                parents.discard(kid)
                parents.add(kid._parent())
                kid._parent()._elements.inverse.pop(kid)
                kid._parent = None
        for parent in parents:
            parent.reflow()
            
    def tick(self):
        self.display.fill(Style.COLOURS.BACKGROUND)
        times = []
        for phase in (self.handle_events, self.update, self.handle_reflow, self.render, self.cleanup):
            start = time.perf_counter()
            phase()
            times.append(time.perf_counter() - start)
        for i, tt in enumerate(times):
            taken = self.fonts[16].render(f"{round(tt * 1000, 2)} ms", 1, [255]*3) 
            self.display.blit(taken, (0, self.display.height-taken.height*(i+1)))
        pygame.display.flip() #actually shows any changes to the display 

    def loop(self, fps):
        while self.running:
            self.tick()
            self.clock.tick(fps)