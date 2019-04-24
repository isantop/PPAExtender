#!/usr/bin/python3
'''
   Copyright 2019 Ian Santopietro (ian@system76.com)

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
import gi
from gi.repository import GObject
import dbus
import dbus.service
import dbus.mainloop.glib

import apt
from aptsources.sourceslist import SourceEntry
import time

from softwareproperties.SoftwareProperties import SoftwareProperties

class RepomanException(dbus.DBusException):
    _dbus_error_name = 'ro.santopiet.repoman.RepomanException'

class PermissionDeniedByPolicy(dbus.DBusException):
    _dbus_error_name = 'ro.santopiet.repoman.PermissionDeniedByPolicy'

class AptException(Exception):
    pass

class PPAObject(dbus.service.Object):
    cache = apt.Cache()

    def __init__(self, conn=None, object_path=None, bus_name=None):
        dbus.service.Object.__init__(self, conn, object_path, bus_name)

        # The following variables are used bu _check_polkit_privilege
        self.dbus_info = None
        self.polkit = None
        self.enforce_polkit = True
        self.sp = SoftwareProperties()
    
    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='s', out_signature='i',
        sender_keyword='sender', connection_keyword='conn'
    )
    def DelPPA(self, ppa, sender=None, conn=None):
        self._check_polkit_privilege(
            sender, conn, 'ro.santopiet.repoman.delppa'
        )
        # PPA Remove code here
        try:
            self.sp.reload_sourceslist()
            self.sp.remove_source(ppa, remove_source_code=True)
            self.sp.sourceslist.save()
            self.sp.reload_sourceslist()
            return 0
        except:
            raise AptException("Could not remove the APT Source")
    
    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='s', out_signature='i',
        sender_keyword='sender', connection_keyword='conn'
    )
    def AddPPA(self, ppa, sender=None, conn=None):
        self._check_polkit_privilege(
            sender, conn, 'ro.santopiet.repoman.addppa'
        )
        # PPA Add code here
        try:
            self.sp.reload_sourceslist()
            self.sp.add_source_from_line(ppa)
            self.sp.sourceslist.save()
            self.sp.reload_sourceslist()
            return 0
        except:
            raise AptException("Could not remove the APT Source")
    
    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='ss', out_signature='i',
        sender_keyword='sender', connection_keyword='conn'
    )
    def ModifyPPA(self, old_source, new_source, sender=None, conn=None):
        self._check_polkit_privilege(
            sender, conn, 'ro.santopiet.repoman.modppa'
        )
        # PPA Modify code here
        try:
            self.sp.reload_sourceslist()
            old_source = self._strip_source_line(old_source)
            isvs = self.sp.get_isv_sources()
            for i in isvs:
                if str(i) == old_source:
                    source = i
            index = self.sp.sourceslist.list.index(source)
            file = self.sp.sourceslist.list[index].file
            new_source_entry = SourceEntry(new_source,file)
            self.sp.sourceslist.list[index] = new_source_entry
            self.sp.sourceslist.save()
            self.cache.open()
            self.cache.update()
            self.cache.open(None)
            self.cache.close()
            self.sp.reload_sourceslist()
            return 0
        except:
            raise AptException("Could not modify the APT Source")
    
    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='sb', out_signature='i',
        sender_keyword='sender', connection_keyword='conn'
    )
    def SetCompEnabled(self, comp_name, is_enabled, sender=None, conn=None):
        self._check_polkit_privilege(
            sender, conn, 'ro.santopiet.repoman.modppa'
        )
        # PPA Modify code here
        if is_enabled:
            self.sp.enable_component(comp_name)
        else: 
            self.sp.disable_component(comp_name)
        return 0

    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='sb', out_signature='i',
        sender_keyword='sender', connection_keyword='conn'
    )
    def SetChildEnabled(self, child_name, is_enabled, sender=None, conn=None):
        self._check_polkit_privilege(
            sender, conn, 'ro.santopiet.repoman.modppa'
        )
        # PPA Modify code here
        repos = self.sp.distro.source_template.children
        for repo in repos:
            if repo.name == child_name:
                child = repo
        if is_enabled:
            self.sp.enable_child_source(child)
        else: 
            self.sp.disable_child_source(child)
        return 0
    
    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='b', out_signature='i',
        sender_keyword='sender', connection_keyword='conn'
    )
    def SetSourceCodeEnabled(self, is_enabled, sender=None, conn=None):
        self._check_polkit_privilege(
            sender, conn, 'ro.santopiet.repoman.modppa'
        )
        # PPA Modify code here
        if is_enabled:
            self.sp.enable_source_code_sources()
        else: 
            self.sp.disable_source_code_sources()
        return 0

    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='', out_signature='',
        sender_keyword='sender', connection_keyword='conn'
    )
    def RaiseException(self, sender=None, conn=None):
        raise RepomanException('Error managing software sources!')
    
    @dbus.service.method(
        "ro.santopiet.repoman.Interface",
        in_signature='', out_signature='',
        sender_keyword='sender', connection_keyword='conn'
    )
    def Exit(self, sender=None, conn=None):
        mainloop.quit()
    
    @classmethod
    def _log_in_file(klass, filename, string):
        date = time.asctime(time.localtime())
        ff = open(filename, "a")
        ff.write("%s : %s\n" %(date,str(string)))
        ff.close()
    
    @classmethod
    def _strip_source_line(self, source):
        source = source.replace("#", "# ")
        source = source.replace("[", "")
        source = source.replace("]", "")
        source = source.replace("'", "")
        source = source.replace("  ", " ")
        return source

    def _check_polkit_privilege(self, sender, conn, privilege):
        # from jockey
        '''Verify that sender has a given PolicyKit privilege.

        sender is the sender's (private) D-BUS name, such as ":1:42"
        (sender_keyword in @dbus.service.methods). conn is
        the dbus.Connection object (connection_keyword in
        @dbus.service.methods). privilege is the PolicyKit privilege string.

        This method returns if the caller is privileged, and otherwise throws a
        PermissionDeniedByPolicy exception.
        '''
        if sender is None and conn is None:
            # called locally, not through D-BUS
            return
        if not self.enforce_polkit:
            # that happens for testing purposes when running on the session
            # bus, and it does not make sense to restrict operations here
            return

        # get peer PID
        if self.dbus_info is None:
            self.dbus_info = dbus.Interface(conn.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus/Bus', False), 'org.freedesktop.DBus')
        pid = self.dbus_info.GetConnectionUnixProcessID(sender)
        
        # query PolicyKit
        if self.polkit is None:
            self.polkit = dbus.Interface(dbus.SystemBus().get_object(
                'org.freedesktop.PolicyKit1',
                '/org/freedesktop/PolicyKit1/Authority', False),
                'org.freedesktop.PolicyKit1.Authority')
        try:
            # we don't need is_challenge return here, since we call with AllowUserInteraction
            (is_auth, _, details) = self.polkit.CheckAuthorization(
                    ('unix-process', {'pid': dbus.UInt32(pid, variant_level=1),
                    'start-time': dbus.UInt64(0, variant_level=1)}), 
                    privilege, {'': ''}, dbus.UInt32(1), '', timeout=600)
        except dbus.DBusException as e:
            if e._dbus_error_name == 'org.freedesktop.DBus.Error.ServiceUnknown':
                # polkitd timed out, connect again
                self.polkit = None
                return self._check_polkit_privilege(sender, conn, privilege)
            else:
                raise

        if not is_auth:
            PPAObject._log_in_file('/tmp/repoman.log','_check_polkit_privilege: sender %s on connection %s pid %i is not authorized for %s: %s' %
                    (sender, conn, pid, privilege, str(details)))
            raise PermissionDeniedByPolicy(privilege)


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    bus = dbus.SystemBus()
    name = dbus.service.BusName("ro.santopiet.repoman", bus)
    object = PPAObject(bus, '/PPAObject')

    mainloop = GObject.MainLoop()
    mainloop.run()