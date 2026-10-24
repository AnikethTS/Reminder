import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from datetime import datetime

from scheduler import describe_when, due_state, parse_datetime, repeat_label
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
.soon-badge {
    background-color: #e5a50a;
    color: #1c1c1c;
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

        self._header = Gtk.HeaderBar()
        self._header.set_show_close_button(True)
        self._header.set_title("Remainders")
        self.set_titlebar(self._header)

        add_btn = Gtk.Button()
        add_btn.set_image(
            Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        )
        add_btn.set_tooltip_text("Add reminder (Ctrl+N)")
        add_btn.connect("clicked", lambda _: self._app.open_add_dialog())
        self._header.pack_end(add_btn)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Search reminders")
        self._search.set_margin_start(10)
        self._search.set_margin_end(10)
        self._search.set_margin_top(10)
        self._search.set_margin_bottom(4)
        self._search.connect("search-changed", lambda entry: self.refresh())
        content.pack_start(self._search, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.connect("row-activated", self._on_row_activated)

        scroll.add(self._listbox)
        content.pack_start(scroll, True, True, 0)
        self.add(content)
        self.connect("key-press-event", self._on_key)

        self.refresh()

    def show_and_focus(self):
        self.show_all()
        self.present()

    def refresh(self):
        for child in self._listbox.get_children():
            self._listbox.remove(child)

        reminders = load_reminders()
        now = datetime.now()
        query = self._search.get_text().strip().casefold()
        visible = [r for r in reminders if self._matches(r, query)]
        visible.sort(key=self._sort_key)

        overdue = sum(1 for r in reminders if due_state(r, now) == "overdue")
        subtitle = f"{len(reminders)} reminder" if len(reminders) == 1 else f"{len(reminders)} reminders"
        if overdue:
            subtitle += f" · {overdue} overdue"
        self._header.set_subtitle(subtitle)

        if not reminders:
            self._listbox.add(self._empty_state_row(
                "No reminders yet",
                "Click + to add your first reminder",
            ))
        elif not visible:
            self._listbox.add(self._empty_state_row(
                "No matching reminders",
                "Try a different search",
            ))
        else:
            for reminder in visible:
                self._listbox.add(self._make_row(reminder, now))

        self._listbox.show_all()

    def _matches(self, reminder, query):
        if not query:
            return True
        haystack = f"{reminder.get('title', '')}\n{reminder.get('message', '')}".casefold()
        return query in haystack

    def _sort_key(self, reminder):
        when = parse_datetime(reminder.get("datetime"))
        return (when is None, when or datetime.max)

    def _empty_state_row(self, title, subtitle):
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

        title_lbl = Gtk.Label()
        title_lbl.set_markup(
            f"<span weight='bold' size='large'>{GLib.markup_escape_text(title)}</span>"
        )
        box.pack_start(title_lbl, False, False, 0)

        sub = Gtk.Label(label=subtitle)
        sub.get_style_context().add_class("dim-label")
        box.pack_start(sub, False, False, 0)

        row.add(box)
        return row

    def _make_row(self, reminder, now):
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
            f"<span weight='bold'>{GLib.markup_escape_text(reminder.get('title') or '')}</span>"
        )
        title_lbl.set_ellipsize(3)
        title_box.pack_start(title_lbl, False, False, 0)

        state = due_state(reminder, now)
        if state == "overdue":
            self._badge(title_box, "overdue", "overdue-badge")
        elif state == "soon":
            self._badge(title_box, "soon", "soon-badge")

        text.pack_start(title_box, False, False, 0)

        when = parse_datetime(reminder.get("datetime"))
        if when is None:
            detail = "Invalid date"
        else:
            detail = f"{describe_when(when, now)}  ·  {when.strftime('%b %d, %Y  %H:%M')}"
            repeat = reminder.get("repeat", "none")
            if repeat != "none":
                detail += f"  ·  {repeat_label(repeat)}"
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
            lambda _b, rid=reminder["id"], title=reminder.get("title", ""): self._confirm_delete(rid, title),
        )
        outer.pack_start(del_btn, False, False, 0)

        row.add(outer)
        return row

    def _badge(self, box, label, css_class):
        badge = Gtk.Label(label=label)
        badge.get_style_context().add_class(css_class)
        box.pack_start(badge, False, False, 0)

    def _confirm_delete(self, reminder_id, title):
        name = title.strip() or "This reminder"
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            message_format="Delete this reminder?",
        )
        dialog.format_secondary_text(f"“{name}” will be removed.")
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        delete_btn = dialog.add_button("_Delete", Gtk.ResponseType.OK)
        delete_btn.get_style_context().add_class("destructive-action")
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self._app.delete_reminder(reminder_id)

    def _on_key(self, _window, event):
        if not (event.state & Gdk.ModifierType.CONTROL_MASK):
            return False
        if event.keyval in (Gdk.KEY_n, Gdk.KEY_N):
            self._app.open_add_dialog()
            return True
        if event.keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self._search.grab_focus()
            return True
        return False

    def _on_row_activated(self, _listbox, row):
        if hasattr(row, "_reminder_id"):
            self._app.open_edit_dialog(row._reminder_id)

    def _on_close(self, *_):
        self.hide()
        return True
