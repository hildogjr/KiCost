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
from .global_vars import * # Debug, language and default configurations.

__all__ = ['kicost_setup', 'kicost_unsetup']

if sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH):
    from .os_windows import *

from .kicad_config import *

EESCHEMA_KICOST_FIELDS = ['manf#', 'variant']

###############################################################################
## Auxiliary functions.
###############################################################################


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
        from .kicost import kicost_gui_notdependences
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
    if sys.platform.startswith(PLATFORM_MACOS_STARTS_WITH): # Mac-OS.
        print('I don\'t know how to create the context menu on OSX')
        return False
    elif sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH):
        reg_set(r'xmlfile\shell\KiCost\command',
                None, 'kicost {opt} "%1"'.format(opt=cmd_opt),
                winreg.HKEY_CLASSES_ROOT)
        reg_set(r'xmlfile\shell\KiCost',
                'Icon', icon_path, winreg.HKEY_CLASSES_ROOT)
        reg_set(r'csvfile\shell\KiCost\command',
                None, 'kicost {opt} "%1"'.format(opt=cmd_opt),
                winreg.HKEY_CLASSES_ROOT)
        reg_set(r'csvfile\shell\KiCost',
                'Icon', icon_path, winreg.HKEY_CLASSES_ROOT)
        return True
    elif sys.platform.startswith(PLATFORM_LINUX_STARTS_WITH):
        print('I don\'t know how to create the context menu on Linux')
        return False


def delete_os_contex_menu():
    '''Delete the OS context menu to recognized KiCost files (XML/CSV).'''
    if sys.platform.startswith(PLATFORM_MACOS_STARTS_WITH): # Mac-OS.
        print('I don\'t know how to create the context menu on OSX.')
        return False
    elif sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH):
        return reg_del(r'xmlfile\shell\KiCost\command', winreg.HKEY_CLASSES_ROOT) and \
            reg_del(r'xmlfile\shell\KiCost', winreg.HKEY_CLASSES_ROOT) and \
            reg_del(r'csvfile\shell\KiCost\command', winreg.HKEY_CLASSES_ROOT) and \
            reg_del(r'csvfile\shell\KiCost', winreg.HKEY_CLASSES_ROOT)
    elif sys.platform.startswith(PLATFORM_LINUX_STARTS_WITH):
        print('I don\'t know how to create the context menu on Linux.')
        return False


def create_shortcut(target, directory, name, icon, location=None,
                    description='', category='', terminal='false'):
    '''Generic routine to create shortcuts.'''
    if not location:
        location = os.path.abspath(target)
    if sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH): # Windows.
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
    elif sys.platform.startswith(PLATFORM_LINUX_STARTS_WITH) or sys.platform.startswith(PLATFORM_MACOS_STARTS_WITH): # Mac-OS.
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
        from .kicost import kicost_gui_notdependences
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
        if sys.platform.startswith(PLATFORM_MACOS_STARTS_WITH): # Mac-OS.
            print('I don\'t kwon the desktop folder of mac-OS.')
            shotcut_directories = []
        elif sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH):
            shotcut_directories = [os.path.normpath(reg_get(r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders', 'Desktop'))]
        elif sys.platform.startswith(PLATFORM_LINUX_STARTS_WITH):
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
    try:
        create_os_contex_menu(kicost_path)
        print('KiCost listed at the OS context menu for the associated files.')
    except:
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
            print('Adding KiCost to Eeschema plugin list...')
            try:
                if have_gui:
                    bom_plugin_add_entry(kicost_file_path, 'kicost --gui "%I"', 'KiCost')
                else:
                    bom_plugin_add_entry(kicost_file_path, 'kicost -qwi "%I"', 'KiCost')
                print('KiCost added to KiCad plugin list.')
            except:
                print('Fail to add KiCost to Eeschema plugin list.')
            print('Adding the KiCost fields to Eeschema template...')
            try:
                fields_add_entry(EESCHEMA_KICOST_FIELDS)
                print('{} fields added to Eeschema template.'.format(EESCHEMA_KICOST_FIELDS))
            except:
                print('Error to add {} to Eeschema fields template.'.format(EESCHEMA_KICOST_FIELDS))
        except:
            print('Fail to create KiCad-KiCost integration.')

    print('KiCost setup configuration finished.')

    return


def kicost_unsetup():
    '''Create all the configuration used by KiCost.'''

    print('Removing BOM plugin entry from Eeschema configuration...')
    try:
        bom_plugin_remove_entry('KiCost')
        print('BOM plugin entry removed from Eeschema configuration.')
    except:
        print('Error to remove KiCost from Eeschema plugin list.')

    print('Removing KiCost fields to Eeschema template...')
    try:
        fields_remove_entry(EESCHEMA_KICOST_FIELDS)
        print('{} fields removed to Eeschema template.'.format(EESCHEMA_KICOST_FIELDS))
    except:
        print('Error to remove {} to Eeschema fields template.'.format(EESCHEMA_KICOST_FIELDS))

    print('Deleting KiCost shortcuts...')
    if sys.platform.startswith(PLATFORM_MACOS_STARTS_WITH): # Mac-OS.
        print('I don\'t kwon the desktop folder of mac-OS.')
        kicost_shortcuts = []
    elif sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH):
        kicost_shortcuts = [os.path.normpath(reg_get(r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders', 'Desktop'))]
        kicost_shortcuts = [os.path.join(sc, 'KiCost.lnk') for sc in kicost_shortcuts]
    elif sys.platform.startswith(PLATFORM_LINUX_STARTS_WITH):
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
        print('Fail to remove kiCost shortcuts.')
    print('KiCost shortcuts deleted.')

    print('Removing KiCost from the \'Open with...\' OS context menu...')
    try:
        delete_os_contex_menu()
        print('KiCost removed from the \'Open with...\' OS context menu.')
    except:
        print('Fail to remove kiCost from OS context menu.')

    print('KiCost setup configuration finished.')

    return



###############################################################################
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    kicost_setup()
