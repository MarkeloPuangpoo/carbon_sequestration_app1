import os
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, request, redirect, url_for, render_template, flash, send_from_directory
from matplotlib import font_manager
from matplotlib import rcParams

# ฟังก์ชันในการใช้ฟอนต์ที่รองรับภาษาไทย
def set_font_for_matplotlib():
    rcParams['font.family'] = 'TH Sarabun'  # ใช้ฟอนต์ TH Sarabun ที่รองรับภาษาไทย

app = Flask(__name__)
app.secret_key = 'df4c5f5bdd9d0061905ade9a8e93fbe5'

# ตั้งค่าโฟลเดอร์อัพโหลด
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ฟังก์ชันในการตรวจสอบไฟล์ที่อัพโหลด
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ฟังก์ชันในการคำนวณการกักเก็บคาร์บอน
def calculate_carbon_storage_gongkang(circumference, height):
    diameter = circumference * 7 / 22  # ใช้ค่า pi = 22/7

    # คำนวณมวลชีวภาพเหนือพื้นดิน, กิ่ง, ราก
    WS = 0.05466 * (diameter**2 * height)**0.945
    WB = 0.01579 * (diameter**2 * height)**0.9124
    WL = 0.0678 * (diameter**2 * height)**0.5806
    WT = WS + WB + WL

    # คำนวณมวลชีวภาพใต้ดิน
    below_ground_biomass = WT * 0.48

    # คำนวณมวลชีวภาพรวม
    total_biomass = WT + below_ground_biomass

    # คำนวณการกักเก็บคาร์บอน
    carbon_storage = total_biomass * 0.4715 * (44 / 12)

    return carbon_storage, WS, WB, WL, WT, below_ground_biomass, total_biomass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        circumference = float(request.form['circumference'])
        height = float(request.form['height'])

        # คำนวณการกักเก็บคาร์บอน
        carbon_storage, WS, WB, WL, WT, below_ground_biomass, total_biomass = calculate_carbon_storage_gongkang(circumference, height)

        # ส่งผลลัพธ์ไปยังเทมเพลต
        return render_template('result.html', circumference=circumference, height=height,
                               carbon_storage=carbon_storage, WS=WS, WB=WB, WL=WL, WT=WT,
                               below_ground_biomass=below_ground_biomass, total_biomass=total_biomass)
    except ValueError:
        flash("Invalid input! Please enter numeric values.")
        return redirect(url_for('index'))

# เพิ่มฟังก์ชันในการดาวน์โหลดไฟล์
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_excel', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                # อ่านข้อมูลจากไฟล์ Excel
                df = pd.read_excel(filepath)

                # คำนวณการกักเก็บคาร์บอนทั้งหมด
                df['Carbon_Storage'], df['WS'], df['WB'], df['WL'], df['WT'], df['Below_Ground_Biomass'], df['Total_Biomass'] = zip(
                    *df.apply(lambda row: calculate_carbon_storage_gongkang(row['Circumference'], row['Height']), axis=1)
                )

                total_carbon = df['Carbon_Storage'].sum()

                # สร้างกราฟ
                graph_path = os.path.join('static', 'carbon_graph.png')  # บันทึกกราฟในโฟลเดอร์ static
                plt.figure(figsize=(10, 6))
                for i, row in df.iterrows():
                    plt.bar(f"Tree number {i+1}", row['Carbon_Storage'])

                plt.title('Carbon sequestration from individual trees')
                plt.ylabel('Carbon sequestration (kgCO2)')
                plt.savefig(graph_path)  # บันทึกกราฟในโฟลเดอร์ static
                plt.close()

                # สร้างไฟล์ CSV
                csv_filename = f"carbon_sequestration_results_{filename}.csv"
                csv_filepath = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
                df.to_csv(csv_filepath, index=False)

                # ส่งข้อมูลผลลัพธ์พร้อมกราฟไปยังเทมเพลต
                return render_template('upload_result.html',
                                       graph_path=graph_path.split('static/')[-1],
                                       total_carbon=total_carbon, dataframe=df,
                                       download_link=csv_filename)  # ส่งลิงก์ดาวน์โหลด

            except Exception as e:
                flash(f"Error processing file: {e}")
                return redirect(request.url)

    return render_template('upload_excel.html')


if __name__ == '__main__':
    app.run(debug=True)
