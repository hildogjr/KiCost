#!python
# -*- coding: utf-8 -*- 
# MIT license
#
# Copyright (C) 2018 by Hildo Guillardi Júnior
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'
# This script aims to be a post installation configuration script, setting
# shortcuts, plugins, ...

if sys.platform.startswith('win32'):
    # Create the functions to deal with Windows registry, from http://stackoverflow.com/a/35286642
    import winreg
    __all__ = ['get_reg', 'set_reg', 'del_reg']

    def get_reg(path, name, key=winreg.HKEY_CURRENT_USER):
        # Read variable from Windows Registry.
        try:
            reg = winreg.ConnectRegistry(None, key)
            registry_key = winreg.OpenKey(reg, path, 0, winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(registry_key, name)
            winreg.CloseKey(reg)
            return value
        except WindowsError:
            return None

    def set_reg(path, name, value, key=winreg.HKEY_CURRENT_USER, key_type=winreg.REG_SZ):
        # Write in the Windows Registry.
        try:
            reg = winreg.ConnectRegistry(None, key)
            winreg.CreateKey(reg, path)
            registry_key = winreg.OpenKey(reg, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, name, 0, key_type, value)
            winreg.CloseKey(reg)
            # Uptade the Windows behaviour.
            #SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
            return True
        except PermissionError:
            print('You shoud run this command as system administrator: run the terminal as admnistrator and type the command again.')
        except WindowsError:
            return False
    
    def del_reg(name, key=winreg.HKEY_CURRENT_USER):
        # Delete a registry key on Windows.
        try:
            reg = winreg.ConnectRegistry(None, key)
            #registry_key = winreg.OpenKey(reg, name_base, 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteKey(reg, name)
            winreg.CloseKey(reg)
            # Uptade the Windows behaviour.
            #SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
            return True
        except PermissionError:
            print('You shoud run this command as system administrator: run the terminal as admnistrator and type the command again.')
        except WindowsError:
            return False