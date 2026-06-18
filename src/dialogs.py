import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import uuid
from datetime import datetime
from storage import load_reminders, save_reminders


class AddDialog(Gtk.Dialog):
    def __init__(self):
        super().__init__(title="Add Reminder")
        self.set_border_width(12)
        self.set_resizable(False)
        self.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Add",    Gtk.ResponseType.OK,
        )
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        box  = self.get_content_area()
        grid = Gtk.Grid(row_spacing=8, column_spacing=10)
        grid.set_margin_top(6)
        box.add(grid)

        def lbl(text, row):
            w = Gtk.Label(label=text, xalign=1)
            w.get_style_context().add_class("dim-label")
            grid.attach(w, 0, row, 1, 1)

        lbl("Title", 0)
        self._title = Gtk.Entry()
        self._title.set_placeholder_text("Reminder title")
        self._title.set_activates_default(True)
        self._title.set_hexpand(True)
        grid.attach(self._title, 1, 0, 2, 1)

        lbl("Message", 1)
        self._msg = Gtk.Entry()
        self._msg.set_placeholder_text("Optional details")
        self._msg.set_hexpand(True)
        grid.attach(self._msg, 1, 1, 2, 1)

        lbl("Date", 2)
        now = datetime.now()
        self._cal = Gtk.Calendar()
        self._cal.select_month(now.month - 1, now.year)
        self._cal.select_day(now.day)
        grid.attach(self._cal, 1, 2, 2, 1)

        lbl("Time", 3)
        time_box = Gtk.Box(spacing=4)

        self._hour = Gtk.SpinButton.new_with_range(0, 23, 1)
        self._hour.set_value(now.hour)
        self._hour.set_wrap(True)
        self._hour.set_width_chars(2)
        time_box.pack_start(self._hour, False, False, 0)
        time_box.pack_start(Gtk.Label(label=":"), False, False, 0)

        self._minute = Gtk.SpinButton.new_with_range(0, 59, 1)
        self._minute.set_value((now.minute + 5) % 60)
        self._minute.set_wrap(True)
        self._minute.set_width_chars(2)
        time_box.pack_start(self._minute, False, False, 0)
        grid.attach(time_box, 1, 3, 1, 1)

        lbl("Repeat", 4)
        self._repeat = Gtk.ComboBoxText()
        for opt in ("None", "Daily", "Weekly", "Monthly"):
            self._repeat.append_text(opt)
        self._repeat.set_active(0)
        grid.attach(self._repeat, 1, 4, 1, 1)

        self.show_all()
        self._title.grab_focus()

    def build_reminder(self):
        year, month, day = self._cal.get_date()
        dt = datetime(
            year, month + 1, day,
            int(self._hour.get_value()),
            int(self._minute.get_value()),
        )
        repeat_map = {0: "none", 1: "daily", 2: "weekly", 3: "monthly"}
        return {
            "id":       str(uuid.uuid4()),
            "title":    self._title.get_text().strip(),
            "message":  self._msg.get_text().strip(),
            "datetime": dt.isoformat(),
            "repeat":   repeat_map[self._repeat.get_active()],
            "enabled":  True,
        }


class ManageDialog(Gtk.Dialog):
    def __init__(self, reminders):
        super().__init__(title="Manage Reminders")
        self.add_buttons("_Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(560, 340)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self._reminders = reminders

        box = self.get_content_area()
        box.set_spacing(8)
        box.set_border_width(10)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_shadow_type(Gtk.ShadowType.IN)

        self._store = Gtk.ListStore(str, str, str, str, bool)
        self._fill_store()

        self._tree = Gtk.TreeView(model=self._store)

        for col_idx, header in [(1, "Title"), (2, "Date & Time"), (3, "Repeat")]:
            r = Gtk.CellRendererText(ellipsize=3)
            col = Gtk.TreeViewColumn(header, r, text=col_idx)
            col.set_resizable(True)
            col.set_min_width(120)
            self._tree.append_column(col)

        toggle_r = Gtk.CellRendererToggle()
        toggle_r.connect("toggled", self._on_toggle)
        self._tree.append_column(Gtk.TreeViewColumn("Enabled", toggle_r, active=4))

        scroll.add(self._tree)
        box.pack_start(scroll, True, True, 0)

        btn_bar = Gtk.Box(spacing=8)
        del_btn = Gtk.Button(label="Delete Selected")
        del_btn.connect("clicked", self._delete_selected)
        btn_bar.pack_end(del_btn, False, False, 0)
        box.pack_start(btn_bar, False, False, 0)

        self.show_all()

    def _fill_store(self):
        self._store.clear()
        for r in sorted(self._reminders, key=lambda x: x["datetime"]):
            dt = datetime.fromisoformat(r["datetime"])
            self._store.append([
                r["id"],
                r["title"],
                dt.strftime("%b %d, %Y  %H:%M"),
                r.get("repeat", "none").capitalize(),
                r.get("enabled", True),
            ])

    def _on_toggle(self, _w, path):
        self._store[path][4] = not self._store[path][4]
        rid = self._store[path][0]
        for r in self._reminders:
            if r["id"] == rid:
                r["enabled"] = self._store[path][4]
                break
        save_reminders(self._reminders)

    def _delete_selected(self, _w):
        model, it = self._tree.get_selection().get_selected()
        if not it:
            return
        rid = model[it][0]
        self._reminders = [r for r in self._reminders if r["id"] != rid]
        save_reminders(self._reminders)
        self._fill_store()
