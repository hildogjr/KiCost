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

__all__ = ['config_setup_kicost', 'config_unsetup_kicost']


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
        appdata = os.path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], appname)
    elif sys.platform == 'win32':
        appdata = os.path.join(os.environ['APPDATA'], appname)
    else:
        # ~/.kicad
        appdata = os.path.expanduser(os.path.join("~", "." + appname))
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
    new_list.append(Symbol("plugins"))
    changes = False
    if len(bom_plugins_raw) == 1:
        bom_plugins_raw = after(bom_plugins_raw[0], "bom_plugins=")
        bom_plugins_raw = de_escape(bom_plugins_raw)
        # print(bom_plugins_raw)
        bom_list = sexpdata.loads(bom_plugins_raw)
        for plugin in bom_list[1:]:
            #print("name = ", plugin[1].value())
            #print("cmd = " , plugin[2][1])
            if plugin[1].value() == name:
                # we want to delete this entry
                if args.verbose:
                    print("Removing %s" % name)
                changes = True
            else:
                new_list.append(plugin)
    if changes and not args.test:
        s = sexpdata.dumps(new_list)
        # save into config
        config = update_config_file(config, "bom_plugins", escape(s))
    write_config_file(os.path.join(paths.kicad_config_dir, "eeschema"), config)

def add_bom_plugin_entry(paths, name, cmd):
    # get from eeschema config
    config = read_config_file(os.path.join(paths.kicad_config_dir, "eeschema"))
    bom_plugins_raw = [p for p in config if p.startswith("bom_plugins")]
    new_list = []
    new_list.append(Symbol("plugins"))
    if len(bom_plugins_raw)==1:
        bom_plugins_raw = after(bom_plugins_raw[0], "bom_plugins=")
        bom_plugins_raw = de_escape(bom_plugins_raw)
        #print(bom_plugins_raw)
        bom_list = sexpdata.loads(bom_plugins_raw)
        for plugin in bom_list[1:]:
            #print("name = ", plugin[1].value())
            #print("cmd = " , plugin[2][1])
            new_list.append(plugin)
    if not args.test:
        if args.verbose:
            print("Adding %s" % name)
        new_list.append([Symbol('plugin'), Symbol(name), [Symbol('cmd'), cmd]])
        s = sexpdata.dumps(new_list)
        # save into config
        config = update_config_file(config, "bom_plugins", escape(s))
    write_config_file(os.path.join(paths.kicad_config_dir, "eeschema"), config)


###############################################################################
## Auxiliary functions.
###############################################################################


def kicost_gui_notdependences():
    '''Just warnning about the wxPython installtion.'''
    print('You don\'t have the wxPython dependence to run the GUI interface. Run once of the follow commands in terminal to install them:')
    print('pip3 install -U wxPython # For Windows & macOS')

    print('pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-16.04 wxPython # For Linux 16.04')
    print('Or download from last version from <https://wxpython.org/pages/downloads/>')


def install_kicad_plugin(path):
    '''Create the plugin installation if KiCad present'''
    from shutil import copyfile
    copyfile(os.path.join(path, 'kicost_kicadplugin.py'),'')
    return


def create_os_contex_menu(path):
    '''Create the OS context menu to recognized KiCost files (XML/CSV).'''
    from kicost.edas import eda_dict
    if sys.platform.startswith('windows'):
        import _winreg as wreg
        key = wreg.OpenKey(wreg.HKEY_LOCAL_MACHINE, "HKEY_CLASSES_ROOT\\xmlfile\\shell\\KiCost",0, wreg.KEY_ALL_ACCESS)
        if not guide:
            cmd_opt = '--guide'
        else:
            cmd_opt = '-wi'
        wreg.SetValue(key, 'command', wreg.REG_SZ, '{kicost} {opt} "%1"'.format(
                    kicost=os.path.join(kicost_path, 'kicost'),
                    opt=cmd_opt
                ))
        wreg.SetValueEx(key, 'ValueName', 0, wreg.REG_SZ, 'testvalue')
        key.Close()

def create_gui_shortcut(path):
    '''Create the OS shortcut on applications list.'''
    try:
        
        directory
        location
        
        create_shortcut('kicost', directory, 'KiCost', 
                os.path.join(location, 'kicost.ico'),
                location,
                'Generate a Cost Bill of Material for EDA softwares')
    except:
        print('Error. Shortcut not created!')
        pass
    return

def create_shortcut(target, directory, name, icon, location, description=''):
    '''Generic routine to create shortcuts.'''
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
        if description:
            content += '\nComment='+description
        content += '\nCategories=BOM'
        content += '\nTerminal=false'
        if directory:
            content += '\nPath={}'.format(directory)
        if icon:
            content += '\nIcon{}'.format(icon)
        path = os.path.join(directory, name+'.desktop')
        with open(path, 'w') as shortcut:
            shortcut.write(content)
            shortcut.close()
        os.chmod(path)
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
        print('KiCad identified at \'{}\', proceding this GUI plugin configuration...'.format(kicost_path))
        kicost_path = kicost.__file__
    except:
        try:
            import imp
            kicost_path = imp.find_module('kicost')[1]
        except:
            print('KiCost can\'t be reached.\nPost setup not executed!')
            return None
    return os.path.dirname( os.path.abspath(kicost_path) )


def config_setup_kicost():
    '''Create all the configuration used by KiCost.'''
    # Check if KiCost really exist.
    kicost_path = get_kicost_path()
    if not kicost_path:
        raise('KiCost installation not found to configurate it.')
    kicost_config_path = get_app_config_path('kicad')
    if not kicost_config_path:
        raise('KiCad configuration folder not found.')
    print('KiCost identified at \'{}\', proceding with it configuration...'.format(kicost_path))
    add_bom_plugin_entry(kicost_config_path, 'KiCost', 'kicost --guide "%I"')
    add_bom_plugin_entry(kicost_config_path, 'KiCost', 'kicost -qwi "%I"')
    
    # Check if KiCad is installed.
    
    kicad_installation = True
    # Check if wxPython is present.
    try:
        import wx # wxWidgets for Python.
        print('wxPython identified, proceding this GUI shortcut configuration...')
        guide = True
    except ImportError:
        kicost_gui_notdependences
        guide = False
    except Exception as e:
        print(e)
        guide = False
        pass

    if guide:
        create_gui_shortcut(kicost_path)
    install_kicad_plugin(kicost_path)
    create_os_contex_menu(kicost_path)

def config_unsetup_kicost():
    '''Create all the configuration used by KiCost.'''
    kicost_path = get_kicost_path()
    remove_bom_plugin_entry(kicost_path, 'KiCost')
    return

###############################################################################
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    config_setup_kicost()
