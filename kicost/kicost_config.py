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
import os, sys, re
try:
    import sexpdata
except:
    from . import sexpdata

__all__ = ['kicost_setup', 'kicost_unsetup']

WINDOWS_STARTS_WITH = "win32"



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


def remove_bom_plugin_entry(kicad_config_path, name, re_flags=re.IGNORECASE):
    '''Remove a BOM plugin enttry to the Eeschema configuration file.'''
    config = read_config_file(os.path.join(kicad_config_path, "eeschema"))
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
    write_config_file(os.path.join(kicad_config_path, "eeschema"), config)


def add_bom_plugin_entry(kicad_config_path, name, cmd, nickname=None, re_flags=re.IGNORECASE):
    '''Add a BOM plugin entry to the Eeschema configuration file.'''
    config = read_config_file(os.path.join(kicad_config_path, "eeschema"))
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
        new_list.insert(1, new_list[-1])
        del new_list[-1]
    config = update_config_file(config, "bom_plugins", escape( sexpdata.dumps(new_list) ))
    write_config_file(os.path.join(kicad_config_path, "eeschema"), config)



###############################################################################
## Auxiliary functions.
###############################################################################

if sys.platform.startswith(WINDOWS_STARTS_WITH):
    # Create the functions to deal with Windows registry, from http://stackoverflow.com/a/35286642
    import winreg

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


def install_kicad_plugin(path):
    '''Create the plugin installation if KiCad present'''
    from shutil import copyfile
    copyfile(os.path.join(path, 'kicost_kicadplugin.py'),'')
    return


def create_os_contex_menu(kicost_path):
    '''Create the OS context menu to recognized KiCost files (XML/CSV).'''
    try:
        import wx # wxWidgets for Python.
        #print('GUI requirements (wxPython) identified.')
        have_gui = True
    except ImportError:
        kicost_gui_notdependences
        have_gui = False
    except Exception as e:
        print(e)
        have_gui = False
        pass
    if have_gui:
        cmd_opt = '--gui'
    else:
        cmd_opt = '-wi'
    icon_path = os.path.join(kicost_path, 'kicost.ico')
    if sys.platform.startswith('darwin'): # Mac-OS.
        print('I don\'t know how to create the context menu on OSX')
        return False
    elif sys.platform.startswith(WINDOWS_STARTS_WITH):
        set_reg(r'xmlfile\shell\KiCost\command',
                None, 'kicost {opt} "%1"'.format(opt=cmd_opt),
                winreg.HKEY_CLASSES_ROOT)
        set_reg(r'xmlfile\shell\KiCost',
                'Icon', icon_path, winreg.HKEY_CLASSES_ROOT)
        set_reg(r'csvfile\shell\KiCost\command',
                None, 'kicost {opt} "%1"'.format(opt=cmd_opt),
                winreg.HKEY_CLASSES_ROOT)
        set_reg(r'csvfile\shell\KiCost',
                'Icon', icon_path, winreg.HKEY_CLASSES_ROOT)
        return True
    elif sys.platform.startswith('linux'):
        print('I don\'t know how to create the context menu on Linux')
        return False


def delete_os_contex_menu():
    '''Delete the OS context menu to recognized KiCost files (XML/CSV).'''
    if sys.platform.startswith('darwin'): # Mac-OS.
        print('I don\'t know how to create the context menu on OSX.')
        return False
    elif sys.platform.startswith(WINDOWS_STARTS_WITH):
        return del_reg(r'xmlfile\shell\KiCost\command', winreg.HKEY_CLASSES_ROOT) and \
            del_reg(r'xmlfile\shell\KiCost', winreg.HKEY_CLASSES_ROOT) and \
            del_reg(r'csvfile\shell\KiCost\command', winreg.HKEY_CLASSES_ROOT) and \
            del_reg(r'csvfile\shell\KiCost', winreg.HKEY_CLASSES_ROOT)
    elif sys.platform.startswith('linux'):
        print('I don\'t know how to create the context menu on Linux.')
        return False


def create_shortcut(target, directory, name, icon, location=None,
                    description='', category='', terminal='false'):
    '''Generic routine to create shortcuts.'''
    if not location:
        location = os.path.abspath(target)
    if sys.platform.startswith(WINDOWS_STARTS_WITH): # Windows.
        from win32com.client import Dispatch
        shell = Dispatch('WScript.Shell')
        shortcut_path = os.path.join(directory, name+'.lnk')
        shortcut_path = os.path.expandvars(shortcut_path)
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = location
        shortcut.IconLocation = icon
        shortcut.save()
        return True
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'): # Mac-OS.
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
        return True
    else:
        print('Unrecognized OS.\nShortcut not created!')
        return False
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
        except ImportError:
            print('KiCost module not found.\nPost setup not executed!')
            return None
    return os.path.abspath(kicost_path)


def kicost_setup():
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
    print('KiCost identified at \'{}\', proceeding with it configuration in file \'{}\'...'.format(kicost_path, kicad_config_path))
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

    if have_gui:
        print('Creating app shortcuts...')
        if sys.platform.startswith('darwin'): # Mac-OS.
            print('I don\'t kwon the desktop folder of mac-OS.')
            shotcut_directories = []
        elif sys.platform.startswith(WINDOWS_STARTS_WITH):
            shotcut_directories = [os.path.normpath(get_reg(r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders', 'Desktop'))]
        elif sys.platform.startswith('linux'):
            shotcut_directories = [os.path.expanduser(os.path.join("~", "Desktop"))]
        else:
            print('Not recognized OS.\nShortcut not created!')
        for shotcut_directory in shotcut_directories:
            if not create_shortcut('kicost', shotcut_directory, 
                            'KiCost', os.path.join(kicost_path, 'kicost.ico'), '',
                            'Generate a Cost Bill of Material for EDA softwares', 'BOM'):
                print('Failed to create the KiCost shortcut!')
                break
        print('Check your desktop for the KiCost shortcut.')

    print('Creating OS context integration...')
    if create_os_contex_menu(kicost_path):
        print('KiCost listed at the OS context menu for the associated files.')
    else:
        print('Failed to create KiCost OS context menu integration.')

    if have_gui:
        print('Setting the GUI to display the NEWS message...')
        try:
            from .kicost_gui import CONFIG_FILE, GUI_NEWS_MESSAGE_ENTRY
            configHandle = wx.Config(CONFIG_FILE)
            configHandle.Write(GUI_NEWS_MESSAGE_ENTRY, 'True')
            print('The user interface will display the NEWS message on first startup.')
        except:
            print('Failed to set to display the news message on GUI.')

    print('Creating KiCad integration...')
    if not os.path.isfile(os.path.join(kicad_config_path, 'eeschema')):
        print('###  ---> Eeschema was never started. start it and after run `kicost --setup` to configure.')
    else:
        try:
            if have_gui:
                add_bom_plugin_entry(kicad_config_path, kicost_file_path, 'kicost --gui "%I"', 'KiCost')
            else:
                add_bom_plugin_entry(kicad_config_path, kicost_file_path, 'kicost -qwi "%I"', 'KiCost')
            try:
                # Set KiCost as default plugin.
                import fileinput
                for line in fileinput.input(os.path.join(kicad_config_path, 'eeschema'), inplace=True):
                    if line.strip().startswith('bom_plugin_selected='):
                        line = 'bom_plugin_selected=KiCost\n'
                    sys.stdout.write(line)
                print('KiCost will appear in the Eeschema BOM plugin list.')
            except:
                print('Falied to set KiCost as default BOM plugin.')
        except:
            print('Failed to add KiCost as KiCad BOM plugin.')

    print('KiCost setup configuration finished.')

    return


def kicost_unsetup():
    '''Create all the configuration used by KiCost.'''
    kicad_config_path = get_app_config_path('kicad')
    kicost_path = os.path.join(get_kicost_path(), 'kicost.py')
    if not kicad_config_path:
        raise('KiCad configuration folder not found.')

    print('Removing BOM plugin entry from Eeschma configuration...')
    remove_bom_plugin_entry(kicad_config_path, 'KiCost')
    print('BOM plugin entry removed from Eeschma configuration.')

    print('Deleting KiCost shortcuts...')
    if sys.platform.startswith('darwin'): # Mac-OS.
        print('I don\'t kwon the desktop folder of mac-OS.')
        kicost_shortcuts = []
    elif sys.platform.startswith(WINDOWS_STARTS_WITH):
        kicost_shortcuts = [os.path.normpath(get_reg(r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders', 'Desktop'))]
        kicost_shortcuts = [os.path.join(sc, 'KiCost.lnk') for sc in kicost_shortcuts]
    elif sys.platform.startswith('linux'):
        kicost_shortcuts = [os.path.expanduser(os.path.join('~', 'Desktop'))]
        for count in range(len(kicost_shortcuts)):
            kicost_shortcuts[count] = os.path.join(kicost_shortcuts[count], 'KiCost.desktop')
    else:
        print('Unrecognized OS.\nShortcut not created!')
    try:
        for kicost_shortcut in kicost_shortcuts:
            kicost_shortcut = os.path.expandvars(kicost_shortcut)
            try:
                os.remove(kicost_shortcut)
            except FileNotFoundError:
                pass
    except:
        print('Falied to remove kiCost shortcuts.')
    print('KiCost shortcuts deleted.')

    print('Removing KiCost from the \'Open with...\' OS context menu...')
    if delete_os_contex_menu():
        print('KiCost removed from the \'Open with...\' OS context menu.')
    else:
        print('Falied to remove kiCost from OS context menu.')

    print('KiCost setup configuration finished.')

    return



###############################################################################
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    kicost_setup()
