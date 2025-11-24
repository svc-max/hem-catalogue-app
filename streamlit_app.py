import streamlit as st
import pandas as pd
import pdfkit
import base64
from pathlib import Path
from datetime import datetime
import io
import os

# --- 1. CONFIGURATION & AUTH ---
def check_password():
    def password_entered():
        if st.session_state.get("password") and "PASSWORD" in st.secrets and st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
    return False

if check_password():
    st.set_page_config(page_title="Hem Luxury Catalogue", page_icon="✨", layout="wide")

    # --- 2. PDF SETTINGS & AESTHETIC CSS ---
    path_wkhtmltopdf = os.path.join(os.path.dirname(__file__), 'bin', 'wkhtmltopdf')
    try:
        os.chmod(path_wkhtmltopdf, 0o755)
    except: pass
    CONFIG = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    # DESIGN: Clean, High-Density Landscape Grid
    HTML_CSS = """
    <style>
        @page { size: A4 landscape; margin: 10mm; }
        body { 
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; 
            color: #2c2c2c; 
            margin: 0; padding: 0;
            -webkit-print-color-adjust: exact; 
        }
        
        /* TYPOGRAPHY */
        h1, h2, h3 { font-family: 'Georgia', serif; font-weight: normal; }
        
        /* COVER PAGE (Adapted for Landscape) */
        .cover-page {
            height: calc(100vh - 20mm); width: 100%;
            background: linear-gradient(135deg, #fff 0%, #f9f9f9 100%);
            position: relative;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center;
            page-break-after: always;
            border: 1px solid #eee;
        }
        .cover-content { z-index: 1; padding: 30px 60px; border: 3px solid #2c2c2c; background: #fff; }
        .brand-title { font-size: 48pt; letter-spacing: 4px; margin: 0; text-transform: uppercase; color: #000; }
        .collection-title { font-size: 18pt; font-style: italic; color: #555; margin-top: 10px; margin-bottom: 30px; }
        .client-name { font-size: 12pt; text-transform: uppercase; letter-spacing: 2px; color: #2c2c2c; border-top: 1px solid #ccc; padding-top: 15px; }

        /* CONTENT PAGES */
        .category-header {
            font-size: 16pt; font-weight: bold; color: #000;
            border-bottom: 2px solid #FFD700; /* Gold Line */
            margin: 20px 0 15px 0;
            padding-bottom: 5px;
            text-transform: uppercase;
            page-break-after: avoid;
        }

        /* GRID LAYOUT - HIGH DENSITY (5 Columns) */
        .grid-container {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            row-gap: 25px;
        }

        /* COMPACT PRODUCT CARD */
        .card {
            background: #fff;
            border: 1px solid #eee;
            position: relative;
            page-break-inside: avoid;
            display: flex; flex-direction: column;
        }
        
        /* Serial Number Badge - Top Left */
        .serial-tag {
            position: absolute; top: 0; left: 0;
            background-color: #FFD700; color: #000;
            font-size: 8pt; font-weight: bold;
            padding: 3px 6px; z-index: 10;
        }
        
        /* Image styling - Compact Square */
        .img-box {
            width: 100%; height: 120px; /* Fixed height */
            background: #fff;
            display: flex; justify-content: center; align-items: center;
            padding: 10px 0; margin-top: 15px; /* Space for ref tag */
        }
        .img-box img { max-width: 90%; max-height: 95%; object-fit: contain; }
        
        /* Text styling - Concise */
        .card-meta { 
            text-align: center; padding: 8px 5px; 
            border-top: 1px solid #f0f0f0; background: #fafafa;
            flex-grow: 1; display: flex; flex-direction: column; justify-content: center;
        }
        .p-name { 
            font-family: 'Georgia', serif; font-size: 9.5pt; font-weight: bold; 
            color: #000; margin-bottom: 4px; line-height: 1.2;
            max-height: 2.4em; overflow: hidden; /* Limit to 2 lines */
        }
        .p-frag { font-size: 8pt; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
    """

    @st.cache_data
    def get_image_as_base64_str(path):
        if path is None or not Path(path).exists(): return ""
        try:
            with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return ""

    @st.cache_data
    def load_data():
        products_df = pd.read_excel('products_master.xlsx', dtype={'SKU Code': str})
        products_df['ImagePath'] = products_df['ImageFileName'].apply(lambda x: Path('images') / str(x) if pd.notna(x) else None)
        products_df['ImageB64'] = products_df['ImagePath'].apply(get_image_as_base64_str)
        return products_df

    # --- 3. SESSION STATE MANAGEMENT ---
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'gen_pdf_bytes' not in st.session_state: st.session_state.gen_pdf_bytes = None
    if 'gen_excel_bytes' not in st.session_state: st.session_state.gen_excel_bytes = None

    def add_to_cart(selected_df):
        current_skus = {item['SKU Code'] for item in st.session_state.cart}
        new_items = []
        for _, row in selected_df.iterrows():
            if row['SKU Code'] not in current_skus:
                new_items.append(row.to_dict())
        
        if new_items:
            st.session_state.cart.extend(new_items)
            st.toast(f"Added {len(new_items)} items to catalogue.", icon="✨")
            st.session_state.gen_pdf_bytes = None
            st.session_state.gen_excel_bytes = None
        else:
            st.toast("Items already in catalogue.", icon="ℹ️")

    def remove_from_cart(skus_to_remove):
        st.session_state.cart = [item for item in st.session_state.cart if item['SKU Code'] not in skus_to_remove]
        st.session_state.gen_pdf_bytes = None
        st.session_state.gen_excel_bytes = None
        st.toast("Items removed.", icon="🗑️")

    # --- 4. GENERATORS ---
    def generate_pdf_html(df_sorted, customer_name, logo_b64):
        html = f"<html><head>{HTML_CSS}</head><body>"
        
        # Cover Page
        html += f"""
        <div class="cover-page">
            <div class="cover-content">
                <img src="data:image/png;base64,{logo_b64}" width="180" style="margin-bottom:20px;">
                <h1 class="brand-title">Collection</h1>
                <div class="collection-title">Exclusive Export Catalogue</div>
                <div class="client-name">Prepared For: {customer_name}</div>
            </div>
        </div>
        """
        
        # Product Groups
        for category, group in df_sorted.groupby('Category'):
            html += f'<div class="category-header">{category}</div>'
            html += '<div class="grid-container">'
            for _, row in group.iterrows():
                img = row['ImageB64']
                img_tag = f'<img src="data:image/png;base64,{img}">' if img else ''
                
                html += f"""
                <div class="card">
                    <div class="serial-tag">REF #{row['SerialNo']}</div>
                    <div class="img-box">{img_tag}</div>
                    <div class="card-meta">
                        <div class="p-name">{row.get('ItemName','')}</div>
                        <div class="p-frag">{row.get('Fragrance','')}</div>
                    </div>
                </div>
                """
            html += '</div>' # End Grid
            
        html += "</body></html>"
        return html

    def generate_excel_file(df_sorted, customer_name):
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        worksheet = workbook.add_worksheet('Order Sheet')

        # Styles
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2c2c2c', 'font_color': '#FFD700', 'border': 1})
        fmt_cell = workbook.add_format({'border': 1})
        fmt_input = workbook.add_format({'border': 1, 'bg_color': '#fffbe6'}) # Light gold input bg

        headers = ['Ref #', 'Item Name', 'Fragrance', 'Packaging', 'SKU Code', 'Order Qty']
        worksheet.write_row(0, 0, headers, fmt_header)

        for i, row in df_sorted.iterrows():
            r = i + 1
            data = [row['SerialNo'], row['ItemName'], row['Fragrance'], row['Packaging'], row['SKU Code']]
            worksheet.write_row(r, 0, data, fmt_cell)
            worksheet.write(r, 5, "", fmt_input) # Input cell

        worksheet.set_column(0, 0, 8)
        worksheet.set_column(1, 2, 30)
        worksheet.set_column(3, 4, 15)
        worksheet.set_column(5, 5, 15)

        writer.close()
        output.seek(0)
        return output

    # --- 5. MAIN UI ---
    products_df = load_data()
    
    st.title("Hem Luxury Catalogue Creator")
    
    tab_select, tab_review, tab_generate = st.tabs(["1. Filter & Select", "2. Review Cart", "3. Generate Files"])

    # --- TAB 1: SELECTION ---
    with tab_select:
        col_fil, col_res = st.columns([1, 3])
        
        with col_fil:
            st.subheader("Refine Search")
            search_txt = st.text_input("Search Keywords")
            cats_sel = st.multiselect("Categories", sorted(products_df['Category'].dropna().unique()))
            
        with col_res:
            mask = pd.Series(True, index=products_df.index)
            if search_txt: mask &= products_df['ItemName'].str.contains(search_txt, case=False) | products_df['SKU Code'].str.contains(search_txt, case=False)
            if cats_sel: mask &= products_df['Category'].isin(cats_sel)
            filtered_df = products_df[mask]
            
            st.markdown(f"**Showing {len(filtered_df)} products**")
            col_act1, col_act2 = st.columns([1, 3])
            if col_act1.button("Select ALL Filtered Results"):
                add_to_cart(filtered_df)
                
            display_df = filtered_df.head(200)[['SKU Code', 'ItemName', 'Category', 'Fragrance']]
            selection = st.data_editor(
                display_df.assign(Select=False),
                column_config={"Select": st.column_config.CheckboxColumn(required=True)},
                hide_index=True,
                use_container_width=True,
                height=500
            )
            if st.button("Add Selected Items"):
                selected_skus = selection[selection['Select']]['SKU Code'].tolist()
                if selected_skus:
                    add_to_cart(products_df[products_df['SKU Code'].isin(selected_skus)])

    # --- TAB 2: REVIEW ---
    with tab_review:
        if not st.session_state.cart:
            st.info("Your catalogue is empty.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.subheader(f"Current Catalogue: {len(cart_df)} Items")
            edit_cart = st.data_editor(
                cart_df[['SKU Code', 'ItemName', 'Category', 'Fragrance']].assign(Remove=False),
                column_config={"Remove": st.column_config.CheckboxColumn(required=True)},
                hide_index=True, use_container_width=True
            )
            if st.button("Remove Marked Items"):
                to_remove = edit_cart[edit_cart['Remove']]['SKU Code'].tolist()
                if to_remove:
                    remove_from_cart(to_remove)
                    st.rerun()
            if st.button("Clear Entire Catalogue", type="secondary"):
                st.session_state.cart = []
                st.session_state.gen_pdf_bytes = None
                st.session_state.gen_excel_bytes = None
                st.rerun()

    # --- TAB 3: GENERATE ---
    with tab_generate:
        st.header("Finalize & Export")
        if not st.session_state.cart:
            st.warning("Please add items first.")
        else:
            cust_name = st.text_input("Client Name (appears on cover)", value="Valued Client")
            if st.button("Generate Catalogue Files", type="primary"):
                with st.spinner("Designing PDF and preparing Excel sheet..."):
                    final_df = pd.DataFrame(st.session_state.cart).sort_values(['Category', 'ItemName']).reset_index(drop=True)
                    final_df['SerialNo'] = final_df.index + 1
                    
                    logo_b64 = get_image_as_base64_str(Path('assets') / 'logo.png')
                    html_content = generate_pdf_html(final_df, cust_name, logo_b64)
                    # Set to Landscape
                    pdf_opts = {
                        'page-size': 'A4', 
                        'orientation': 'Landscape',
                        'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
                        'encoding': "UTF-8", 'no-outline': None
                    }
                    st.session_state.gen_pdf_bytes = pdfkit.from_string(html_content, False, options=pdf_opts, configuration=CONFIG)
                    
                    excel_buffer = generate_excel_file(final_df, cust_name)
                    st.session_state.gen_excel_bytes = excel_buffer.getvalue()
                    st.success("Files generated successfully!")
            
            st.divider()
            if st.session_state.gen_pdf_bytes and st.session_state.gen_excel_bytes:
                col_d1, col_d2 = st.columns(2)
                clean_name = cust_name.replace(" ", "_")
                with col_d1:
                    st.download_button(label="📄 Download Landscape PDF", data=st.session_state.gen_pdf_bytes, file_name=f"Hem_Catalogue_{clean_name}.pdf", mime="application/pdf", key="dl_pdf")
                with col_d2:
                    st.download_button(label="📊 Download Order Excel", data=st.session_state.gen_excel_bytes, file_name=f"OrderSheet_{clean_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xls")