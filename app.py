import streamlit as st
import pandas as pd
import os
from collections import Counter

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")
CANDIDATES_FILE = "candidates.xlsx"

st.set_page_config(page_title="MVP 투표", page_icon="🏆", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 900px;
        margin: 0 auto;
    }

    .page-title {
        text-align: center;
        font-size: 2.6rem;
        font-weight: 900;
        margin-bottom: 0.3rem;
    }

    .page-sub {
        text-align: center;
        color: #6b7280;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }

    /* 후보 버튼 */
    div[data-testid="stButton"] > button {
        border-radius: 14px !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        padding: 0.85rem 1rem !important;
        width: 100% !important;
    }

    /* 투표 완료 카드 */
    .voted-card {
        background: linear-gradient(135deg, #059669, #10b981);
        border-radius: 28px;
        padding: 4rem 2rem;
        text-align: center;
        box-shadow: 0 20px 60px rgba(16,185,129,0.3);
        margin: 2rem 0;
    }

    /* 투표 마감 배너 */
    .closed-banner {
        background: #fee2e2;
        border: 2px solid #fca5a5;
        border-radius: 14px;
        padding: 1.8rem;
        text-align: center;
        color: #991b1b;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 2rem 0;
    }

    /* 관리자 상태 바 */
    .admin-bar {
        background: #1e293b;
        border-radius: 16px;
        padding: 1.2rem 1.8rem;
        color: white;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    /* 개표 카드 공통 */
    .result-row {
        border-radius: 18px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }

    .result-hidden {
        background: #1e293b;
    }

    .result-normal {
        background: #f1f5f9;
        border: 2px solid #e2e8f0;
    }

    .result-mvp {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        box-shadow: 0 12px 40px rgba(245,158,11,0.4);
    }

    .r-rank {
        font-size: 1.3rem;
        font-weight: 900;
        min-width: 36px;
        text-align: center;
    }

    .r-name {
        font-size: 1.35rem;
        font-weight: 800;
        flex: 0 0 auto;
        min-width: 80px;
    }

    .r-bar-wrap {
        flex: 1;
        background: rgba(0,0,0,0.1);
        border-radius: 99px;
        height: 10px;
        overflow: hidden;
    }

    .r-bar {
        height: 100%;
        border-radius: 99px;
        background: #3b82f6;
    }

    .r-bar-mvp {
        background: white;
    }

    .r-votes {
        font-size: 1.1rem;
        font-weight: 700;
        min-width: 80px;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)


# ── Supabase 연결 ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_sb():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────
def load_candidates():
    if not os.path.exists(CANDIDATES_FILE):
        return []
    df = pd.read_excel(CANDIDATES_FILE, header=0)
    names = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
    return [n for n in names if n and n.lower() != "nan"]


def is_voting_open():
    try:
        res = get_sb().table("settings").select("value").eq("key", "voting_open").execute()
        return res.data[0]["value"] == "true" if res.data else True
    except:
        return True


def set_voting(val: bool):
    get_sb().table("settings").upsert({"key": "voting_open", "value": str(val).lower()}).execute()


def submit_vote(candidate: str):
    get_sb().table("votes").insert({"candidate": candidate}).execute()


def get_total_votes():
    try:
        res = get_sb().table("votes").select("id", count="exact").execute()
        return res.count or 0
    except:
        return 0


def get_results():
    res = get_sb().table("votes").select("candidate").execute()
    counts = Counter(r["candidate"] for r in res.data)
    candidates = load_candidates()
    results = [(c, counts.get(c, 0)) for c in candidates]
    results.sort(key=lambda x: x[1])   # 오름차순 — 꼴찌부터 공개
    return results


# ── 세션 초기화 ───────────────────────────────────────────────────────────────
for k, v in [
    ("page", "vote"),
    ("voter_name", None),
    ("selected", None),
    ("voted", False),
    ("results_snapshot", None),
    ("reveal_count", 0),
]:
    if k not in st.session_state:
        st.session_state[k] = v

candidates = load_candidates()


# ════════════════════════════════════════════════════════════════════════════
# 투표 화면
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "vote":

    st.markdown('<p class="page-title">🏆 MVP 투표</p>', unsafe_allow_html=True)

    # ── 투표 완료 ──
    if st.session_state.voted:
        st.markdown("""
        <div class="voted-card">
            <div style="font-size:4rem">✅</div>
            <div style="font-size:2rem;font-weight:900;color:white;margin-top:0.6rem">투표 완료!</div>
            <div style="font-size:1.1rem;color:rgba(255,255,255,0.8);margin-top:0.4rem">소중한 한 표 감사합니다 😊</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 투표 마감 ──
    elif not is_voting_open():
        st.markdown('<div class="closed-banner">🔒 투표가 마감되었습니다</div>', unsafe_allow_html=True)

    elif not candidates:
        st.error("후보자 목록(candidates.xlsx)이 없습니다.")

    # ── Step 1: 본인 이름 선택 ──
    elif st.session_state.voter_name is None:
        st.markdown('<p class="page-sub">먼저 본인 이름을 선택하세요</p>', unsafe_allow_html=True)
        _, col, _ = st.columns([1, 2, 1])
        with col:
            name = st.selectbox("본인 이름", ["선택하세요"] + candidates, label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("다음 ▶", use_container_width=True, type="primary"):
                if name == "선택하세요":
                    st.warning("이름을 선택해주세요.")
                else:
                    st.session_state.voter_name = name
                    st.session_state.selected = None
                    st.rerun()

    # ── Step 2: 후보 선택 ──
    else:
        voter = st.session_state.voter_name
        pool = [c for c in candidates if c != voter]
        st.markdown('<p class="page-sub">MVP로 추천하고 싶은 동료를 선택하세요</p>', unsafe_allow_html=True)

        cols = st.columns(3)
        for i, name in enumerate(pool):
            with cols[i % 3]:
                is_sel = st.session_state.selected == name
                label = f"✅  {name}" if is_sel else name
                btn_type = "primary" if is_sel else "secondary"
                if st.button(label, key=f"c_{name}", use_container_width=True, type=btn_type):
                    st.session_state.selected = name
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        _, col, _ = st.columns([1, 2, 1])
        with col:
            if st.session_state.selected:
                if st.button(f"🗳️  {st.session_state.selected}에게 투표하기",
                             use_container_width=True, type="primary"):
                    submit_vote(st.session_state.selected)
                    st.session_state.voted = True
                    st.rerun()
            else:
                st.button("후보자를 먼저 선택하세요", use_container_width=True, disabled=True)

    # ── 관리자 로그인 (숨김) ──
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    with st.expander("🔧 관리자"):
        pwd = st.text_input("비밀번호", type="password", key="pwd")
        if st.button("로그인", key="login_btn"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")


# ════════════════════════════════════════════════════════════════════════════
# 관리자 화면
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "admin":

    st.markdown('<p class="page-title">🔧 관리자</p>', unsafe_allow_html=True)

    voting_open = is_voting_open()
    total = get_total_votes()
    status = "🟢 투표 진행 중" if voting_open else "🔴 투표 마감됨"

    st.markdown(
        f'<div class="admin-bar">상태: <b>{status}</b> &nbsp;·&nbsp; 현재 투표 수: <b>{total}표</b></div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if voting_open:
            if st.button("🔒 투표 마감", use_container_width=True):
                set_voting(False)
                st.rerun()
        else:
            if st.button("🔓 투표 재개", use_container_width=True):
                set_voting(True)
                st.rerun()
    with c2:
        if st.button("🔄 새로고침", use_container_width=True):
            st.rerun()
    with c3:
        if st.button("← 투표 화면", use_container_width=True):
            st.session_state.page = "vote"
            st.rerun()

    st.markdown("---")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if st.button("🎬  개표 시작", use_container_width=True, type="primary"):
            set_voting(False)
            st.session_state.results_snapshot = get_results()
            st.session_state.reveal_count = 0
            st.session_state.page = "reveal"
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 개표 화면
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "reveal":

    results = st.session_state.results_snapshot   # [(name, votes), ...] 오름차순
    reveal_count = st.session_state.reveal_count
    total_candidates = len(results)
    total_votes = sum(v for _, v in results)
    max_votes = max((v for _, v in results), default=1) or 1

    # 화면에는 1위(MVP)가 위 → 꼴찌가 아래
    display = list(reversed(results))   # 내림차순

    st.markdown('<p class="page-title">🏆 개표 결과</p>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    for i, (name, votes) in enumerate(display):
        rank = i + 1
        # 꼴찌(아래)부터 공개: display[i]는 reveal_count >= (total - i) 일 때 공개
        is_revealed = reveal_count >= (total_candidates - i)
        is_mvp = (rank == 1)

        if not is_revealed:
            st.markdown(f"""
            <div class="result-row result-hidden">
                <div class="r-rank" style="color:#334155">#{rank}</div>
                <div class="r-name" style="color:#334155">? ? ?</div>
                <div class="r-bar-wrap"></div>
                <div class="r-votes" style="color:#334155">- 표</div>
            </div>
            """, unsafe_allow_html=True)

        elif is_mvp:
            pct = round(votes / total_votes * 100) if total_votes else 0
            bar = int(votes / max_votes * 100)
            st.markdown(f"""
            <div class="result-row result-mvp">
                <div class="r-rank" style="color:white">🏆</div>
                <div class="r-name" style="color:white">{name}</div>
                <div class="r-bar-wrap">
                    <div class="r-bar r-bar-mvp" style="width:{bar}%"></div>
                </div>
                <div class="r-votes" style="color:white">{votes}표 ({pct}%)</div>
            </div>
            """, unsafe_allow_html=True)

        else:
            pct = round(votes / total_votes * 100) if total_votes else 0
            bar = int(votes / max_votes * 100)
            st.markdown(f"""
            <div class="result-row result-normal">
                <div class="r-rank" style="color:#94a3b8">#{rank}</div>
                <div class="r-name" style="color:#1e293b">{name}</div>
                <div class="r-bar-wrap">
                    <div class="r-bar" style="width:{bar}%"></div>
                </div>
                <div class="r-votes" style="color:#475569">{votes}표 ({pct}%)</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if reveal_count < total_candidates:
            is_last = (reveal_count == total_candidates - 1)
            btn_label = "🏆  MVP 공개!" if is_last else f"다음 공개  ▶  ({total_candidates - reveal_count}명 남음)"
            if st.button(btn_label, use_container_width=True, type="primary"):
                st.session_state.reveal_count += 1
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center;font-size:2.2rem;font-weight:900;
                        color:#f59e0b;padding:1rem;letter-spacing:2px;">
                🎉 축하합니다! 🎉
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← 관리자 화면", use_container_width=True):
            st.session_state.page = "admin"
            st.rerun()
