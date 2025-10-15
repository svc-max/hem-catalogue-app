# --- CORRECTED SCRIPT FOR CUSTOMER PORTAL (v. Oct 15) ---
import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from datetime import datetime
import json
import os
import urllib.parse

# --- GLOBAL CONFIGURATION & SETUP ---
SELECTIONS_DIR = Path("selections")
SELECTIONS_DIR.mkdir(exist_ok=True)

# --- HELPER FUNCTIONS ---

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
    st.title("Hem Catalogue App")
    st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect. Please try again.")
    return False

@st.cache_data
def load_data():
    products_df = pd.read_excel('products_master.xlsx', dtype={'SKU Code': str})
    packaging_df = pd.read_excel('packaging_master.xlsx')
    customers_df = pd.read_excel('customers_master.xlsx')
    countries_df = pd.read_excel('countries_master.xlsx')
    rules_df = pd.read_excel('exclusivity_rules.xlsx', dtype={'SKU Code': str})
    products_df['ImagePath'] = products_df['ImageFileName'].apply(lambda x: Path('images') / str(x) if pd.notna(x) else None)
    return products_df, packaging_df, customers_df, countries_df, rules_df

def get_selections():
    return ["---"] + [f.stem for f in SELECTIONS_DIR.glob("*.json")]

def load_selection():
    selection_name = st.session_state.selected_preset
    if selection_name and selection_name != "---":
        filepath = SELECTIONS_DIR / f"{selection_name}.json"
        with open(filepath, 'r') as f: data = json.load(f)
        for key, value in data.items(): st.session_state[key] = value
        st.toast(f"Loaded selection: {selection_name}", icon="✅")

def save_selection():
    selection_name = st.session_state.get("selection_name_input", "").strip()
    if not selection_name:
        st.sidebar.warning("Please enter a name for the selection.")
        return
    filepath = SELECTIONS_DIR / f"{selection_name}.json"
    state_to_save = { 'customer': st.session_state.get('customer'), 'country': st.session_state.get('country'),
                      'categories': st.session_state.get('categories'), 'packaging': st.session_state.get('packaging'),
                      'brands': st.session_state.get('brands'), 'fragrances': st.session_state.get('fragrances') }
    with open(filepath, 'w') as f: json.dump(state_to_save, f, indent=4)
    st.sidebar.success(f"Saved selection: {selection_name}")
    st.session_state["selection_name_input"] = ""

def toggle_all_items(key_for_multiselect, options_list, key_for_checkbox):
    if st.session_state[key_for_checkbox]: st.session_state[key_for_multiselect] = options_list
    else: st.session_state[key_for_multiselect] = []

# --- VIEW: Salesperson Tool ---
def render_salesperson_view():
    st.set_page_config(page_title="Hem Catalogue Link Generator", page_icon="🔗", layout="wide")
    
    products_df, _, customers_df, countries_df, rules_df = load_data()
    
    categories_list = sorted(products_df['Category'].dropna().unique())
    packaging_list = sorted(products_df['Packaging'].dropna().unique())
    brands_list = sorted(products_df['Brand'].dropna().unique())
    fragrances_list = sorted(products_df['Fragrance'].dropna().unique())
    customer_list = ["-- General / No Customer --"] + sorted(customers_df['CustomerName'].dropna().unique())
    country_list = ["-- General / No Country --"] + sorted(countries_df['CountryName'].dropna().unique())

    if 'filters_initialized' not in st.session_state:
        st.session_state.customer = customer_list[0]
        st.session_state.country = country_list[0]
        st.session_state.categories = categories_list
        st.session_state.packaging = packaging_list
        st.session_state.brands = brands_list
        st.session_state.fragrances = fragrances_list
        st.session_state.filters_initialized = True

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
        st.checkbox("Select All Categories", value=len(st.session_state.get('categories', [])) == len(categories_list), key='all_cat_checkbox', on_change=toggle_all_items, args=('categories', categories_list, 'all_cat_checkbox'))
        st.multiselect('Filter by Category', options=categories_list, key='categories')
        st.sidebar.divider()
        st.checkbox("Select All Packaging", value=len(st.session_state.get('packaging', [])) == len(packaging_list), key='all_pkg_checkbox', on_change=toggle_all_items, args=('packaging', packaging_list, 'all_pkg_checkbox'))
        st.multiselect('Filter by Packaging', options=packaging_list, key='packaging')
    with st.sidebar.expander("Filter by Specifics"):
        st.multiselect('Filter by Brand', options=brands_list, key='brands')
        st.multiselect('Filter by Fragrance', options=fragrances_list, key='fragrances')
    
    with st.sidebar.expander("Save Current Selection"):
        st.text_input("Enter selection name", key="selection_name_input")
        st.button("Save Filters", on_click=save_selection)

    st.title("Dynamic Customer Link Generator 🔗")
    st.caption("Use the filters on the left to create a product selection, then generate a unique order link for your customer.")
    
    with st.container(border=True):
        if st.button("Generate Customer Order Link", type="primary"):
            params = {
                "customer": st.session_state.customer if st.session_state.customer != "-- General / No Customer --" else "",
                "country": st.session_state.country if st.session_state.country != "-- General / No Country --" else "",
                "categories": st.session_state.categories, "packaging": st.session_state.packaging,
                "brands": st.session_state.brands, "fragrances": st.session_state.fragrances
            }
            base_url = "https://hem-order.streamlit.app/" 
            query_string = urllib.parse.urlencode(params, doseq=True)
            final_url = base_url + "?" + query_string
            st.success("Link Generated!")
            st.markdown("Copy the link below and send it to your customer:")
            st.code(final_url)

    st.markdown("---")

    try:
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
        filtered_df = base_filtered_df[base_filtered_df['Category'].isin(st.session_state.categories) & base_filtered_df['Packaging'].isin(st.session_state.packaging) & base_filtered_df['Brand'].isin(st.session_state.brands) & base_filtered_df['Fragrance'].isin(st.session_state.fragrances)].copy()

        st.header("Salesperson Preview")
        st.caption("A compact, searchable view of the selected products for verification.")
        if filtered_df.empty:
            st.warning("No products match the current filter selection.")
        else:
            preview_df = filtered_df.copy()
            exclusivity_info = rules_df[['SKU Code', 'RuleType', 'RuleValue']].copy()
            exclusivity_info['Exclusivity'] = exclusivity_info['RuleType'] + ": " + exclusivity_info['RuleValue']
            preview_df = pd.merge(preview_df, exclusivity_info[['SKU Code', 'Exclusivity']], on='SKU Code', how='left')
            preview_df['Exclusivity'] = preview_df['Exclusivity'].fillna('General')
            preview_df['Product'] = preview_df['ItemName'] + " - " + preview_df['Fragrance']
            final_columns = ['Category', 'Packaging', 'Product', 'Exclusivity', 'SKU Code']
            st.dataframe(preview_df[final_columns], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# --- VIEW: Customer Order Portal ---
def render_customer_view():
    st.set_page_config(page_title="Hem Order Portal", page_icon="📝", layout="wide")
    
    products_df, _, _, _, rules_df = load_data()
    
    # --- CORRECTED & ROBUST PARAMETER HANDLING ---
    params = st.query_params
    
    customer_list = params.get_all("customer")
    customer = customer_list[0] if customer_list and customer_list[0] else None
    
    country_list = params.get_all("country")
    country = country_list[0] if country_list and country_list[0] else None
    
    selected_categories = params.get_all("categories")
    selected_packaging = params.get_all("packaging")
    selected_brands = params.get_all("brands")
    selected_fragrances = params.get_all("fragrances")

    st.title(f"Product Catalogue for {customer}" if customer else "Product Catalogue")
    st.markdown("---")
    
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
    
    filtered_df = base_filtered_df[ base_filtered_df['Category'].isin(selected_categories) & base_filtered_df['Packaging'].isin(selected_packaging) & base_filtered_df['Brand'].isin(selected_brands) & base_filtered_df['Fragrance'].isin(selected_fragrances) ].copy()

    if filtered_df.empty:
        st.warning("No products match the specified selection.")
    else:
        st.header("Product List")
        st.dataframe(filtered_df[['SKU Code', 'ItemName', 'Fragrance', 'Packaging', 'ImageFileName']], hide_index=True)
        
# --- MAIN LOGIC: The "Router" ---
if st.query_params:
    render_customer_view()
else:
    if check_password():
        render_salesperson_view()