import os
import zipfile
import json
from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv
from seo_generator import generate_seo_full

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

UPLOAD_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ANGLE_PROMPTS = {
    "Front": "Render a front-facing image of the {name} with photorealistic accuracy.",
    "Back": "Render a back view of the {name}, showing clean alignment and full frame.",
    "Side": "Render a side profile of the {name} captured upright.",
    "Three Quarter": "Render a three-quarter view of the {name}, showing both front and side.",
    "Zoom Detail": "Zoom in on stitching, joinery, or upholstery details of the {name}.",
    "Hospitality Scene": "Place the {name} in a styled hospitality venue like a restaurant.",
    "360 Walkaround": "Create a 360° walkaround prompt for the {name}.",
    "360 Script": """Scene 1: Front\nScene 2: 45°\nScene 3: Side\nScene 4: 135°\nScene 5: Rear\nScene 6: Overhead"""
}

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("product_name").strip()
    category = request.form.get("category").strip()
    safe_name = name.replace(" ", "_")
    folder = os.path.join(UPLOAD_FOLDER, f"{safe_name}_output")
    os.makedirs(folder, exist_ok=True)

    include_360 = "include_360" in request.form
    generate_seo = "generate_seo" in request.form
    description_text = request.form.get("description_text", "").strip()

    features = {
        "Upholstery": request.form.get("upholstery_type"),
        "Upholstery Style": request.form.get("upholstery_style"),
        "Arms": request.form.get("arms"),
        "Backrest": request.form.get("backrest"),
        "Leg Material": request.form.get("leg_material"),
        "Leg Finish": request.form.get("leg_finish"),
        "Stackable": request.form.get("stackable"),
        "Feet": request.form.get("feet"),
        "Cushion": request.form.get("cushion"),
        "Fire Rated Foam": "Yes" if "fire_rated" in request.form else "No",
        "Outdoor Suitable": "Yes" if "outdoor_suitable" in request.form else "No"
    }

    feature_block = "\n".join([f"- {k}: {v}" for k, v in features.items() if v])

    for field in ["base_image", "fabric_image", "frame_image"]:
        file = request.files.get(field)
        if file and file.filename:
            file.save(os.path.join(folder, field + os.path.splitext(file.filename)[-1]))

    output = {}
    for angle, template in ANGLE_PROMPTS.items():
        if not include_360 and angle.startswith("360"):
            continue
        prompt = (
            f"You are provided with a base image of a chair, and optional fabric/frame swatches. "
            f"Based on the uploaded images and selected customisations, {template.format(name=name)}\n"
            f"Include the following:\n{feature_block}\n"
            f"Ensure photorealistic accuracy and commercial-ready framing."
        )
        output[angle] = prompt
        with open(os.path.join(folder, f"{safe_name}_{angle.replace(' ', '_').lower()}.txt"), "w", encoding="utf-8") as f:
            f.write(prompt)

    merged_txt_path = os.path.join(folder, f"{safe_name}_ALL_PROMPTS.txt")
    with open(merged_txt_path, "w", encoding="utf-8") as f:
        for angle, text in output.items():
            f.write(f"=== {angle.upper()} ===\n{text}\n\n")

    with open(os.path.join(folder, f"{safe_name}_prompts.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    if generate_seo and description_text:
        seo = generate_seo_full(name, category, description_text)
        with open(os.path.join(folder, f"{safe_name}_SEO.txt"), "w", encoding="utf-8") as f:
            f.write(seo["intro"] + "\n\n")
            f.write("=== FEATURES HTML BLOCK ===\n" + seo["features_html"] + "\n\n")
            f.write("=== DIMENSIONS ===\n")
            for k, v in seo["dimensions"].items():
                f.write(f"{k}: {v}\n")
            f.write("\n=== META DATA ===\n")
            f.write("Meta Title: " + seo["meta_title"] + "\n")
            f.write("Meta Description: " + seo["meta_description"] + "\n")
            f.write("Meta Keywords: " + ", ".join(seo["meta_keywords"]) + "\n")
            f.write("URL Key: " + seo["url_key"] + "\n")

        with open(os.path.join(folder, f"{safe_name}_SEO.json"), "w", encoding="utf-8") as f:
            json.dump(seo, f, indent=2)

    zip_path = os.path.join(folder, f"{safe_name}_export.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in os.listdir(folder):
            zipf.write(os.path.join(folder, file), arcname=file)

    global LAST_FOLDER
    LAST_FOLDER = folder

    return render_template("index.html", output=open(merged_txt_path, encoding="utf-8").read())

@app.route("/download/<fmt>")
def download(fmt):
    base_name = os.path.basename(LAST_FOLDER)
    safe_name = base_name.split("_")[0]
    if fmt == "txt":
        return send_file(os.path.join(LAST_FOLDER, f"{safe_name}_ALL_PROMPTS.txt"), as_attachment=True)
    elif fmt == "json":
        return send_file(os.path.join(LAST_FOLDER, f"{safe_name}_prompts.json"), as_attachment=True)
    elif fmt == "zip":
        return send_file(os.path.join(LAST_FOLDER, f"{safe_name}_export.zip"), as_attachment=True)
    elif fmt == "seo":
        return send_file(os.path.join(LAST_FOLDER, f"{safe_name}_SEO.txt"), as_attachment=True)
    else:
        return "Invalid format"

if __name__ == "__main__":
    app.run(debug=True)
