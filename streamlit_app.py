# --- FINAL, COMPLETE CATALOGUE MAKER SCRIPT ---
import streamlit as st
import pandas as pd
import pdfkit
import base64
from pathlib import Path
from datetime import datetime
import json
import os

# --- Password Protection ---
def check_password():
    """Returns `True` if the user entered the correct password."""
    def password_entered():
        if st.session_state.get("password") and "PASSWORD" in st.secrets and st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Enter Password to access the App", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect. Please try again.")
    return False

# --- Main App Logic ---
if check_password():
    st.set_page_config(page_title="Hem Brochure Maker", page_icon="🎨", layout="wide")

    # --- Configuration for wkhtmltopdf ---
    path_wkhtmltopdf = os.path.join(os.path.dirname(__file__), 'bin', 'wkhtmltopdf')
    try:
        os.chmod(path_wkhtmltopdf, 0o755)
    except (OSError, FileNotFoundError):
        pass
    CONFIG = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    
    # --- Brochure CSS (Landscape, Grid, Visual Focus) ---
    HTML_CSS = """
    <style>
        @page { size: A4 landscape; margin: 0; }
        body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; margin: 0; padding: 0; color: #333; }
        
        /* Header & Footer */
        .page-header { 
            padding: 20px 40px; 
            border-bottom: 4px solid #d32f2f; /* Brand Color Accent */
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            background-color: #fff;
        }
        .header-logo img { height: 60px; }
        .header-title { font-size: 24pt; font-weight: 300; text-transform: uppercase; letter-spacing: 2px; color: #222; }
        
        .page-footer {
            position: fixed; bottom: 0; left: 0; right: 0;
            padding: 10px 40px; font-size: 8pt; color: #888; text-align: right;
            border-top: 1px solid #eee; background: #fff;
        }

        /* Cover Page */
        .cover-page {
            height: 100vh; width: 100%;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; page-break-after: always;
            background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        }
        .cover-title { font-size: 48pt; font-weight: bold; margin-bottom: 20px; color: #d32f2f; }
        .cover-subtitle { font-size: 18pt; color: #555; margin-bottom: 50px; }
        .cover-meta { font-size: 12pt; color: #777; }

        /* Product Grid Layout */
        .catalogue-container { padding: 40px; }
        .category-separator { 
            width: 100%; margin-top: 20px; margin-bottom: 20px; 
            border-bottom: 1px solid #ccc; 
            font-size: 18pt; font-weight: 300; color: #d32f2f; 
            page-break-after: avoid;
        }
        
        .grid-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr); /* 3 Columns */
            gap: 30px;
            row-gap: 40px;
        }

        /* Individual Product Card */
        .product-card {
            background: #fff;
            border: 1px solid #eee;
            border-radius: 8px;
            overflow: hidden;
            page-break-inside: avoid; /* Don't chop cards in half */
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        .card-image-box {
            height: 200px; /* Fixed height for image area */
            width: 100%;
            display: flex; justify-content: center; align-items: center;
            background-color: #fff;
            padding: 10px;
            box-sizing: border-box;
            border-bottom: 1px solid #f9f9f9;
        }
        .card-image { max-height: 100%; max-width: 100%; object-fit: contain; }
        
        .card-details { padding: 15px; text-align: center; }
        .card-title { font-size: 12pt; font-weight: 700; margin-bottom: 5px; color: #222; min-height: 30px;}
        .card-fragrance { font-size: 10pt; color: #d32f2f; font-weight: 600; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
        
        .specs-table { width: 100%; font-size: 8pt; color: #666; margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; }
        .specs-table td { padding: 2px; }
        .spec-label { text-align: left; font-weight: 600; }
        .spec-val { text-align: right; }
    </style>
    """

    @st.cache_data
    def get_image_as_base64_str(path):
        if path is None or not Path(path).exists(): return ""
        try:
            with open(path, "rb") as image_file: return base64.b64encode(image_file.read()).decode()
        except Exception: return ""

    @st.cache_data
    def load_data():
        products_df = pd.read_excel('products_master.xlsx', dtype={'SKU Code': str})
        packaging_df = pd.read_excel('packaging_master.xlsx')
        customers_df = pd.read_excel('customers_master.xlsx')
        # Pre-calculate paths
        products_df['ImagePath'] = products_df['ImageFileName'].apply(lambda x: Path('images') / str(x) if pd.notna(x) else None)
        products_df['ImageB64'] = products_df['ImagePath'].apply(get_image_as_base64_str)
        return products_df, packaging_df, customers_df

    # --- Helper: Initialize Session State for "Shopping Cart" ---
    if 'catalogue_cart' not in st.session_state:
        st.session_state.catalogue_cart = [] # List of dictionaries (Product Rows)

    def add_to_cart(selected_rows_df):
        """Adds items to the catalogue list, avoiding duplicates."""
        current_skus = {item['SKU Code'] for item in st.session_state.catalogue_cart}
        count = 0
        for index, row in selected_rows_df.iterrows():
            if row['SKU Code'] not in current_skus:
                st.session_state.catalogue_cart.append(row.to_dict())
                count += 1
        if count > 0:
            st.toast(f"Added {count} products to catalogue!", icon="🛒")
        else:
            st.toast("Selected items are already in the catalogue.", icon="ℹ️")

    def clear_cart():
        st.session_state.catalogue_cart = []

    def generate_brochure_html(cart_items, packaging_df, customer_name, logo_b64):
        # Convert cart to DF for grouping
        df = pd.DataFrame(cart_items)
        
        current_date = datetime.now().strftime("%B %Y")
        
        html = f"""<html><head><meta charset="utf-8">{HTML_CSS}</head><body>"""
        
        # 1. Cover Page
        html += f"""
        <div class="cover-page">
            <div style="margin-bottom:30px;"><img src="data:image/png;base64,{logo_b64}" style="max-height:120px;"></div>
            <div class="cover-title">Product Collection</div>
            <div class="cover-subtitle">Curated Exclusively for {customer_name}</div>
            <div class="cover-meta">{current_date}</div>
        </div>
        """

        # 2. Content Pages
        # Header for content pages
        html += f"""
        <div class="page-header">
            <div class="header-logo"><img src="data:image/png;base64,{logo_b64}"></div>
            <div class="header-title">Export Catalogue</div>
        </div>
        <div class="catalogue-container">
        """

        # Group by Category
        for category, cat_group in df.groupby('Category'):
            html += f'<div class="category-separator">{category}</div>'
            html += '<div class="grid-container">'
            
            for index, row in cat_group.iterrows():
                # Get packaging specs
                pkg_name = row.get('Packaging')
                pkg_info = packaging_df[packaging_df['PackagingName'] == pkg_name]
                
                pcs_ctn = "N/A"
                cbm = "N/A"
                
                if not pkg_info.empty:
                    pcs_ctn = pkg_info.iloc[0].get('Pcs Per master Ctn', 'N/A')
                    cbm = f"{pkg_info.iloc[0].get('CBM', 0):.3f}"

                img_b64 = row.get('ImageB64', '')
                img_tag = f'<img class="card-image" src="data:image/png;base64,{img_b64}">' if img_b64 else '<span style="color:#ccc;">No Image</span>'
                
                html += f"""
                <div class="product-card">
                    <div class="card-image-box">{img_tag}</div>
                    <div class="card-details">
                        <div class="card-title">{row.get('ItemName', 'Unknown Item')}</div>
                        <div class="card-fragrance">{row.get('Fragrance', '')}</div>
                        <div style="font-size:9pt; color:#555;">{pkg_name}</div>
                        <table class="specs-table">
                            <tr><td class="spec-label">Pcs/Master:</td><td class="spec-val">{pcs_ctn}</td></tr>
                            <tr><td class="spec-label">CBM:</td><td class="spec-val">{cbm}</td></tr>
                            <tr><td class="spec-label">SKU:</td><td class="spec-val">{row.get('SKU Code')}</td></tr>
                        </table>
                    </div>
                </div>
                """
            
            html += '</div>' # End grid container
            html += '<div style="margin-bottom: 40px;"></div>' # Spacer between categories

        html += "</div>" # End catalogue container
        html += "</body></html>"
        return html

    # --- Load Master Data ---
    products_df, packaging_df, customers_df = load_data()

    # --- UI Layout ---
    st.title("✨ Custom Brochure Designer")
    
    # We use tabs for the workflow: Build -> Review -> Publish
    tab_builder, tab_review, tab_publish = st.tabs(["1. Select Products", "2. Review & Organize", "3. Generate PDF"])

    # --- TAB 1: BUILDER (Search & Add) ---
    with tab_builder:
        col_filters, col_results = st.columns([1, 3])
        
        with col_filters:
            st.subheader("🔍 Find Products")
            search_term = st.text_input("Search Item Name / SKU")
            
            # Category Filter
            all_cats = sorted(products_df['Category'].dropna().unique())
            sel_cats = st.multiselect("Category", all_cats)
            
            # Brand Filter
            all_brands = sorted(products_df['Brand'].dropna().unique())
            sel_brands = st.multiselect("Brand", all_brands)
            
            # Fragrance Filter
            all_frags = sorted(products_df['Fragrance'].dropna().unique())
            sel_frags = st.multiselect("Fragrance", all_frags)

        with col_results:
            # Apply Filters
            filtered_df = products_df.copy()
            if search_term:
                filtered_df = filtered_df[filtered_df['ItemName'].str.contains(search_term, case=False, na=False) | 
                                          filtered_df['SKU Code'].str.contains(search_term, case=False, na=False)]
            if sel_cats:
                filtered_df = filtered_df[filtered_df['Category'].isin(sel_cats)]
            if sel_brands:
                filtered_df = filtered_df[filtered_df['Brand'].isin(sel_brands)]
            if sel_frags:
                filtered_df = filtered_df[filtered_df['Fragrance'].isin(sel_frags)]
            
            st.subheader(f"Available Products ({len(filtered_df)})")
            
            # Use Data Editor with Checkboxes for Selection
            # We add a temporary 'Select' column
            filtered_df_display = filtered_df[['SKU Code', 'ItemName', 'Category', 'Fragrance', 'Packaging']].copy()
            filtered_df_display.insert(0, "Select", False)
            
            edited_df = st.data_editor(
                filtered_df_display, 
                hide_index=True, 
                use_container_width=True,
                column_config={"Select": st.column_config.CheckboxColumn(required=True)}
            )
            
            # Button to Add
            selected_rows = edited_df[edited_df.Select]
            col_btn_1, col_btn_2 = st.columns([1, 4])
            if col_btn_1.button("Add Selected to Brochure", type="primary"):
                if not selected_rows.empty:
                    # We need to get the full rows from the original DF based on SKU
                    full_rows = products_df[products_df['SKU Code'].isin(selected_rows['SKU Code'])]
                    add_to_cart(full_rows)
                else:
                    st.warning("Please check the boxes next to items you want to add.")

    # --- TAB 2: REVIEW (Cart Management) ---
    with tab_review:
        st.subheader("🛒 Your Brochure Content")
        
        if not st.session_state.catalogue_cart:
            st.info("Your catalogue is empty. Go to the 'Select Products' tab to add items.")
        else:
            cart_df = pd.DataFrame(st.session_state.catalogue_cart)
            
            st.markdown(f"**Total Items:** {len(cart_df)}")
            
            # Allow user to delete items here
            cart_display = cart_df[['SKU Code', 'ItemName', 'Category', 'Fragrance', 'Packaging']].copy()
            cart_display.insert(0, "Remove", False)
            
            edited_cart = st.data_editor(
                cart_display, 
                hide_index=True, 
                use_container_width=True,
                column_config={"Remove": st.column_config.CheckboxColumn(required=True)}
            )
            
            if st.button("Update List (Remove Selected)"):
                skus_to_remove = edited_cart[edited_cart.Remove]['SKU Code'].tolist()
                if skus_to_remove:
                    st.session_state.catalogue_cart = [
                        item for item in st.session_state.catalogue_cart 
                        if item['SKU Code'] not in skus_to_remove
                    ]
                    st.rerun()
            
            if st.button("Clear Entire List", type="secondary"):
                clear_cart()
                st.rerun()

    # --- TAB 3: PUBLISH (PDF Gen) ---
    with tab_publish:
        st.subheader("🖨️ Generate PDF")
        
        col_pub_1, col_pub_2 = st.columns(2)
        with col_pub_1:
            customer_name = st.text_input("Customer Name (for Cover Page)", value="Valued Client")
        
        if st.button("Create Landscape Brochure", type="primary", disabled=(len(st.session_state.catalogue_cart) == 0)):
            with st.spinner("Designing brochure..."):
                logo_b64 = get_image_as_base64_str(Path('assets') / 'logo.png')
                
                html_string = generate_brochure_html(st.session_state.catalogue_cart, packaging_df, customer_name, logo_b64)
                
                # Landscape Options
                options = {
                    'page-size': 'A4',
                    'orientation': 'Landscape',
                    'margin-top': '0mm',
                    'margin-right': '0mm',
                    'margin-bottom': '0mm',
                    'margin-left': '0mm',
                    'encoding': "UTF-8",
                    'no-outline': None,
                    'enable-local-file-access': None
                }
                
                try:
                    pdf_bytes = pdfkit.from_string(html_string, False, options=options, configuration=CONFIG)
                    
                    file_name_clean = customer_name.replace(' ', '_')
                    st.success("Brochure Generated Successfully!")
                    st.download_button(
                        label="📥 Download PDF Brochure",
                        data=pdf_bytes,
                        file_name=f"Hem_Catalogue_{file_name_clean}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"PDF Generation Error: {str(e)}")