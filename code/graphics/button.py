#file: button.py
#Copyright (C) 2008 FunnyMan3595
#This file is part of Endgame: Singularity.

#Endgame: Singularity is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#Endgame: Singularity is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Endgame: Singularity; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#This file contains the Button class.

from __future__ import absolute_import

import pygame

from code.graphics import constants, widget, text, image
from code.pycompat import *


class HotkeyText(text.Text):

    force_underline = widget.causes_rebuild("_force_underline")

    def __init__(self, *args, **kwargs):
        self.hotkey_target = kwargs.pop('hotkey_target', None)
        self.hotkey = kwargs.pop('hotkey', False)
        self.autohotkey = kwargs.pop('autohotkey', False)
        self.force_underline = kwargs.pop('force_underline', None)

        super(HotkeyText, self).__init__(*args, **kwargs)

    @property
    def hotkey_target(self):
        return self._hotkey_target

    @hotkey_target.setter
    def hotkey_target(self, target):
        self._hotkey_target = target
        if self.hotkey_target is not None:
            self._hotkey_target.hotkey = self._hotkey

    @property
    def hotkey(self):
        return self._hotkey

    @hotkey.setter
    def hotkey(self, hotkey):
        self._hotkey = hotkey
        if self.hotkey_target is not None:
            self.hotkey_target.hotkey = self._hotkey
        self.needs_rebuild = True

    @property
    def text(self):
        return text.Text.text.fget(self)

    @text.setter
    def text(self, value):
        if self.autohotkey and (value != None):
            from code.g import hotkey
            parsed_hotkey = hotkey(value)
            self.hotkey = parsed_hotkey['key']
            text.Text.text.fset(self, parsed_hotkey['text'])
        else:
            text.Text.text.fset(self, value)

    def calc_underline(self):
        if self.force_underline != None:
            self.underline = self.force_underline
        elif self.text and self.hotkey and type(self.hotkey) in (str, unicode):
            if self.hotkey in self.text:
                self.underline = self.text.index(self.hotkey)
            elif self.hotkey.lower() in self.text.lower():
                self.underline = self.text.lower().index(self.hotkey.lower())
        else:
            self.underline = -1

    def rebuild(self):
        old_underline = self.underline
        self.calc_underline()
        if self.underline != old_underline:
            self.needs_redraw = True

        super(HotkeyText, self).rebuild()

class Button(text.SelectableText, HotkeyText):

    # Rewrite .hotkey, to update key handlers.
    _hotkey = ""
    def _on_set_hotkey(self, value):
        if self.parent and value != self._hotkey:
            if self._hotkey:
                self.parent.remove_key_handler(self._hotkey, self.handle_event)
            if value:
                self.parent.add_key_handler(value, self.handle_event)
        self._hotkey = value
        self.needs_rebuild = True

    hotkey = property(lambda self: self._hotkey, _on_set_hotkey)

    def __init__(self, parent, pos, size = (0, .045), base_font = None,
                 borders = constants.ALL, text_shrink_factor = .825,
                 priority = 100, **kwargs):
        self.parent = parent

        self.priority = priority

        super(Button, self).__init__(parent, pos, size, **kwargs)

        self.base_font = base_font or "special"
        self.borders = borders
        self.shrink_factor = text_shrink_factor

        self.selected = False

    def add_hooks(self):
        super(Button, self).add_hooks()
        if self.parent:
            self.parent.add_handler(constants.MOUSEMOTION, self.watch_mouse,
                                    self.priority)
            self.parent.add_handler(constants.CLICK, self.handle_event,
                                self.priority)
            if self.hotkey:
                self.parent.add_key_handler(self.hotkey, self.handle_event,
                                            self.priority)

    def remove_hooks(self):
        super(Button, self).remove_hooks()
        if self.parent:
            self.parent.remove_handler(constants.MOUSEMOTION, self.watch_mouse)
            self.parent.remove_handler(constants.CLICK, self.handle_event)
            if self.hotkey:
                self.parent.remove_key_handler(self.hotkey, self.handle_event)

    def watch_mouse(self, event):
        """Selects the button if the mouse is over it."""
        if self.visible and getattr(self, "collision_rect", None):
            # This gets called a lot, so it's been optimized.
            select_now = self.is_over(pygame.mouse.get_pos())
            if (self._selected ^ select_now): # If there's a change.
                self.selected = select_now

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            if self.visible and self.is_over(event.pos):
                self.activate_with_sound(event)
        elif event.type == pygame.KEYDOWN:
            if self.visible and self.hotkey in (event.unicode, event.key):
                self.activate_with_sound(event)

    def activate_with_sound(self, event):
        """Called when the button is pressed or otherwise triggered.

           This method is called directly by the GUI handler, and should be
           overwritten only to remove the click it plays."""

        from code.mixer import play_sound
        play_sound("click")
        self.activated(event)

    def activated(self, event):
        """Called when the button is pressed or otherwise triggered."""
        raise constants.Handled

class ImageButton(Button):

    def __init__(self, *args, **kwargs):
        image_surface = kwargs.pop("image", None)

        super(ImageButton, self).__init__(*args, **kwargs)

        self.image = image.Image(self, (-.5, -.5), (-.9, -.9),
                                 anchor = constants.MID_CENTER,
                                 image = image_surface)


class FunctionButton(Button):
    def __init__(self, *args, **kwargs):
        self.function = kwargs.pop("function", lambda *args, **kwargs: None)
        self.args = kwargs.pop("args", ())
        self.kwargs = kwargs.pop("kwargs", {})
        super(FunctionButton, self).__init__(*args, **kwargs)

    def activated(self, event):
        """FunctionButton's custom activated menu.  Makes the given function
           call and raises Handled if it returns without incident."""
        self.function(*self.args, **self.kwargs)
        raise constants.Handled


class ExitDialogButton(FunctionButton):
    def __init__(self, *args, **kwargs):
        self.exit_code = kwargs.pop("exit_code", None)
        self.exit_code_func = kwargs.pop("exit_code_func", None)
        self.default = kwargs.pop("default", True)
        super(ExitDialogButton, self).__init__(*args, **kwargs)
        self.function = self.exit_dialog

    def add_hooks(self):
        super(ExitDialogButton, self).add_hooks()
        if self.parent:
            self.parent.add_key_handler(pygame.K_ESCAPE, self.activate_default)

    def remove_hooks(self):
        super(ExitDialogButton, self).remove_hooks()
        if self.parent:
            self.parent.remove_key_handler(pygame.K_ESCAPE, self.activate_default)

    def activate_default(self, event):
        if event.type != pygame.KEYDOWN or not self.default:
            return

        return self.activate_with_sound(event)

    def exit_dialog(self):
        """Closes the dialog with the given exit code."""
        if self.exit_code_func:
            raise constants.ExitDialog(self.exit_code_func())
        else:
            raise constants.ExitDialog(self.exit_code)

class DialogButton(FunctionButton):
    def __init__(self, *args, **kwargs):
        self.dialog = kwargs.pop("dialog", None)
        super(DialogButton, self).__init__(*args, **kwargs)
        self.function = self.show_dialog

    def show_dialog(self):
        """When the assigned dialog exits, raises Handled with the dialog's
           exit code as a parameter.  Subclass if you care what the code was."""
        if not self.dialog:
            raise constants.Handled
        else:
            from code.graphics import dialog
            raise constants.Handled(dialog.call_dialog(self.dialog, self))


TOGGLE_VALUE = object()
WIDGET_SELF = object()
class ToggleButton(Button):
    active = False
    button_group = None

    def replace_args(self, value):
        if value is TOGGLE_VALUE:
            return self.active
        elif value is WIDGET_SELF:
            return self
        else:
            return value
            
    def get_args(self):
        return tuple(self.replace_args(value) for value in self._args)
        
    def set_args(self, args):
        self._args = args
    args = property(get_args, set_args)

    def chosen_one(self):
        if self.button_group is not None:
            for button in self.button_group:
                button.set_active(False)
            self.set_active(True)
        else:
            self.set_active(not self.active)

    def set_active(self, active):
        self.active = active
        self.selected = active
        if hasattr(self, "_collision_rect"):
            self.watch_mouse(None)

    def activated(self, event):
        self.chosen_one()
        super(ToggleButton, self).activated(event)

    def watch_mouse(self, event):
        if not self.active:
            super(ToggleButton, self).watch_mouse(event)

class ButtonGroup(list):
    def add(self, button):
        button.button_group = self
        super(ButtonGroup, self).append(button)

    def remove(self, button):
        button.button_group = None
        super(ButtonGroup, self).remove(button)
