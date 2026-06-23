import base64
import io
import webbrowser

import webview
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS


HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>照片隐形足迹曝光器</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
      background: #f5f7fb;
      color: #172033;
    }
    .app {
      width: 100%;
      min-height: 100vh;
      padding: 22px;
    }
    .header {
      margin-bottom: 16px;
    }
    h1 {
      margin: 0 0 10px 0;
      font-size: 30px;
      line-height: 1.2;
    }
    .notice {
      padding: 12px 14px;
      border-radius: 10px;
      background: #e8f3ff;
      color: #174a7c;
      border: 1px solid #c8def5;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 18px 0;
    }
    button {
      border: 0;
      border-radius: 10px;
      padding: 10px 16px;
      background: #1769e0;
      color: #fff;
      font-size: 15px;
      cursor: pointer;
      transition: transform .12s ease, opacity .12s ease;
    }
    button:hover {
      transform: translateY(-1px);
      opacity: .92;
    }
    button.secondary {
      background: #2f3a4a;
    }
    button:disabled {
      background: #9aa7b8;
      cursor: not-allowed;
      transform: none;
    }
    .status {
      color: #536171;
      font-size: 14px;
    }
    .top-grid {
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .card {
      background: #fff;
      border: 1px solid #dde5ef;
      border-radius: 14px;
      box-shadow: 0 10px 28px rgba(19, 38, 66, .06);
      overflow: hidden;
    }
    .card-title {
      padding: 12px 14px;
      border-bottom: 1px solid #e7edf5;
      font-weight: 700;
      background: #fbfcff;
    }
    .metadata {
      padding: 18px;
      min-height: 230px;
      font-size: 18px;
      line-height: 1.9;
      white-space: pre-line;
    }
    .preview-wrap {
      padding: 14px;
      min-height: 230px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #fafafa;
    }
    .preview-wrap img {
      max-width: 100%;
      max-height: 280px;
      border-radius: 8px;
      box-shadow: 0 8px 22px rgba(0,0,0,.10);
    }
    .empty {
      color: #7b8794;
    }
    #map {
      width: 100%;
      height: 500px;
      background: #eef1f4;
    }
    .map-note {
      padding: 10px 14px;
      color: #536171;
      font-size: 14px;
      border-top: 1px solid #e7edf5;
    }
  </style>
</head>
<body>
  <main class="app">
    <section class="header">
      <h1>📸 照片隐形足迹曝光器</h1>
      <div class="notice">本项目仅用于期末演示。请注意，发送原图可能会暴露你的真实位置隐私。</div>
    </section>

    <section class="toolbar">
      <button id="selectButton">选择照片</button>
      <button id="googleButton" class="secondary" disabled>打开 Google 地图</button>
      <button id="osmButton" class="secondary" disabled>打开 OpenStreetMap</button>
      <span id="status" class="status">请选择 JPG / JPEG / TIFF 原图开始分析</span>
    </section>

    <section class="top-grid">
      <div class="card">
        <div class="card-title">提取的元数据</div>
        <div id="metadata" class="metadata empty">尚未选择照片。</div>
      </div>
      <div class="card">
        <div class="card-title">原图预览</div>
        <div class="preview-wrap">
          <span id="previewEmpty" class="empty">照片预览区</span>
          <img id="previewImage" alt="原图预览" style="display:none" />
        </div>
      </div>
    </section>

    <section class="card">
      <div class="card-title">拍摄位置地图</div>
      <div id="map"></div>
      <div class="map-note">地图支持鼠标拖动、滚轮缩放、双击缩放；若底图未加载，请切换网络或点击上方外部地图按钮。</div>
    </section>
  </main>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    let map = null;
    let marker = null;
    let googleUrl = null;
    let osmUrl = null;

    function ensureMap() {
      if (map) return map;
      map = L.map("map", {
        zoomControl: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        dragging: true
      }).setView([35.0, 105.0], 3);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors"
      }).addTo(map);
      setTimeout(() => map.invalidateSize(), 200);
      return map;
    }

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function setMetadata(text, isEmpty=false) {
      const el = document.getElementById("metadata");
      el.textContent = text;
      el.classList.toggle("empty", isEmpty);
    }

    function updatePreview(dataUrl) {
      const img = document.getElementById("previewImage");
      const empty = document.getElementById("previewEmpty");
      if (dataUrl) {
        img.src = dataUrl;
        img.style.display = "block";
        empty.style.display = "none";
      } else {
        img.style.display = "none";
        empty.style.display = "inline";
      }
    }

    function updateMap(latitude, longitude) {
      const currentMap = ensureMap();
      currentMap.setView([latitude, longitude], 16, { animate: true });
      if (marker) marker.remove();
      marker = L.marker([latitude, longitude]).addTo(currentMap).bindTooltip("照片拍摄地", { permanent: false });
      marker.openTooltip();
      setTimeout(() => currentMap.invalidateSize(), 200);
    }

    async function selectPhoto() {
      const button = document.getElementById("selectButton");
      button.disabled = true;
      setStatus("正在分析照片...");
      try {
        const result = await window.pywebview.api.select_photo();
        if (!result || result.cancelled) {
          setStatus("已取消选择");
          return;
        }
        if (!result.ok) {
          setStatus(result.message || "照片分析失败");
          setMetadata(result.message || "无法读取这张照片。", true);
          updatePreview(null);
          return;
        }
        updatePreview(result.preview_data_url);
        setMetadata(result.metadata_text);
        googleUrl = result.google_url;
        osmUrl = result.osm_url;
        document.getElementById("googleButton").disabled = !googleUrl;
        document.getElementById("osmButton").disabled = !osmUrl;
        if (result.has_gps) {
          updateMap(result.latitude, result.longitude);
          setStatus("分析完成：GPS 位置已显示，可拖动地图查看周边。");
        } else {
          ensureMap();
          setStatus("太棒了！这张照片经过了安全处理，没有包含位置隐私信息。");
        }
      } finally {
        button.disabled = false;
      }
    }

    document.getElementById("selectButton").addEventListener("click", selectPhoto);
    document.getElementById("googleButton").addEventListener("click", () => {
      if (googleUrl) window.pywebview.api.open_url(googleUrl);
    });
    document.getElementById("osmButton").addEventListener("click", () => {
      if (osmUrl) window.pywebview.api.open_url(osmUrl);
    });

    window.addEventListener("pywebviewready", () => {
      ensureMap();
    });
  </script>
</body>
</html>
"""


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


def create_preview_data_url(image):
    preview_image = image.copy()
    preview_image.thumbnail((520, 360), Image.Resampling.LANCZOS)
    if preview_image.mode not in ("RGB", "L"):
        preview_image = preview_image.convert("RGB")
    buffer = io.BytesIO()
    preview_image.save(buffer, format="JPEG", quality=88)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


class AppApi:
    def select_photo(self):
        paths = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("照片文件 (*.jpg;*.jpeg;*.tiff;*.tif)",),
        )
        if not paths:
            return {"cancelled": True}
        file_path = paths[0]
        try:
            image = Image.open(file_path)
            preview_data_url = create_preview_data_url(image)
            exif_data = image.getexif()
            capture_time = None
            device_make = None
            device_model = None
            decimal_latitude = None
            decimal_longitude = None
            if exif_data:
                capture_time = find_exif_value(exif_data, "DateTimeOriginal")
                device_make = decode_bytes_text(find_exif_value(exif_data, "Make"))
                device_model = decode_bytes_text(find_exif_value(exif_data, "Model"))
                decimal_latitude, decimal_longitude = parse_gps_coordinates(exif_data)
            lines = []
            lines.append(f"拍摄时间: {capture_time if capture_time else '未找到'}")
            if device_make or device_model:
                lines.append(f"设备型号: {device_make if device_make else '未知'} {device_model if device_model else '未知'}")
            else:
                lines.append("设备型号: 未找到")
            has_gps = decimal_latitude is not None and decimal_longitude is not None
            google_url = None
            osm_url = None
            if has_gps:
                lines.append(f"纬度: {decimal_latitude:.6f}")
                lines.append(f"经度: {decimal_longitude:.6f}")
                google_url = f"https://www.google.com/maps?q={decimal_latitude:.8f},{decimal_longitude:.8f}&z=16"
                osm_url = (
                    f"https://www.openstreetmap.org/?mlat={decimal_latitude:.8f}"
                    f"&mlon={decimal_longitude:.8f}#map=16/{decimal_latitude:.8f}/{decimal_longitude:.8f}"
                )
            else:
                lines.append("位置隐私: 未发现 GPS 信息")
            return {
                "ok": True,
                "preview_data_url": preview_data_url,
                "metadata_text": "\n".join(lines),
                "has_gps": has_gps,
                "latitude": decimal_latitude,
                "longitude": decimal_longitude,
                "google_url": google_url,
                "osm_url": osm_url,
            }
        except Exception as exc:
            return {"ok": False, "message": f"无法读取这张照片: {exc}"}

    def open_url(self, url):
        webbrowser.open(url)
        return True


def main():
    api = AppApi()
    webview.create_window(
        "照片隐形足迹曝光器",
        html=HTML,
        js_api=api,
        width=1120,
        height=900,
        min_size=(920, 720),
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
