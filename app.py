from flask import Flask, render_template, request, send_file, jsonify
import os, uuid, threading, time
from functions.check_url import check_url, generate_excel, icons

app = Flask(__name__)
UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
MAX_FILES = 3

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# global log buffer và file download
logs = []
latest_file = None
file_counter = 0  # đếm số file upload
current_file_id = None  # file đang check

def add_log(stage, msg, file_id=None):
    """Nếu file_id khác None, log sẽ nằm trong section riêng"""
    full_msg = f"{icons.get(stage,'•')} {msg}"
    if file_id is not None:
        full_msg = f"<div class='file-section' id='file-{file_id}'>{full_msg}</div>"
    logs.append(full_msg)
    if len(logs) > 1000:  # giữ 1000 dòng log
        logs.pop(0)
    print(full_msg)  # log ra console

def manage_dir(folder, n=MAX_FILES):
    files = sorted([os.path.join(folder,f) for f in os.listdir(folder)], key=os.path.getctime)
    while len(files) > n:
        os.remove(files[0])
        files.pop(0)

def run_checker(file_path, excel_path, file_id):
    global latest_file
    manage_dir(UPLOAD_DIR)
    manage_dir(RESULT_DIR)

    with open(file_path, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip()]

    add_log("load", f"Đọc {len(urls)} URL từ file.", file_id)

    results = []
    for i, url in enumerate(urls, 1):
        add_log("process", f"[{i}/{len(urls)}] Kiểm tra {url}", file_id)
        results.append(check_url(url))
        time.sleep(0.05)  # để log chạy mượt

    add_log("export", "Xuất Excel...", file_id)
    generate_excel(results, excel_path)
    add_log("done", "Hoàn tất! Excel sẵn sàng.", file_id)
    latest_file = excel_path

@app.route("/", methods=["GET","POST"])
def index():
    global file_counter, current_file_id, logs
    if request.method == "POST":
        file = request.files.get("txt_file")
        if not file:
            add_log("error", "Không có file được chọn.")
            return '', 400  # lỗi client

        # reset log khi có file mới
        logs = []

        fn = f"{uuid.uuid4()}.txt"
        fp = os.path.join(UPLOAD_DIR, fn)
        file.save(fp)
        file_counter += 1
        file_id = file_counter
        current_file_id = file_id
        add_log("load", f"Tải file \"{file.filename}\" thành công.", file_id)

        excel_fn = f"{uuid.uuid4()}.xlsx"
        excel_fp = os.path.join(RESULT_DIR, excel_fn)

        t = threading.Thread(target=run_checker, args=(fp, excel_fp, file_id))
        t.start()

        return '', 204  # AJAX không reload trang

    return render_template("index.html")

@app.route("/logs")
def get_logs():
    return jsonify(logs)

@app.route("/download")
def download():
    global latest_file
    if latest_file and os.path.exists(latest_file):
        return send_file(latest_file, as_attachment=True)
    return '', 404

if __name__ == "__main__":
    app.run(debug=True)
