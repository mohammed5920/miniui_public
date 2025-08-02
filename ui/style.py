import pygame
import re
TAG_RE = re.compile(r'<(/?)(\w+)>')

class Style:
    class SIZES:
        FONT_MED = 20
        SCROLL_BAR = 10
        BASE_RES = (1600, 900)

    class TIME:
        ANIM_SPEED = 1
        FADE_TIME = 0.2 * ANIM_SPEED

    class PADDING:
        BUTTON_PADDING = 3 #between text and button edges
        LAYOUT_PADDING = 5 #between items and at corners
        CORNER_RADIUS = 7 #curve of the rectangle borders

    class ALPHA:
        LAYOUT = 16
        BUTTON = 32
        BUTTON_HOVER = 64
        BUTTON_ACTIVE = 255

    class COLOURS:
        BACKGROUND = (50, 51, 57) #of the whole prgram
        FOREGROUND = [255]*3 #foreground * alpha creates visually appealing layers and contrast against background
        FOREGROUND_DEEMPHASISED = [222]*3
        TEXT_NORMAL = [255]*3
        TEXT_HIGHLIGHTED = (99, 108, 119)
        TEXT_INPUT = (99, 108, 119)
        RED = (218, 62, 68)
        GREEN = (67, 162, 90)
        YELLOW = (202, 150, 84)

    class FONTS:
        SANS = "ui/assets/MuseoSans_700.otf"
        MONOSPACE = "ui/assets/LiberationMono-Regular.ttf"

COLOR_MAP = {
    "r" : Style.COLOURS.RED,
    "g" : Style.COLOURS.GREEN    
}
EFFECT_MAP = {
    "b" : "bold",
    "i" : "italic",
    "u" : "underline",
    "st" : "strikethrough"
}

def bt_render(text:str, font:pygame.Font, default_colour=Style.COLOURS.TEXT_NORMAL) -> pygame.Surface:
    pos = 0
    stack = []
    current_style = {'color': default_colour, 'bold': False, 'italic': False, 'underline': False, 'strikethrough' : False}
    output = []

    for match in TAG_RE.finditer(text):
        start, end = match.span()
        tag_open, tag_name = match.groups()

        if start > pos:
            output.append((text[pos:start], current_style.copy()))

        if tag_open == '':
            if tag_name in COLOR_MAP:
                stack.append(('color', current_style['color']))
                current_style['color'] = COLOR_MAP[tag_name]
            elif tag_name in EFFECT_MAP:
                attr = EFFECT_MAP[tag_name]
                stack.append((attr, current_style[attr]))
                current_style[attr] = True
        else:
            if tag_name in COLOR_MAP or tag_name in EFFECT_MAP:
                attr = 'color' if tag_name in COLOR_MAP else EFFECT_MAP[tag_name]
            if stack:
                attr, prev_val = stack.pop()
                current_style[attr] = prev_val

        pos = end

    if pos < len(text):
        output.append((text[pos:], current_style.copy()))

    result = pygame.Surface(font.size(TAG_RE.sub('', text)), pygame.SRCALPHA)
    pos_x = 0
    for segment, style in output:
        font.set_bold(style['bold']) 
        font.set_italic(style['italic'])
        font.set_underline(style['underline'])
        font.set_strikethrough(style['strikethrough'])
        surface = font.render(segment, True, style['color'])
        result.blit(surface, (pos_x, 0))
        pos_x += surface.get_width()
    
    return result