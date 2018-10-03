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

__all__ = ['config_setup', 'config_unsetup']



###############################################################################
# Main functions.
###############################################################################


def config_setup():
    '''Create all the configuration used by KiCost.'''
    # Check if KiCost really exist.
    try:
        import kicost
        print('KiCad identified at \'{}\', proceding this GUI plugin configuration...'.format(kicost_path))
        kicost_path = os.path.dirname(kicost.__file__)
    except:
        print('KiCost can\'t be reached.\nPost setup not executed!')
        return
    # Check if KiCad is installed.
    print('KiCad identified at \'{}\', proceding this GUI plugin configuration...'.format(kicost_path))
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


def config_unsetup():
    '''Create all the configuration used by KiCost.'''
    
    return




###############################################################################
# Auxiliary functions.
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
    rom kicost.edas import eda_dict
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
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    post_setup()
