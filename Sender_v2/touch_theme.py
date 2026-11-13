"""Native X11 rounded windows and a locally captured, blurred modal backdrop."""
import ctypes
import os

def rounded_window(window,radius=22):
    """Apply a true rounded bounding shape to the Tk/XWayland popup."""
    try:
        window.update_idletasks()
        width,height=window.winfo_width(),window.winfo_height()
        if width<2 or height<2:return
        x=ctypes.CDLL('libX11.so.6');shape=ctypes.CDLL('libXext.so.6')
        x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
        x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
        class Rect(ctypes.Structure):
            _fields_=[('x',ctypes.c_short),('y',ctypes.c_short),('width',ctypes.c_ushort),('height',ctypes.c_ushort)]
        shape.XShapeCombineRectangles.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_int,
                                              ctypes.POINTER(Rect),ctypes.c_int,ctypes.c_int,ctypes.c_int]
        x.XQueryTree.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong),
                              ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),ctypes.POINTER(ctypes.c_uint)]
        x.XFree.argtypes=[ctypes.c_void_p]
        import math
        r=min(radius,width/2,height/2)
        rectangles=[]
        for y in range(height):
            dy=max(0,r-y-.5,y+.5-(height-r))
            inset=math.ceil(r-math.sqrt(max(0,r*r-dy*dy))) if dy else 0
            rectangles.append(Rect(inset,y,width-2*inset,1))
        rects=(Rect*len(rectangles))(*rectangles)
        display=x.XOpenDisplay(os.environ.get('DISPLAY',':0').encode())
        if not display:return
        try:
            root,parent=ctypes.c_ulong(),ctypes.c_ulong()
            children=ctypes.POINTER(ctypes.c_ulong)();count=ctypes.c_uint()
            widget=window.winfo_id()
            x.XQueryTree(display,widget,ctypes.byref(root),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(count))
            if children:x.XFree(children)
            for native in (widget,parent.value):
                if native:shape.XShapeCombineRectangles(display,native,0,0,0,rects,len(rectangles),0,0)
            x.XFlush(display)
        finally:x.XCloseDisplay(display)
    except (OSError,AttributeError):
        pass

def backdrop(root,popup_size):
    """Blur only the sender's own window; never save the captured pixels to disk."""
    import tkinter as tk
    overlay=tk.Label(root,bg='#050a12',bd=0,highlightthickness=0)
    try:
        from PIL import Image,ImageDraw,ImageFilter,ImageGrab,ImageTk
        root.update_idletasks()
        width,height=root.winfo_width(),root.winfo_height()
        x,y=root.winfo_rootx(),root.winfo_rooty()
        import io,subprocess
        # Wayfire presents XWayland clients outside the X11 root framebuffer.
        # Capture the actual Wayland output in memory for the blurred backdrop.
        try:
            capture=subprocess.run(['grim','-'],capture_output=True,check=True,timeout=2)
            pixels=Image.open(io.BytesIO(capture.stdout)).convert('RGBA').crop((x,y,x+width,y+height))
        except (OSError,subprocess.SubprocessError):
            pixels=ImageGrab.grab(bbox=(x,y,x+width,y+height),xdisplay=os.environ.get('DISPLAY',':0')).convert('RGBA')
        pixels=pixels.filter(ImageFilter.GaussianBlur(9))
        pixels=Image.alpha_composite(pixels,Image.new('RGBA',pixels.size,(4,9,17,115)))
        shadow=Image.new('RGBA',pixels.size,(0,0,0,0))
        pw,ph=popup_size;px,py=(width-pw)//2,(height-ph)//2
        ImageDraw.Draw(shadow).rounded_rectangle((px-5,py+5,px+pw+5,py+ph+12),radius=28,fill=(0,0,0,190))
        pixels=Image.alpha_composite(pixels,shadow.filter(ImageFilter.GaussianBlur(15)))
        overlay.pixels=pixels
        overlay.image=ImageTk.PhotoImage(pixels,master=root)
        overlay.configure(image=overlay.image)
    except (ImportError,OSError):
        pass
    overlay.place(x=0,y=0,relwidth=1,relheight=1)
    overlay.lift()
    return overlay

def popup_surface(popup,overlay,size,color='#142136'):
    """Paint matching backdrop pixels at corners even if the compositor ignores XShape."""
    import tkinter as tk
    from PIL import Image,ImageDraw,ImageTk
    width,height=size
    background=getattr(overlay,'pixels',None)
    if background is None:
        background=Image.new('RGBA',(width,height),'#050a12')
    else:
        x,y=(background.width-width)//2,(background.height-height)//2
        background=background.crop((x,y,x+width,y+height))
    ImageDraw.Draw(background).rounded_rectangle((0,0,width-1,height-1),radius=28,fill=color)
    popup._rounded_surface=ImageTk.PhotoImage(background,master=popup)
    label=tk.Label(popup,image=popup._rounded_surface,bd=0,highlightthickness=0)
    label.place(x=0,y=0,width=width,height=height)
    label.lower()
