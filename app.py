import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, Gdk, GLib, Notify
from gi.repository import AyatanaAppIndicator3 as AppIndicator3

import traceback
from datetime import datetime, timedelta

from config  import APP_NAME, CHECK_INTERVAL_SECONDS, DATA_DIR, ICON_DIR
from storage import load_reminders, save_reminders
from icon    import create_tray_icon
from sound   import play_sound
from dialogs import AddDialog, ManageDialog


class RemindersApp:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        Notify.init(APP_NAME)
        create_tray_icon()

        self.indicator = AppIndicator3.Indicator.new_with_path(
            "remainders",
            "remainders",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            str(ICON_DIR),
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title(APP_NAME)

        self._menu = Gtk.Menu()
        self._rebuild_menu()
        self.indicator.set_menu(self._menu)

        GLib.idle_add(self._check_reminders)
        GLib.timeout_add_seconds(CHECK_INTERVAL_SECONDS, self._check_reminders)

    def _rebuild_menu(self):
        for child in self._menu.get_children():
            self._menu.remove(child)

        header = Gtk.MenuItem(label=APP_NAME)
        header.set_sensitive(False)
        self._menu.append(header)
        self._menu.append(Gtk.SeparatorMenuItem())

        upcoming = self._upcoming(limit=5)
        if upcoming:
            for r in upcoming:
                dt  = datetime.fromisoformat(r["datetime"])
                lbl = f"  {r['title']}  ·  {dt.strftime('%b %d, %H:%M')}"
                item = Gtk.MenuItem(label=lbl)
                item.set_sensitive(False)
                self._menu.append(item)
        else:
            empty = Gtk.MenuItem(label="  No upcoming reminders")
            empty.set_sensitive(False)
            self._menu.append(empty)

        self._menu.append(Gtk.SeparatorMenuItem())

        add_item = Gtk.MenuItem(label="Add Reminder…")
        add_item.connect("activate", lambda _: GLib.timeout_add(150, self._show_add))
        self._menu.append(add_item)

        manage_item = Gtk.MenuItem(label="Manage Reminders…")
        manage_item.connect("activate", lambda _: GLib.timeout_add(150, self._show_manage))
        self._menu.append(manage_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self._quit())
        self._menu.append(quit_item)

        self._menu.show_all()


    def _upcoming(self, limit=None):
        now  = datetime.now()
        rows = [
            r for r in load_reminders()
            if r.get("enabled", True) and datetime.fromisoformat(r["datetime"]) > now
        ]
        rows.sort(key=lambda r: r["datetime"])
        return rows[:limit] if limit else rows

    def _check_reminders(self):
        now       = datetime.now()
        reminders = load_reminders()
        changed   = False

        for r in reminders:
            if not r.get("enabled", True):
                continue
            dt = datetime.fromisoformat(r["datetime"])
            if dt <= now and (now - dt).total_seconds() < CHECK_INTERVAL_SECONDS + 5:
                self._fire(r)
                repeat = r.get("repeat", "none")
                if repeat == "none":
                    r["enabled"] = False
                elif repeat == "daily":
                    r["datetime"] = (dt + timedelta(days=1)).isoformat()
                elif repeat == "weekly":
                    r["datetime"] = (dt + timedelta(weeks=1)).isoformat()
                elif repeat == "monthly":
                    month = dt.month % 12 + 1
                    year  = dt.year + (1 if dt.month == 12 else 0)
                    r["datetime"] = dt.replace(year=year, month=month).isoformat()
                changed = True

        if changed:
            save_reminders(reminders)
            self._rebuild_menu()

        return True  

    def _fire(self, reminder):
        play_sound()

        notif = Notify.Notification.new(
            reminder["title"],
            reminder.get("message", ""),
            "appointment-soon",
        )
        notif.set_urgency(Notify.Urgency.NORMAL)

        rid = reminder["id"]
        notif.add_action("snooze-5", "Snooze 5 min", self._on_snooze, rid)
        notif.add_action("dismiss",  "Dismiss",       lambda *_: None,  None)

        try:
            notif.show()
        except Exception as e:
            print(f"[Remainders] notification error: {e}")

    def _on_snooze(self, _notif, _action, reminder_id):
        reminders = load_reminders()
        for r in reminders:
            if r["id"] == reminder_id:
                r["datetime"] = (datetime.now() + timedelta(minutes=5)).isoformat()
                r["enabled"]  = True
                break
        save_reminders(reminders)
        GLib.idle_add(self._rebuild_menu)

    def _show_add(self):
        try:
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME)
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)
            dlg      = AddDialog()
            response = dlg.run()
            if response == Gtk.ResponseType.OK:
                reminder = dlg.build_reminder()
                if reminder["title"]:
                    reminders = load_reminders()
                    reminders.append(reminder)
                    save_reminders(reminders)
                    self._rebuild_menu()
            dlg.destroy()
        except Exception:
            traceback.print_exc()
        return False

    def _show_manage(self):
        try:
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME)
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)
            dlg = ManageDialog(load_reminders())
            dlg.run()
            dlg.destroy()
            self._rebuild_menu()
        except Exception:
            traceback.print_exc()
        return False

    def _quit(self):
        Notify.uninit()
        Gtk.main_quit()

    def run(self):
        Gtk.main()
