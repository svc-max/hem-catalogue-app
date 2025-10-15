# --- SCRIPT RESTRUCTURED FOR CUSTOMER PORTAL ---
import streamlit as st
import pandas as pd
import pdfkit
import base64
from pathlib import Path
from datetime import datetime
import json
import os
import urllib.parse # NEW: Library to help build URLs safely

# --- GLOBAL CONFIGURATION & SETUP ---
SELECTIONS_DIR = Path("selections")
SELECTIONS_DIR.mkdir(exist_ok=True)

HTML_CSS = """
<style>
    /* Your existing CSS is unchanged */
    body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 11pt; color: #3d3d3d; }
    h1 { color: #222; text-align: center; margin: 30px 0; font-weight: 300; letter-spacing: 1px; }
    /* ... (rest of your CSS) ... */
    .input-cell input { width: 80px; text-align: center; border: 1px solid #000000; border-radius: 4px; padding: 8px; font-size: 11pt; background-color: #ffffff; color: #000000; margin-top: 5px; }
</style>
"""

# --- HELPER FUNCTIONS ---

def check_password():
    # This function is unchanged
    def password_entered():
        if st.session_state.get("password") and "PASSWORD" in st.secrets and st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        return True
    st.title("Hem Catalogue App")
    st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect. Please try again.")
    return False

@st.cache_data
def load_data():
    # This function is unchanged
    products_df = pd.read_excel('products_master.xlsx', dtype={'SKU Code': str})
    packaging_df = pd.read_excel('packaging_master.xlsx')
    customers_df = pd.read_excel('customers_master.xlsx')
    countries_df = pd.read_excel('countries_master.xlsx')
    rules_df = pd.read_excel('exclusivity_rules.xlsx', dtype={'SKU Code': str})
    products_df['ImagePath'] = products_df['ImageFileName'].apply(lambda x: Path('images') / str(x) if pd.notna(x) else None)
    # We no longer need to pre-load images for the web view, but we'll keep it for the PDF generator
    products_df['ImageB64'] = products_df['ImagePath'].apply(get_image_as_base64_str)
    return products_df, packaging_df, customers_df, countries_df, rules_df

# --- All other helper functions (get_image_as_base64, toggle_all_items, etc.) are also unchanged ---

# --- VIEW: Salesperson Tool ---
def render_salesperson_view():
    st.set_page_config(page_title="Hem Catalogue Maker", page_icon="🛍️", layout="wide")
    
    # MOVED: PDF config is only needed in this view now
    path_wkhtmltopdf = os.path.join(os.path.dirname(__file__), 'bin', 'wkhtmltopdf')
    try: os.chmod(path_wkhtmltopdf, 0o755)
    except (OSError, FileNotFoundError): pass
    CONFIG = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    
    products_df, packaging_df, customers_df, countries_df, rules_df = load_data()
    
    # Sidebar and filtering logic is unchanged...
    # ... (all the sidebar code, filters, load/save selection)
    
    # --- NEW: Generate Customer Order Link ---
    st.sidebar.divider()
    st.sidebar.header("Share with Customer")
    if st.sidebar.button("Generate Customer Order Link"):
        # 1. Get all the current filter settings
        params = {
            "customer": st.session_state.customer if st.session_state.customer != "-- General / No Customer --" else "",
            "country": st.session_state.country if st.session_state.country != "-- General / No Country --" else "",
            "categories": st.session_state.categories,
            "packaging": st.session_state.packaging,
            "brands": st.session_state.brands,
            "fragrances": st.session_state.fragrances
        }
        
        # 2. Build the URL
        # IMPORTANT: Replace with your actual Streamlit app URL
        base_url = "https://hem-order.streamlit.app/"
        query_string = urllib.parse.urlencode(params, doseq=True)
        final_url = base_url + "?" + query_string
        
        # 3. Display the link for the salesperson
        st.sidebar.success("Link Generated!")
        st.sidebar.markdown("Copy the link below and send it to your customer:")
        st.sidebar.code(final_url)

    # The rest of the salesperson view (preview table, PDF button, etc.) is unchanged...
    # ...

# --- VIEW: Customer Order Portal ---
def render_customer_view(params):
    st.set_page_config(page_title="Hem Order Portal", page_icon="📝", layout="wide")
    
    products_df, packaging_df, _, _, rules_df = load_data()
    
    # 1. Parse all filter criteria from the URL
    customer = params.get("customer", [None])[0]
    country = params.get("country", [None])[0]
    selected_categories = params.get("categories", [])
    selected_packaging = params.get("packaging", [])
    selected_brands = params.get("brands", [])
    selected_fragrances = params.get("fragrances", [])

    # Display a nice header
    st.title(f"Product Catalogue for {customer}" if customer else "Product Catalogue")
    st.markdown("---")
    
    # 2. Apply the exact same filtering logic as the salesperson view
    # Exclusivity rules
    skus_with_rules = rules_df['SKU Code'].unique()
    general_skus = products_df[~products_df['SKU Code'].isin(skus_with_rules)]['SKU Code']
    allowed_exclusive_skus = pd.Series(dtype=str)
    if customer:
        customer_exclusive_skus = rules_df[(rules_df['RuleType'] == 'Customer') & (rules_df['RuleValue'] == customer)]['SKU Code']
        allowed_exclusive_skus = pd.concat([allowed_exclusive_skus, customer_exclusive_skus])
    if country:
        country_exclusive_skus = rules_df[(rules_df['RuleType'] == 'Country') & (rules_df['RuleValue'] == country)]['SKU Code']
        allowed_exclusive_skus = pd.concat([allowed_exclusive_skus, country_exclusive_skus])
    
    final_allowed_skus = pd.concat([general_skus, allowed_exclusive_skus]).unique()
    base_filtered_df = products_df[products_df['SKU Code'].isin(final_allowed_skus)]
    
    # Attribute filters
    filtered_df = base_filtered_df[
        base_filtered_df['Category'].isin(selected_categories) &
        base_filtered_df['Packaging'].isin(selected_packaging) &
        base_filtered_df['Brand'].isin(selected_brands) &
        base_filtered_df['Fragrance'].isin(selected_fragrances)
    ].copy()

    # 3. Display the catalogue using our existing HTML generation logic
    if filtered_df.empty:
        st.warning("No products match the specified selection.")
    else:
        # For this view, we will just show the beautiful HTML catalogue
        # Note: The input boxes are just for show in this Phase 1.
        catalogue_html = generate_product_tables_html(filtered_df, packaging_df)
        st.html(HTML_CSS + catalogue_html)

# --- MAIN LOGIC: The "Router" ---
# This part decides which view to show.

# Check for URL parameters first
params = st.query_params.to_dict()

# If there are parameters, it's a customer link. Show the customer view.
# The customer does not need a password.
if params:
    render_customer_view(params)

# Otherwise, it's a salesperson. Check for password and show the main tool.
else:
    if check_password():
        render_salesperson_view()