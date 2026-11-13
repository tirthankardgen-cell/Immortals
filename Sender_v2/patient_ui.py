"""Touch-only patient selection, registration, recording and delivery popup."""
import time
import math
from datetime import datetime
from patient_common import SEXES

def dashboard_class(Base):
    class PatientDashboard(Base):
        def __init__(self, monitor, fullscreen=True):
            self.screen = 'home'
            self.overlay = None
            self.page = 0
            self.entry_target = None
            self.shift = False
            self.preview = None
            self.popup = None
            self.backdrop = None
            self.auto_recorded_session = None
            super().__init__(monitor, fullscreen)
            self.zigbee_button.destroy()
            self.zigbee_button = self.button(self.canvas,'Record Vitals',self.review,True)
            self.change_button = self.button(self.canvas,'Change Patient',self.home)
            self.ecg_toggle_button = self.button(self.root,'ECG available: ON',self.toggle_ecg_available)
            self.close_button = self.button(self.root,'Close',self.close)
            self.home()

        def draw_close_button(self):
            if self.popup:
                self.close_button.place_forget()
            elif self.screen == 'monitor':
                self.close_button.place(x=920*self.sx,y=8*self.sy,width=84*self.sx,height=44*self.sy)
                self.close_button.lift()
            else:
                # Overlay screens have their own native header button.
                self.close_button.place_forget()

        def toggle_ecg_available(self):
            self.monitor.zigbee.set_ecg_available(not self.monitor.ecg_enabled)
            self.draw_ecg_toggle()

        def draw_ecg_toggle(self):
            if self.screen not in ('home','monitor') or self.popup:
                self.ecg_toggle_button.place_forget()
                return
            available = self.monitor.ecg_enabled
            self.ecg_toggle_button.configure(text='ECG available: '+('ON' if available else 'OFF'))
            self.ecg_toggle_button.set_selected(available)
            if self.screen == 'home':
                self.ecg_toggle_button.place(relx=1,x=-470,y=8,width=220,height=44)
            else:
                self.ecg_toggle_button.place(x=450*self.sx,y=8*self.sy,width=220*self.sx,height=44*self.sy)
            self.ecg_toggle_button.lift()

        def button(self, parent, text, command, primary=False, **kwargs):
            from tkinter import font as tkfont
            font = tkfont.Font(family='DejaVu Sans',size=12,weight='bold')
            requested_width = kwargs.pop('width',None)
            requested_height = kwargs.pop('height',None)
            width = font.measure('0')*requested_width+28 if requested_width else font.measure(text)+32
            height = font.metrics('linespace')*(requested_height or 1)+22
            requested_pixels = max(44,width),max(44,height)
            button = self.tk.Button(parent,text=text,command=command,bg=parent.cget('bg'),fg='#071c16' if primary else self.TEXT,
                                    activebackground=parent.cget('bg'),activeforeground='#071c16' if primary else self.TEXT,
                                    bd=0,highlightthickness=0,font=font,padx=0,pady=0,compound='center',takefocus=False,**kwargs)
            button._rounded_key = None
            button._rounded_primary = primary
            def paint(width,height):
                color = self.GREEN if button._rounded_primary else '#263b56'
                key = width,height,color
                if key == button._rounded_key:return
                button._rounded_key = key
                try:
                    from PIL import Image,ImageDraw,ImageFilter,ImageTk
                    shadow=Image.new('RGBA',(max(1,width),max(1,height)),(0,0,0,0))
                    ImageDraw.Draw(shadow).rounded_rectangle((2,4,width-2,height-1),radius=13,fill=(0,0,0,110))
                    pixels=Image.new('RGBA',shadow.size,parent.cget('bg'))
                    pixels=Image.alpha_composite(pixels,shadow.filter(ImageFilter.GaussianBlur(3)))
                    ImageDraw.Draw(pixels).rounded_rectangle((0,0,width-1,height-5),radius=13,fill=color)
                    image=ImageTk.PhotoImage(pixels,master=button)
                except ImportError:
                    image = self.tk.PhotoImage(master=button,width=max(1,width),height=max(1,height))
                    radius = min(13,height/2,width/2)
                    for row in range(height):
                        dy = max(0,radius-row-.5,row+.5-(height-radius))
                        inset = math.ceil(radius-math.sqrt(max(0,radius*radius-dy*dy))) if dy else 0
                        if width>2*inset:image.put(color,to=(inset,row,width-inset,row+1))
                button._rounded_image = image
                # A native button adds internal pixels to its image request.
                # Keep requested geometry fixed while painting allocated size;
                # otherwise Configure -> image resize would grow without bound.
                button.configure(image=image,width=requested_pixels[0],height=requested_pixels[1])
            button.set_selected = lambda selected: (setattr(button,'_rounded_primary',selected),
                                                    button.configure(fg='#071c16' if selected else self.TEXT),
                                                    paint(button.winfo_width(),button.winfo_height()))
            paint(max(44,width),max(44,height))
            button.bind('<Configure>',lambda e:paint(e.width,e.height))
            return button

        def label(self, parent, text, size=13, color=None, **kwargs):
            return self.tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color or self.TEXT,
                                 font=('DejaVu Sans',size,'bold' if size>=18 else 'normal'), **kwargs)

        def new_screen(self, title, back=None):
            if self.overlay:
                self.overlay.destroy()
            self.entry_target = None
            self.overlay = self.tk.Frame(self.root, bg=self.BG)
            self.overlay.place(x=0,y=0,relwidth=1,relheight=1)
            top = self.tk.Frame(self.overlay,bg=self.PANEL)
            top.pack(fill='x')
            if back:
                self.button(top,'‹ Back',back).pack(side='left',padx=12,pady=8)
            self.label(top,title,18).pack(side='left',padx=14)
            self.button(top,'Close',self.close).pack(side='right',padx=8,pady=8)
            self.button(top,'Full screen',self.fullscreen).pack(side='right',padx=8,pady=8)
            body = self.tk.Frame(self.overlay,bg=self.BG)
            body.pack(fill='both',expand=True,padx=24,pady=10)
            return body

        def notice(self, parent):
            self.notice_var = self.tk.StringVar()
            self.label(parent,'',11,self.GOLD,textvariable=self.notice_var,wraplength=900,anchor='w').pack(fill='x',pady=6)

        def home(self):
            self.monitor.zigbee.end_session()
            self.screen = 'home'
            body = self.new_screen('IMMORTALS  |  Remote Checkups')
            self.label(body,'Ready for the next checkup',24).pack(pady=(10,5))
            self.label(body,'Choose a patient or register a new patient to begin.',13,self.MUTED).pack(pady=3)
            buttons = self.tk.Frame(body,bg=self.BG)
            buttons.pack(fill='x',pady=(18,20))
            self.button(buttons,'Choose Patient',self.choose,True,width=20,height=2).pack(side='left',fill='x',expand=True,padx=(0,10))
            self.button(buttons,'Add Patient',self.add,width=20,height=2).pack(side='left',fill='x',expand=True,padx=(10,0))
            self.home_status = self.tk.StringVar()
            panel=self.tk.Canvas(body,height=104,bg=self.BG,highlightthickness=0)
            panel.pack(fill='x')
            def draw_status(*args):
                if not panel.winfo_exists():return
                panel.delete('all')
                width=max(1,panel.winfo_width())
                Base.rounded_shape(panel,0,0,width,104,18,self.PANEL)
                panel.create_text(20,16,text=self.home_status.get(),anchor='nw',fill=self.MUTED,
                                  font=('DejaVu Sans',12),width=max(1,width-40))
            panel.bind('<Configure>',draw_status)
            self.home_status.trace_add('write',draw_status)
            actions=self.tk.Frame(body,bg=self.BG)
            actions.pack(fill='x',pady=18)
            self.button(actions,'Sync Patient List',lambda:self.monitor.zigbee.request_sync()).pack(side='left',fill='x',expand=True,padx=(0,8))
            self.button(actions,'Review Saved Record',self.open_saved).pack(side='left',fill='x',expand=True,padx=8)
            self.button(actions,'Sync All Saved Data',self.sync_all,True).pack(side='left',fill='x',expand=True,padx=(8,0))
            self.label(body,'The sender works offline. Saved checkups travel to the gateway over Zigbee.',11,self.MUTED).pack(pady=6)

        def entry(self, parent, variable, numeric=False):
            widget = self.tk.Entry(parent,textvariable=variable,font=('DejaVu Sans',18),bg='#1c2c43',fg=self.TEXT,
                                   insertbackground=self.GREEN,relief='flat',selectbackground='#314968')
            widget.bind('<FocusIn>',lambda e:self.target_entry(widget,numeric))
            widget.bind('<Button-1>',lambda e:self.target_entry(widget,numeric))
            return widget

        def target_entry(self, widget, numeric=False):
            self.entry_target = widget
            if (getattr(self,'keyboard_numeric',None) != numeric or not hasattr(self,'keyboard_frame')
                    or not self.keyboard_frame.winfo_exists()):
                self.keyboard(numeric)

        def key(self, value):
            widget = self.entry_target
            if widget is None or not widget.winfo_exists():
                return
            try:
                if widget.selection_present():
                    widget.delete('sel.first','sel.last')
                elif value == '⌫':
                    cursor = widget.index('insert')
                    if cursor:
                        widget.delete(cursor-1,cursor)
                    return
            except self.tk.TclError:
                return
            if value == 'Clear':
                widget.delete(0,'end')
            elif value == 'Shift':
                self.shift = not self.shift
                self.keyboard(self.keyboard_numeric)
            elif value != '⌫':
                text = ' ' if value == 'Space' else value
                widget.insert('insert',text.upper() if self.shift else text.lower())
            widget.focus_set()

        def keyboard(self, numeric=False):
            if hasattr(self,'keyboard_frame') and self.keyboard_frame.winfo_exists():
                self.keyboard_frame.destroy()
            self.keyboard_numeric = numeric
            self.keyboard_frame = self.tk.Frame(self.keyboard_holder,bg=self.PANEL)
            self.keyboard_frame.pack(fill='x')
            rows = ['1234567890','qwertyuiop','asdfghjkl','zxcvbnm-'] if not numeric else ['1234567890']
            for chars in rows:
                row = self.tk.Frame(self.keyboard_frame,bg=self.PANEL)
                row.pack(fill='x',padx=5,pady=2)
                for char in chars:
                    self.button(row,char.upper() if self.shift else char,lambda c=char:self.key(c)).pack(side='left',fill='x',expand=True,padx=2)
            row = self.tk.Frame(self.keyboard_frame,bg=self.PANEL)
            row.pack(fill='x',padx=5,pady=3)
            for key in (('Clear','⌫') if numeric else ('Shift','Space','Clear','⌫')):
                self.button(row,key,lambda k=key:self.key(k)).pack(side='left',fill='x',expand=True,padx=3)

        def choose(self):
            self.screen = 'choose'
            body = self.new_screen('Choose Patient',self.home)
            self.keyboard_holder = self.tk.Frame(self.overlay,bg=self.PANEL)
            self.keyboard_holder.pack(side='bottom',fill='x',before=body)
            self.search = self.tk.StringVar()
            search_row = self.tk.Frame(body,bg=self.BG)
            search_row.pack(fill='x')
            entry = self.entry(search_row,self.search)
            entry.pack(side='left',fill='x',expand=True,ipady=7)
            self.button(search_row,'Sync',lambda:self.monitor.zigbee.request_sync()).pack(side='right',padx=(12,0))
            self.label(body,'Search by name or patient ID · verify the ID for similar names',10,self.MUTED).pack(anchor='w',pady=4)
            self.list_frame = self.tk.Frame(body,bg=self.BG)
            self.list_frame.pack(fill='both',expand=True)
            navigation = self.tk.Frame(body,bg=self.BG)
            navigation.pack(fill='x')
            self.button(navigation,'‹ Previous',lambda:self.turn_page(-1)).pack(side='left')
            self.page_label = self.tk.StringVar()
            self.label(navigation,'',11,self.MUTED,textvariable=self.page_label).pack(side='left',padx=20)
            self.button(navigation,'Next ›',lambda:self.turn_page(1)).pack(side='right')
            self.page = 0
            self.search.trace_add('write',lambda *args:self.search_changed())
            self.list_signature = None
            self.populate_patients()
            self.target_entry(entry)
            entry.focus_set()

        def search_changed(self):
            self.page = 0
            self.populate_patients()

        def turn_page(self, amount):
            self.page = max(0,self.page+amount)
            self.populate_patients()

        def populate_patients(self):
            patients = self.monitor.zigbee.store.patients(self.search.get())
            per_page = 3
            self.page = min(self.page,max(0,(len(patients)-1)//per_page))
            signature = tuple((p['patient_id'],p['name']) for p in patients),self.page
            if signature == self.list_signature:
                return
            self.list_signature = signature
            for widget in self.list_frame.winfo_children():
                widget.destroy()
            if not patients:
                self.label(self.list_frame,'No matching patients. Use Add Patient to register.',12,self.MUTED).pack(pady=24)
            for patient in patients[self.page*per_page:(self.page+1)*per_page]:
                text = patient['name']+'   |   '+patient.get('patient_code',patient['patient_id'])+f"   |   {patient['age']} / {patient['sex']}"
                self.button(self.list_frame,text,lambda p=patient:self.confirm(p),anchor='w').pack(fill='x',pady=3)
            self.page_label.set(f'{len(patients)} patients · Page {self.page+1} of {max(1,(len(patients)+2)//3)}')

        def add(self):
            self.screen = 'add'
            body = self.new_screen('Add Patient',self.home)
            self.keyboard_holder = self.tk.Frame(self.overlay,bg=self.PANEL)
            self.keyboard_holder.pack(side='bottom',fill='x',before=body)
            self.name_var,self.age_var,self.sex_var = self.tk.StringVar(),self.tk.StringVar(),self.tk.StringVar()
            fields = self.tk.Frame(body,bg=self.BG)
            fields.pack(fill='x',pady=6)
            name_box = self.tk.Frame(fields,bg=self.BG)
            name_box.pack(side='left',fill='x',expand=True)
            self.label(name_box,'Patient name',11,self.MUTED).pack(anchor='w')
            name = self.entry(name_box,self.name_var)
            name.pack(fill='x',ipady=7,pady=5)
            age_box = self.tk.Frame(fields,bg=self.BG)
            age_box.pack(side='right',padx=(16,0))
            self.label(age_box,'Age (0–130)',11,self.MUTED).pack(anchor='w')
            self.entry(age_box,self.age_var,True).pack(ipady=7,pady=5)
            self.label(body,'Sex',11,self.MUTED).pack(anchor='w')
            choices = self.tk.Frame(body,bg=self.BG)
            choices.pack(fill='x',pady=5)
            sex_buttons = []
            for sex in SEXES:
                choice = self.button(choices,sex,lambda s=sex:self.sex_var.set(s))
                choice.pack(side='left',fill='x',expand=True,padx=4)
                sex_buttons.append((sex,choice))
            self.sex_var.trace_add('write',lambda *args:[b.set_selected(s==self.sex_var.get()) for s,b in sex_buttons])
            self.notice(body)
            self.button(body,'Create Patient & Continue',self.save_patient,True).pack(anchor='e',pady=5)
            self.target_entry(name)
            name.focus_set()

        def save_patient(self):
            try:
                if not self.age_var.get().strip().isdigit():
                    raise ValueError('Enter a whole-number age from 0 to 130')
                patient = self.monitor.zigbee.create_patient(self.name_var.get(),int(self.age_var.get()),self.sex_var.get())
                self.confirm(patient)
            except (ValueError,OSError) as exc:
                self.notice_var.set(str(exc))

        def confirm(self, patient):
            self.screen = 'confirm'
            body = self.new_screen('Confirm Patient',self.choose)
            self.label(body,patient['name'],28).pack(pady=(45,20))
            self.label(body,patient.get('patient_code',patient['patient_id']),20,self.BLUE).pack(pady=8)
            self.label(body,f"Age {patient['age']}  ·  {patient['sex']}",18).pack(pady=15)
            self.label(body,'Confirm these details before checking sensor readings.',13,self.MUTED).pack(pady=18)
            self.button(body,'Confirm & Check Readings',lambda:self.start_patient(patient),True).pack(pady=20)

        def start_patient(self, patient):
            self.monitor.zigbee.select(patient)
            self.auto_recorded_session = None
            self.screen = 'monitor'
            if self.overlay:
                self.overlay.destroy()
                self.overlay = None

        def review(self):
            try:
                self.preview = self.monitor.zigbee.record()
            except (ValueError,OSError):
                return
            self.show_record_popup()

        def open_saved(self):
            pending = self.monitor.zigbee.store.pending(('draft','pending','gateway'),1)
            if pending:
                self.preview = pending[0]
                self.show_record_popup()

        def show_record_popup(self):
            from touch_theme import backdrop,rounded_window,popup_surface
            if self.popup and self.popup.winfo_exists():
                self.popup.destroy()
            self.popup = self.tk.Toplevel(self.root)
            self.popup.withdraw()
            self.popup.overrideredirect(True)
            self.popup.configure(bg=self.PANEL)
            self.popup.transient(self.root)
            self.root.update_idletasks()
            width = min(900,self.root.winfo_width()-32)
            height = min(560,self.root.winfo_height()-32)
            if self.backdrop:self.backdrop.destroy()
            self.backdrop=backdrop(self.root,(width,height))
            self.popup.geometry(f'{width}x{height}+{self.root.winfo_rootx()+(self.root.winfo_width()-width)//2}+{self.root.winfo_rooty()+(self.root.winfo_height()-height)//2}')
            popup_surface(self.popup,self.backdrop,(width,height),self.PANEL)
            self.popup.deiconify()
            self.popup.grab_set()
            self.popup.after(60,lambda:rounded_window(self.popup) if self.popup and self.popup.winfo_exists() else None)
            self.popup.protocol('WM_DELETE_WINDOW',self.finish_popup)
            body = self.tk.Frame(self.popup,bg=self.PANEL)
            body.pack(fill='both',expand=True,padx=22,pady=14)
            self.label(body,'✓  Data recorded successfully',21,self.GREEN).pack(anchor='w',pady=(0,10))
            patient = self.preview['patient']
            self.label(body,patient['name']+'  ·  '+patient['patient_id'],13,self.BLUE).pack(anchor='w',pady=5)
            captured = datetime.fromisoformat(self.preview['reading']['captured_at']).astimezone().strftime('%d %b %Y  %H:%M:%S')
            self.label(body,'Recorded at '+captured,10,self.MUTED).pack(anchor='w')
            rows = self.tk.Frame(body,bg=self.BG)
            rows.pack(fill='both',expand=True,pady=10)
            for name, sensor in self.preview['reading']['sensors'].items():
                values = sensor['values']
                detail = ' · '.join(f'{key}: {value if value is not None else "unavailable"}' for key,value in values.items()
                                     if key in ('heart_rate_bpm','spo2_percent','candidate_bpm','object_c','ambient_c','temperature_c','humidity_percent','pressure_hpa'))
                self.label(rows,name.upper()+': '+(detail or 'No valid measurement')+'\n'+sensor['status'],10,anchor='w',justify='left',wraplength=width-55).pack(fill='x',pady=4,padx=8)
            waves = self.preview['reading']['waveforms']
            self.label(body,f"Waveforms recorded: pulse {len(waves['pulse']['values'])} points · ECG {len(waves['ecg']['values'])} points",10,self.MUTED).pack(anchor='w')
            self.popup_status = self.tk.StringVar(value='All available data is saved on this device — ready to send to gateway.')
            self.label(body,'',12,self.GOLD,textvariable=self.popup_status,wraplength=width-44,justify='left').pack(fill='x',pady=10)
            actions = self.tk.Frame(body,bg=self.PANEL)
            actions.pack(fill='x')
            self.popup_done = self.button(actions,'Main Screen',self.finish_popup)
            self.popup_done.pack(side='left')
            self.popup_again = self.button(actions,'Record Again',self.record_again)
            self.popup_again.pack(side='left',padx=12)
            self.popup_send = self.button(actions,'Send to Gateway',self.submit_review,True)
            self.popup_send.pack(side='right')
            self.send_started = None
            self.failure_closing = False
            state = self.monitor.zigbee.store.receipt(self.preview['request_id'])['state']
            if state != 'draft':
                self.send_started = time.monotonic()
                self.popup_send.configure(state='disabled')
                self.popup_again.configure(state='disabled')
                self.update_popup()

        def submit_review(self):
            try:
                self.monitor.zigbee.submit(self.preview)
                self.send_started = time.monotonic()
                self.popup_send.configure(state='disabled')
                self.popup_status.set('Sending to gateway… Your record is saved on this device.')
                self.popup_again.configure(state='disabled')
                self.update_popup()
            except (ValueError,OSError) as exc:
                self.popup_status.set(str(exc))

        def update_popup(self):
            if not self.popup or not self.popup.winfo_exists() or not self.send_started:
                return
            state = self.monitor.zigbee.status()
            receipt = self.monitor.zigbee.store.receipt(self.preview['request_id'])
            if receipt['state'] == 'uploaded':
                self.popup_status.set('Sent successfully. Saved by gateway.')
                self.popup_again.configure(state='normal',text='New Check')
                self.popup_done.configure(text='Main Screen')
                return
            if receipt['state'] == 'gateway':
                self.popup_status.set('Sent successfully. Saved on gateway. Gateway synchronization is pending…')
                self.popup_again.configure(state='normal',text='New Check')
                self.popup_done.configure(text='Main Screen')
            elif receipt['state'] == 'rejected':
                self.popup_status.set('Saved on this device. Gateway needs attention: '+receipt['detail'])
                self.popup_done.configure(text='Main Screen')
                return
            elif state['last_error'] or time.monotonic()-self.send_started > 25:
                self.popup_status.set('Gateway unavailable. Saved on this device. All pending records will sync automatically when the gateway returns. Returning to main screen…')
                if not self.failure_closing:
                    self.failure_closing = True
                    self.return_home_later()
                return
            self.root.after(400,self.update_popup)

        def finish_popup(self):
            if self.popup and self.popup.winfo_exists():
                self.popup.grab_release()
                self.popup.destroy()
            self.popup = None
            if self.backdrop:self.backdrop.destroy();self.backdrop=None
            self.home()
            self.draw_ecg_toggle()
            self.root.focus_force()

        def return_home_later(self):
            popup=self.popup
            self.root.after(4500,lambda:self.finish_popup() if self.popup==popup else None)

        def record_again(self):
            patient=self.preview['patient']
            self.monitor.zigbee.store.discard_draft(self.preview['request_id'])
            if self.popup and self.popup.winfo_exists():
                self.popup.grab_release();self.popup.destroy()
            self.popup=None
            if self.backdrop:self.backdrop.destroy();self.backdrop=None
            self.start_patient(patient)

        def sync_all(self):
            from touch_theme import backdrop,rounded_window,popup_surface
            keys=self.monitor.zigbee.sync_all()
            if self.popup and self.popup.winfo_exists():self.popup.destroy()
            self.popup=self.tk.Toplevel(self.root)
            self.popup.withdraw()
            self.popup.overrideredirect(True)
            self.popup.configure(bg=self.PANEL)
            self.popup.transient(self.root)
            self.popup.geometry(f'780x310+{self.root.winfo_rootx()+(self.root.winfo_width()-780)//2}+{self.root.winfo_rooty()+(self.root.winfo_height()-310)//2}')
            if self.backdrop:self.backdrop.destroy()
            self.backdrop=backdrop(self.root,(780,310))
            popup_surface(self.popup,self.backdrop,(780,310),self.PANEL)
            self.popup.deiconify()
            self.popup.grab_set()
            self.popup.after(60,lambda:rounded_window(self.popup) if self.popup and self.popup.winfo_exists() else None)
            body=self.tk.Frame(self.popup,bg=self.PANEL);body.pack(fill='both',expand=True,padx=28,pady=22)
            self.label(body,'Sync saved checkups to gateway',21,self.GREEN).pack(anchor='w',pady=8)
            self.batch_status=self.tk.StringVar()
            self.label(body,'',14,self.GOLD,textvariable=self.batch_status,wraplength=720,justify='left').pack(fill='both',expand=True,pady=12)
            self.button(body,'Close — Main Screen',self.finish_popup).pack(anchor='e')
            started=time.monotonic()
            def poll():
                if not self.popup or not self.popup.winfo_exists():return
                receipts=[self.monitor.zigbee.store.receipt(key)['state'] for key in keys]
                sent=sum(state in ('gateway','uploaded') for state in receipts)
                left=sum(state in ('pending','draft') for state in receipts)
                state=self.monitor.zigbee.status()
                if not keys or sent==len(keys):
                    self.batch_status.set(f'All {len(keys)} saved records are confirmed by the gateway.');return
                if left and (state['last_error'] or time.monotonic()-started>30 and sent==0):
                    self.batch_status.set('Gateway unavailable. All unsent records remain saved on this device and will sync automatically when it returns. Returning to main screen…')
                    self.root.after(4500,self.finish_popup);return
                self.batch_status.set(f'Sending saved records… {sent} of {len(keys)} confirmed by gateway. {left} remain safely stored on this device.')
                self.root.after(500,poll)
            poll()

        def back_to_monitor(self):
            self.screen = 'monitor'
            if self.overlay:
                self.overlay.destroy()
                self.overlay = None

        def draw_zigbee_button(self):
            active = self.monitor.zigbee.active
            remaining = max(0,8.3-(time.monotonic()-active['started_mono'])) if active else 0
            self.zigbee_button.configure(text=f'Collecting… {remaining:.0f}s' if remaining else 'Record Available',
                                         state='disabled' if remaining else 'normal')
            self.zigbee_button.place(x=792*self.sx,y=548*self.sy,width=212*self.sx,height=44*self.sy)
            self.change_button.place(x=20*self.sx,y=548*self.sy,width=155*self.sx,height=44*self.sy)

        def render(self):
            if self.monitor.stop.is_set():
                self.close()
                return
            self.draw_ecg_toggle()
            if self.screen == 'monitor':
                super().render()
                active=self.monitor.zigbee.active
                if active and not self.popup and self.auto_recorded_session != active['monitoring_session_id']:
                    ready,missing=self.monitor.zigbee.readiness()
                    if ready:
                        self.auto_recorded_session=active['monitoring_session_id']
                        self.review()
                    else:
                        self.text(190,574,'Waiting for '+', '.join(missing),9,self.GOLD,width=585)
            else:
                state = self.monitor.zigbee.status()
                if self.screen == 'home':
                    delivery = state['submission']['detail'] if state['submission'] else 'No capture submitted yet'
                    delivery = delivery.replace('Saved to Firebase','Saved by gateway')
                    link='Gateway unavailable — records stay saved here' if state['last_error'] else 'Zigbee gateway ready'
                    self.home_status.set(link+' · '+state['sync_status']+f"\nRecorded: {state['recorded_count']} · Waiting on device: {state['pending_count']} · Gateway syncing: {state['gateway_pending_count']}\n"+delivery)
                elif self.screen == 'choose':
                    self.populate_patients()
                self.root.after(250,self.render)
            self.draw_close_button()
    return PatientDashboard
