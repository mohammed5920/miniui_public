from dataclasses import dataclass
import re

import numpy as np
import pygame

import ui.base
import ui.pos
import ui.stock
import ui.style
import ui.util
from ui.style import Style

TAG_RE = re.compile(r'<(/?)(\w+)>')

@dataclass
class TextData:
    text: str
    size: int
    colour: tuple[int, int, int]

class TextLabel(ui.base.UIElement):
    """'rich' text with no background"""
    def __init__(self, ui_instance, text, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.textdata = TextData(text, Style.SIZES.FONT_MED, Style.COLOURS.TEXT_NORMAL)
    def measure(self):
        return self._uii.fonts[self.textdata.size].size(TAG_RE.sub('', self.textdata.text))
    def draw_surf(self):
        return ui.style.bt_render(self.textdata.text, self._uii.fonts[self.textdata.size], self.textdata.colour)

class Button(ui.base.UIElement):
    """label with background that can be clicked on to call the callback\n
    callback provides 1 argument, position of mouse relative to the top left of the button"""
    def __init__(self, ui_instance, text: str, click_func, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.textdata = self.textdata = TextData(text, Style.SIZES.FONT_MED, Style.COLOURS.TEXT_NORMAL)
        self.on_click = click_func
        self.force_on = False

    def measure(self):
        return np.add(self._uii.fonts[self.textdata.size].size(self.textdata.text), (Style.PADDING.BUTTON_PADDING*2, Style.PADDING.BUTTON_PADDING*2))

    def update(self, dt):
        if self.istate.click_percent or self.istate.hover_percent:
            self.mark_dirty()
        super().update(dt)

    def draw_surf(self):
        if self.istate.is_clicked or self.force_on:
            bg_col = Style.ALPHA.BUTTON_ACTIVE
            t_col = Style.COLOURS.TEXT_HIGHLIGHTED
        else: 
            bg_col = ui.util.Graphics.lerp(Style.ALPHA.BUTTON, 
                                        Style.ALPHA.BUTTON_HOVER, 
                                        self.istate.hover_percent/100)
            t_col = self.textdata.colour
        result = ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, self._rect.size, bg_col)
        result.blit(self._uii.fonts[self.textdata.size].render(self.textdata.text, True, t_col), (Style.PADDING.BUTTON_PADDING, Style.PADDING.BUTTON_PADDING))
        return result
    
class EntryBox(ui.base.UIElement):
    """button that can be clicked on and typed in. contents stored in Entrybox.textdata"""
    def __init__(self, ui_instance, default_text="Type...", **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.default = default_text
        self.textdata = TextData("", Style.SIZES.FONT_MED, Style.COLOURS.TEXT_INPUT)

    #input handling
    def on_kb_defocus(self):
        self.mark_dirty()
        self.reflow()

    def on_keystroke(self, event):
        if not self.istate.is_kb_focused: return
        match event.key:
            case pygame.K_BACKSPACE:
                if self.textdata.text: self.textdata.text = self.textdata.text[:-1]
            case pygame.K_DELETE:
                self.textdata.text = ""
            case _:
                self.textdata.text += event.unicode
        self.mark_dirty()
        self.reflow()
    
    def on_click(self, translated_mouse): #might implement carat here
        self._uii.get_kb_focus(self)
        self.mark_dirty()
        self.reflow()
    
    #drawing
    def measure(self):
        return np.add(self._uii.fonts[self.textdata.size].size(self.textdata.text or (self.default if not self.istate.is_kb_focused else "")), 
                      (Style.PADDING.BUTTON_PADDING*2, Style.PADDING.BUTTON_PADDING*2))
    def update(self, dt):
        if self.istate.click_percent or self.istate.hover_percent:
            self.mark_dirty()
        super().update(dt)

    def draw_surf(self):
        if self.istate.is_kb_focused: 
            bg_a = 255
            t_col = Style.COLOURS.TEXT_INPUT
        else: 
            bg_a = ui.util.Graphics.lerp(Style.ALPHA.BUTTON, 
                                         Style.ALPHA.BUTTON_HOVER, 
                                         self.istate.hover_percent/100)
            t_col = Style.COLOURS.TEXT_NORMAL
        result = ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, self._rect.size, bg_a)
        t_surf = self._uii.fonts[self.textdata.size].render(self.textdata.text or (self.default if not self.istate.is_kb_focused else ""), True, t_col)
        t_surf.set_alpha(128 if not self.istate.is_kb_focused else 255)
        result.blit(t_surf, (Style.PADDING.BUTTON_PADDING, Style.PADDING.BUTTON_PADDING))
        return result
    
class TextList(ui.base.UIElement):
    """will render max_lines (or all) lines of text in list pointed to by list_ref\n
    can be clicked on to call a function with the clicked line as an argument"""
    def __init__(self, ui_instance, list_ref, click_func=None, max_lines=999, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.list_ref : list[str] = list_ref
        self.max_lines = max_lines
        self.click_func = click_func
        self._offset = 0 
        self._moused_idx = -1
    
    #input handling
    def while_hovered(self, translated_mouse):
        if not self.list_ref: return
        self._moused_idx = (translated_mouse[1] - Style.PADDING.LAYOUT_PADDING) // (self._uii.fonts[Style.SIZES.FONT_MED].size(self.list_ref[0])[1] 
                                                                                    + Style.PADDING.LAYOUT_PADDING)
    def on_exit(self):
        self._moused_idx = -1
    def on_click(self, translated_mouse):
        print(self.list_ref[self._moused_idx+self._offset])
        if not self.click_func: return
        self.click_func(self._moused_idx + self._offset)
    def on_scroll(self, up, down):
        self.reflow()
        if down: self._offset = min(self._offset+1, len(self.list_ref)-self.max_lines)
        if up: self._offset = max(0, self._offset-1)

    #rendering
    def update(self, dt):
        if self.istate.click_percent or self.istate.hover_percent:
            self.mark_dirty()
        super().update(dt)
    
    def measure(self):
        t_h = m_w = 0
        for line in self.list_ref[self._offset:self._offset+self.max_lines]:
            l_w, l_h = self._uii.fonts[Style.SIZES.FONT_MED].size(line)
            t_h += l_h
            m_w = max(m_w, l_w)
        base = np.add((m_w, t_h), (Style.PADDING.LAYOUT_PADDING*2, Style.PADDING.LAYOUT_PADDING*(len(self.list_ref[self._offset:self._offset+self.max_lines])+1)))
        if self.max_lines >= len(self.list_ref): return base
        return np.add(base, (Style.SIZES.SCROLL_BAR*2+Style.PADDING.LAYOUT_PADDING*2,0))
    
    def draw_surf(self):
        result = ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, self._rect.size, Style.ALPHA.BUTTON_ACTIVE)
        h = Style.PADDING.LAYOUT_PADDING
        
        for i, line in enumerate(self.list_ref[self._offset:self._offset+self.max_lines]):
            line = self._uii.fonts[Style.SIZES.FONT_MED].render(line, 1, Style.COLOURS.TEXT_HIGHLIGHTED, 
                                                                bgcolor=(Style.COLOURS.FOREGROUND_DEEMPHASISED if i==self._moused_idx else None))
            result.blit(line, (self._rect.width/2-line.width/2,h))
            h += line.height + Style.PADDING.LAYOUT_PADDING
            if i != len(self.list_ref)-1 and i != self.max_lines-1:
                divider_start = Style.PADDING.LAYOUT_PADDING + (Style.SIZES.SCROLL_BAR if self.max_lines < len(self.list_ref) else 0)
                divider_end = self._rect.width - Style.PADDING.LAYOUT_PADDING - (Style.SIZES.SCROLL_BAR if self.max_lines < len(self.list_ref) else 0)
                pygame.draw.line(result, Style.COLOURS.TEXT_HIGHLIGHTED, 
                                (divider_start, h-(Style.PADDING.LAYOUT_PADDING)),
                                (divider_end, h-(Style.PADDING.LAYOUT_PADDING)))
                
        #scrollbar 
        if self.max_lines >= len(self.list_ref): return result
        scr_bg = ui.util.Graphics.coloured_square(Style.COLOURS.TEXT_HIGHLIGHTED, 
                                                  (Style.SIZES.SCROLL_BAR, self._rect.height-Style.PADDING.LAYOUT_PADDING*2),
                                                  Style.ALPHA.BUTTON_HOVER)
        result.blit(scr_bg, (self._rect.width-scr_bg.width-Style.PADDING.LAYOUT_PADDING, Style.PADDING.LAYOUT_PADDING))
        
        scr = ui.util.Graphics.coloured_square(Style.COLOURS.TEXT_HIGHLIGHTED, 
                                               (Style.SIZES.SCROLL_BAR*0.8, Style.SIZES.SCROLL_BAR*0.8),
                                                Style.ALPHA.BUTTON_ACTIVE)
        scr_percent = (self._offset)/(len(self.list_ref)-self.max_lines)
        result.blit(scr, (self._rect.width-scr_bg.width+1-Style.PADDING.LAYOUT_PADDING, 
                             (self._rect.height-2*Style.PADDING.LAYOUT_PADDING-scr.height-Style.SIZES.SCROLL_BAR*0.8)*scr_percent+Style.PADDING.LAYOUT_PADDING+Style.SIZES.SCROLL_BAR*0.4))
        return result
    
class ContextMenu(ui.base.UIContainer):
    """wrapper class to layout buttons generated when user right clicks an object that overrides UIElement.on_right()"""
    def __init__(self, ui_instance, names_functions, **kwargs):
        super().__init__(ui_instance, ui.pos.BoxLayout(alignment="vertical"), **kwargs)
        [self.add_elements({name : ui.stock.Button(ui_instance, name, func)}) for (name, func) in names_functions]
        self._uii.add_event_listener("lmb_up", self.del_handler)
        self._uii.add_event_listener("rmb_down", self.rmb_handler)
        self._uii.add_event_listener("key_down", self.del_handler)
        self._uii.add_event_listener("resize", self.del_handler)
    
    def rmb_handler(self, pos):
        if self._rect and not self._rect.collidepoint(pos): self.delete()

    def del_handler(self, _):
        self.delete()

    def cleanup(self):
        self._uii.remove_event_listener("rmb_down", self.rmb_handler)
        self._uii.remove_event_listener("key_down", self.del_handler)
        self._uii.remove_event_listener("lmb_up", self.del_handler)
        self._uii.remove_event_listener("resize", self.del_handler)

class ProgressBar(ui.base.UIElement):
    """experimental"""
    def __init__(self, ui_instance, width, total=None, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.rel_width = width / self._uii.display.width
        self.total = total
        self.pos = 0
    
    def prog_string(self):
        return f"{self.pos}/{self.total}"

    def change(self, new):
        if new == self.pos: return
        self.pos = new
        self.mark_dirty()

    def measure(self):
        return (self.rel_width * self._uii.display.width, 
                self._uii.fonts[Style.SIZES.FONT_MED].size(self.prog_string())[1] + Style.PADDING.BUTTON_PADDING*2 + Style.PADDING.LAYOUT_PADDING*2)
    
    def draw_surf(self):
        res = ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, self._rect.size, Style.ALPHA.LAYOUT)
        try: prog = (self.pos/self.total)
        except ZeroDivisionError: prog = self._rect.width
        prog = ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, 
                                                np.multiply(self._rect.size, (min(prog,1), 1)), 
                                                Style.ALPHA.BUTTON_ACTIVE)
        res.blit(prog, (0,0))
        t = self._uii.fonts[Style.SIZES.FONT_MED].render(self.prog_string(), True, Style.COLOURS.TEXT_INPUT)
        res.blit(t, (res.width/2 - t.width/2, Style.PADDING.BUTTON_PADDING+Style.PADDING.LAYOUT_PADDING))
        return res