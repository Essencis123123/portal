import streamlit as st
import pandas as pd

# Load the materials data from the Excel file
@st.cache_data
def load_data():
    df = pd.read_excel('Códigos Oracle.xlsx')
    return df

# Initialize Streamlit app
st.title('Search Materials')

# Load data
data = load_data()

# Search functionality
search_keyword = st.text_input('Search by Código or Nome')

# Filtering DataFrame based on the search keyword
if search_keyword:
    filtered_data = data[data['código'].astype(str).str.contains(search_keyword) | 
                         data['nome'].str.contains(search_keyword, case=False)]
else:
    filtered_data = data

# Pagination setup
page_size = 10
page_number = st.number_input('Select page number:', 1, len(filtered_data) // page_size + 1)

# Displaying data in a table format
start_row = (page_number - 1) * page_size
end_row = start_row + page_size
st.dataframe(filtered_data.iloc[start_row:end_row])

# Show total materials found
st.write(f'Total materials found: {len(filtered_data)}')
