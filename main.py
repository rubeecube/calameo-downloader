import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from fpdf import FPDF
import cairosvg
import progressbar


def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def parse_document_info(soup):
    """Extract title, length, and first image URL (p1.svgz or p1.jpg)"""
    # Get meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not meta_desc:
        raise Exception("Could not find document description.")
    desc = meta_desc["content"]

    # Parse title
    title = "CalameoBook"
    if "Title:" in desc:
        title = desc.split("Title:")[1].split(", Author")[0].strip()

    # Parse length
    if "Length:" in desc:
        length_text = desc.split("Length:")[1].split(" pages")[0].strip()
        length = int(length_text)
    else:
        raise Exception("Could not detect document length.")

    # Get first page (usually p1.svgz or p1.jpg)
    img_tag = soup.find("img", class_="page")
    if not img_tag:
        raise Exception("No <img class='page'> tag found.")
    first_page_url = img_tag["src"]

    return title, length, first_page_url


def generate_all_page_urls(first_page_url, total_pages):
    """Generate all page URLs based on pattern found in first_page_url"""
    prefix, file_ext = first_page_url.split("p1.")
    urls = [f"{prefix}p{i}.{file_ext}" for i in range(1, total_pages + 1)]
    return urls


def download_all_images(image_urls):
    """Download list of images and return filepaths"""
    os.makedirs("downloads", exist_ok=True)
    image_paths = []

    print(f"\n[↓] Downloading {len(image_urls)} pages...\n")
    bar = progressbar.ProgressBar(maxval=len(image_urls))
    bar.start()
    for i, url in enumerate(image_urls):
        ext = url.split(".")[-1]
        filename = f"downloads/page_{i+1}.{ext.split('?')[0]}"

        try:
            r = requests.get(url, stream=True, timeout=10)
            with open(filename, "wb") as f:
                f.write(r.content)
            image_paths.append(filename)
        except Exception as e:
            print(f"❌ Failed to download page {i+1}: {e}")
        bar.update(i)
    bar.finish()

    return image_paths


def convert_images_to_pdf(image_paths, out_pdf):
    print("\n[⇄] Converting to PDF...\n")
    pdf = FPDF()

    bar = progressbar.ProgressBar(maxval=len(image_paths))
    bar.start()
    for i, path in enumerate(image_paths):
        if path.endswith(".svgz") or path.endswith(".svg"):
            # Convert SVGZ to PNG
            png_path = path.replace(".svgz", ".png").replace(".svg", ".png")
            cairosvg.svg2png(url=path, write_to=png_path)
            image = Image.open(png_path)
        else:
            image = Image.open(path)

        width, height = image.size
        pdf_w, pdf_h = float(width * 0.75), float(height * 0.75)  # Resize for FPDF
        pdf.add_page()
        pdf.image(path if not path.endswith(".svgz") else png_path, 0, 0, pdf_w, pdf_h)
        bar.update(i)

    bar.finish()
    pdf.output(out_pdf)
    print(f"\n✅ PDF saved as '{out_pdf}'")


def cleanup_folder(folder="downloads"):
    print("\n[🧹] Cleaning up temporary files...")
    for file in os.listdir(folder):
        os.remove(os.path.join(folder, file))
    os.rmdir(folder)
    print("✔ Cleanup complete.")


def main(calameo_url):
    print(f"📘 Processing Calameo URL: {calameo_url}")

    # Step 1: Load page and parse info
    driver = setup_driver()
    driver.get(calameo_url)
    title = None
    while title is None:
        time.sleep(1)  # wait for JS-rendered elements
        soup = BeautifulSoup(driver.page_source, "lxml")
        try:
            title, page_count, first_page_url = parse_document_info(soup)
        except Exception:
            pass
    driver.quit()
    print(f"📖 Title: {title}")
    print(f"📄 Pages: {page_count}")
    print(f"🖼 First Page URL: {first_page_url}")

    # Step 2: Generate all URLs
    all_urls = generate_all_page_urls(first_page_url, page_count)

    # Step 3: Download all pages
    image_files = download_all_images(all_urls)

    # Step 4: Convert to PDF
    output_pdf_name = f"{title}.pdf"
    convert_images_to_pdf(image_files, output_pdf_name)

    # Step 5: Clean up
    cleanup_folder("downloads")


if __name__ == "__main__":
    book_url_list = []
    only_pdf = False

    for url in book_url_list:
        main(url)
