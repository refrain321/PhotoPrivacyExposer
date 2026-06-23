import io
import concurrent.futures
import math
import threading
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk
from PIL.ExifTags import GPSTAGS, TAGS


TILE_SERVERS = [
    "http://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "http://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    "http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}",
]


def rational_to_float(value):
    if isinstance(value, tuple):
        if len(value) == 2:
            return rational_to_float(value[0]) / rational_to_float(value[1])
        return rational_to_float(value[0])
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        if value.denominator == 0:
            return 0.0
        return float(value.numerator) / float(value.denominator)
    return float(value)


def dms_to_decimal(dms_values):
    degrees = rational_to_float(dms_values[0])
    minutes = rational_to_float(dms_values[1])
    seconds = rational_to_float(dms_values[2])
    return degrees + (minutes / 60.0) + (seconds / 3600.0)


def decode_bytes_text(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    return str(value).strip()


def find_exif_value(exif_data, tag_name):
    for tag_id, value in exif_data.items():
        if TAGS.get(tag_id) == tag_name:
            return value
    try:
        exif_sub_ifd = exif_data.get_ifd(0x8769)
        for tag_id, value in exif_sub_ifd.items():
            if TAGS.get(tag_id) == tag_name:
                return value
    except KeyError:
        pass
    return None


def parse_gps_coordinates(exif_data):
    gps_info_tag = 34853
    try:
        gps_ifd = exif_data.get_ifd(gps_info_tag)
    except KeyError:
        return None, None

    if not gps_ifd:
        return None, None

    decoded_gps = {}
    for gps_tag_id, gps_value in gps_ifd.items():
        gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
        decoded_gps[gps_tag_name] = gps_value

    if "GPSLatitude" not in decoded_gps or "GPSLongitude" not in decoded_gps:
        return None, None

    decimal_latitude = dms_to_decimal(decoded_gps["GPSLatitude"])
    decimal_longitude = dms_to_decimal(decoded_gps["GPSLongitude"])

    latitude_ref = decode_bytes_text(decoded_gps.get("GPSLatitudeRef", "N"))
    longitude_ref = decode_bytes_text(decoded_gps.get("GPSLongitudeRef", "E"))

    if latitude_ref and latitude_ref.upper() == "S":
        decimal_latitude *= -1
    if longitude_ref and longitude_ref.upper() == "W":
        decimal_longitude *= -1

    return decimal_latitude, decimal_longitude


class PhotoPrivacyApp:
    def __init__(self, root_window):
        self.root_window = root_window
        self.root_window.title("照片隐形足迹曝光器")
        self.root_window.geometry("960x820")
        self.root_window.minsize(860, 720)

        self.preview_photo = None
        self.map_photo = None
        self.map_zoom = 16
        self.current_coordinates = None
        self.latest_google_maps_url = None
        self.latest_openstreetmap_url = None
        self.map_render_generation = 0

        self.build_interface()

    def build_interface(self):
        header_frame = ttk.Frame(self.root_window, padding=(16, 12))
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text="📸 照片隐形足迹曝光器",
            font=("Microsoft YaHei UI", 18, "bold"),
        )
        title_label.pack(anchor=tk.W)

        warning_label = ttk.Label(
            header_frame,
            text="本项目仅用于期末演示。请注意，发送原图可能会暴露你的真实位置隐私。",
            wraplength=900,
            foreground="#1f4e79",
        )
        warning_label.pack(anchor=tk.W, pady=(8, 0))

        control_frame = ttk.Frame(self.root_window, padding=(16, 0))
        control_frame.pack(fill=tk.X)

        select_button = ttk.Button(
            control_frame,
            text="选择照片",
            command=self.open_photo_dialog,
        )
        select_button.pack(anchor=tk.W)

        content_frame = ttk.Frame(self.root_window, padding=16)
        content_frame.pack(fill=tk.BOTH, expand=True)

        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        metadata_panel = ttk.LabelFrame(content_frame, text="提取的元数据", padding=12)
        metadata_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.metadata_text = tk.Text(
            metadata_panel,
            height=12,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 11),
            state=tk.DISABLED,
            relief=tk.FLAT,
            background=self.root_window.cget("bg"),
        )
        self.metadata_text.pack(fill=tk.BOTH, expand=True)

        preview_panel = ttk.LabelFrame(content_frame, text="原图预览", padding=12)
        preview_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.preview_label = ttk.Label(preview_panel, anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        map_panel = ttk.LabelFrame(self.root_window, text="拍摄位置地图", padding=12)
        map_panel.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        map_control_frame = ttk.Frame(map_panel)
        map_control_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(map_control_frame, text="+", width=4, command=self.zoom_in_map).pack(side=tk.LEFT)
        ttk.Button(map_control_frame, text="-", width=4, command=self.zoom_out_map).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            map_control_frame,
            text="打开 Google 地图",
            command=self.open_google_maps,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(
            map_control_frame,
            text="打开 OpenStreetMap",
            command=self.open_openstreetmap,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.map_status_label = ttk.Label(map_control_frame, text="等待照片 GPS 数据")
        self.map_status_label.pack(side=tk.LEFT, padx=(12, 0))

        self.map_canvas = tk.Canvas(
            map_panel,
            width=900,
            height=420,
            background="#f3f1ec",
            highlightthickness=0,
        )
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.map_canvas.create_text(
            450,
            210,
            text="选择含 GPS 信息的照片后显示地图",
            fill="#666666",
            font=("Microsoft YaHei UI", 13),
        )

        self.set_metadata_text("请选择一张 JPG / JPEG / TIFF 照片开始分析。")

    def set_metadata_text(self, content):
        self.metadata_text.configure(state=tk.NORMAL)
        self.metadata_text.delete("1.0", tk.END)
        self.metadata_text.insert(tk.END, content)
        self.metadata_text.configure(state=tk.DISABLED)

    def show_privacy_safe_message(self):
        messagebox.showinfo(
            "隐私安全",
            "太棒了！这张照片经过了安全处理，没有包含位置隐私信息。",
        )

    def clear_map_markers(self):
        self.current_coordinates = None
        self.latest_google_maps_url = None
        self.latest_openstreetmap_url = None
        self.map_status_label.configure(text="未检测到 GPS 位置")
        self.map_canvas.delete("all")
        self.map_canvas.create_text(
            450,
            210,
            text="这张照片没有可显示的 GPS 地图信息",
            fill="#666666",
            font=("Microsoft YaHei UI", 13),
        )

    def update_map(self, decimal_latitude, decimal_longitude):
        self.current_coordinates = (decimal_latitude, decimal_longitude)
        self.latest_google_maps_url = (
            f"https://www.google.com/maps?q={decimal_latitude:.8f},{decimal_longitude:.8f}&z=16"
        )
        self.latest_openstreetmap_url = (
            f"https://www.openstreetmap.org/?mlat={decimal_latitude:.8f}"
            f"&mlon={decimal_longitude:.8f}#map=16/{decimal_latitude:.8f}/{decimal_longitude:.8f}"
        )
        self.render_map(decimal_latitude, decimal_longitude)

    def open_google_maps(self):
        if self.latest_google_maps_url:
            webbrowser.open(self.latest_google_maps_url)

    def open_openstreetmap(self):
        if self.latest_openstreetmap_url:
            webbrowser.open(self.latest_openstreetmap_url)

    def zoom_in_map(self):
        if self.current_coordinates and self.map_zoom < 18:
            self.map_zoom += 1
            self.render_map(*self.current_coordinates)

    def zoom_out_map(self):
        if self.current_coordinates and self.map_zoom > 3:
            self.map_zoom -= 1
            self.render_map(*self.current_coordinates)

    def coordinate_to_pixel(self, decimal_latitude, decimal_longitude, zoom_level):
        sin_latitude = math.sin(math.radians(decimal_latitude))
        tile_count = 2 ** zoom_level
        pixel_x = ((decimal_longitude + 180.0) / 360.0) * tile_count * 256
        pixel_y = (
            0.5
            - math.log((1 + sin_latitude) / (1 - sin_latitude)) / (4 * math.pi)
        ) * tile_count * 256
        return pixel_x, pixel_y

    def download_tile_image(self, tile_x, tile_y, zoom_level):
        tile_count = 2 ** zoom_level
        normalized_x = tile_x % tile_count
        if tile_y < 0 or tile_y >= tile_count:
            return None

        for tile_server in TILE_SERVERS:
            tile_url = (
                tile_server
                .replace("{x}", str(normalized_x))
                .replace("{y}", str(tile_y))
                .replace("{z}", str(zoom_level))
            )
            try:
                request = urllib.request.Request(
                    tile_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    tile_bytes = response.read()
                return Image.open(io.BytesIO(tile_bytes)).convert("RGB")
            except Exception:
                continue
        return None

    def render_map(self, decimal_latitude, decimal_longitude):
        map_width = max(self.map_canvas.winfo_width(), 900)
        map_height = max(self.map_canvas.winfo_height(), 420)
        zoom_level = self.map_zoom
        self.map_render_generation += 1
        render_generation = self.map_render_generation

        self.map_canvas.delete("all")
        self.map_canvas.create_text(
            map_width // 2,
            map_height // 2,
            text="地图正在后台加载，请稍候...",
            fill="#1f4e79",
            font=("Microsoft YaHei UI", 13),
        )
        self.map_status_label.configure(
            text=f"纬度 {decimal_latitude:.6f}，经度 {decimal_longitude:.6f}，地图加载中"
        )

        render_thread = threading.Thread(
            target=self.render_map_in_background,
            args=(
                decimal_latitude,
                decimal_longitude,
                zoom_level,
                map_width,
                map_height,
                render_generation,
            ),
            daemon=True,
        )
        render_thread.start()

    def render_map_in_background(
        self,
        decimal_latitude,
        decimal_longitude,
        zoom_level,
        map_width,
        map_height,
        render_generation,
    ):
        center_pixel_x, center_pixel_y = self.coordinate_to_pixel(
            decimal_latitude,
            decimal_longitude,
            zoom_level,
        )
        left_pixel = center_pixel_x - map_width / 2
        top_pixel = center_pixel_y - map_height / 2
        start_tile_x = math.floor(left_pixel / 256)
        start_tile_y = math.floor(top_pixel / 256)
        end_tile_x = math.floor((left_pixel + map_width) / 256)
        end_tile_y = math.floor((top_pixel + map_height) / 256)
        map_image = Image.new("RGB", (map_width, map_height), "#f3f1ec")
        loaded_tiles = 0

        tile_positions = [
            (tile_x, tile_y)
            for tile_x in range(start_tile_x, end_tile_x + 1)
            for tile_y in range(start_tile_y, end_tile_y + 1)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_position = {
                executor.submit(
                    self.download_tile_image,
                    tile_x,
                    tile_y,
                    zoom_level,
                ): (tile_x, tile_y)
                for tile_x, tile_y in tile_positions
            }
            for future in concurrent.futures.as_completed(future_to_position):
                tile_x, tile_y = future_to_position[future]
                try:
                    tile_image = future.result()
                except Exception:
                    tile_image = None
                if tile_image is None:
                    continue
                paste_x = int(tile_x * 256 - left_pixel)
                paste_y = int(tile_y * 256 - top_pixel)
                map_image.paste(tile_image.resize((256, 256)), (paste_x, paste_y))
                loaded_tiles += 1

        draw = ImageDraw.Draw(map_image)
        marker_x = map_width // 2
        marker_y = map_height // 2
        draw.ellipse(
            (marker_x - 13, marker_y - 13, marker_x + 13, marker_y + 13),
            fill="#d94b35",
            outline="#9c2f21",
            width=4,
        )
        draw.polygon(
            [
                (marker_x - 10, marker_y + 8),
                (marker_x + 10, marker_y + 8),
                (marker_x, marker_y + 36),
            ],
            fill="#d94b35",
            outline="#9c2f21",
        )
        draw.text((marker_x + 20, marker_y - 22), "照片拍摄地", fill="#8a2c20")

        self.root_window.after(
            0,
            lambda: self.apply_rendered_map(
                map_image,
                loaded_tiles,
                marker_x,
                marker_y,
                decimal_latitude,
                decimal_longitude,
                render_generation,
            ),
        )

    def apply_rendered_map(
        self,
        map_image,
        loaded_tiles,
        marker_x,
        marker_y,
        decimal_latitude,
        decimal_longitude,
        render_generation,
    ):
        if render_generation != self.map_render_generation:
            return

        self.map_photo = ImageTk.PhotoImage(map_image)
        self.map_canvas.delete("all")
        self.map_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
        if loaded_tiles == 0:
            self.map_canvas.create_text(
                marker_x,
                marker_y + 72,
                text="内嵌地图底图加载失败，但 GPS 坐标已解析；可点击上方按钮打开 Google 地图",
                fill="#8a2c20",
                font=("Microsoft YaHei UI", 12),
            )
        self.map_status_label.configure(
            text=f"纬度 {decimal_latitude:.6f}，经度 {decimal_longitude:.6f}"
        )

    def render_preview(self, image):
        preview_image = image.copy()
        preview_image.thumbnail((360, 360), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview_image)
        self.preview_label.configure(image=self.preview_photo, text="")

    def build_metadata_lines(self, capture_time, device_make, device_model, decimal_latitude=None, decimal_longitude=None):
        lines = []
        if capture_time:
            lines.append(f"拍摄时间: {capture_time}")
        else:
            lines.append("拍摄时间: 未找到")

        if device_make or device_model:
            make_display = device_make if device_make else "未知"
            model_display = device_model if device_model else "未知"
            lines.append(f"设备型号: {make_display} {model_display}")
        else:
            lines.append("设备型号: 未找到")

        if decimal_latitude is not None and decimal_longitude is not None:
            lines.append(f"纬度: {decimal_latitude:.6f}")
            lines.append(f"经度: {decimal_longitude:.6f}")

        return "\n".join(lines)

    def process_photo(self, file_path):
        try:
            image = Image.open(file_path)
            self.render_preview(image)

            exif_data = image.getexif()
            if not exif_data:
                self.set_metadata_text(
                    "拍摄时间: 未找到\n设备型号: 未找到"
                )
                self.clear_map_markers()
                self.show_privacy_safe_message()
                return

            capture_time = find_exif_value(exif_data, "DateTimeOriginal")
            device_make = decode_bytes_text(find_exif_value(exif_data, "Make"))
            device_model = decode_bytes_text(find_exif_value(exif_data, "Model"))
            decimal_latitude, decimal_longitude = parse_gps_coordinates(exif_data)

            self.set_metadata_text(
                self.build_metadata_lines(
                    capture_time,
                    device_make,
                    device_model,
                    decimal_latitude,
                    decimal_longitude,
                )
            )

            if decimal_latitude is not None and decimal_longitude is not None:
                self.update_map(decimal_latitude, decimal_longitude)
            else:
                self.clear_map_markers()
                self.show_privacy_safe_message()

        except Exception:
            self.set_metadata_text("无法读取这张照片的元数据。")
            self.preview_label.configure(image="", text="无法预览")
            self.preview_photo = None
            self.clear_map_markers()
            self.show_privacy_safe_message()

    def open_photo_dialog(self):
        file_path = filedialog.askopenfilename(
            title="选择照片",
            filetypes=[
                ("照片文件", "*.jpg *.jpeg *.tiff *.tif"),
                ("JPEG", "*.jpg *.jpeg"),
                ("TIFF", "*.tiff *.tif"),
            ],
        )
        if file_path:
            self.process_photo(file_path)


def main():
    root_window = tk.Tk()
    try:
        root_window.iconbitmap(default="")
    except tk.TclError:
        pass
    PhotoPrivacyApp(root_window)
    root_window.mainloop()


if __name__ == "__main__":
    main()
