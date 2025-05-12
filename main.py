
import tkinter as tk
from tkinter import filedialog, Button, Frame
from PIL import Image, ImageTk
import cv2

class ObjectTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Object Tracker v4")

        self.cap = None
        self.frame = None
        self.bboxes = []
        self.tracker_type = cv2.legacy.TrackerCSRT_create
        self.trackers = None
        self.is_tracking = False
        self.is_paused = True

        self.canvas = tk.Canvas(root, width=640, height=480)
        self.canvas.pack()
        self.canvas_image_id = None

        controls = Frame(root)
        controls.pack(pady=10)
        Button(controls, text="Upload Video", command=self.load_video).pack(side="left", padx=5)
        Button(controls, text="Play / Pause", command=self.toggle_play).pack(side="left", padx=5)
        Button(controls, text="Clear Last", command=self.remove_last_box).pack(side="left", padx=5)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.start_x = self.start_y = 0
        self.cur_rect_id = None
        self.drawing = False

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        if not path:
            return
        self.cap = cv2.VideoCapture(path)
        self.bboxes.clear()
        self.is_tracking = False
        self.is_paused = True
        self.trackers = None
        ret, frame = self.cap.read()
        if ret:
            self.frame = frame
            self._show_frame(frame)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.root.after(30, self.update_frame)

    def toggle_play(self):
        if not self.cap or self.frame is None:
            return
        if not self.is_tracking and self.bboxes:
            self.trackers = cv2.legacy.MultiTracker_create()
            for box in self.bboxes:
                self.trackers.add(self.tracker_type(), self.frame, box)
            self.is_tracking = True
        self.is_paused = not self.is_paused

    def remove_last_box(self):
        if self.bboxes:
            self.bboxes.pop()
        if self.is_tracking:
            self.rebuild_trackers()

    def on_mouse_down(self, event):
        if not self.is_paused or self.is_tracking or self.frame is None:
            return
        self.drawing = True
        self.start_x, self.start_y = event.x, event.y
        self.cur_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red")

    def on_mouse_drag(self, event):
        if self.drawing and self.cur_rect_id:
            self.canvas.coords(self.cur_rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        if self.drawing and self.cur_rect_id and self.frame is not None:
            coords = self.canvas.coords(self.cur_rect_id)
            if len(coords) == 4:
                x0, y0, x1, y1 = coords
                x, y = int(min(x0, x1)), int(min(y0, y1))
                w, h = int(abs(x1 - x0)), int(abs(y1 - y0))
                if w > 10 and h > 10:
                    fx = self.frame.shape[1] / self.canvas.winfo_width()
                    fy = self.frame.shape[0] / self.canvas.winfo_height()
                    box = (x * fx, y * fy, w * fx, h * fy)
                    self.bboxes.append(box)
            self.canvas.delete(self.cur_rect_id)
        self.drawing = False
        self.cur_rect_id = None

    def on_right_click(self, event):
        if not self.is_tracking:
            return
        click_x = event.x * self.frame.shape[1] / self.canvas.winfo_width()
        click_y = event.y * self.frame.shape[0] / self.canvas.winfo_height()
        new_boxes = []
        for box in self.bboxes:
            x, y, w, h = box
            if not (x <= click_x <= x + w and y <= click_y <= y + h):
                new_boxes.append(box)
        self.bboxes = new_boxes
        self.rebuild_trackers()

    def rebuild_trackers(self):
        if self.frame is None:
            return
        self.trackers = cv2.legacy.MultiTracker_create()
        for box in self.bboxes:
            self.trackers.add(self.tracker_type(), self.frame, box)
        if len(self.bboxes) == 0:
            self.is_tracking = False
            self.is_paused = True

    def _show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((640, 480))
        self.tkimg = ImageTk.PhotoImage(img)
        if self.canvas_image_id is None:
            self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg)
        else:
            self.canvas.itemconfig(self.canvas_image_id, image=self.tkimg)

    def update_frame(self):
        if self.cap and not self.is_paused:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.is_paused = True
        if self.frame is not None:
            display = self.frame.copy()
            if self.is_tracking and self.trackers:
                ok, boxes = self.trackers.update(self.frame)
                for b in boxes:
                    x, y, w, h = map(int, b)
                    cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            self._show_frame(display)
        self.root.after(30, self.update_frame)

if __name__ == "__main__":
    root = tk.Tk()
    app = ObjectTrackerGUI(root)
    root.mainloop()
