import wx
import json
import socket
from pathlib import Path
import os
from datetime import datetime
import sys

class ChangePasswordDialog(wx.Dialog):
    """Dialog pro změnu hesla správce."""
    def __init__(self, parent, current_pw):
        super().__init__(parent, title="Změna hesla správce", size=(300, 350))
        self.current_pw = current_pw or ''
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Pokud už je heslo nastaveno, ověříme aktuální
        if self.current_pw:
            vbox.Add(wx.StaticText(panel, label="Aktuální heslo:"), flag=wx.ALL, border=10)
            self.pw_current = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
            vbox.Add(self.pw_current, flag=wx.EXPAND|wx.ALL, border=10)

        # Nové heslo a potvrzení
        vbox.Add(wx.StaticText(panel, label="Nové heslo:"), flag=wx.ALL, border=10)
        self.pw_new = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        vbox.Add(self.pw_new, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(wx.StaticText(panel, label="Potvrďte heslo:"), flag=wx.ALL, border=10)
        self.pw_confirm = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        vbox.Add(self.pw_confirm, flag=wx.EXPAND|wx.ALL, border=10)

        # OK / Cancel tlačítka
        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK, label="Potvrdit")
        btn_cancel = wx.Button(panel, wx.ID_CANCEL, label="Zrušit")
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.ALL, border=10)

        panel.SetSizer(vbox)

    def ShowModal(self):
        while True:
            res = super().ShowModal()
            if res != wx.ID_OK:
                return res
            # Ověříme stávající heslo
            if hasattr(self, 'pw_current') and self.pw_current.GetValue() != self.current_pw:
                wx.MessageBox("Aktuální heslo je nesprávné.", "Chyba", wx.ICON_ERROR)
                continue
            # Kontrola nového hesla (povolujeme prázdné heslo pro zrušení zabezpečení)
            new_pw = self.pw_new.GetValue()
            if new_pw != self.pw_confirm.GetValue():
                wx.MessageBox("Nové heslo a potvrzení se neshodují.", "Chyba", wx.ICON_ERROR)
                continue
            # Vrací OK, pokud je heslo platné (i prázdné)
            return wx.ID_OK

    def get_new_password(self):
        return self.pw_new.GetValue() or ''


class SettingsDialog(wx.Dialog):
    """Dialog pro úpravu nastavení včetně hesla správce a volby USB tisku."""
    def __init__(self, parent):
        super().__init__(parent, title="Nastavení", size=(400, 450))
        self.settings_file = Path(os.path.expanduser('~')) / 'Documents' / 'app_settings.json'
        self.saved_settings = {}
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    self.saved_settings = json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Standardní pole nastavení (bez hesla)
        fields = [
            ('ip', 'IP tiskárny:'),
            ('port', 'Port tiskárny:'),
            ('company_name', 'Jméno společnosti:'),
            ('ra', 'RA:'),
            ('control', 'Control Provided By:'),
            ('label_number', 'Počáteční číslo štítku:'),
        ]
        self.fields = {}
        for key, label in fields:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            lbl = wx.StaticText(panel, label=label)
            default = self.saved_settings.get(key, '')
            txt = wx.TextCtrl(panel, value=str(default))
            self.fields[key] = txt
            hbox.Add(lbl, flag=wx.RIGHT, border=8)
            hbox.Add(txt, proportion=1)
            vbox.Add(hbox, flag=wx.EXPAND|wx.ALL, border=10)

        # Checkbox pro USB tisk
        self.use_usb_chk = wx.CheckBox(panel, label="Tisk přes USB")
        self.use_usb_chk.SetValue(self.saved_settings.get('use_usb', False))
        vbox.Add(self.use_usb_chk, flag=wx.LEFT|wx.TOP, border=10)

        # Tlačítko pro změnu hesla
        pwd_set = 'Ano' if self.saved_settings.get('admin_password') else 'Ne'
        self.pwd_status = wx.StaticText(panel, label=f"Heslo nastaveno: {pwd_set}")
        vbox.Add(self.pwd_status, flag=wx.LEFT|wx.TOP, border=10)
        self.change_pwd_btn = wx.Button(panel, label="Změnit heslo")
        self.change_pwd_btn.Bind(wx.EVT_BUTTON, self.on_change_password)
        vbox.Add(self.change_pwd_btn, flag=wx.LEFT|wx.TOP, border=10)

        # OK a Cancel
        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK, label="OK")
        btn_cancel = wx.Button(panel, wx.ID_CANCEL, label="Storno")
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.ALL, border=10)

        panel.SetSizer(vbox)

    def on_change_password(self, event):
        # Otevře dialog pro změnu hesla
        current = self.saved_settings.get('admin_password', '')
        dlg = ChangePasswordDialog(self, current)
        if dlg.ShowModal() == wx.ID_OK:
            new_pw = dlg.get_new_password()
            self.saved_settings['admin_password'] = new_pw
            self.pwd_status.SetLabel("Heslo nastaveno: Ano" if new_pw else "Heslo nastaveno: Ne")
        dlg.Destroy()

    def get_settings(self):
        # Vrací nastavení včetně případné změny hesla
        data = self.saved_settings.copy()
        for key, txt in self.fields.items():
            data[key] = txt.GetValue()
        data['use_usb'] = self.use_usb_chk.GetValue()
        return data, self.settings_file


class PasswordPrompt(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Heslo správce", size=(300, 160))
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label="Zadejte heslo správce:")
        self.password_txt = wx.TextCtrl(panel, style=wx.TE_PASSWORD)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()

        vbox.Add(lbl, flag=wx.ALL, border=10)
        vbox.Add(self.password_txt, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.ALL, border=10)
        panel.SetSizer(vbox)

    def get_password(self):
        return self.password_txt.GetValue()

class MyFrame(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(350, 300))

        # Get the correct path for the icon
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            # Running as a normal script
            base_path = os.path.dirname(__file__)

        icon_path = os.path.join(base_path, "icon.ico")
        if os.path.exists(icon_path):
            self.SetIcon(wx.Icon(icon_path))
        else:
            wx.MessageBox(f"Icon not found: {icon_path}", "Error", wx.ICON_ERROR)

        self.settings = {}
        self.load_settings()

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Výběr kontroly
        choices = [
            "SPX by XRY"
        ] # Add more choices as needed - SPX by XRY, "SPX by XRY/ETD", "SPX by PHS/ETD", "SPX by VCK/ETD", "SPX by VCK/PHS", "SPX by KC", "SPX by RA/RCVD", "SPX by EXEMPTED-BIOM", "SPX by EXEMPTED-NUCL"
        self.radio = wx.RadioBox(panel, label="Vyber kontrolu", choices=choices, style=wx.RA_SPECIFY_ROWS)
        sizer.Add(self.radio, flag=wx.EXPAND|wx.ALL, border=10)

        # Jméno a počet
        self.name_lbl = wx.StaticText(panel, label="Jméno:")
        self.name_txt = wx.TextCtrl(panel)
        self.count_lbl = wx.StaticText(panel, label="Počet:")
        self.count_txt = wx.TextCtrl(panel, value="1")
        sizer.Add(self.name_lbl, flag=wx.LEFT|wx.TOP, border=10)
        sizer.Add(self.name_txt, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=10)
        sizer.Add(self.count_lbl, flag=wx.LEFT|wx.TOP, border=10)
        sizer.Add(self.count_txt, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=10)

        # Tlačítka
        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        self.print_btn = wx.Button(panel, label="Tisk")
        self.clear_btn = wx.Button(panel, label="Vymazat")
        btn_box.Add(self.print_btn, 1, wx.EXPAND|wx.ALL, 5)
        btn_box.Add(self.clear_btn, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(btn_box, flag=wx.EXPAND|wx.ALL, border=10)

        self.settings_btn = wx.Button(panel, label="Nastavení")
        sizer.Add(self.settings_btn, flag=wx.ALIGN_CENTER|wx.ALL, border=10)

        panel.SetSizer(sizer)

        # Bind events
        self.print_btn.Bind(wx.EVT_BUTTON, self.on_print)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.settings_btn.Bind(wx.EVT_BUTTON, self.on_settings)

        self.Show()

    def load_settings(self):
        path = Path(os.path.expanduser('~')) / 'Documents' / 'app_settings.json'
        if path.exists():
            with open(path, 'r') as f:
                self.settings = json.load(f)

    def on_print(self, event):
        # Pokud je heslo nastaveno, zobrazí se dialog
        if self.settings.get('admin_password', ''):
            prompt = PasswordPrompt(self)
            if prompt.ShowModal() != wx.ID_OK:
                prompt.Destroy()
                return
            entered = prompt.get_password()
            prompt.Destroy()
            if entered != self.settings.get('admin_password', ''):
                wx.MessageBox("Nesprávné heslo!", "Chyba", wx.ICON_ERROR)
                return

        # Příprava tisku
        now = datetime.now().strftime("%d%b%y %H:%M").upper()
        company = self.settings.get('company_name', '')
        ra = self.settings.get('ra', '')
        control = self.settings.get('control', '')
        name = self.name_txt.GetValue()
        try:
            copies = max(1, int(self.count_txt.GetValue()))
        except ValueError:
            copies = 1
        selected = self.radio.GetStringSelection() or "SPX by XRY"

        for _ in range(copies):
            label_num = self.next_label()
            zpl = self.make_zpl(company, ra, control, now, name, label_num, selected)
            if self.settings.get('use_usb'):
                self.usb_print(zpl)
            else:
                self.net_print(self.settings.get('ip',''), self.settings.get('port',''), zpl)
            print(f"Vytištěn štítek {label_num}")


    def next_label(self):
        num = int(self.settings.get('label_number', '117823'))
        num = (num + 1) % 1000000
        lbl = f"{num:06d}"
        self.settings['label_number'] = lbl
        path = Path(os.path.expanduser('~')) / 'Documents' / 'app_settings.json'
        with open(path, 'w') as f:
            json.dump(self.settings, f, indent=4)
        return lbl

    def make_zpl(self, comp, ra, ctrl, dt, name, lbl, sel):
        return f"""^XA
^CI28
^FO10,10^GB730,173,3^FS
^FO10,10^GB365,35,3^FS          ; Horní levá buňka
^FO10,10^GB730,35,3^FS          ; Horní pravá buňka
^FO10,10^GB730,70,3^FS          ; Střední buňka
^FO10,10^GB730,140,3^FS         ; Spodní rámeček
^FO105,150^GB0,30,3^FS            ; První vertikální čára
^FO245,150^GB0,30,3^FS            ; Druhá vertikální čára
^FO310,150^GB0,30,3^FS            ; Třetí vertikální čára
^FO545,150^GB0,30,3^FS            ; Čtvrtá vertikální čára
^FO625,150^GB0,30,3^FS            ; Pátá vertikální čára
^CF0,20,20
^FO15,155^FDDate&Time^FS
^FO115,155^FD{dt}^FS
^CF0,50,50
^FO250,100^FD{sel}^FS
^CF0,30,30
^FO100,15^FD{comp}^FS
^CF0,30,30
^FO30,50^FD{ctrl}^FS
^CF0,30,30
^FO450,15^FD{ra}^FS
^CF0,25,25
^FO365,155^FD{name}^FS
^CF0,20,20
^FO650,155^FD{lbl}^FS
^XZ"""

    def net_print(self, host, port, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, int(port)))
                s.sendall(data.encode('utf-8'))
        except Exception as e:
            wx.MessageBox(f"Chyba síťového tisku: {e}", "Chyba", wx.ICON_ERROR)

    def usb_print(self, data):
        try:
            import win32print
            # Attempt to auto-detect a Zebra or ZDesigner printer
            printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            printer_name = self.settings.get('printer_name', '') or next((p for p in printers if 'zebra' in p.lower() or 'zdesigner' in p.lower()), None)
            if not printer_name:
                wx.MessageBox("Zebra nebo ZDesigner tiskárna nebyla nalezena.", "Chyba", wx.ICON_ERROR)
                return
            handle = win32print.OpenPrinter(printer_name)
            try:
                job_info = win32print.StartDocPrinter(handle, 1, ("Zebra Print Job", None, "RAW"))
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data.encode('utf-8'))
                win32print.EndPagePrinter(handle)
                win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
        except Exception as e:
            wx.MessageBox(f"Chyba USB tisku: {e}", "Chyba", wx.ICON_ERROR)

    def on_clear(self, event):
        self.name_txt.Clear()
        self.count_txt.SetValue("1")

    def on_settings(self, event):
        dlg = SettingsDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            new_set, path = dlg.get_settings()
            with open(path, 'w') as f:
                json.dump(new_set, f, indent=4)
            self.load_settings()
        dlg.Destroy()

if __name__ == '__main__':
    app = wx.App(False)
    frame = MyFrame(None, "Scprint")
    app.MainLoop()
