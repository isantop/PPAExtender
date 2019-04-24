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

import gi
import logging
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .dialog import FpAddDialog, FpDeleteDialog

try:
    import pyflatpak as Flatpak
except ImportError:
    pass
import gettext
gettext.bindtextdomain('repoman', '/usr/share/repoman/po')
gettext.textdomain("repoman")
_ = gettext.gettext

class FlatpakList(Gtk.Box):

    listiter_count = Gtk.TreeIter()

    def __init__(self, parent):
        Gtk.Box.__init__(self, False, 0)
        self.parent = parent

        self.settings = Gtk.Settings()

        self.log = logging.getLogger("repoman.List")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.WARNING)

        self.content_grid = Gtk.Grid()
        self.content_grid.set_margin_top(24)
        self.content_grid.set_margin_left(12)
        self.content_grid.set_margin_right(12)
        self.content_grid.set_margin_bottom(12)
        self.content_grid.set_row_spacing(6)
        self.content_grid.set_hexpand(True)
        self.content_grid.set_vexpand(True)
        self.add(self.content_grid)

        sources_title = Gtk.Label(_("Flatpak Sources"))
        Gtk.StyleContext.add_class(sources_title.get_style_context(), "h2")
        sources_title.set_halign(Gtk.Align.START)
        self.content_grid.attach(sources_title, 0, 0, 1, 1)

        sources_label = Gtk.Label(_("These sources are for software installed as Flatpak apps"))
        sources_label.set_line_wrap(True)
        sources_label.set_halign(Gtk.Align.START)
        sources_label.set_justify(Gtk.Justification.FILL)
        sources_label.set_hexpand(True)
        self.content_grid.attach(sources_label, 0, 1, 1, 1)

        list_grid = Gtk.Grid()
        self.content_grid.attach(list_grid, 0, 2, 1, 1)
        list_window = Gtk.ScrolledWindow()
        list_grid.attach(list_window, 0, 0, 1, 1)

        self.fp_liststore = Gtk.ListStore(str, str, str, str)
        self.view = Gtk.TreeView(self.fp_liststore)
        name_renderer = Gtk.CellRendererText()
        url_renderer = Gtk.CellRendererText()
        option_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn(_("Source"), name_renderer, markup=1)
        url_column = Gtk.TreeViewColumn(_("URL"), url_renderer, markup=2)
        option_column = Gtk.TreeViewColumn(_("Option"), option_renderer, markup=3)
        self.view.append_column(name_column)
        self.view.append_column(url_column)
        self.view.append_column(option_column)
        self.view.set_hexpand(True)
        self.view.set_vexpand(True)
        self.view.connect("row-activated", self.on_row_activated)
        tree_selection = self.view.get_selection()
        tree_selection.connect('changed', self.on_row_change)
        list_window.add(self.view)

        # add button
        add_button = Gtk.ToolButton()
        add_button.set_icon_name("list-add-symbolic")
        Gtk.StyleContext.add_class(add_button.get_style_context(),
                                   "image-button")
        add_button.set_tooltip_text(_("Add New Source"))
        add_button.connect("clicked", self.on_add_button_clicked)

        # Delete button
        delete_button = Gtk.ToolButton()
        delete_button.set_icon_name("edit-delete-symbolic")
        Gtk.StyleContext.add_class(delete_button.get_style_context(),
                                   "image-button")
        delete_button.set_tooltip_text(_("Delete Selected Source"))
        delete_button.connect("clicked", self.on_delete_button_clicked)

        action_bar = Gtk.Toolbar()
        action_bar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)
        Gtk.StyleContext.add_class(action_bar.get_style_context(),
                                   "inline-toolbar")
        action_bar.insert(delete_button, 0)
        action_bar.insert(add_button, 0)
        list_grid.attach(action_bar, 0, 1, 1, 1)

        self.generate_entries(Flatpak.remotes.get_remotes())
    
    def generate_entries(self, fp_remotes_dict):
        self.fp_liststore.clear()

        for remote in fp_remotes_dict:
            #row = self.fp_liststore.insert(-1)
            self.fp_liststore.append(
                [
                    fp_remotes_dict[remote]['name'],
                    fp_remotes_dict[remote]['title'],
                    fp_remotes_dict[remote]['url'],
                    fp_remotes_dict[remote]['option']
                ]
            )
    
    def on_row_activated(self, widget, data1, data2):
        tree_iter = self.fp_liststore.get_iter(data1)
        value = self.fp_liststore.get_value(tree_iter, 0)
        self.log.info('Remote to delete: %s' % value)
        self.do_delete(value)
    
    def on_row_change(self, widget):
        (model, pathlist) = widget.get_selected_rows()
        for path in pathlist :
            tree_iter = model.get_iter(path)
            value = model.get_value(tree_iter,1)
            self.ppa_name = value

    def on_add_button_clicked(self, widget):
        #self.ppa.remove(self.ppa_name)
        dialog = FpAddDialog(self.parent.parent)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            fp_name = dialog.fp_name_entry.get_text()
            fp_url = dialog.fp_entry.get_text()
            Flatpak.remotes.add_remote(fp_name, fp_url)
            dialog.destroy()
        else:
            dialog.destroy()
        self.generate_entries(Flatpak.remotes.get_remotes())
    
    def on_delete_button_clicked(self, widget):
        selec = self.view.get_selection()
        (model, pathlist) = selec.get_selected_rows()
        tree_iter = model.get_iter(pathlist[0])
        value = model.get_value(tree_iter, 0)
        self.log.info("Remote to Delete: %s" % value)
        self.do_delete(value)
        
    def do_delete(self, remote):
        dialog = FpDeleteDialog(self.parent.parent)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            Flatpak.remotes.delete_remote(remote)
            dialog.destroy()
        else:
            dialog.destroy()
        self.generate_entries(Flatpak.remotes.get_remotes())