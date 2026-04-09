"""Görsel Sıkıştırma & Supabase Yükleme Web Uygulaması."""

import io
import os
import uuid
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file

from compressor import compress_image

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB toplam limit

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/compress", methods=["POST"])
def compress():
    """Görselleri sıkıştır, bilgileri döndür."""
    files = request.files.getlist("images")
    if not files or files[0].filename == "":
        return jsonify({"error": "Görsel seçilmedi"}), 400

    results = []
    for f in files:
        if not f.filename or not allowed_file(f.filename):
            results.append({
                "filename": f.filename or "unknown",
                "status": "error",
                "message": "Desteklenmeyen dosya formatı",
            })
            continue

        try:
            original_bytes = f.read()
            original_size = len(original_bytes)

            compressed_bytes, content_type = compress_image(original_bytes, f.filename)
            compressed_size = len(compressed_bytes)

            file_id = uuid.uuid4().hex[:8]
            results.append({
                "filename": f.filename,
                "file_id": file_id,
                "status": "ok",
                "original_kb": round(original_size / 1024),
                "compressed_kb": round(compressed_size / 1024),
                "reduction": f"{round((1 - compressed_size / original_size) * 100)}%",
            })
        except Exception as e:
            results.append({
                "filename": f.filename,
                "status": "error",
                "message": str(e),
            })

    success_count = sum(1 for r in results if r["status"] == "ok")
    return jsonify({
        "total": len(results),
        "success": success_count,
        "failed": len(results) - success_count,
        "results": results,
    })


@app.route("/download", methods=["POST"])
def download():
    """Görselleri sıkıştırıp ZIP olarak indir."""
    files = request.files.getlist("images")
    if not files or files[0].filename == "":
        return jsonify({"error": "Görsel seçilmedi"}), 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if not f.filename or not allowed_file(f.filename):
                continue
            original_bytes = f.read()
            compressed_bytes, _ = compress_image(original_bytes, f.filename)
            new_name = f"{Path(f.filename).stem}_compressed.webp"
            zf.writestr(new_name, compressed_bytes)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="compressed_images.zip",
    )


@app.route("/upload", methods=["POST"])
def upload():
    """Görselleri sıkıştır ve Supabase'e yükle."""
    from storage import get_client, upload_to_bucket

    files = request.files.getlist("images")
    if not files or files[0].filename == "":
        return jsonify({"error": "Görsel seçilmedi"}), 400

    bucket = os.environ.get("SUPABASE_BUCKET", "images")
    folder = request.form.get("folder", "").strip()

    try:
        client = get_client()
    except Exception as e:
        return jsonify({"error": f"Supabase bağlantı hatası: {str(e)}"}), 500

    results = []
    for f in files:
        if not f.filename or not allowed_file(f.filename):
            results.append({
                "filename": f.filename or "unknown",
                "status": "error",
                "message": "Desteklenmeyen dosya formatı",
            })
            continue

        try:
            original_bytes = f.read()
            original_size = len(original_bytes)

            compressed_bytes, content_type = compress_image(original_bytes, f.filename)
            compressed_size = len(compressed_bytes)

            ext = ".webp"
            safe_name = f"{uuid.uuid4().hex[:8]}_{Path(f.filename).stem}{ext}"
            upload_path = f"{folder}/{safe_name}" if folder else safe_name

            upload_to_bucket(client, bucket, upload_path, compressed_bytes, content_type)

            results.append({
                "filename": f.filename,
                "status": "ok",
                "original_kb": round(original_size / 1024),
                "compressed_kb": round(compressed_size / 1024),
                "reduction": f"{round((1 - compressed_size / original_size) * 100)}%",
                "path": upload_path,
            })
        except Exception as e:
            results.append({
                "filename": f.filename,
                "status": "error",
                "message": str(e),
            })

    success_count = sum(1 for r in results if r["status"] == "ok")
    return jsonify({
        "total": len(results),
        "success": success_count,
        "failed": len(results) - success_count,
        "results": results,
    })


if __name__ == "__main__":
    app.run(debug=True, port=3000)
