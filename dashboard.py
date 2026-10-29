"""OmniMart AI operations dashboard: streamlit run dashboard.py"""
import os
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="OmniMart AI · Operations", page_icon="🛒", layout="wide")
st.title("🛒 OmniMart AI")
st.caption("Phase 1 · Live checkout operations · Payments shown here are simulated")
api=st.sidebar.text_input("API base URL",os.getenv("OMNIMART_API_URL","http://localhost:8000/api"))
if st.sidebar.button("Refresh data"): st.rerun()
try:
    sessions=requests.get(f"{api}/sessions",timeout=4).json()
    products=requests.get(f"{api}/products",timeout=4).json()
except requests.RequestException as e:
    st.error(f"Could not connect to FastAPI at {api}. Start the backend, then refresh. ({e})")
    st.stop()
df=pd.DataFrame(sessions)
paid=df[df.status.eq("paid")] if not df.empty else pd.DataFrame()
c1,c2,c3,c4=st.columns(4)
c1.metric("Visits",len(df));c2.metric("Paid checkouts",len(paid));c3.metric("Simulated revenue",f"₹{paid.total.sum() if not paid.empty else 0:,.2f}");c4.metric("Active visits",int(df.status.eq("active").sum()) if not df.empty else 0)
left,right=st.columns([1.35,1])
with left:
    st.subheader("Recent visits")
    if not df.empty:
        shown=df.copy();shown["created_at"]=pd.to_datetime(shown.created_at,errors="coerce");st.dataframe(shown.sort_values("created_at",ascending=False),use_container_width=True,hide_index=True)
    else:st.info("No visits yet.")
with right:
    st.subheader("Catalog by category")
    pdf=pd.DataFrame(products)
    if not pdf.empty:st.bar_chart(pdf.groupby("category").size().rename("Products"))
st.subheader("Checkout outcomes")
if not df.empty:st.bar_chart(df.groupby("status").size().rename("Visits"))
st.subheader("Product catalog")
if not pdf.empty:st.dataframe(pdf[["name","category","price","stock"]],use_container_width=True,hide_index=True)
