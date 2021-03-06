#!/usr/bin/python3
'''
   Copyright 2017 Mirko Brombin (brombinmirko@gmail.com)
   Copyright 2017 Ian Santopietro (ian@system76.com)

   This file is part of Repoman.

    Repoman is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Repoman is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Repoman.  If not, see <http://www.gnu.org/licenses/>.
'''

import apt
import dbus
import logging
import sys
import threading, queue, time

from softwareproperties.SoftwareProperties import SoftwareProperties
from aptsources.sourceslist import SourceEntry

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib

GLib.threads_init()

bus = dbus.SystemBus()
remote_object = bus.get_object(
    'ro.santopiet.repoman', '/PPAObject'
)

class RemoveThread(threading.Thread):
    cache = apt.Cache()

    def __init__(self, parent, sources_path, ppa, sp):
        threading.Thread.__init__(self)
        self.parent = parent
        self.sources_path = sources_path
        self.ppa = ppa
        self.sp = sp

        self.log = logging.getLogger("repoman.PPA.RemoveThread")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.WARNING)

    def run(self):
        self.log.info( "Removing PPA %s" % (self.ppa) )
        try:
            remote_object.DelPPA(self.ppa)
        except:
            self.exc = sys.exc_info()
            self.throw_error(self.exc[1])
        self.sp.reload_sourceslist()
        isv_list = self.sp.get_isv_sources()
        GObject.idle_add(self.parent.parent.stack.list_all.view.set_sensitive, True)
        GObject.idle_add(self.parent.parent.hbar.spinner.stop)
        GObject.idle_add(self.parent.parent.stack.list_all.generate_entries, isv_list)

    def throw_error(self, message):
        GObject.idle_add(self.parent.parent.stack.list_all.throw_error_dialog,
                         message, "error")

class AddThread(threading.Thread):
    cache = apt.Cache()

    def __init__(self, parent, ppa, sp):
        threading.Thread.__init__(self)
        self.parent = parent
        self.ppa = ppa
        self.sp = sp

        self.log = logging.getLogger("repoman.PPA.AddThread")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.WARNING)

    def run(self):
        self.log.info("Adding PPA %s" % (self.ppa))
        try:
            remote_object.AddPPA(self.ppa)
        except:
            self.exc = sys.exc_info()
            self.throw_error(self.exc[1])
        self.sp.reload_sourceslist()
        isv_list = self.sp.get_isv_sources()
        GObject.idle_add(self.parent.parent.parent.stack.list_all.generate_entries, isv_list)
        GObject.idle_add(self.parent.parent.parent.stack.list_all.view.set_sensitive, True)
        GObject.idle_add(self.parent.parent.parent.hbar.spinner.stop)

    def throw_error(self, message):
        GObject.idle_add(self.parent.parent.parent.stack.list_all.throw_error_dialog,
                         message, "error")

class ModifyThread(threading.Thread):
    cache = apt.Cache()

    def __init__(self, parent, old_source, new_source, sp):
        threading.Thread.__init__(self)
        self.parent = parent
        self.old_source = old_source
        self.new_source = new_source
        self.sp = sp

        self.log = logging.getLogger("repoman.PPA.ModifyThread")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.WARNING)

    def run(self):
        self.log.debug("Old source: %s" % self.old_source)
        self.log.debug("New source: %s" % self.new_source)
        
        try:
            remote_object.ModifyPPA(self.old_source, self.new_source)
        except:
            self.exc = sys.exc_info()
            self.throw_error(self.exc[1])
        
        self.sp.reload_sourceslist()
        isv_list = self.sp.get_isv_sources()
        GObject.idle_add(self.parent.parent.parent.stack.list_all.generate_entries, isv_list)
        GObject.idle_add(self.parent.parent.parent.stack.list_all.view.set_sensitive, True)
        GObject.idle_add(self.parent.parent.parent.hbar.spinner.stop)

    def throw_error(self, message):
        GObject.idle_add(self.parent.parent.parent.stack.list_all.throw_error_dialog,
                         message, "error")

# This method need to be improved
class PPA:
    waiting = "Waiting for PPA"
    invalid = "Not a valid PPA"
    valid = "Valid PPA found"
    sources_path = "/etc/apt/sources.list.d/"
    cache = apt.Cache()
    sp = SoftwareProperties()

    def __init__(self, parent=None):
        self.parent = parent

        self.log = logging.getLogger("repoman.Updates")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.WARNING)

    # Returns a list of all 3rd-party software sources.
    def get_isv(self):
        self.sp.reload_sourceslist()
        list = self.sp.get_isv_sources()
        return list

    # Returns the current distro Components.
    def get_distro_sources(self):
        components = self.sp.distro.source_template.components
        return components

    # Returns the current child repos (updates)
    def get_distro_child_repos(self):
        repos = self.sp.distro.source_template.children
        return repos

    # Get whether a component is enabled or not
    def get_comp_download_state(self, comp):
        (active, inconsistent) = self.sp.get_comp_download_state(comp)
        return (active, inconsistent)

    # Get whether a child repo is enabled or not
    def get_child_download_state(self, child):
        (active, inconsistent) = self.sp.get_comp_child_state(child)
        self.log.debug(child.name + " (" + str(active) + ", " + str(inconsistent) + ")")
        return (active, inconsistent)

    # Get Source Code State
    def get_source_code_enabled(self):
        enabled = self.sp.get_source_code_state()
        if enabled == None:
            return(False, True)
        else:
            return (enabled, False)

    # Enable/Disable a component
    def set_comp_enabled(self, comp, enabled):
        self.log.info('Component: %s\nEnabled: %s' % (comp, enabled))
        try:
            remote_object.SetCompEnabled(comp, enabled)
        except:
            self.exc = sys.exc_info()
            self.throw_error(self.exc[1])
        return 0

    # Enable/Disable a child repo
    def set_child_enabled(self, child, enabled):
        self.log.info('Child: %s\nEnabled: %s' % (child, enabled))
        try:
            remote_object.SetChildEnabled(child.name, enabled)
        except:
            self.exc = sys.exc_info()
            self.throw_error(self.exc[1])
        return 0

    # Enable/Disable source code
    def set_source_code_enabled(self, enabled):
        self.log.info('Source enabled: %s' % enabled)
        try:
            remote_object.SetSourceCodeEnabled(enabled)
        except:
            self.exc = sys.exc_info()
            self.throw_error(self.exc[1])
        return 0

    def get_line(self, isdisabled, rtype, archs, uri, version, component):
        """Collect all values from the entries and create an apt line"""
        if isdisabled == True:
            disstr = "#"
        else:
            disstr = ""

        if archs == "[arch]":
            archs = ""

        line = "%s%s %s %s %s %s" % (disstr,
                                     rtype,
                                     archs,
                                     uri,
                                     version,
                                     component)
        return line

    # Turn an added deb line into an apt source
    def deb_line_to_source(self, line):
        self.log.info(line)
        source = self.sp._find_source_from_string(line)
        return source

    # Modify an existing PPA
    def modify_ppa(self, old_source, disabled, rtype, archs, uri, version, component):
        self.log.info("Old source: %s" % old_source)
        line = self.get_line(disabled, rtype, archs, uri, version, component)
        self.log.info("New source: %s" % line)
        self.parent.parent.parent.hbar.spinner.start()
        self.parent.parent.parent.stack.list_all.view.set_sensitive(False)
        ModifyThread(self.parent, old_source, line, self.sp).start()


    # Starts a new thread to add a repository
    def add(self, url):
        self.log.info("Adding source: %s" % url)
        print(type(url))
        self.parent.parent.parent.hbar.spinner.start()
        self.parent.parent.parent.stack.list_all.view.set_sensitive(False)
        t = AddThread(self.parent, url, self.sp)
        t.start()

    # Starts a new thread to remove a repository
    def remove(self, ppa):
        self.log.info("Removing source: %s" % ppa)
        self.parent.parent.hbar.spinner.start()
        self.parent.parent.stack.list_all.view.set_sensitive(False)
        RemoveThread(self.parent, self.sources_path, ppa, self.sp).start()

    # Validate if a line appears to be a valid apt line or ppa.
    def validate(self, line):

        if line.startswith("deb"):
            if "http" in line:
                return True

        elif line.startswith("ppa:"):
            if "/" in line:
                return True

        elif line.startswith("http"):
            if "://" in line:
                return True

        else:
            return False

    # Get the current OS name, or fallback if not available
    def get_os_name(self):
        try:
            with open("/etc/os-release") as os_release_file:
                os_release = os_release_file.readlines()
                for line in os_release:
                    parse = line.split('=')
                    if parse[0] == "NAME":
                        if parse[1].startswith('"'):
                            return parse[1][1:-2]
                        else:
                            return parse[1][:-1]
                    else:
                        continue
        except FileNotFoundError:
            return "your OS"

        return "your OS"

    def throw_error(self, message):
        GObject.idle_add(self.parent.parent.parent.stack.list_all.throw_error_dialog,
                         message, "error")

