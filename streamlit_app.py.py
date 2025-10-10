import streamlit as st
import pandas as pd
import pdfkit
import base64
from pathlib import Path
from datetime import datetime
import platform
import json
import os

# --- Page Configuration ---
st.set_page_config(page_title="Metrisum Catalogue Maker", page_icon="📄", layout="wide")

# --- SAVE/LOAD SETUP ---
SELECTIONS_DIR = Path("selections")
SELECTIONS_DIR.mkdir(exist_ok=True)

# --- Configuration for wkhtmltopdf ---
if platform.system() == "Linux":
    CONFIG = pdfkit.configuration()
    st.session_state['is_linux'] = True
else:
    PATH_WKHTMLTOPDF = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    if not Path(PATH_WKHTMLTOPDF).exists():
        st.error(f"FATAL ERROR: wkhtmltopdf.exe not found at {PATH_WKHTMLTOPDF}")
        st.stop()
    CONFIG = pdfkit.configuration(wkhtmltopdf=PATH_WKHTMLTOPDF)
    st.session_state['is_linux'] = False

# --- CSS (Unchanged) ---
HTML_CSS = """
<style>
    /* All your existing CSS goes here - no changes */
    body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 11pt; color: #3d3d3d; }
    h1 { color: #222; text-align: center; margin: 30px 0; font-weight: 300; letter-spacing: 1px; }
    .header-table { width: 100%; border-bottom: 2px solid #f0f0f0; padding-bottom: 20px; border-spacing: 0; }
    .header-logo { text-align: left; width: 40%; }
    .header-logo img { max-height: 70px; }
    .header-details { text-align: right; font-size: 10pt; color: #555; line-height: 1.5; vertical-align: middle; }
    .customer-details { margin-top: 30px; padding: 15px; border: 1px solid #f0f0f0; border-radius: 6px; }
    .customer-name-display { font-weight: bold; }
    .category-header { font-size: 24pt; font-weight: 300; color: #111; border-bottom: 1px solid #ddd; padding-bottom: 12px; margin-top: 45px; margin-bottom: 30px; page-break-after: avoid; letter-spacing: 0.5px; }
    .packaging-header { padding-bottom: 10px; }
    .packaging-title { font-weight: 600; font-size: 14pt; color: #222; }
    .packaging-specs { font-size: 9pt; color: #666; margin-top: 5px; }
    .main-product-table { width: 100%; border-collapse: separate; border-spacing: 0 20px; table-layout: fixed; }
    .main-product-table > tbody > tr > td { width: 50%; padding: 0 15px; vertical-align: top; }
    .product-cell-table { width: 100%; height: 100px; }
    .image-cell { width: 100px; height: 100px; text-align: center; vertical-align: middle; }
    .product-image { max-width: 100px; max-height: 100px; object-fit: contain; }
    .text-cell { padding-left: 15px; vertical-align: middle; }
    .item-name { font-weight: 600; font-size: 12pt; color: #000; }
    .item-fragrance { font-size: 10pt; color: #555; }
    .input-cell { width: 90px; vertical-align: middle; text-align: center; color: #3d3d3d; font-size: 9pt; line-height: 1.2; }
    .input-cell input { width: 80px; text-align: center; border: 1px solid #000000; border-radius: 4px; padding: 8px; font-size: 11pt; background-color: #ffffff; color: #000000; margin-top: 5px; }
</style>
"""

# --- Helper Functions ---
@st.cache_data
def get_image_as_base64_str(path):
    if path is None or not Path(path).exists(): return ""
    try:
        with open(path, "rb") as image_file: return base64.b64encode(image_file.read()).decode()
    except Exception: return ""

def toggle_all_items(key_for_multiselect, options_list, key_for_checkbox):
    if st.session_state[key_for_checkbox]:
        st.session_state[key_for_multiselect] = options_list
    else:
        st.session_state[key_for_multiselect] = []

def generate_product_tables_html(filtered_df, packaging_df): # Unchanged
    html = ""
    for category, category_group in filtered_df.groupby('Category'):
        html += f"<h2 class='category-header'>{category}</h2>"
        for packaging, packaging_group in category_group.groupby('Packaging'):
            pkg_details = packaging_df[packaging_df['PackagingName'] == packaging].iloc[0]
            spec_string = (f"Pcs/Ctn <strong>{pkg_details.get('Pcs Per master Ctn', 'N/A')}</strong> | Gross Wt <strong>{pkg_details.get('GrossWtKg', 'N/A')} Kg</strong> | CBM <strong>{pkg_details.get('CBM', 0):.3f}</strong>")
            html += f"""<div class="packaging-header"><div class="packaging-title">{packaging}</div><div class="packaging-specs">{spec_string}</div></div>"""
            html += '<table class="main-product-table"><tbody>'
            for i in range(0, len(packaging_group), 2):
                html += '<tr>'
                row1 = packaging_group.iloc[i]
                img_b64_1 = row1['ImageB64']
                img_tag_1 = f'<img class="product-image" src="data:image/png;base64,{img_b64_1}">' if img_b64_1 else ''
                html += f"""<td><table class="product-cell-table"><tr><td class="image-cell" rowspan="2">{img_tag_1}</td><td class="text-cell"><div class="item-name">{row1.get('ItemName', '')}</div><div class="item-fragrance">{row1.get('Fragrance', '')}</div></td><td class="input-cell" rowspan="2">Order Qty (Cartons)<br><input type="text" name="qty_{row1.get('SKU Code','')}" /></td></tr><tr><td class="text-cell"></td></tr></table></td>"""
                if (i + 1) < len(packaging_group):
                    row2 = packaging_group.iloc[i + 1]
                    img_b64_2 = row2['ImageB64']
                    img_tag_2 = f'<img class="product-image" src="data:image/png;base64,{img_b64_2}">' if img_b64_2 else ''
                    html += f"""<td><table class="product-cell-table"><tr><td class="image-cell" rowspan="2">{img_tag_2}</td><td class="text-cell"><div class="item-name">{row2.get('ItemName', '')}</div><div class="item-fragrance">{row2.get('Fragrance', '')}</div></td><td class="input-cell" rowspan="2">Order Qty (Cartons)<br><input type="text" name="qty_{row2.get('SKU Code','')}" /></td></tr><tr><td class="text-cell"></td></tr></table></td>"""
                else: html += '<td></td>'
                html += '</tr>'
            html += '</tbody></table>'
    return html

def generate_full_pdf_html(product_tables_html, customer_name, logo_b64, current_date): # Unchanged
    html = f"""<html><head><meta charset="utf-8">{HTML_CSS}</head><body>"""
    html += f"""<table class="header-table"><tr><td class="header-logo"><img src="data:image/png;base64,{logo_b64}"></td><td class="header-details"><strong>Hem Corporation Private Limited</strong><br>G-5, Riddhi Siddhi Apts, Mithagar 'X' Road, Mulund (E)<br>Mumbai - 400081, India<br>exports@hemincense.com</td></tr></table><h1>Product Order Form</h1><div class="customer-details"><strong>Order For:</strong> {'<span class="customer-name-display">' + customer_name + '</span>' if customer_name else '_________________'} <strong style="margin-left: 40px;">Date:</strong> {current_date}</div>"""
    html += product_tables_html
    html += "</body></html>"
    return html

@st.cache_data
def load_data(): # Unchanged
    products_df = pd.read_excel('products_master.xlsx', dtype={'SKU Code': str})
    packaging_df = pd.read_excel('packaging_master.xlsx')
    customers_df = pd.read_excel('customers_master.xlsx')
    countries_df = pd.read_excel('countries_master.xlsx')
    rules_df = pd.read_excel('exclusivity_rules.xlsx', dtype={'SKU Code': str})
    products_df['ImagePath'] = products_df['ImageFileName'].apply(lambda x: Path('images') / str(x) if pd.notna(x) else None)
    products_df['ImageB64'] = products_df['ImagePath'].apply(get_image_as_base64_str)
    return products_df, packaging_df, customers_df, countries_df, rules_df

def get_selections(): # Unchanged
    return ["---"] + [f.stem for f in SELECTIONS_DIR.glob("*.json")]

def load_selection(): # Unchanged
    selection_name = st.session_state.selected_preset
    if selection_name and selection_name != "---":
        filepath = SELECTIONS_DIR / f"{selection_name}.json"
        with open(filepath, 'r') as f:
            data = json.load(f)
            for key, value in data.items():
                st.session_state[key] = value
        st.toast(f"Loaded selection: {selection_name}", icon="✅")

def save_selection(): # Unchanged
    selection_name = st.session_state.get("selection_name_input", "").strip()
    if not selection_name:
        st.sidebar.warning("Please enter a name for the selection.")
        return
    filepath = SELECTIONS_DIR / f"{selection_name}.json"
    state_to_save = {
        'customer': st.session_state.get('customer'), 'country': st.session_state.get('country'),
        'categories': st.session_state.get('categories'), 'packaging': st.session_state.get('packaging'),
        'brands': st.session_state.get('brands'), 'fragrances': st.session_state.get('fragrances')
    }
    with open(filepath, 'w') as f: json.dump(state_to_save, f, indent=4)
    st.sidebar.success(f"Saved selection: {selection_name}")
    st.session_state["selection_name_input"] = ""

# --- Main App ---
st.title("Dynamic Product Catalogue Maker 🛍️")

try:
    products_df, packaging_df, customers_df, countries_df, rules_df = load_data()

    # --- MOVED AND FIXED: Create filter option lists and initialize state ---
    # 1. Create the complete lists of options first
    categories_list = sorted(products_df['Category'].dropna().unique())
    packaging_list = sorted(products_df['Packaging'].dropna().unique())
    brands_list = sorted(products_df['Brand'].dropna().unique())
    fragrances_list = sorted(products_df['Fragrance'].dropna().unique())
    customer_list = ["-- General / No Customer --"] + sorted(customers_df['CustomerName'].dropna().unique())
    country_list = ["-- General / No Country --"] + sorted(countries_df['CountryName'].dropna().unique())

    # 2. Initialize session state ONCE for all filters
    if 'filters_initialized' not in st.session_state:
        st.session_state.customer = customer_list[0]
        st.session_state.country = country_list[0]
        st.session_state.categories = categories_list
        st.session_state.packaging = packaging_list
        st.session_state.brands = brands_list
        st.session_state.fragrances = fragrances_list
        st.session_state.filters_initialized = True # Flag to prevent re-initialization

    # --- Sidebar ---
    st.sidebar.title("Configuration")
    st.sidebar.header("Load Selection")
    saved_selections = get_selections()
    st.selectbox("Choose a saved filter set", options=saved_selections, key="selected_preset", on_change=load_selection)
    
    st.sidebar.divider()
    
    st.sidebar.header("Catalogue Selection")
    st.sidebar.selectbox("1. Select Customer", customer_list, key='customer')
    st.sidebar.selectbox("2. Select Country", country_list, key='country')
    
    st.sidebar.header("Product Filters")
    with st.sidebar.expander("Filter by Product Type", expanded=True):
        all_categories_selected = len(st.session_state.get('categories', [])) == len(categories_list)
        st.checkbox("Select All Categories", value=all_categories_selected, key='all_cat_checkbox', on_change=toggle_all_items, args=('categories', categories_list, 'all_cat_checkbox'))
        st.multiselect('Filter by Category', options=categories_list, key='categories')
        st.sidebar.divider()
        all_packaging_selected = len(st.session_state.get('packaging', [])) == len(packaging_list)
        st.checkbox("Select All Packaging", value=all_packaging_selected, key='all_pkg_checkbox', on_change=toggle_all_items, args=('packaging', packaging_list, 'all_pkg_checkbox'))
        st.multiselect('Filter by Packaging', options=packaging_list, key='packaging')
    
    with st.sidebar.expander("Filter by Specifics"):
        st.multiselect('Filter by Brand', options=brands_list, key='brands')
        st.multiselect('Filter by Fragrance', options=fragrances_list, key='fragrances')
    
    # --- Filtering Logic ---
    skus_with_rules = rules_df['SKU Code'].unique()
    general_skus = products_df[~products_df['SKU Code'].isin(skus_with_rules)]['SKU Code']
    allowed_exclusive_skus = pd.Series(dtype=str)
    if st.session_state.customer != "-- General / No Customer --":
        customer_exclusive_skus = rules_df[(rules_df['RuleType'] == 'Customer') & (rules_df['RuleValue'] == st.session_state.customer)]['SKU Code']
        allowed_exclusive_skus = pd.concat([allowed_exclusive_skus, customer_exclusive_skus])
    if st.session_state.country != "-- General / No Country --":
        country_exclusive_skus = rules_df[(rules_df['RuleType'] == 'Country') & (rules_df['RuleValue'] == st.session_state.country)]['SKU Code']
        allowed_exclusive_skus = pd.concat([allowed_exclusive_skus, country_exclusive_skus])
    
    final_allowed_skus = pd.concat([general_skus, allowed_exclusive_skus]).unique()
    base_filtered_df = products_df[products_df['SKU Code'].isin(final_allowed_skus)]
    filtered_df = base_filtered_df[
        base_filtered_df['Category'].isin(st.session_state.categories) &
        base_filtered_df['Packaging'].isin(st.session_state.packaging) &
        base_filtered_df['Brand'].isin(st.session_state.brands) &
        base_filtered_df['Fragrance'].isin(st.session_state.fragrances)
    ].copy()

    # --- Main Page Content ---
    st.header("Live Catalogue Preview")
    st.caption("This is a quick preview of the catalogue layout...")
    if filtered_df.empty:
        st.warning("No products match the current filter selection.")
    else:
        preview_html_tables = generate_product_tables_html(filtered_df, packaging_df)
        st.html(f"<div style='background-color: #ffffff; height: 500px; overflow-y: auto; border: 1px solid #e0e0e0; padding: 15px; border-radius: 5px;'>{HTML_CSS}{preview_html_tables}</div>")

    st.header("Generate Your Catalogue")
    customer_name_input = st.text_input("Enter Customer Name for PDF", value=st.session_state.customer if st.session_state.customer != '-- General / No Customer --' else '')

    if st.button("Generate PDF Order Form", type="primary"):
        if filtered_df.empty: st.error("Cannot generate PDF...")
        else:
            with st.spinner('Building your definitive catalogue... Please wait.'):
                current_date = datetime.now().strftime("%d-%b-%Y")
                logo_b64 = get_image_as_base64_str(Path('assets/logo.png'))
                product_tables_html = generate_product_tables_html(filtered_df, packaging_df)
                final_html_string = generate_full_pdf_html(product_tables_html, customer_name_input, logo_b64, current_date)
                options = { 'page-size': 'A4', 'margin-top': '0.75in', 'margin-right': '0.75in', 'margin-bottom': '0.75in', 'margin-left': '0.75in', 'encoding': "UTF-8", 'enable-forms': None }
                pdf_bytes = pdfkit.from_string(final_html_string, False, options=options, configuration=CONFIG)
                file_name_customer = customer_name_input.replace(' ', '_') if customer_name_input else "General"
                file_name = f"Order_Form_{file_name_customer}_{current_date}.pdf"
                st.download_button("📥 Download PDF Order Form", data=pdf_bytes, file_name=file_name, mime="application/pdf")
                st.success("Your PDF has been generated successfully!")

except FileNotFoundError as e:
    st.error(f"Error: A required master file was not found: `{e.filename}`.")
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")

# --- SAVE SELECTION UI ---
with st.sidebar.expander("Save Current Selection"):
    st.text_input("Enter selection name", key="selection_name_input")
    st.button("Save Filters", on_click=save_selection)

if st.session_state.get('is_linux'):
    st.sidebar.info("Running in a Linux environment...")