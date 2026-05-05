import os
import json

class Config:
    def __init__(self):
        try:
            with open('utils/color_palettes.json') as f:
                self.color_palettes = json.load(f)
            self.current_palette = self.color_palettes.get("default", {})
        except FileNotFoundError:
            self.color_palettes = {}
            self.current_palette = {}

config = Config()
