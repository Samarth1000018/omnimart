"""Phase two review dashboard for persisted signal exports."""
import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="OmniMart AI · Loss prevention review",page_icon="🧭",layout="wide")
st.title("🧭 Store activity review")
st.caption("Phase 2 · Explainable signals for human review; alerts do not establish intent.")
path=st.sidebar.text_input("Signals CSV",os.getenv("OMNIMART_SIGNALS_CSV","signals.csv"))
if not os.path.exists(path):
    st.info(f"No signal export found at `{path}`. Connect the tracking service or point to a CSV export.")
    st.stop()
df=pd.read_csv(path)
if df.empty:st.success("No review signals in this export.");st.stop()
for col,default in [("score",0),("signal","unknown"),("track_id","unknown"),("at","")]:
    if col not in df:df[col]=default
c1,c2,c3=st.columns(3);c1.metric("Review signals",len(df));c2.metric("Tracks",df.track_id.nunique());c3.metric("High score (≥0.6)",int((pd.to_numeric(df.score,errors="coerce")>=.6).sum()))
st.subheader("Signal volume")
st.bar_chart(df.groupby("signal").size().rename("Events"))
st.subheader("Review queue")
threshold=st.slider("Minimum signal score",0.0,1.0,0.0,.05)
filtered=df[pd.to_numeric(df.score,errors="coerce").fillna(0)>=threshold].sort_values("score",ascending=False)
st.dataframe(filtered,use_container_width=True,hide_index=True)
