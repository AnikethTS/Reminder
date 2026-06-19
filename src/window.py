import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from datetime import datetime
from storage import load_reminders


CSS = b"""
window {
    background-color: @theme_bg_color;
}
.reminder-row {
    padding: 4px 0;
    border-bottom: 1px solid alpha(@borders, 0.4);
}
.reminder-row:last-child {
    border-bottom: none;
}
.reminder-title {
    font-size: 1.0em;
    font-weight: bold;
}
.reminder-detail {
    font-size: 0.85em;
}
.overdue-badge {
    background-color: #e01b24;
    color: white;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.75em;
}
.empty-state-title {
    font-size: 1.15em;
    font-weight: bold;
}
"""


class MainWindow(Gtk.Window):
    """Main GUI window — hides on close so the tray app keeps running."""

    def __init__(self, app):
        super().__init__(title="Remainders")
        self._app = app

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.set_default_size(440, 540)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        self.connect("delete-event", self._on_close)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Remainders")
        self.set_titlebar(header)

        add_btn = Gtk.Button()
        add_btn.set_image(
            Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        )
        add_btn.set_tooltip_text("Add reminder")
        add_btn.connect("clicked", lambda _: self._app.open_add_dialog())
        header.pack_end(add_btn)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.connect("row-activated", self._on_row_activated)

        scroll.add(self._listbox)
        self.add(scroll)

        self.refresh()

    def show_and_focus(self):
        self.show_all()
        self.present()

    def refresh(self):
        for child in self._listbox.get_children():
            self._listbox.remove(child)

        reminders = load_reminders()
        now = datetime.now()

        if not reminders:
            self._listbox.add(self._empty_state_row())
        else:
            for r in sorted(reminders, key=lambda x: x["datetime"]):
                is_overdue = (
                    r.get("enabled", True)
                    and datetime.fromisoformat(r["datetime"]) < now
                    and r.get("repeat", "none") == "none"
                )
                self._listbox.add(self._make_row(r, is_overdue))

        self._listbox.show_all()

    def _empty_state_row(self):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_vexpand(True)
        box.set_margin_top(80)
        box.set_margin_bottom(80)

        icon = Gtk.Image.new_from_icon_name("alarm-symbolic", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        box.pack_start(icon, False, False, 0)

        title = Gtk.Label()
        title.set_markup("<span weight='bold' size='large'>No reminders yet</span>")
        box.pack_start(title, False, False, 0)

        sub = Gtk.Label(label="Click + to add your first reminder")
        sub.get_style_context().add_class("dim-label")
        box.pack_start(sub, False, False, 0)

        row.add(box)
        return row

    def _make_row(self, reminder, is_overdue=False):
        row = Gtk.ListBoxRow()
        row._reminder_id = reminder["id"]
        row.get_style_context().add_class("reminder-row")

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        outer.set_border_width(10)

        bell = Gtk.Image.new_from_icon_name("alarm-symbolic", Gtk.IconSize.MENU)
        bell.set_valign(Gtk.Align.CENTER)
        outer.pack_start(bell, False, False, 0)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)

        title_box = Gtk.Box(spacing=8)
        title_lbl = Gtk.Label(xalign=0)
        title_lbl.set_markup(
            f"<span weight='bold'>{GLib.markup_escape_text(reminder['title'])}</span>"
        )
        title_lbl.set_ellipsize(3)
        title_box.pack_start(title_lbl, False, False, 0)

        if is_overdue:
            badge = Gtk.Label(label="overdue")
            badge.get_style_context().add_class("overdue-badge")
            title_box.pack_start(badge, False, False, 0)

        text.pack_start(title_box, False, False, 0)

        dt     = datetime.fromisoformat(reminder["datetime"])
        repeat = reminder.get("repeat", "none")
        detail = dt.strftime("%b %d, %Y  %H:%M")
        if repeat != "none":
            detail += f"  ·  {repeat.capitalize()}"
        if reminder.get("message"):
            detail = reminder["message"] + "\n" + detail

        detail_lbl = Gtk.Label(label=detail, xalign=0)
        detail_lbl.get_style_context().add_class("dim-label")
        detail_lbl.set_line_wrap(True)
        text.pack_start(detail_lbl, False, False, 0)

        outer.pack_start(text, True, True, 0)

        switch = Gtk.Switch()
        switch.set_active(reminder.get("enabled", True))
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect(
            "notify::active",
            lambda s, _p, rid=reminder["id"]: self._app.toggle_reminder(rid, s.get_active()),
        )
        outer.pack_start(switch, False, False, 0)

        del_btn = Gtk.Button()
        del_btn.set_image(
            Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.MENU)
        )
        del_btn.get_style_context().add_class("flat")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.set_tooltip_text("Delete")
        del_btn.connect(
            "clicked",
            lambda _b, rid=reminder["id"]: self._app.delete_reminder(rid),
        )
        outer.pack_start(del_btn, False, False, 0)

        row.add(outer)
        return row

    def _on_row_activated(self, _listbox, row):
        if hasattr(row, "_reminder_id"):
            self._app.open_edit_dialog(row._reminder_id)

    def _on_close(self, *_):
        self.hide()
        return True
