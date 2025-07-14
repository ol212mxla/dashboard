import streamlit as st
import pandas as pd

df = pd.read_csv("Returning_Customers_Last_30_Days_2025-06-14_to_2025-07-13.csv")

st.title("Analytics for maxfieldla.com, Last 30 Days")

st.header("Returning Customers")
st.dataframe(df)

