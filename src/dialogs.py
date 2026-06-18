import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import uuid
from datetime import datetime
from storage import save_reminders
from config  import SNOOZE_OPTIONS, APP_NAME


# ── Add / Edit Dialog ──────────────────────────────────────────────────────────

class AddDialog(Gtk.Dialog):
    """Add a new reminder or edit an existing one (pass reminder= to pre-fill)."""

    def __init__(self, reminder=None):
        title = "Edit Reminder" if reminder else "Add Reminder"
        btn   = "_Save"        if reminder else "_Add"
        super().__init__(title=title)
        self.set_border_width(12)
        self.set_resizable(False)
        self.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, btn, Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        self._original_id = reminder["id"] if reminder else None

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

        # Pre-fill if editing
        if reminder:
            self._title.set_text(reminder.get("title", ""))
            self._msg.set_text(reminder.get("message", ""))
            dt = datetime.fromisoformat(reminder["datetime"])
            self._cal.select_month(dt.month - 1, dt.year)
            self._cal.select_day(dt.day)
            self._hour.set_value(dt.hour)
            self._minute.set_value(dt.minute)
            rev = {"none": 0, "daily": 1, "weekly": 2, "monthly": 3}
            self._repeat.set_active(rev.get(reminder.get("repeat", "none"), 0))

        self.show_all()
        self._title.grab_focus()

    def build_reminder(self):
        year, month, day = self._cal.get_date()
        dt = datetime(year, month + 1, day,
                      int(self._hour.get_value()), int(self._minute.get_value()))
        repeat_map = {0: "none", 1: "daily", 2: "weekly", 3: "monthly"}
        return {
            "id":       self._original_id or str(uuid.uuid4()),
            "title":    self._title.get_text().strip(),
            "message":  self._msg.get_text().strip(),
            "datetime": dt.isoformat(),
            "repeat":   repeat_map[self._repeat.get_active()],
            "enabled":  True,
        }


# ── Manage Reminders Dialog ────────────────────────────────────────────────────

class ManageDialog(Gtk.Dialog):
    def __init__(self, reminders):
        super().__init__(title="Manage Reminders")
        self.add_buttons("_Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(580, 360)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self._reminders = reminders
        self._edit_dlg  = None

        box = self.get_content_area()
        box.set_spacing(8)
        box.set_border_width(10)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_shadow_type(Gtk.ShadowType.IN)

        # columns: id, title, datetime_str, repeat, enabled
        self._store = Gtk.ListStore(str, str, str, str, bool)
        self._fill_store()

        self._tree = Gtk.TreeView(model=self._store)
        self._tree.connect("row-activated", self._on_row_activated)

        for col_idx, header in [(1, "Title"), (2, "Date & Time"), (3, "Repeat")]:
            r   = Gtk.CellRendererText(ellipsize=3)
            col = Gtk.TreeViewColumn(header, r, text=col_idx)
            col.set_resizable(True)
            col.set_min_width(120)
            self._tree.append_column(col)

        toggle_r = Gtk.CellRendererToggle()
        toggle_r.connect("toggled", self._on_toggle)
        self._tree.append_column(Gtk.TreeViewColumn("Enabled", toggle_r, active=4))

        scroll.add(self._tree)
        box.pack_start(scroll, True, True, 0)

        btn_bar  = Gtk.Box(spacing=8)
        edit_btn = Gtk.Button(label="Edit Selected")
        edit_btn.connect("clicked", lambda _: self._open_edit())
        del_btn  = Gtk.Button(label="Delete Selected")
        del_btn.connect("clicked", self._delete_selected)
        btn_bar.pack_end(del_btn,  False, False, 0)
        btn_bar.pack_end(edit_btn, False, False, 0)
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

    def _selected_reminder(self):
        model, it = self._tree.get_selection().get_selected()
        if not it:
            return None
        rid = model[it][0]
        return next((r for r in self._reminders if r["id"] == rid), None)

    def _on_row_activated(self, _tree, _path, _col):
        self._open_edit()

    def _open_edit(self):
        reminder = self._selected_reminder()
        if not reminder:
            return
        if self._edit_dlg:
            self._edit_dlg.present()
            return
        self._edit_dlg = AddDialog(reminder)
        self._edit_dlg.connect("response", self._on_edit_response, reminder["id"])
        self._edit_dlg.show()

    def _on_edit_response(self, dlg, response, original_id):
        if response == Gtk.ResponseType.OK:
            updated = dlg.build_reminder()
            if updated["title"]:
                updated["id"] = original_id
                self._reminders = [
                    updated if r["id"] == original_id else r
                    for r in self._reminders
                ]
                save_reminders(self._reminders)
                self._fill_store()
        dlg.destroy()
        self._edit_dlg = None

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


# ── Reminder Fired Popup ───────────────────────────────────────────────────────

class ReminderPopup(Gtk.Window):
    """Non-blocking popup shown when a reminder fires, with snooze options."""

    AUTO_CLOSE_SECONDS = 120

    def __init__(self, reminder, on_snooze, on_close):
        super().__init__(title=APP_NAME)
        self._on_snooze = on_snooze
        self._on_close  = on_close

        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(16)
        self.set_resizable(False)
        self.set_decorated(True)
        self.connect("delete-event", self._close)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(outer)

        # Title
        title_lbl = Gtk.Label()
        title_lbl.set_markup(
            f"<span size='large' weight='bold'>"
            f"{GLib.markup_escape_text(reminder['title'])}"
            f"</span>"
        )
        title_lbl.set_line_wrap(True)
        title_lbl.set_xalign(0)
        outer.pack_start(title_lbl, False, False, 0)

        # Message
        if reminder.get("message"):
            msg_lbl = Gtk.Label(label=reminder["message"])
            msg_lbl.set_line_wrap(True)
            msg_lbl.set_xalign(0)
            msg_lbl.get_style_context().add_class("dim-label")
            outer.pack_start(msg_lbl, False, False, 0)

        outer.pack_start(Gtk.Separator(), False, False, 0)

        # Snooze buttons
        snooze_lbl = Gtk.Label(label="Snooze for:", xalign=0)
        snooze_lbl.get_style_context().add_class("dim-label")
        outer.pack_start(snooze_lbl, False, False, 0)

        snooze_row = Gtk.Box(spacing=6)
        for minutes, label in SNOOZE_OPTIONS:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", lambda _, m=minutes: self._snooze(m))
            snooze_row.pack_start(btn, True, True, 0)
        outer.pack_start(snooze_row, False, False, 0)

        # Dismiss
        dismiss = Gtk.Button(label="Dismiss")
        dismiss.connect("clicked", lambda _: self._close())
        outer.pack_start(dismiss, False, False, 0)

        # Auto-close timer
        self._timer = GLib.timeout_add_seconds(self.AUTO_CLOSE_SECONDS, self._auto_close)

        self.show_all()

    def _snooze(self, minutes):
        GLib.source_remove(self._timer)
        self._on_snooze(minutes)
        self._on_close()
        self.destroy()

    def _close(self, *_):
        GLib.source_remove(self._timer)
        self._on_close()
        self.destroy()
        return False  # let window-manager close proceed

    def _auto_close(self):
        self._on_close()
        self.destroy()
        return False
