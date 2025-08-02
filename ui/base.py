from weakref import ref
from typing import Callable, TYPE_CHECKING

import pygame
from bidict import bidict

if TYPE_CHECKING: import ui.core
import ui.pos
import ui.util
from ui.style import Style

class UIElement:
    def __eq__(self, value):
        return value._id == self._id
    def __hash__(self):
        return self._id
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.mark_dirty()
        self.reflow()
    def __del__(self):
        print(f"{self} gc'ed sucessfully.")
    
    def __init__(self, ui_instance, **kwargs):
        self._id = ui_instance.get_unique_id()
        self._uii : 'ui.core.UIEngine' = ui_instance
        self._rect : pygame.Rect = kwargs.get("rect", None)
        self._pos : ui.pos.Position = self.place()._pos

        self._cache : pygame.Surface = None
        self._dirty = True
        self._reflow_flag = True

        self._parent : ref[UIContainer] = ref(kwargs["parent"]) if "parent" in kwargs else None
        self._elements : bidict[str, UIElement] = bidict()

        self.istate = InteractionState()
        ui_instance.track(self)

    def place(self, anchor : ui.pos.Alignment = ui.pos.Alignment.CENTRE, align : ui.pos.Alignment = None, offset=(0, 0)):
        """where does this element go?
        align: which point on the component are we talking about?
        anchor: where should we "stick" to on the parent?
        xy: offset for that point"""
        self._pos = ui.pos.Position(anchor, align, offset)
        return self

    def measure(self) -> tuple[int, int]:
        """tells the parent container how big the element is"""
        raise NotImplementedError
    
    def distribute(self, rect: pygame.Rect):
        """called by the parent container to tell it where to draw"""
        if not self._rect or rect.size != self._rect.size: self.mark_dirty()
        self._rect = rect

    def reflow(self):
        """bubbles up to the parent and causes a reflow of the entire subtree on the next frame"""
        self._reflow_flag = True
        #check for parent to avoid crashing trying to reflow on a component that hasn't been added to the tree yet + on root
        if self._parent: self._parent().reflow()

    def delete(self):
        """queue the component for deletion
        this defers deletion to the global deletion handler"""
        self._uii.queue_deletion(self)
    
    def cleanup(self):
        """runs once the component is deleted
        \nif overridden on a container it should clean up only the container's state
        \nchildren get their cleanup() called separately"""
        pass

    def mark_dirty(self):
        """force the surface to redraw"""
        self._dirty = True

    def draw_surf(self) -> pygame.Surface:
        """returns the pygame surface of the component"""
        return False

    def render(self, surface):
        """draws the element to the input surface"""
        drawn = self._cache = self.draw_surf() if self._dirty or not self._cache else self._cache
        self._dirty = False
        if drawn:
            surface.blit(drawn, self._rect.topleft)

    def update(self, dt):
        """update internal state, must be called even if overridden"""
        self.istate.update(dt)

    #every input i could think of
    def on_click(self, translated_mouse : tuple[int, int]): pass
    def on_down(self, translated_mouse : tuple[int, int]): pass
    def on_up(self): pass
    def on_enter(self): pass
    def on_exit(self): pass
    def on_scroll(self, up, down): pass
    def on_right(self) -> list[tuple[str, Callable]]: pass
    def on_keystroke(self, event : pygame.Event): pass
    def on_kb_focus (self): pass
    def on_kb_defocus(self): pass
    def while_clicked(self, translated_mouse : tuple[int, int]): pass
    def while_hovered(self, translated_mouse : tuple[int, int]): pass

class UIContainer(UIElement):
    def __getitem__(self, key : str) -> UIElement:
        return self._elements[key]
    def __setitem__(self, key : str, value : UIElement):
        if key in self: raise ui.util.Exceptions.UILayoutException("Reassiging container elements isn't supported - delete and add again.")
        self.add_elements({key : value})
    def __delitem__(self, key : str):
        self._elements[key].delete()
    def __contains__(self, key : str):
        return key in self._elements

    def __init__(self, ui_instance, strategy, enable_bg=True, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self._strategy : ui.pos.Strategy = strategy
        self._reflow_flag = True
        self._enable_bg = enable_bg

    # ------ manage kids/parents 

    def add_elements(self, elements : dict[str, UIElement]):
        """add all components in the dict to the layout"""
        for key, element in elements.items():
            if key is None: key = element._id
            if key in self._elements: raise ui.util.Exceptions.UILayoutException(f"{key} used for 2 different elements in the same container!")
            if element in self._elements.inverse: raise ui.util.Exceptions.UILayoutException(f"{element} added twice to the same container!")
            if element._parent: raise ui.util.Exceptions.UILayoutException(f"{element} can't have 2 parents!")
            element._parent = ref(self)
            self._elements[key] = element
        self.reflow()
        return self
    
    # ------ implement layout system

    def measure(self):
        return self._strategy.measure(self._elements.values())

    def distribute(self, rect):
        super().distribute(rect)
        self._strategy.distribute(self._elements.values(), self._rect)
        self._reflow_flag = False

    def draw_surf(self):
        return ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, self._rect.size, Style.ALPHA.LAYOUT) if self._enable_bg else None

    def render(self, surface):
        super().render(surface)
        #pygame.draw.rect(surface, ui.util.Graphics.rgb_from_key(self._id), self._rect, width=1)

    def on_right(self):
        return (("(TEST) delete layout", lambda x: self.delete()),)

class InteractionState:
    def __init__(self):
        self.is_clicked = False
        self.is_hovered = False
        self.is_kb_focused = False
        self.keep_kb_focus = False #even if the mouse clicks elsewhere
        self.click_percent = 0
        self.hover_percent = 0
        self.translated_mouse : tuple[int, int] = None
    def update(self, dt):
        delta = dt/10/Style.TIME.FADE_TIME
        self.click_percent = max(0.0, min(100.0, self.click_percent+delta* (1 if self.is_clicked else -1) ))
        self.hover_percent = max(0.0, min(100.0, self.hover_percent+delta* (1 if self.is_hovered else -1) ))
