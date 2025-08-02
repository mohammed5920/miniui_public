from enum import Enum
from typing import Literal, TYPE_CHECKING

import numpy as np
import pygame

from ui.style import Style
import ui.base

if TYPE_CHECKING:
    import ui.core

class Alignment(Enum):
    TOP_LEFT = (0, 0)
    TOP_CENTRE = (0.5, 0)
    TOP_RIGHT = (1, 0)
    CENTRE_LEFT = (0, 0.5)
    CENTRE = (0.5, 0.5)
    CENTRE_RIGHT = (1, 0.5)
    BOTTOM_LEFT = (0, 1)
    BOTTOM_CENTRE = (0.5, 1)
    BOTTOM_RIGHT = (1, 1)
    
def virtualise_coords(uii, coords):
    return np.multiply(np.divide(coords, Style.SIZES.BASE_RES), uii.display.size)

class Position:
    def __init__(self, anchor=Alignment.CENTRE, align=None, offset=(0, 0)):
        self.align = align if align is not None else anchor
        self.anchor = anchor
        self.offset = offset

    def resolve(self, child_size, parent_size):
        #not exhaustively tested
        ax, ay = self.align.value
        hx, hy = self.anchor.value
        anchor_px = int(parent_size[0] * hx)
        anchor_py = int(parent_size[1] * hy)
        align_px = int(child_size[0] * ax)
        align_py = int(child_size[1] * ay)
        final_x = anchor_px - align_px + self.offset[0]
        final_y = anchor_py - align_py + self.offset[1]
        return final_x, final_y
    
class Strategy:
    def measure(self, children: list['ui.base.UIElement']) -> pygame.Rect:
        raise NotImplementedError
    def distribute(self, children: list['ui.base.UIElement'], bounds: pygame.Rect) -> None:
        raise NotImplementedError
    
class BoxLayout(Strategy):
    """lays out kids one by one either horizontally or vertically"""
    def __init__(self, alignment : Literal["vertical", "horizontal"]):
        self.alignment = alignment

    def measure(self, children):
        main_total = cross_max = 0
        for child in children:
            c_w, c_h = child.measure() 
            main_total += c_h if self.alignment == "vertical" else c_w
            cross_max = max(c_w if self.alignment == "vertical" else c_h, cross_max) 
            
        #total of kids + padding between kids + padding at either side of main axis
        total_main = main_total + (len(children)-1)*Style.PADDING.LAYOUT_PADDING + 2 * Style.PADDING.LAYOUT_PADDING
        if self.alignment == "vertical":
            return (cross_max + 2 * Style.PADDING.LAYOUT_PADDING, total_main)
        else:
            return (total_main, cross_max + 2 * Style.PADDING.LAYOUT_PADDING)
    
    def distribute(self, children, bounds):
        tl = bounds.topleft
        main_total = Style.PADDING.LAYOUT_PADDING
        for child in children:
            c_w, c_h = child.measure()
            #calculate where to shift the top left of the kid to take into account position in the layout + padding
            c_offset = (Style.PADDING.LAYOUT_PADDING, main_total) if self.alignment == "vertical" else (main_total, Style.PADDING.LAYOUT_PADDING)
            #calculate the space to give the kid to align itself in
            c_space = (bounds.width - 2*Style.PADDING.LAYOUT_PADDING, c_h) if self.alignment == "vertical" else (c_w, bounds.height-2*Style.PADDING.LAYOUT_PADDING)
            #ask the kid to resolve the alignment in the empty space and then offset it and send it off to the kid
            rc_tl = np.add(c_offset, child._pos.resolve((c_w, c_h), c_space))
            child.distribute(pygame.Rect(np.add(tl, rc_tl), (c_w, c_h)))
            main_total += c_h if self.alignment == "vertical" else c_w
            main_total += Style.PADDING.LAYOUT_PADDING 

class StackLayout(Strategy):
    """lays out kids according to manual alighnment in their position class (by default centred)
    \n is sized according to the size of the first child"""
    def measure(self, children):
        if not children: return (0, 0)
        for child in children:
            return child.measure()
            
    def distribute(self, children, bounds):
        tl = bounds.topleft
        size = bounds.size
        for child in children:
            c_size = child.measure()
            c_tl = np.add(tl, child._pos.resolve(c_size, size))
            child.distribute(pygame.Rect(c_tl, c_size))