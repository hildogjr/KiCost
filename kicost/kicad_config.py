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
# This script aims to be a Eeschema configuration layer.

# Python libraries.
import os, sys, re
try:
    import sexpdata # Try to use a external updated library.
except:
    from . import sexpdata # Use the local file.
WINDOWS_STARTS_WITH = 'win32'

__all__ = ['get_app_config_path',
           'PATH_KICAD_CONFIG', 'PATH_EESCHEMA_CONFIG',
           'bom_plugin_add_entry', 'bom_plugin_remove_entry',
           'fields_add_entry', 'fields_remove_entry']

def get_app_config_path(appname):
    if sys.platform == 'darwin':
        from AppKit import NSSearchPathForDirectoriesInDomains
        # http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
        # NSApplicationSupportDirectory = 14
        # NSUserDomainMask = 1
        # True for expanding the tilde into a fully qualified path
        appdata = os.path.join(NSSearchPathForDirectoriesInDomains(5, 1, True)[0], "Preferences" , appname)
    elif sys.platform == 'win32':
        appdata = os.path.join(os.environ['APPDATA'], appname)
    else:
        # ~/.config/kicad
        appdata = os.path.expanduser(os.path.join("~", ".config", appname))
    return appdata

PATH_KICAD_CONFIG = get_app_config_path('kicad')
if not PATH_KICAD_CONFIG:
    raise('KiCad configuration folder not found.')
PATH_EESCHEMA_CONFIG = os.path.join(PATH_KICAD_CONFIG, "eeschema")

def get_user_documents():
    if sys.platform == 'darwin':
        user_documents = os.path.expanduser(os.path.join("~", "Documents"))
    elif sys.platform == 'win32':
        # e.g. c:\users\bob\Documents
        user_documents = os.path.join(os.environ['USERPROFILE'], "Documents")
    else:
        user_documents = os.path.expanduser(os.path.join("~", "Documents"))
    return user_documents


def get_running_processes(appname):
    processes = []
    for p in psutil.process_iter():
        try:
            if p.name().lower().startswith(appname):
                processes.append(p)
        except psutil.Error:
            pass
    return processes


def before(value, a):
    # Find first part and return slice before it.
    pos_a = value.find(a)
    if pos_a == -1: return ""
    return value[0:pos_a]


def after(value, a):
    # Find and validate first part.
    pos_a = value.find(a)
    if pos_a == -1: return ""
    # Returns chars after the found string.
    adjusted_pos_a = pos_a + len(a)
    if adjusted_pos_a >= len(value): return ""
    return value[adjusted_pos_a:]


def de_escape(s):
    result = ""
    in_escape = False
    for c in s:
        if in_escape:
            result += c
            in_escape = False
        else:
            if c== '\\':
                in_escape = True
            else:
                result += c
    return result


def escape(s):
    result = ""
    for c in s:
        result += '\\' + c if c == '\\' else c
    return result


def get_config_item(config, key):
    for p in config:
        if before(p,'=').strip() == key:
            return after(p, '=')


def update_config_file(config, key, value):
    new_config = []
    for p in config:
        if before(p,'=') == key:
            new_config.append(key + '=' + value)
        else:
            new_config.append(p)
    return new_config


def write_config_file(path, config):
    with open(path, "w") as f:
        f.write('\n'.join(config))


def read_config_file(path):
    with open(path) as f:
        config = f.read().split('\n')
    return config


def fields_add_entry(name):
    '''Add a list of fields to the Eeschema template.'''
    return

def fields_remove_entry(name):
    '''Remove a list of fields from the Eeschema template.'''
    return


def bom_plugin_remove_entry(name, re_flags=re.IGNORECASE):
    '''Remove a BOM plugin entry to the Eeschema configuration file.'''
    config = read_config_file(PATH_EESCHEMA_CONFIG)
    bom_plugins_raw = [p for p in config if p.startswith("bom_plugins")]
    new_list = []
    new_list.append(sexpdata.Symbol("plugins"))
    changes = False
    if len(bom_plugins_raw) == 1:
        bom_plugins_raw = after(bom_plugins_raw[0], "bom_plugins=")
        bom_plugins_raw = de_escape(bom_plugins_raw)
        bom_list = sexpdata.loads(bom_plugins_raw)
        if sys.platform.startswith(WINDOWS_STARTS_WITH):
            name = name.replace("\\",'/')
        for plugin in bom_list[1:]:
            search = plugin[1]
            if sys.platform.startswith(WINDOWS_STARTS_WITH):
                search = plugin[1].replace("\\",'/')
            if re.findall(name, search, re_flags):
                changes = True # The name in really in the 'name'.
                continue # We want to delete this entry.
            else:
                for entry in plugin[2:]:
                    if entry[0]==sexpdata.Symbol('opts') and\
                        re.findall('nickname\s*=\s*'+name, entry[1], re_flags):
                            changes = True
                            continue # The name is in the 'nickname'.
                new_list.append(plugin) # This plugin remains on the list.
    if changes:
        s = sexpdata.dumps(new_list)
        config = update_config_file(config, "bom_plugins", escape(s))
    write_config_file(PATH_EESCHEMA_CONFIG, config)


def bom_plugin_add_entry(name, cmd, nickname=None, re_flags=re.IGNORECASE, put_first=True):
    '''Add a BOM plugin entry to the Eeschema configuration file.'''
    config = read_config_file(PATH_EESCHEMA_CONFIG)
    bom_plugins_raw = [p for p in config if p.startswith("bom_plugins")]
    new_list = []
    new_list.append(sexpdata.Symbol("plugins"))
    if len(bom_plugins_raw)==1:
        bom_plugins_raw = after(bom_plugins_raw[0], "bom_plugins=")
        bom_plugins_raw = de_escape(bom_plugins_raw)
        bom_list = sexpdata.loads(bom_plugins_raw)
        if sys.platform.startswith(WINDOWS_STARTS_WITH):
            name = name.replace("\\",'/')
        for plugin in bom_list[1:]:
            search = plugin[1]
            if sys.platform.startswith(WINDOWS_STARTS_WITH):
                search = plugin[1].replace("\\",'/')
            if re.findall(name, search, re_flags):
                if not nickname:
                    return # Plugin already added and don't have nickname.
                for entry in plugin[2:]:
                    if entry[0]==sexpdata.Symbol('opts') and\
                        re.findall('nickname\s*=\s*'+nickname, entry[1], re_flags):
                            return # Plugin already added with this nickname.
            new_list.append(plugin)
    if not nickname:
        new_list.append([sexpdata.Symbol('plugin'), sexpdata.Symbol(name), [sexpdata.Symbol('cmd'), cmd]])
    else:
        new_list.append([sexpdata.Symbol('plugin'), name,
                        [sexpdata.Symbol('cmd'), cmd],
                        [sexpdata.Symbol('opts'), 'nickname={}'.format(nickname)]] )
    if len(new_list):
        # Put KiCost at first.
        if put_first:
            new_list.insert(1, new_list[-1])
            del new_list[-1]
    config = update_config_file(config, "bom_plugins", escape( sexpdata.dumps(new_list) ))
    write_config_file(PATH_EESCHEMA_CONFIG, config)