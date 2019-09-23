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

import sys

if sys.platform.startswith('win32'):
    # Create the functions to deal with Windows registry, from http://stackoverflow.com/a/35286642
    if sys.version_info < (3,0):
        from _winreg import *
    else:
        from winreg import *
    __all__ = ['reg_enum_values', 'reg_enum_keys', 'reg_get', 'reg_set', 'reg_del']


    def reg_enum_values(path, key=HKEY_CURRENT_USER):
        # Read variable from Windows Registry.
        try:
            reg = ConnectRegistry(None, key)
            try:
                registry_key = OpenKey(reg, path, 0, KEY_READ)
            except FileNotFoundError:
                registry_key = OpenKey(reg, path, 0, KEY_READ | KEY_WOW64_64KEY)
            values = ()
            try:
                idx = 0
                while 1:
                    values.append( EnumValue(registry_key, idx) )
                    idx = idx + 1
            except WindowsError:
                pass
            return values
            CloseKey(reg)
            return value
        except WindowsError:
            return None

    def reg_enum_keys(path, key=HKEY_CURRENT_USER):
        # Read variable from Windows Registry.
        try:
            reg = ConnectRegistry(None, key)
            try:
                registry_key = OpenKey(reg, path, 0, KEY_READ)
            except FileNotFoundError:
                registry_key = OpenKey(reg, path, 0, KEY_READ | KEY_WOW64_64KEY)
            sub_keys = []
            try:
                idx = 0
                while 1:
                    sub_keys.append( EnumKey(registry_key, idx) )
                    idx = idx + 1
            except WindowsError:
                pass
            CloseKey(reg)
            return sub_keys
        except WindowsError:
            return None

    def reg_get(path, name, key=HKEY_CURRENT_USER):
        # Read variable from Windows Registry.
        try:
            reg = ConnectRegistry(None, key)
            try:
                registry_key = OpenKey(reg, path, 0, KEY_READ)
            except FileNotFoundError:
                registry_key = OpenKey(reg, path, 0, KEY_READ | KEY_WOW64_64KEY)
            value, regtype = QueryValueEx(registry_key, name)
            CloseKey(reg)
            return value
        except WindowsError:
            return None

    def reg_set(path, name, value, key=HKEY_CURRENT_USER, key_type=REG_SZ):
        # Write in the Windows Registry.
        try:
            reg = ConnectRegistry(None, key)
            CreateKey(reg, path)
            try:
                registry_key = OpenKey(reg, path, 0, KEY_WRITE)
            except FileNotFoundError:
                registry_key = OpenKey(reg, path, 0, KEY_WRITE | KEY_WOW64_64KEY)
            SetValueEx(registry_key, name, 0, key_type, value)
            CloseKey(reg)
            # Update the Windows behaviour.
            #SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
            return True
        except PermissionError:
            print('You should run this command as system administrator: run the terminal as administrator and type the command again.')
        except WindowsError:
            return False
    
    def reg_del(name, key=HKEY_CURRENT_USER):
        # Delete a registry key on Windows.
        try:
            reg = ConnectRegistry(None, key)
            #registry_key = OpenKey(reg, name_base, 0, KEY_ALL_ACCESS)
            DeleteKey(reg, name)
            CloseKey(reg)
            # Update the Windows behaviour.
            #SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
            return True
        except PermissionError:
            print('You should run this command as system administrator: run the terminal as administrator and type the command again.')
        except WindowsError:
            return False