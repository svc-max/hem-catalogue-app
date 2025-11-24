import streamlit as st
import pandas as pd
import pdfkit
import base64
from pathlib import Path
from datetime import datetime
import io
import os

# --- 1. Password Protection ---
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
    st.set_page_config(page_title="Hem Gallery Maker", page_icon="📸", layout="wide")

    # --- 2. PDF Configuration & CSS ---
    path_wkhtmltopdf = os.path.join(os.path.dirname(__file__), 'bin', 'wkhtmltopdf')
    try:
        os.chmod(path_wkhtmltopdf, 0o755)
    except: pass
    CONFIG = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    # DESIGN PHILOSOPHY: "Apple Store" style. Clean, white space, product focus.
    HTML_CSS = """
    <style>
        @page { size: A4 landscape; margin: 10mm; }
        body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; color: #333; -webkit-print-color-adjust: exact; }
        
        /* Cover Page */
        .cover { height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; page-break-after: always; }
        .cover-title { font-size: 50pt; font-weight: 100; letter-spacing: 3px; text-transform: uppercase; margin: 20px 0; }
        .cover-sub { font-size: 18pt; color: #777; }

        /* Headers */
        .category-header { 
            font-size: 16pt; font-weight: 700; color: #000; 
            border-bottom: 2px solid #000; margin: 20px 0 15px 0; 
            padding-bottom: 5px; text-transform: uppercase;
            page-break-after: avoid;
        }

        /* The Grid - High Density (5 Columns) */
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr); 
            gap: 15px;
            row-gap: 25px;
        }

        /* Product Card */
        .card {
            position: relative;
            border: 1px solid #f0f0f0;
            break-inside: avoid;
            page-break-inside: avoid;
            background: #fff;
        }

        /* The Serial Number Badge - The Visual Anchor */
        .serial-badge {
            position: absolute;
            top: 0; left: 0;
            background-color: #000;
            color: #fff;
            font-size: 10pt;
            font-weight: bold;
            padding: 4px 8px;
            z-index: 10;
        }

        /* Image Area */
        .img-container {
            height: 140px; /* Compact height */
            width: 100%;
            display: flex; align-items: center; justify-content: center;
            padding: 5px;
            box-sizing: border-box;
            background: #fff;
        }
        .img-container img { max-height: 100%; max-width: 100%; object-fit: contain; }

        /* Text Area */
        .info-container {
            padding: 8px 5px;
            text-align: center;
            background: #fafafa;
            border-top: 1px solid #eee;
            min-height: 50px;
        }
        .p-name { font-size: 9pt; font-weight: 700; color: #222; line-height: 1.2; margin-bottom: 3px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
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

    # --- 3. Shopping Cart Logic ---
    if 'cart' not in st.session_state: st.session_state.cart = []

    def add_to_cart(selected_df):
        current_skus = {item['SKU Code'] for item in st.session_state.cart}
        new_items = [row.to_dict() for _, row in selected_df.iterrows() if row['SKU Code'] not in current_skus]
        st.session_state.cart.extend(new_items)
        st.toast(f"Added {len(new_items)} items!", icon="➕")

    # --- 4. Generators ---
    
    def generate_pdf_html(df_sorted, customer_name, logo_b64):
        # df_sorted must have 'SerialNo' column
        html = f"<html><head>{HTML_CSS}</head><body>"
        
        # Cover
        html += f"""<div class="cover"><img src="data:image/png;base64,{logo_b64}" width="150"><div class="cover-title">Product Gallery</div><div class="cover-sub">Prepared for {customer_name}</div></div>"""
        
        # Gallery
        for category, group in df_sorted.groupby('Category'):
            html += f'<div class="category-header">{category}</div>'
            html += '<div class="gallery-grid">'
            for _, row in group.iterrows():
                img = row['ImageB64']
                img_tag = f'<img src="data:image/png;base64,{img}">' if img else '<span style="color:#ccc; font-size:9pt;">No Image</span>'
                
                html += f"""
                <div class="card">
                    <div class="serial-badge">#{row['SerialNo']}</div>
                    <div class="img-container">{img_tag}</div>
                    <div class="info-container">
                        <div class="p-name">{row.get('ItemName','')}</div>
                        <div class="p-frag">{row.get('Fragrance','')}</div>
                    </div>
                </div>
                """
            html += '</div>' # End Grid
        html += "</body></html>"
        return html

    def generate_excel_order_form(df_sorted, customer_name):
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        worksheet = workbook.add_worksheet('Order Form')

        # Formats
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#000000', 'font_color': '#FFFFFF', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1})
        input_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFFACD'}) # Light yellow for input

        # Headers
        headers = ['Ref #', 'Category', 'Item Name', 'Fragrance', 'Packaging', 'SKU Code', 'Order Qty (Ctns)']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_fmt)

        # Data
        for i, row in df_sorted.iterrows():
            r = i + 1
            worksheet.write(r, 0, row['SerialNo'], cell_fmt)
            worksheet.write(r, 1, row['Category'], cell_fmt)
            worksheet.write(r, 2, row['ItemName'], cell_fmt)
            worksheet.write(r, 3, row['Fragrance'], cell_fmt)
            worksheet.write(r, 4, row['Packaging'], cell_fmt)
            worksheet.write(r, 5, row['SKU Code'], cell_fmt)
            worksheet.write(r, 6, "", input_fmt) # Empty cell for input

        # Adjust Widths
        worksheet.set_column(0, 0, 8)  # Ref
        worksheet.set_column(1, 1, 20) # Category
        worksheet.set_column(2, 3, 30) # Name/Frag
        worksheet.set_column(4, 5, 20) # Pkg/SKU
        worksheet.set_column(6, 6, 15) # Qty

        writer.close()
        output.seek(0)
        return output

    # --- 5. UI Layout ---
    products_df = load_data()
    
    st.title("Hem Gallery & Order Sheet Generator")
    
    col_L, col_R = st.columns([1, 2])
    
    with col_L:
        st.subheader("1. Filter & Add")
        with st.expander("Search Filters", expanded=True):
            search = st.text_input("Search Name/SKU")
            cats = st.multiselect("Categories", sorted(products_df['Category'].dropna().unique()))
            
            # Filter Logic
            mask = pd.Series(True, index=products_df.index)
            if search: mask &= products_df['ItemName'].str.contains(search, case=False) | products_df['SKU Code'].str.contains(search, case=False)
            if cats: mask &= products_df['Category'].isin(cats)
            
            results = products_df[mask]
        
        st.write(f"Found: {len(results)}")
        
        # Simplified Adder
        # We just take the first 500 matches to prevent UI lag if they search empty
        to_show = results.head(500)[['SKU Code', 'ItemName', 'Category', 'Fragrance']]
        selected_rows = st.data_editor(
            to_show.assign(Add=False), 
            column_config={"Add": st.column_config.CheckboxColumn(required=True)},
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        if st.button("Add Selected to Gallery", type="primary"):
             skus = selected_rows[selected_rows['Add']]['SKU Code'].tolist()
             if skus:
                 add_to_cart(products_df[products_df['SKU Code'].isin(skus)])
                 
    with col_R:
        st.subheader("2. Review & Download")
        if not st.session_state.cart:
            st.info("Gallery is empty.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.markdown(f"### Total Items: {len(cart_df)}")
            
            # Show simple list
            st.dataframe(cart_df[['Category', 'ItemName', 'Fragrance']], height=300, use_container_width=True)
            
            if st.button("Clear Gallery"):
                st.session_state.cart = []
                st.rerun()
            
            st.divider()
            st.subheader("3. Generate Files")
            cust_name = st.text_input("Customer Name", value="Valued Partner")
            
            if st.button("🚀 Generate Package (PDF + Excel)"):
                with st.spinner("Processing..."):
                    # Sort the cart for logical flow
                    final_df = cart_df.sort_values(['Category', 'ItemName']).reset_index(drop=True)
                    # Assign Serial Numbers (1 to N)
                    final_df['SerialNo'] = final_df.index + 1
                    
                    # 1. Generate PDF
                    logo_b64 = get_image_as_base64_str(Path('assets')/ 'logo.png')
                    html = generate_pdf_html(final_df, cust_name, logo_b64)
                    pdf_options = {
                        'page-size': 'A4', 'orientation': 'Landscape',
                        'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
                        'encoding': "UTF-8"
                    }
                    pdf_bytes = pdfkit.from_string(html, False, options=pdf_options, configuration=CONFIG)
                    
                    # 2. Generate Excel
                    excel_buffer = generate_excel_order_form(final_df, cust_name)
                    
                    # 3. Download Buttons
                    col_d1, col_d2 = st.columns(2)
                    file_name_base = cust_name.replace(" ", "_")
                    
                    col_d1.download_button(
                        "📥 Download Visual PDF", 
                        pdf_bytes, 
                        f"Gallery_{file_name_base}.pdf", 
                        "application/pdf"
                    )
                    
                    col_d2.download_button(
                        "📥 Download Excel Order Form", 
                        excel_buffer, 
                        f"OrderForm_{file_name_base}.xlsx", 
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("Files generated! The PDF and Excel Serial Numbers match perfectly.")