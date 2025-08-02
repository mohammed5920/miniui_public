import threading
from typing import Callable

import pygame

from ui.style import Style

class Exceptions:
    class UIException(Exception):
        """generic UI related exception"""
        pass

    class UIMediaException(UIException):
        """Can't open / stream media"""
        pass

    class UILayoutException(UIException):
        """Can't process a layout"""
        pass

    class UIRenderingException(UIException):
        """Error happened while rendering pygame surface"""
        pass

class Graphics:
    def rgb_from_key(key: int) -> tuple[int, int, int]:
        r = (key >> 16) & 0xFF
        g = (key >> 8) & 0xFF
        b = key & 0xFF
        return (r, g, b)

    def lerp(c1, c2, t: float) -> float:
        return c1 + (c2 - c1) * t

    def lerp_color(c1, c2, t: float) -> tuple[int, int, int]:
        return tuple(
            Graphics.lerp(c1[i], c2[i], t)
            for i in range(3)
        )    
    
    def coloured_square(colour : tuple[int, int, int], size : tuple[int, int], alpha:int=None):
        result = pygame.Surface(size, pygame.SRCALPHA if alpha is not None else 0)
        if alpha is not None:
            colour = [*colour, alpha]
        pygame.draw.rect(result, colour, ((0,0), size), border_radius=Style.PADDING.CORNER_RADIUS)
        return result

class Wrappers:
    class FontWrapper(dict):
        """can store the UI font at multiple sizes"""
        def __missing__(self, key):
            self[key] = pygame.Font("ui/assets/LiberationMono-Regular.ttf", key)
            return self[key]
        
        def __getitem__(self, key) -> pygame.Font:
            return super().__getitem__(key)
        
    class ThreadWrapper(threading.Thread):
        def __init__(self, target : Callable, args=(), callback=None):
            super().__init__()
            self._target : Callable = target
            self._args : tuple = args
            self.callback : Callable = callback
            self.result = None
            self.error = None

        def run(self):
            try:
                self.result = self._target(*self._args)
            except Exception as e:
                self.error = e