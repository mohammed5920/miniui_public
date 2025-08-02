import pathlib

import pydub
import pydub.playback
import pygame
import numpy as np

import ui.base
import ui.core
import ui.pos
from ui.style import Style
import ui.util

class Waveform(ui.base.UIElement):
    """generates a waveform that can be clicked on to play 10 seconds starting from click position"""
    def __init__(self, ui_instance, size, path, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.path = pathlib.Path(path)
        self.audio_seg : pydub.AudioSegment = pydub.AudioSegment.from_file(self.path, self.path.suffix[1:]).set_frame_rate(44100).set_sample_width(2).set_channels(2)
        self.relative = np.divide(size, self._uii.display.size)    
        self.loading = False

        self.graph : pygame.Surface = None
        self.channel : pygame.mixer.Channel = None
        self._uii.add_event_listener("resize", self.resize)
        self.resize(self._uii.display.size)
        
    def resize(self, screen_size):
        self.graph = pygame.Surface((np.multiply(screen_size, self.relative)), pygame.SRCALPHA)
        samp_array = np.array(self.audio_seg.split_to_mono()[0].get_array_of_samples()[::10]).astype(np.float64)
        samp_array /= np.max(np.abs(samp_array))
        samples_per_line = int(len(samp_array) // self.graph.width)
        bins = samp_array[:self.graph.width*samples_per_line].reshape((self.graph.width, samples_per_line))
        mins, maxs = bins.min(axis=1), bins.max(axis=1)

        mid = self.graph.height // 2
        for x in range(self.graph.width):
            y_min = int(mid - maxs[x] * mid)
            y_max = int(mid - mins[x] * mid)
            pygame.draw.line(self.graph, Style.COLOURS.TEXT_NORMAL, (x, y_min), (x, y_max))

    def measure(self):
        return np.multiply(self.relative, self._uii.display.size)
    
    def draw_surf(self):
        res = self.graph.copy()
        if self.istate.translated_mouse is not None:
            pos = int(self.istate.translated_mouse[0]/res.width * self.audio_seg.duration_seconds)
            if pos > 60: tc = f"{pos//60}:{pos%60:02d}"
            else: tc = str(pos)
            pygame.draw.line(res, Style.COLOURS.FOREGROUND_DEEMPHASISED, 
                             (self.istate.translated_mouse[0], 0),
                             (self.istate.translated_mouse[0], res.height))
            res.blit(self._uii.fonts[Style.SIZES.FONT_MED].render(tc, 1, Style.COLOURS.TEXT_HIGHLIGHTED, Style.COLOURS.FOREGROUND_DEEMPHASISED), (0,0))
        return res
    
    def while_hovered(self, translated_mouse):
        self.mark_dirty()
    def on_exit(self):
        self.mark_dirty()
    def on_down(self, translated_mouse):
        prog = (translated_mouse[0] / self.graph.width)*self.audio_seg.duration_seconds*1000
        self.channel = pygame.mixer.Sound(np.array(self.audio_seg[prog:prog+10000].get_array_of_samples())).play()
    def on_up(self):
        self.channel.stop()

    def cleanup(self):
        self._uii.remove_event_listener("resize", self.resize)

class Scrubber(ui.base.UIElement):
    """generates a scrubber with n nodes to scrub from 0 to total"""
    def __init__(self, ui_instance, width, total, nodes, **kwargs):
        super().__init__(ui_instance, **kwargs)
        self.rel_width = width / self._uii.display.width
        self.total = total
        self.nodes = [(total/nodes)*i for i in range(nodes)]

    def measure(self):
        return (self.rel_width * self._uii.display.width, 
                self._uii.fonts[Style.SIZES.FONT_MED].size("Hg")[1] + Style.PADDING.BUTTON_PADDING*2 + Style.PADDING.LAYOUT_PADDING*2)
    
    def draw_surf(self):
        res = pygame.Surface(self.measure(), pygame.SRCALPHA)
        #bg
        res.blit(ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, res.size, Style.ALPHA.LAYOUT), (0,0))
        #line
        p_total = Style.PADDING.BUTTON_PADDING + Style.PADDING.LAYOUT_PADDING
        l_width = res.width - p_total * 2
        pygame.draw.line(res, Style.COLOURS.FOREGROUND, 
                         (p_total, res.height/2),
                         (p_total + l_width, res.height/2))
        #nodes
        for pos in self.nodes:
            pos = int(pos)
            if pos > 60: tc = f"{pos//60}:{pos%60:02d}"
            else: tc = str(pos)
            n_t = self._uii.fonts[Style.SIZES.FONT_MED].render(tc, 1, Style.COLOURS.TEXT_HIGHLIGHTED)
            bg = ui.util.Graphics.coloured_square(Style.COLOURS.FOREGROUND, np.add(n_t.size, [Style.PADDING.BUTTON_PADDING*2]*2), Style.ALPHA.BUTTON_ACTIVE)
            bg.blit(n_t, [Style.PADDING.BUTTON_PADDING]*2)
            res.blit(bg, ((p_total+(pos/self.total)*l_width) - bg.width/2, res.height/2 - bg.height/2))
        return res
    
    def while_clicked(self, translated_mouse):
        pixel_positions = [ts/self.total * self._rect.width for ts in self.nodes]
        closest_idx = min(range(len(pixel_positions)), key=lambda i: abs(pixel_positions[i] - translated_mouse[0]))
        new_timestamp = (translated_mouse[0] / self._rect.width) * self.total
        prev = self.nodes[closest_idx - 1] if closest_idx > 0 else 0
        next_ = self.nodes[closest_idx + 1] if closest_idx < len(self.nodes) - 1 else self.total
        self.nodes[closest_idx] = max(min(int(new_timestamp), next_ - 1), prev + 1)
        self.mark_dirty()