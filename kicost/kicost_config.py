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


# Python libraries.
import os, sys
try:
    import sexpdata
except:
    from . import sexpdata

__all__ = ['setup', 'unsetup']


###############################################################################
## Functions to associate KiCost with KiCad, showing it in the BoM plugin list.
## Most of this functions are from https://github.com/bobc/kicad-getlibs/blob/master/kipi/kicad_getlibs.py
###############################################################################

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

def de_escape (s):
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

def escape (s):
    result = ""
    for c in s:
        if c == '\\':
            result += '\\' + c
        else:
            result += c
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

def remove_bom_plugin_entry(paths, name):
    # get list of current plugins from eeschema config
    config = read_config_file(os.path.join(paths.kicad_config_dir, "eeschema"))
    bom_plugins_raw = [p for p in config if p.startswith("bom_plugins")]
    new_list = []
    new_list.append(sexpdata.Symbol("plugins"))
    changes = False
    if len(bom_plugins_raw) == 1:
        bom_plugins_raw = after(bom_plugins_raw[0], "bom_plugins=")
        bom_plugins_raw = de_escape(bom_plugins_raw)
        bom_list = sexpdata.loads(bom_plugins_raw)
        for plugin in bom_list[1:]:
            #print("name = ", plugin[1].value())
            #print("cmd = " , plugin[2][1])
            if plugin[1].value() == name:
                # we want to delete this entry
                changes = True
            else:
                new_list.append(plugin)
    if changes:
        s = sexpdata.dumps(new_list)
        config = update_config_file(config, "bom_plugins", escape(s))
    write_config_file(os.path.join(paths.kicad_config_dir, "eeschema"), config)

def add_bom_plugin_entry(paths, name, cmd):
    # get from eeschema config
    config = read_config_file(os.path.join(paths.kicad_config_dir, "eeschema"))
    bom_plugins_raw = [p for p in config if p.startswith("bom_plugins")]
    new_list = []
    new_list.append(sexpdata.Symbol("plugins"))
    if len(bom_plugins_raw)==1:
        bom_plugins_raw = after(bom_plugins_raw[0], "bom_plugins=")
        bom_plugins_raw = de_escape(bom_plugins_raw)
        #print(bom_plugins_raw)
        bom_list = sexpdata.loads(bom_plugins_raw)
        for plugin in bom_list[1:]:
            new_list.append(plugin)
    #new_list.append([sexpdata.Symbol('plugin'), sexpdata.Symbol(name), [sexpdata.Symbol('cmd'), cmd]])
    new_list.append( [sexpdata.Symbol('plugin'), '/usr/local/lib/python3.5/dist-packages/kicost/kicost.py', [sexpdata.Symbol('cmd'), 'kicost --gui "%I"'], [sexpdata.Symbol('opts'), 'nickname=KiCost']] )
    s = sexpdata.dumps(new_list)
    # save into config
    config = update_config_file(config, "bom_plugins", escape(s))
    write_config_file(os.path.join(paths.kicad_config_dir, "eeschema"), config)



###############################################################################
## Auxiliary functions.
###############################################################################

if sys.platform.startswith('windows'):
    import shutil, sysconfig, winreg

    def get_reg(path, name):
        # Read variable from Windows Registry.
        # From http://stackoverflow.com/a/35286642
        try:
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                                           winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(registry_key, name)
            winreg.CloseKey(registry_key)
            return value
        except WindowsError:
            return None

    def set_reg(path, name, value):
        # Write in the Windows Registry.
        try:
            winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, path)
            registry_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, path, 0, 
                                           winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
            winreg.CloseKey(registry_key)
            return True
        except WindowsError:
            return False


def install_kicad_plugin(path):
    '''Create the plugin installation if KiCad present'''
    from shutil import copyfile
    copyfile(os.path.join(path, 'kicost_kicadplugin.py'),'')
    return


def create_os_contex_menu(path):
    '''Create the OS context menu to recognized KiCost files (XML/CSV).'''
    try:
        import wx # wxWidgets for Python.
        print('GUI requirements (wxPython) identified.')
        have_gui = True
    except ImportError:
        kicost_gui_notdependences
        have_gui = False
    except Exception as e:
        print(e)
        have_gui = False
        pass
    if not have_gui:
        cmd_opt = '--gui'
    else:
        cmd_opt = '-wi'
    if sys.platform.startswith('darwin'): # Mac-OS.
        print('I don\'t kwon how to create the context menu on OSX')
    elif sys.platform.startswith('windows'):
        set_reg(wreg.HKEY_LOCAL_MACHINE, '\xmlfile\shell\KiCost', 'command', 'kicost {opt} "%1"'.format(cmd_opt))
        set_reg(wreg.HKEY_LOCAL_MACHINE, '\csvfile\shell\KiCost', 'command', 'kicost {opt} "%1"'.format(cmd_opt))
    elif sys.platform.startswith('linux'):
        print('I don\'t kwon how to create the context menu on Linux')


def create_shortcut(target, directory, name, icon, location=None, description='', category='', terminal='false'):
    '''Generic routine to create shortcuts.'''
    if not location:
        location = os.path.abspath(target)
    if sys.platform.startswith('darwin'): # Mac-OS.
        print('I don\'t kwon how to create a shortcut in OSX')
    elif sys.platform.startswith('windows'): # Windows.
        import winshell
        from win32com.client import Dispatch
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(os.path.join(directory, name+'.lnk'))
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = location
        shortcut.IconLocation = icon
        shortcut.save()
    elif sys.platform.startswith('linux'): # Linux.
        content = '[Desktop Entry]\nType=Application\nName={name}\nExec={target}'.format(
                    name=name, target=target)
        content += '\nTerminal={}'.format(terminal)
        if description:
            content += '\nComment=\''+description+'\''
        content += '\nCategories={}'.format(category)
        content += '\nPath={}'.format(location)
        if icon:
            content += '\nIcon={}'.format(icon)
        path = os.path.join(directory, name+'.desktop')
        with open(path, 'w') as shortcut:
            shortcut.write(content)
            shortcut.close()
        import stat
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    else:
        print('Not recognized OS.\nShortcut not created!')
    return



###############################################################################
## Main functions.
###############################################################################

def get_kicost_path():
    '''Get KiCost installation path.'''
    try:
        import kicost
        kicost_path = os.path.dirname(kicost.__file__)
    except:
        try:
            import imp
            kicost_path = imp.find_module('kicost')[1]
        except:
            print('KiCost can\'t be reached.\nPost setup not executed!')
            return None
    return os.path.abspath(kicost_path)


def setup():
    '''Create all the configuration used by KiCost.'''
    # Check if KiCost really exist.
    kicost_path = get_kicost_path()
    kicost_file_path = os.path.join(kicost_path, 'kicost.py')
    if not kicost_path:
        raise('KiCost installation not found to configurate it.')
    # Check if KiCad is installed.
    kicad_config_path = get_app_config_path('kicad')
    if not kicad_config_path:
        raise('KiCad configuration folder not found.')
    print('KiCost identified at \'{}\', proceding with it configuration in file \'{}\'...'.format(kicost_path, kicad_config_path))
    # Check if wxPython is present.
    try:
        import wx # wxWidgets for Python.
        print('GUI requirements (wxPython) identified.')
        have_gui = True
    except ImportError:
        kicost_gui_notdependences
        have_gui = False
    except Exception as e:
        print(e)
        have_gui = False
        pass

    if not have_gui:
        MESSAGE = 'Do want to install the GUI requirement packages? (Y/n)\n'
        if sys.version_info >= (3,0):
            ans = input(MESSAGE)
        else:
            ans = raw_input(MESSAGE)
        if ans.lower() in ['y', 'yes']:
            try:
                from pip import main as pipmain
            except ImportError:
                from pip._internal import main as pipmain
            pipmain(['install', 'wxpython'])
            have_gui = True # now the Graphical User Interface is installed.

    print('Creating KiCad integration...')
    if have_gui:
        class Path():
            pass
        Path.kicad_config_dir = kicad_config_path
        add_bom_plugin_entry(Path(), '"'+kicost_file_path+'"', 'kicost --gui "%I"')
    else:
        class Path():
            pass
        Path.kicad_config_dir = kicad_config_path
        add_bom_plugin_entry(Path(), '"'+kicost_path+'"', 'kicost -qwi "%I"')
    print('KiCost will appear in the Eeschema BOM plugin list.')

    if have_gui:
        print('Creating app shortcuts...')
        if sys.platform.startswith('darwin'): # Mac-OS.
            print('I don\'t kwon the desktop folder of mac-OS.')
            shotcut_directories = []
        elif sys.platform.startswith('windows'):
            shotcut_directories = [os.path.normpath(get_reg(r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders', 'Desktop'))]
        elif sys.platform.startswith('linux'):
            shotcut_directories = [os.path.expanduser(os.path.join("~", "Desktop"))]
        else:
            print('Not recognized OS.\nShortcut not created!')
        for shotcut_directory in shotcut_directories:
            create_shortcut('kicost', shotcut_directory, 
                            'KiCost', os.path.join(kicost_path, 'kicost.ico'), '',
                            'Generate a Cost Bill of Material for EDA softwares', 'BOM')

    print('Creating OS context integration...')
    #create_os_contex_menu(kicost_path)


def unsetup():
    '''Create all the configuration used by KiCost.'''
    kicad_config_path = get_app_config_path('kicad')
    class Path():
        pass
    Path.kicad_config_dir = kicad_config_path
    kicost_path = os.path.join(get_kicost_path(), 'kicost.py')
    if not kicad_config_path:
        raise('KiCad configuration folder not found.')
    remove_bom_plugin_entry(Path(), '"'+kicost_path+'"')
    return



###############################################################################
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    setup()
