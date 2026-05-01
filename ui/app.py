import streamlit as st
import httpx, json

st.set_page_config(page_title="AI Debate Arena", layout="wide")
st.title("🎙️ AI Debate Arena")

topic  = st.text_input("Debate topic", placeholder="AI will replace software engineers")
rounds = st.slider("Number of rounds", 1, 5, 3)

if st.button("Start debate") and topic:
    with st.spinner("Debate in progress…"):
        try:
            resp = httpx.post(
                "http://localhost:8000/debate",
                json={"topic": topic, "max_rounds": rounds},
                timeout=300,
            )
        except httpx.ConnectError:
            st.error("❌ Cannot reach the debate API (is FastAPI running on port 8000?)")
            st.stop()

    # Surface any HTTP-level errors before touching the body
    if not resp.is_success:
        st.error(f"API returned {resp.status_code}: {resp.text or '(empty body)'}")
        st.stop()

    try:
        data = resp.json()
    except json.JSONDecodeError:
        st.error(f"API response is not valid JSON:\n\n{resp.text}")
        st.stop()

    verdict      = data["verdict"]
    winner_color = "🟦" if verdict["winner"] == "proponent" else "🟥"
    st.success(f"{winner_color} Winner: **{verdict['winner'].upper()}** — {verdict['reasoning']}")
    st.info(f"Key turning point: {verdict['key_turning_point']}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟦 Proponent")
        st.metric("Total score", verdict["proponent_total"])
        for i, msg in enumerate(data["transcript"]["proponent"]):
            with st.expander(f"Round {i + 1} argument"):
                st.write(msg["content"])
                if msg.get("evidence"):
                    st.caption("Sources: " + " | ".join(msg["evidence"]))
    with col2:
        st.subheader("🟥 Opponent")
        st.metric("Total score", verdict["opponent_total"])
        for i, msg in enumerate(data["transcript"]["opponent"]):
            with st.expander(f"Round {i + 1} argument"):
                st.write(msg["content"])
                if msg.get("evidence"):
                    st.caption("Sources: " + " | ".join(msg["evidence"]))