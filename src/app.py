import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, Gdk, GLib, Notify
from gi.repository import AyatanaAppIndicator3 as AppIndicator3

import fcntl
import os
import sys
import traceback
from datetime import datetime, timedelta

from config  import (APP_NAME, CHECK_INTERVAL_SECONDS, MISSED_WINDOW_HOURS,
                     DATA_DIR, ICON_DIR, LOCK_FILE)
from storage import load_reminders, save_reminders
from icon    import create_tray_icon, create_attention_icon
from sound   import play_sound
from dialogs import AddDialog, ManageDialog, ReminderPopup


class RemindersApp:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not self._acquire_lock():
            Notify.init(APP_NAME)
            Notify.Notification.new(APP_NAME, "Already running.", "dialog-information").show()
            sys.exit(0)

        Notify.init(APP_NAME)
        create_tray_icon()
        create_attention_icon()

        self.indicator = AppIndicator3.Indicator.new_with_path(
            "remainders",
            "remainders",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            str(ICON_DIR),
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_attention_icon_full("remainders-attention", "Reminder due")
        self.indicator.set_title(APP_NAME)

        self._menu        = Gtk.Menu()
        self._add_dlg     = None   # guard against duplicate dialogs
        self._manage_dlg  = None
        self._active_popups = 0
        self._first_run   = True

        self._rebuild_menu()
        self.indicator.set_menu(self._menu)

        GLib.idle_add(self._check_reminders)
        GLib.timeout_add_seconds(CHECK_INTERVAL_SECONDS, self._check_reminders)

    def _acquire_lock(self):
        try:
            self._lock_fd = open(LOCK_FILE, 'w')
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_fd.write(str(os.getpid()))
            self._lock_fd.flush()
            return True
        except OSError:
            return False

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
            dt  = datetime.fromisoformat(r["datetime"])
            age = (now - dt).total_seconds()

            if dt > now:
                continue

            in_window = age < CHECK_INTERVAL_SECONDS + 5
            is_missed = self._first_run and age < MISSED_WINDOW_HOURS * 3600

            if in_window or is_missed:
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

        self._first_run = False

        if changed:
            save_reminders(reminders)
            self._rebuild_menu()

        return True

    def _fire(self, reminder):
        play_sound()
        self._active_popups += 1
        self._update_icon_state()

        popup = ReminderPopup(
            reminder,
            on_snooze=lambda minutes: self._snooze(reminder["id"], minutes),
            on_close=self._on_popup_closed,
        )
        popup.show()

    def _snooze(self, reminder_id, minutes):
        reminders = load_reminders()
        for r in reminders:
            if r["id"] == reminder_id:
                r["datetime"] = (datetime.now() + timedelta(minutes=minutes)).isoformat()
                r["enabled"]  = True
                break
        save_reminders(reminders)
        self._rebuild_menu()

    def _on_popup_closed(self):
        self._active_popups = max(0, self._active_popups - 1)
        self._update_icon_state()

    def _update_icon_state(self):
        if self._active_popups > 0:
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
        else:
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def _show_add(self):
        try:
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME)
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)
            if self._add_dlg:
                self._add_dlg.present()
                return False
            self._add_dlg = AddDialog()
            self._add_dlg.connect("response", self._on_add_response)
            self._add_dlg.show()
        except Exception:
            traceback.print_exc()
        return False

    def _on_add_response(self, dlg, response):
        if response == Gtk.ResponseType.OK:
            reminder = dlg.build_reminder()
            if reminder["title"]:
                reminders = load_reminders()
                reminders.append(reminder)
                save_reminders(reminders)
                self._rebuild_menu()
        dlg.destroy()
        self._add_dlg = None

    def _show_manage(self):
        try:
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME)
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)
            if self._manage_dlg:
                self._manage_dlg.present()
                return False
            self._manage_dlg = ManageDialog(load_reminders())
            self._manage_dlg.connect("response", self._on_manage_response)
            self._manage_dlg.show()
        except Exception:
            traceback.print_exc()
        return False

    def _on_manage_response(self, dlg, _response):
        dlg.destroy()
        self._manage_dlg = None
        self._rebuild_menu()

    def _quit(self):
        Notify.uninit()
        Gtk.main_quit()

    def run(self):
        Gtk.main()
