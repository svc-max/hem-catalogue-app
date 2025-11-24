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

    # DESIGN: Luxury Gold/Black Theme (Based on your reference image)
    HTML_CSS = """
    <style>
        @page { size: A4 portrait; margin: 0; } /* Portrait works better for the aesthetic reference */
        body { 
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; 
            color: #2c2c2c; 
            margin: 0; padding: 0;
            -webkit-print-color-adjust: exact; 
        }
        
        /* TYPOGRAPHY */
        h1, h2, h3 { font-family: 'Georgia', serif; font-weight: normal; }
        
        /* COVER PAGE */
        .cover-page {
            height: 100vh; width: 100%;
            background: linear-gradient(135deg, #fff 0%, #f9f9f9 100%);
            position: relative;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center;
            page-break-after: always;
        }
        .cover-accent {
            position: absolute; top: 0; left: 0; width: 30%; height: 100%;
            background-color: #FFD700; /* Gold Accent */
            opacity: 0.2;
            z-index: 0;
        }
        .cover-content { z-index: 1; padding: 40px; border: 4px solid #2c2c2c; background: #fff; }
        .brand-title { font-size: 60pt; letter-spacing: 5px; margin: 0; text-transform: uppercase; color: #000; }
        .collection-title { font-size: 24pt; font-style: italic; color: #555; margin-top: 10px; margin-bottom: 40px; }
        .client-name { font-size: 14pt; text-transform: uppercase; letter-spacing: 2px; color: #2c2c2c; border-top: 1px solid #ccc; padding-top: 20px; }

        /* CONTENT PAGES */
        .page-header {
            padding: 30px 40px;
            display: flex; justify-content: space-between; align-items: flex-end;
            border-bottom: 2px solid #FFD700; /* Gold Line */
            margin-bottom: 30px;
        }
        .cat-title { font-size: 32pt; margin: 0; color: #000; }
        .brand-small { font-size: 10pt; color: #999; text-transform: uppercase; letter-spacing: 2px; }

        /* GRID LAYOUT (4 Columns for aesthetic density) */
        .grid-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 0 40px 40px 40px;
        }

        /* PRODUCT CARD */
        .card {
            background: #fff;
            border: none;
            position: relative;
            page-break-inside: avoid;
        }
        
        /* Image styling */
        .img-box {
            width: 100%; height: 160px;
            background: #f4f4f4;
            display: flex; justify-content: center; align-items: center;
            margin-bottom: 15px;
        }
        .img-box img { max-width: 90%; max-height: 90%; object-fit: contain; mix-blend-mode: multiply; }
        
        /* Text styling */
        .card-meta { text-align: left; }
        .p-name { font-family: 'Georgia', serif; font-size: 11pt; font-weight: bold; color: #000; margin-bottom: 5px; line-height: 1.3; }
        .p-frag { font-size: 9pt; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        
        /* Serial Number Badge - Aesthetic Style */
        .serial-tag {
            display: inline-block;
            background-color: #FFD700;
            color: #000;
            font-size: 8pt;
            font-weight: bold;
            padding: 3px 8px;
            margin-bottom: 5px;
        }
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
            # Clear previous generated files since cart changed
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
            <div class="cover-accent"></div>
            <div class="cover-content">
                <img src="data:image/png;base64,{logo_b64}" width="200" style="margin-bottom:20px;">
                <h1 class="brand-title">Collection</h1>
                <div class="collection-title">Exclusive Export Catalogue</div>
                <div class="client-name">Prepared For: {customer_name}</div>
            </div>
        </div>
        """
        
        # Product Pages
        for category, group in df_sorted.groupby('Category'):
            html += f"""
            <div style="page-break-after: always;">
                <div class="page-header">
                    <h2 class="cat-title">{category}</h2>
                    <div class="brand-small">Hem Corporation</div>
                </div>
                <div class="grid-container">
            """
            for _, row in group.iterrows():
                img = row['ImageB64']
                img_tag = f'<img src="data:image/png;base64,{img}">' if img else ''
                
                html += f"""
                <div class="card">
                    <div class="img-box">{img_tag}</div>
                    <div class="card-meta">
                        <div class="serial-tag">REF #{row['SerialNo']}</div>
                        <div class="p-name">{row.get('ItemName','')}</div>
                        <div class="p-frag">{row.get('Fragrance','')}</div>
                    </div>
                </div>
                """
            html += '</div></div>' # End Grid / Page
            
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
            # Filter Data
            mask = pd.Series(True, index=products_df.index)
            if search_txt: mask &= products_df['ItemName'].str.contains(search_txt, case=False) | products_df['SKU Code'].str.contains(search_txt, case=False)
            if cats_sel: mask &= products_df['Category'].isin(cats_sel)
            
            filtered_df = products_df[mask]
            
            st.markdown(f"**Showing {len(filtered_df)} products**")
            
            # ACTIONS ROW
            col_act1, col_act2 = st.columns([1, 3])
            
            # 1. Select All Button
            if col_act1.button("Select ALL Filtered Results"):
                add_to_cart(filtered_df)
                
            # 2. Manual Selection
            # Limit display to 200 rows to prevent UI lag
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
            st.info("Your catalogue is empty. Go to 'Filter & Select' to add products.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.subheader(f"Current Catalogue: {len(cart_df)} Items")
            
            # Edit to Remove
            edit_cart = st.data_editor(
                cart_df[['SKU Code', 'ItemName', 'Category', 'Fragrance']].assign(Remove=False),
                column_config={"Remove": st.column_config.CheckboxColumn(required=True)},
                hide_index=True,
                use_container_width=True
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
            st.warning("Please add items to the catalogue first.")
        else:
            cust_name = st.text_input("Client Name (appears on cover)", value="Valued Client")
            
            # GENERATE BUTTON
            # This generates the bytes and stores them in session state
            if st.button("Generate Catalogue Files", type="primary"):
                with st.spinner("Designing PDF and preparing Excel sheet..."):
                    # Prepare Data
                    final_df = pd.DataFrame(st.session_state.cart).sort_values(['Category', 'ItemName']).reset_index(drop=True)
                    final_df['SerialNo'] = final_df.index + 1
                    
                    # PDF Gen
                    logo_b64 = get_image_as_base64_str(Path('assets') / 'logo.png')
                    html_content = generate_pdf_html(final_df, cust_name, logo_b64)
                    pdf_opts = {
                        'page-size': 'A4', 
                        'orientation': 'Portrait', # Changed to Portrait for magazine/aesthetic feel
                        'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
                        'encoding': "UTF-8",
                        'no-outline': None
                    }
                    st.session_state.gen_pdf_bytes = pdfkit.from_string(html_content, False, options=pdf_opts, configuration=CONFIG)
                    
                    # Excel Gen
                    excel_buffer = generate_excel_file(final_df, cust_name)
                    st.session_state.gen_excel_bytes = excel_buffer.getvalue()
                    
                    st.success("Files generated successfully! Download links below.")
            
            st.divider()
            
            # DOWNLOAD BUTTONS
            # We check if the bytes exist in session state. If so, we show the buttons.
            # This persists even if the user clicks one button and the script re-runs.
            if st.session_state.gen_pdf_bytes and st.session_state.gen_excel_bytes:
                col_d1, col_d2 = st.columns(2)
                
                clean_name = cust_name.replace(" ", "_")
                
                with col_d1:
                    st.download_button(
                        label="📄 Download Aesthetic PDF",
                        data=st.session_state.gen_pdf_bytes,
                        file_name=f"Hem_Catalogue_{clean_name}.pdf",
                        mime="application/pdf",
                        key="dl_pdf" # Unique key
                    )
                    
                with col_d2:
                    st.download_button(
                        label="📊 Download Order Excel",
                        data=st.session_state.gen_excel_bytes,
                        file_name=f"OrderSheet_{clean_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_xls" # Unique key
                    )