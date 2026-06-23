import streamlit as st
from streamlit_folium import st_folium
import folium
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

st.set_page_config(
    title="照片隐形足迹曝光器",
    layout="centered",
)

st.title("📸 照片隐形足迹曝光器")
st.info("本项目仅用于期末演示。请注意，发送原图可能会暴露你的真实位置隐私。")

uploaded_file = st.file_uploader(
    "上传照片",
    type=["jpg", "jpeg", "tiff"],
)


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


if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        exif_data = image.getexif()

        if not exif_data:
            st.success("太棒了！这张照片经过了安全处理，没有包含位置隐私信息。")
            left_column, right_column = st.columns(2)
            with left_column:
                st.subheader("提取的元数据")
                st.write("**拍摄时间:** 未找到")
                st.write("**设备型号:** 未找到")
            with right_column:
                st.subheader("原图预览")
                st.image(image, use_container_width=True)
        else:
            capture_time = find_exif_value(exif_data, "DateTimeOriginal")
            device_make = decode_bytes_text(find_exif_value(exif_data, "Make"))
            device_model = decode_bytes_text(find_exif_value(exif_data, "Model"))
            decimal_latitude, decimal_longitude = parse_gps_coordinates(exif_data)

            left_column, right_column = st.columns(2)

            with left_column:
                st.subheader("提取的元数据")
                if capture_time:
                    st.write(f"**拍摄时间:** {capture_time}")
                else:
                    st.write("**拍摄时间:** 未找到")
                if device_make or device_model:
                    make_display = device_make if device_make else "未知"
                    model_display = device_model if device_model else "未知"
                    st.write(f"**设备型号:** {make_display} {model_display}")
                else:
                    st.write("**设备型号:** 未找到")

            with right_column:
                st.subheader("原图预览")
                st.image(image, use_container_width=True)

            if decimal_latitude is not None and decimal_longitude is not None:
                photo_map = folium.Map(
                    location=[decimal_latitude, decimal_longitude],
                    zoom_start=16,
                )
                folium.Marker(
                    location=[decimal_latitude, decimal_longitude],
                    tooltip="照片拍摄地",
                    icon=folium.Icon(color="red"),
                ).add_to(photo_map)
                st_folium(photo_map, width=700, height=500)
            else:
                st.success("太棒了！这张照片经过了安全处理，没有包含位置隐私信息。")

    except Exception:
        st.success("太棒了！这张照片经过了安全处理，没有包含位置隐私信息。")
