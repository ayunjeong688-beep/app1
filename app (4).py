import os
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import qrcode
from io import BytesIO

try:
    from supabase import create_client
except ImportError:
    create_client = None

try:
    import streamlit.components.v1 as components
except ImportError:
    components = None


# ---------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="우리의 하루",
    page_icon="💗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

KST = ZoneInfo("Asia/Seoul")
MOODS = {
    "🥰": "행복해",
    "😊": "좋아",
    "😐": "그냥 그래",
    "🥺": "속상해",
    "😴": "피곤해",
    "😡": "화났어",
}

# Streamlit Cloud에서는 앱의 Settings > Secrets에 아래 값을 등록하세요.
# SUPABASE_URL = "https://....supabase.co"
# SUPABASE_KEY = "..."
# APP_URL = "https://your-app-name.streamlit.app"
# MY_NAME = "나"
# PARTNER_NAME = "상대방"
# APP_PIN = "두 사람만 아는 비밀번호"


def get_setting(key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return os.getenv(key, default)


MY_NAME = get_setting("MY_NAME", "나")
PARTNER_NAME = get_setting("PARTNER_NAME", "상대방")
APP_PIN = get_setting("APP_PIN", "")
APP_URL = get_setting("APP_URL", "")
SUPABASE_URL = get_setting("SUPABASE_URL", "")
SUPABASE_KEY = get_setting("SUPABASE_KEY", "")

# ---------------------------------------------------------
# 스타일: 작은 화면에서 한 화면에 최대한 들어오도록 구성
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    .stApp {
        background: linear-gradient(145deg, #fff8f7 0%, #fffdf9 58%, #fff2f4 100%);
    }
    header, footer, #MainMenu {visibility: hidden;}
    .block-container {
        max-width: 650px;
        padding: 1rem 0.85rem 1.2rem 0.85rem;
    }
    h1, h2, h3, p { color: #514348; }
    .hero {
        text-align: center;
        padding: 5px 0 10px 0;
    }
    .hero-title {
        color: #bd7187;
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0;
    }
    .hero-sub {
        color: #a58d92;
        font-size: 0.78rem;
        margin-top: 3px;
    }
    .panel {
        background: rgba(255,255,255,0.88);
        border: 1px solid #f5e4e7;
        border-radius: 17px;
        padding: 12px 14px;
        margin: 7px 0;
        box-shadow: 0 4px 14px rgba(190, 130, 145, 0.07);
    }
    .entry {
        background: #fffafb;
        border: 1px solid #f4e6e9;
        border-radius: 13px;
        padding: 10px 12px;
        margin: 7px 0;
    }
    .entry-top {
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:8px;
        color:#9b7e86;
        font-size:0.75rem;
        margin-bottom:5px;
    }
    .entry-body {
        color:#57484d;
        font-size:0.88rem;
        line-height:1.45;
        white-space:pre-wrap;
        overflow-wrap:anywhere;
    }
    .muted { color:#a58f95; font-size:0.74rem; }
    div.stButton > button {
        border-radius: 12px;
        border: 1px solid #efd5dc;
        background: #fff;
        color: #986777;
        font-weight: 650;
        min-height: 2.35rem;
        padding: 0.35rem 0.65rem;
    }
    div.stButton > button[kind="primary"] {
        background: #d98fa3;
        color: white;
        border: 0;
    }
    div[data-testid="stTextArea"] textarea {
        border-radius: 12px;
        border: 1px solid #efdde2;
        background: #fffdfd;
        font-size: 0.88rem;
    }
    div[data-testid="stSelectbox"] > div > div {
        border-radius: 11px;
    }
    div[data-testid="stRadio"] > div {
        gap: 5px;
    }
    div[data-testid="stRadio"] label {
        background: #fff;
        border: 1px solid #f0dfe3;
        padding: 5px 9px;
        border-radius: 12px;
    }
    .status-read { color:#4d9b78; font-weight:700; }
    .status-wait { color:#c18a62; font-weight:700; }
    @media (max-width: 480px) {
        .block-container {padding: 0.65rem 0.55rem 0.8rem 0.55rem;}
        .hero-title {font-size:1.45rem;}
        .panel {padding:10px 11px; margin:6px 0;}
        .entry {padding:8px 10px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 데이터베이스 연결
# ---------------------------------------------------------
@st.cache_resource
def supabase_client():
    if SUPABASE_URL and SUPABASE_KEY and create_client:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None


db = supabase_client()


def load_entries():
    if db:
        try:
            result = (
                db.table("couple_diary")
                .select("*")
                .order("created_at", desc=True)
                .limit(30)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            st.error("일기를 불러오지 못했어요. Supabase 테이블 설정을 확인해 주세요.")
            st.caption(str(exc))
            return []
    # 로컬 테스트용 메모리 저장. 배포용 영구 저장에는 Supabase 설정이 필요합니다.
    return st.session_state.local_entries


def save_entry(author, mood, content):
    now = datetime.now(KST).isoformat()
    row = {
        "author": author,
        "mood": mood,
        "content": content.strip(),
        "created_at": now,
        "read_by": [],
    }
    if db:
        db.table("couple_diary").insert(row).execute()
    else:
        st.session_state.local_entries.insert(0, row)


def mark_as_read(entry_id, entry_index, reader):
    if db:
        entry = next((x for x in st.session_state.entries if str(x.get("id")) == str(entry_id)), None)
        if not entry:
            return
        readers = list(entry.get("read_by") or [])
        if reader not in readers:
            readers.append(reader)
        db.table("couple_diary").update({"read_by": readers}).eq("id", entry_id).execute()
    else:
        readers = st.session_state.local_entries[entry_index].setdefault("read_by", [])
        if reader not in readers:
            readers.append(reader)


if "local_entries" not in st.session_state:
    st.session_state.local_entries = []
if "entries" not in st.session_state:
    st.session_state.entries = []
if "writer" not in st.session_state:
    st.session_state.writer = MY_NAME
if "mood" not in st.session_state:
    st.session_state.mood = "🥰"
if "draft" not in st.session_state:
    st.session_state.draft = ""

# ---------------------------------------------------------
# 선택적 PIN 잠금
# ---------------------------------------------------------
if APP_PIN:
    if not st.session_state.get("unlocked", False):
        st.markdown('<div class="hero"><div class="hero-title">💗 우리의 하루</div><div class="hero-sub">우리 둘만의 작은 기록장</div></div>', unsafe_allow_html=True)
        pin = st.text_input("우리만의 비밀번호", type="password", placeholder="비밀번호 입력")
        if st.button("입장하기", type="primary", use_container_width=True):
            if pin == APP_PIN:
                st.session_state.unlocked = True
                st.rerun()
            else:
                st.error("비밀번호가 맞지 않아요.")
        st.stop()

# ---------------------------------------------------------
# 상단 헤더 및 사용자 선택
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="hero-title">💗 우리의 하루</div>
      <div class="hero-sub">서로의 하루를 가장 먼저 읽어주는 곳</div>
    </div>
    """,
    unsafe_allow_html=True,
)

names = [MY_NAME, PARTNER_NAME]
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("**오늘은 누구인가요?**")
st.radio(
    "작성자 선택",
    options=names,
    horizontal=True,
    key="writer",
    label_visibility="collapsed",
)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 일기 작성
# ---------------------------------------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("**오늘의 기분은?**")
mood_cols = st.columns(6)
for idx, (emoji, label) in enumerate(MOODS.items()):
    with mood_cols[idx]:
        if st.button(
            emoji,
            key=f"mood_{emoji}",
            use_container_width=True,
            type="primary" if st.session_state.mood == emoji else "secondary",
        ):
            st.session_state.mood = emoji
            st.rerun()

st.caption(f"선택한 기분: {st.session_state.mood} {MOODS[st.session_state.mood]}")
draft = st.text_area(
    "오늘의 일기",
    placeholder="오늘 있었던 일을 짧게 남겨보세요 💌",
    height=92,
    key="draft",
    label_visibility="collapsed",
)
if st.button("일기 저장하기 💌", type="primary", use_container_width=True):
    if not draft.strip():
        st.warning("일기 내용을 먼저 작성해 주세요.")
    else:
        try:
            save_entry(st.session_state.writer, st.session_state.mood, draft)
            st.session_state.draft = ""
            st.success("오늘의 일기를 저장했어요!")
            st.rerun()
        except Exception as exc:
            st.error("저장에 실패했어요. Supabase 설정을 확인해 주세요.")
            st.caption(str(exc))
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 서로의 일기 / 읽음 확인
# ---------------------------------------------------------
try:
    st.session_state.entries = load_entries()
except Exception:
    st.session_state.entries = []

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("**우리의 기록 💞**")
if not st.session_state.entries:
    st.markdown('<div class="muted">아직 기록이 없어요. 첫 번째 일기를 남겨보세요!</div>', unsafe_allow_html=True)
else:
    for idx, entry in enumerate(st.session_state.entries[:5]):
        author = entry.get("author", "누군가")
        mood = entry.get("mood", "💗")
        content = entry.get("content", "")
        created = entry.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            date_label = dt.astimezone(KST).strftime("%m/%d %H:%M")
        except Exception:
            date_label = str(created)[:16]

        read_by = entry.get("read_by") or []
        other_person = PARTNER_NAME if author == MY_NAME else MY_NAME
        is_read = other_person in read_by

        status = (
            f'<span class="status-read">✓ {other_person} 확인 완료</span>'
            if is_read
            else f'<span class="status-wait">읽음 기다리는 중</span>'
        )
        st.markdown(
            f"""
            <div class="entry">
              <div class="entry-top">
                <span><b>{author}</b> · {mood} · {date_label}</span>
                {status}
              </div>
              <div class="entry-body">{content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if author != st.session_state.writer and not is_read:
            entry_id = entry.get("id")
            if st.button("읽었어요 ✓", key=f"read_{entry_id if entry_id is not None else idx}", use_container_width=True):
                try:
                    mark_as_read(entry_id, idx, st.session_state.writer)
                    st.success("읽음 표시를 남겼어요!")
                    st.rerun()
                except Exception as exc:
                    st.error("읽음 표시를 저장하지 못했어요.")
                    st.caption(str(exc))
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# QR 코드
# ---------------------------------------------------------
with st.expander("📱 QR 코드로 접속하기", expanded=False):
    if APP_URL:
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(APP_URL)
        qr.make(fit=True)
        image = qr.make_image(fill_color="#8f5c6d", back_color="#fff9fa")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        st.image(buffer.getvalue(), width=150)
        st.caption("상대방이 QR 코드를 스캔하면 같은 다이어리로 접속할 수 있어요.")
        st.code(APP_URL)
    else:
        st.info("배포 후 Streamlit 주소를 Secrets의 APP_URL에 입력하면 QR 코드가 표시돼요.")

if not db:
    st.warning(
        "현재는 로컬 테스트 저장 모드예요. 두 사람이 함께 사용하고 기록을 유지하려면 "
        "Supabase를 연결한 뒤 배포해 주세요."
    )

st.markdown(
    '<div style="text-align:center;color:#b69ca3;font-size:0.68rem;padding:7px 0 2px;">made with love · 우리의 하루</div>',
    unsafe_allow_html=True,
)
