from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from queue import Queue
import os, threading
import yt_dlp

DOWNLOAD_DIR = os.path.join('/storage/emulated/0', 'Download', 'YouTubeDownloader')


def duration(v):
    if not v: return '0:00'
    v = int(v); h, r = divmod(v, 3600); m, s = divmod(r, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


class DownloadRow(BoxLayout):
    def __init__(self, title, **kw):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(105), padding=dp(6), spacing=dp(3), **kw)
        self.add_widget(Label(text=title, size_hint_y=None, height=dp(30), halign='left'))
        self.progress = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(12))
        self.details = Label(text='Waiting...', size_hint_y=None, height=dp(45), halign='left')
        self.add_widget(self.progress); self.add_widget(self.details)


class AppMain(App):
    def build(self):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        self.q = Queue()
        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(7))
        root.add_widget(Label(text='YouTube Downloader Pro', font_size=dp(22), size_hint_y=None, height=dp(42)))

        r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        self.url = TextInput(hint_text='Paste YouTube URL', multiline=False)
        r.add_widget(self.url)
        b = Button(text='Download', size_hint_x=None, width=dp(110)); b.bind(on_release=lambda *_: self.add_download())
        r.add_widget(b); root.add_widget(r)

        r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        self.search_box = TextInput(hint_text='Search YouTube', multiline=False); r.add_widget(self.search_box)
        b = Button(text='Search', size_hint_x=None, width=dp(90)); b.bind(on_release=lambda *_: self.search())
        r.add_widget(b)
        t = Button(text='Trending', size_hint_x=None, width=dp(100)); t.bind(on_release=lambda *_: self.search('trending videos'))
        r.add_widget(t); root.add_widget(r)

        self.results = ScrollView(); self.result_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        self.result_box.bind(minimum_height=self.result_box.setter('height')); self.results.add_widget(self.result_box); root.add_widget(self.results)
        root.add_widget(Label(text='Download Manager', size_hint_y=None, height=dp(32)))
        self.downloads = ScrollView(size_hint_y=.55); self.dl_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        self.dl_box.bind(minimum_height=self.dl_box.setter('height')); self.downloads.add_widget(self.dl_box); root.add_widget(self.downloads)
        for _ in range(3): threading.Thread(target=self.worker, daemon=True).start()
        return root

    def search(self, forced=None):
        q = forced or self.search_box.text.strip()
        if q: threading.Thread(target=self.search_worker, args=(q,), daemon=True).start()

    def search_worker(self, q):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'noplaylist': True}) as ydl:
                info = ydl.extract_info('ytsearch15:' + q, download=False)
            Clock.schedule_once(lambda *_: self.result_box.clear_widgets())
            for x in info.get('entries', []):
                if not x: continue
                Clock.schedule_once(lambda _, x=x: self.add_result(x))
        except Exception as e: Clock.schedule_once(lambda *_: self.error(str(e)))

    def add_result(self, x):
        title=x.get('title','Untitled'); url=x.get('webpage_url') or x.get('url','')
        row=BoxLayout(orientation='vertical', size_hint_y=None, height=dp(105), spacing=dp(3))
        row.add_widget(Label(text=f"{title}\n{x.get('channel') or x.get('uploader') or ''} • {duration(x.get('duration'))}", halign='left'))
        b=Button(text='Download', size_hint_y=None, height=dp(42)); b.bind(on_release=lambda *_: self.queue_download(url,title)); row.add_widget(b)
        self.result_box.add_widget(row)

    def add_download(self):
        u=self.url.text.strip()
        if u: self.queue_download(u,u)

    def queue_download(self,url,title):
        row=DownloadRow(title); self.dl_box.add_widget(row); self.q.put((url,row))

    def worker(self):
        while True:
            url,row=self.q.get()
            try:
                opts={'format':'bestvideo+bestaudio/best','merge_output_format':'mp4','outtmpl':os.path.join(DOWNLOAD_DIR,'%(title)s.%(ext)s'),'continuedl':True,'concurrent_fragment_downloads':8,'progress_hooks':[lambda d,r=row:self.progress(d,r)],'quiet':True,'noplaylist':True}
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
                Clock.schedule_once(lambda _,r=row:setattr(r.details,'text','Completed — saved in Downloads/YouTubeDownloader'))
            except Exception as e: Clock.schedule_once(lambda _,r=row,e=str(e):setattr(r.details,'text','Error: '+e))
            self.q.task_done()

    def progress(self,d,row):
        if d.get('status')=='downloading':
            total=d.get('total_bytes') or d.get('total_bytes_estimate') or 0; done=d.get('downloaded_bytes') or 0
            p=done/total if total else 0; txt=f"{p*100:.1f}%  Speed: {d.get('_speed_str','?')}  ETA: {d.get('_eta_str','?')}"
            Clock.schedule_once(lambda _,r=row,p=p,t=txt:(setattr(r.progress,'value',p),setattr(r.details,'text',t)))

    def error(self,msg): Popup(title='Error',content=Label(text=msg),size_hint=(.9,.35)).open()


if __name__ == '__main__': AppMain().run()
