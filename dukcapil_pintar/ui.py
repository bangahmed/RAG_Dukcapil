"""Komponen Streamlit halaman tanya-jawab.

Isinya: kolom 3xl di tengah, disclaimer satu baris yang tetap di atas,
keadaan kosong berupa logo + judul + tiga chip pertanyaan, satu giliran (bukan
percakapan, karena pipeline tidak punya memori), pertanyaan sebagai gelembung kanan dan
jawaban bertanda logo di kiri, jawaban lebih dulu lalu buktinya, serta composer berupa
kartu di bawah layar yang memuat kolom pertanyaan, selector model, dan tombol tanya.
Palet dan font (ivory + clay, IBM Plex Sans, judul Lora).
"""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from dukcapil_pintar.config import ModelOption, has_secret
from dukcapil_pintar.pipeline import AnswerResult

APP_TITLE = "DUKCAPIL-Pintar"
MODEL_SELECTOR_KEY = "answer_model_key"
QUESTION_INPUT_KEY = "question_input"
DISCLAIMER_TEXT = (
    "Jawaban dibuat AI dari teks regulasi nasional. Verifikasi sebelum diandalkan "
    "dan konfirmasi ke Disdukcapil setempat."
)
COPYRIGHT_TEXT = (
    "© 2026 Arif Alamsah, Djoko Purnomo, Efendy Aprianto, Akhmadi · "
    "Universitas Dian Nuswantoro"
)
_HERO_SUBTITLE = (
    "Tanyakan persyaratan dokumen kependudukan. Setiap jawaban disusun dari teks "
    "regulasi dan menyebut pasal rujukannya."
)
_COMPOSER_PLACEHOLDER = "Tanyakan persyaratan dokumen kependudukan"
_ASK_BUTTON_LABEL = "Tanya"
_CONTEXT_PANEL_NOTE = "Konteks yang diambil. Tinjau sebelum mengandalkan."
_PENDING_NOTE = "Mengambil konteks regulasi…"
_SNIPPET_MAX_CHARS = 140

# Logo kartu identitas bergaya garis tipis, warna clay. Dipakai sebagai gambar data
# URI (bukan berkas) agar tidak butuh penyajian berkas statis di Streamlit Cloud.
_MARK_URI = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 40' fill='none' "
    "stroke='%23aa5233' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E"
    "%3Crect x='3' y='5' width='42' height='30' rx='5'/%3E"
    "%3Ccircle cx='16' cy='18' r='5'/%3E"
    "%3Cpath d='M8 30c1.5-4 4.5-6 8-6s6.5 2 8 6'/%3E"
    "%3Cpath d='M30 15h10M30 21h10M30 27h6'/%3E%3C/svg%3E"
)

# Warna: skala "stone" dan clay dari index.css CICADA (latar #faf9f5, aksen #aa5233 dan
# #d97757). Amber hanya untuk panel konteks dan galat, satu-satunya penanda status.
_PAGE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Lora:wght@500;600&display=swap');
.stApp, .stApp p, .stApp li, .stApp button, .stApp input, .stApp [data-baseweb="select"] {
  font-family: 'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, sans-serif;}
.stApp {background: #faf9f5;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {max-width: 48rem; padding: 1.25rem 1rem 0 1rem;}

.dp-disclaimer {border: 1px solid #e7e5e4; background: rgba(240, 238, 230, 0.7);
  border-radius: 0.5rem; padding: 0.375rem 0.75rem; text-align: center; font-size: 0.6875rem;
  color: #57534e; margin: 0 0 0.5rem 0;}

.dp-hero {text-align: center; padding: 11vh 0 1.25rem 0;}
.dp-hero img {height: 2.25rem; width: auto;}
.dp-hero-title {font-family: 'Lora', Georgia, serif; font-size: 1.875rem; font-weight: 600;
  letter-spacing: -0.02em; line-height: 1.25; color: #1c1917; margin-top: 0.75rem;}
.dp-hero p {color: #78716c; font-size: 0.875rem; max-width: 28rem; margin: 0.5rem auto 0 auto;}
.st-key-starters {flex-direction: row !important; flex-wrap: wrap; justify-content: center;
  gap: 0.375rem !important;}
.st-key-starters .stElementContainer {width: auto !important; flex: 0 1 auto;}
/* Streamlit hanya memudarkan elemen lama selama pipeline berjalan; chip contoh yang sudah
   tidak dirender disembunyikan agar tidak menumpuk di bawah pertanyaan. */
.stElementContainer[data-stale="true"][class*="st-key-starter-"] {display: none;}
.st-key-starters button {border: 1px solid #d6d3d1; background: #fff; color: #44403c;
  border-radius: 999px; padding: 0.375rem 0.75rem; min-height: 0; height: auto;
  box-shadow: 0 1px 2px rgba(28, 25, 23, 0.06);}
.st-key-starters button p {font-size: 0.75rem; line-height: 1.2;}
.st-key-starters button:hover {border-color: #d97757; color: #aa5233;}

.dp-user-turn {display: flex; justify-content: flex-end; margin: 1.25rem 0 1rem 0;}
.dp-user-turn div {background: #f0eee6; border-radius: 1rem 1rem 0.25rem 1rem;
  padding: 0.5rem 0.875rem; max-width: 85%; font-size: 0.875rem; color: #1c1917;}

.st-key-answer, .st-key-answer_pending {position: relative; padding-left: 1.9rem;}
.st-key-answer::before, .st-key-answer_pending::before {content: ''; position: absolute;
  left: 0; top: 0.2rem; width: 1.35rem; height: 1.1rem;
  background: url("__MARK__") no-repeat center / contain;}
.st-key-answer_pending::before {animation: dp-pulse 1.4s ease-in-out infinite;}
@keyframes dp-pulse {0%, 100% {opacity: 1;} 50% {opacity: 0.35;}}
.st-key-answer .stMarkdown p, .st-key-answer .stMarkdown li {font-size: 0.875rem;
  line-height: 1.65; color: #292524;}
.dp-pending {font-size: 0.875rem; color: #78716c; margin: 0;}
.dp-error {border: 1px solid #fcd34d; background: #fffbeb; color: #78350f;
  border-radius: 0.5rem; padding: 0.5rem 0.75rem; font-size: 0.875rem;}

.st-key-context_panel details {border: 1px solid #fcd34d; border-radius: 0.5rem;
  overflow: hidden; background: transparent;}
.st-key-context_panel summary {background: #fffbeb; padding: 0.25rem 0.625rem;}
.st-key-context_panel summary p {color: #78350f; font-size: 0.6875rem; font-weight: 600;}
.st-key-context_panel pre {font-size: 0.75rem;}

.dp-section-label {font-size: 0.6875rem; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: #78716c; margin: 1rem 0 0.375rem 0;}
.dp-citation {border: 1px solid #e7e5e4; border-radius: 0.5rem; padding: 0.375rem 0.625rem;
  margin-bottom: 0.25rem;}
.dp-citation a {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.75rem;
  font-weight: 500; color: #aa5233; text-decoration: none;}
.dp-citation a:hover {text-decoration: underline;}
.dp-cite-page {font-size: 0.6875rem; color: #78716c; margin-left: 0.5rem;}
.dp-cite-snippet {margin: 0.125rem 0 0 0; font-size: 0.6875rem; color: #78716c;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}

.dp-meta {display: flex; flex-wrap: wrap; gap: 0.375rem; border-top: 1px solid #e7e5e4;
  padding-top: 0.625rem; margin-top: 0.875rem;}
.dp-chip {display: inline-flex; border: 1px solid #e7e5e4; background: #f0eee6;
  border-radius: 999px; padding: 0 0.5rem; font-size: 0.6875rem; line-height: 1.25rem;
  color: #57534e;}

/* Halaman setinggi layar dan composer didorong ke dasar, seperti halaman Ask CICADA. */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
  min-height: calc(100vh - 3.5rem);}
/* Pudar di tepi atas composer dibuat di dalam kotaknya sendiri (bukan menimpa konten
   di atasnya), supaya baris terakhir jawaban dan teks "Mengambil konteks…" tetap jelas. */
.st-key-composer_bar {position: sticky; bottom: 0; z-index: 50; margin-top: auto;
  padding: 1.5rem 0 0.75rem 0;
  background: linear-gradient(to bottom, rgba(250, 249, 245, 0), #faf9f5 1.5rem);}
.st-key-composer_bar [data-testid="stForm"] {background: #fff; border: 1px solid #d6d3d1;
  border-radius: 1rem; padding: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(28, 25, 23, 0.06), 0 4px 6px -4px rgba(28, 25, 23, 0.06);}
.st-key-composer_bar [data-testid="stForm"]:focus-within {border-color: #d97757;}
.dp-copyright {text-align: center; font-size: 0.6875rem; color: #78716c; margin: 0.5rem 0 0 0;}
.st-key-composer_bar [data-testid="stTextInputRootElement"],
.st-key-composer_bar [data-baseweb="input"], .st-key-composer_bar [data-baseweb="base-input"] {
  background: transparent !important; border: none !important; box-shadow: none !important;}
.st-key-composer_bar input {font-size: 0.875rem; padding: 0.375rem 0.5rem; color: #1c1917;}
.st-key-composer_bar [data-testid="InputInstructions"] {display: none;}
.st-key-composer_bar [data-testid="stSelectbox"] div {background-color: transparent !important;
  border-color: transparent !important; box-shadow: none !important;}
.st-key-composer_bar [data-testid="stSelectbox"] {border-radius: 0.5rem; font-size: 0.75rem;
  color: #57534e;}
.st-key-composer_bar [data-testid="stSelectbox"]:hover {background: #f0eee6;}
.st-key-composer_bar [data-testid="stSelectbox"] svg {color: #78716c;}
/* Daftar pilihan model: kartu putih bersudut bulat, baris terpilih berlatar parchment. */
div[data-baseweb="popover"] > div {background: #fff; border: 1px solid #e7e5e4;
  border-radius: 0.75rem; overflow: hidden;
  box-shadow: 0 10px 15px -3px rgba(28, 25, 23, 0.1), 0 4px 6px -4px rgba(28, 25, 23, 0.1);}
div[data-baseweb="popover"] ul {background: #fff; padding: 0.25rem;}
div[data-baseweb="popover"] li {font-size: 0.75rem; color: #44403c; border-radius: 0.5rem;
  background: transparent;}
div[data-baseweb="popover"] li:hover, div[data-baseweb="popover"] li[aria-selected="true"] {
  background: #f0eee6;}
.st-key-composer_bar button[kind="primaryFormSubmit"] {background: #aa5233; border: none;
  color: #fff; border-radius: 0.5rem; width: 2.25rem; min-width: 2.25rem; height: 2.25rem;
  min-height: 2.25rem; padding: 0; margin-left: auto; position: relative; display: flex;
  align-items: center; justify-content: center; gap: 0;}
/* Teks tombol disembunyikan secara visual tetapi tetap terbaca pembaca layar; wadahnya
   dikeluarkan dari alur agar tidak menggeser ikon dari tengah. */
.st-key-composer_bar button[kind="primaryFormSubmit"] [data-testid="stMarkdownContainer"] {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0);
  white-space: nowrap;}
.st-key-composer_bar button[kind="primaryFormSubmit"] [data-testid="stIconMaterial"] {
  margin: 0; font-size: 1.25rem; line-height: 1;}
.st-key-composer_bar button[kind="primaryFormSubmit"]:hover {background: #8f4429;}
@media (max-width: 640px) {
  .st-key-composer_bar [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important;}
  .st-key-composer_bar [data-testid="stColumn"]:first-child {display: none;}
}
</style>
""".replace("__MARK__", _MARK_URI)  # noqa: E501


def apply_page_style() -> None:
    """Menyisipkan CSS halaman; dipanggil sekali di awal setiap render."""
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)


def render_disclaimer() -> None:
    """Menampilkan disclaimer satu baris yang selalu ada dan tidak bisa ditutup."""
    st.markdown(f'<p class="dp-disclaimer">{DISCLAIMER_TEXT}</p>', unsafe_allow_html=True)


def render_hero(starter_questions: list[str], on_pick: Callable[[str], None]) -> None:
    """Menampilkan keadaan kosong; ``on_pick`` dipanggil dengan pertanyaan contoh yang diklik."""
    # Judul memakai div ber-role heading, bukan h1 markdown, karena Streamlit menambah
    # ikon tautan pada h1 yang menggeser judul dari tengah.
    st.markdown(
        f'<div class="dp-hero"><img src="{_MARK_URI}" alt="">'
        f'<div class="dp-hero-title" role="heading" aria-level="1">{APP_TITLE}</div>'
        f"<p>{_HERO_SUBTITLE}</p></div>",
        unsafe_allow_html=True,
    )
    with st.container(key="starters"):
        for index, question in enumerate(starter_questions):
            st.button(question, key=f"starter-{index}", on_click=on_pick, args=(question,))


def render_user_turn(question: str) -> None:
    """Menampilkan pertanyaan pengguna sebagai gelembung di sisi kanan."""
    st.markdown(
        f'<div class="dp-user-turn"><div>{html.escape(question)}</div></div>',
        unsafe_allow_html=True,
    )


def answer_container() -> DeltaGenerator:
    """Mengembalikan wadah jawaban yang ditandai logo di sisi kiri."""
    return st.container(key="answer")


def pending_answer_container() -> DeltaGenerator:
    """Mengembalikan wadah jawaban yang logonya berdenyut selama pipeline berjalan."""
    return st.container(key="answer_pending")


def render_pending_note() -> None:
    """Menampilkan keterangan tahap yang sedang berjalan di samping logo berdenyut."""
    st.markdown(f'<p class="dp-pending">{_PENDING_NOTE}</p>', unsafe_allow_html=True)


def render_error(message: str) -> None:
    """Menampilkan pesan galat dalam panel amber, bukan jalan buntu tanpa penjelasan."""
    st.markdown(f'<div class="dp-error">{html.escape(message)}</div>', unsafe_allow_html=True)


def _render_context_panel(result: AnswerResult) -> None:
    """Menampilkan chunk yang diambil retrieval dalam panel amber yang bisa disalin."""
    label = f"{_CONTEXT_PANEL_NOTE} ({len(result.retrieved)} potongan regulasi)"
    with st.container(key="context_panel"), st.expander(label, expanded=False):
        joined = "\n\n".join(item.chunk.text for item in result.retrieved)
        # st.code menyediakan tombol salin, setara tombol Copy di panel SQL CICADA.
        st.code(joined, language=None, wrap_lines=True)


def _snippet(chunk_text: str) -> str:
    """Mengembalikan cuplikan isi pasal tanpa baris header, dipotong agar satu baris."""
    lines = chunk_text.splitlines()
    body = " ".join(lines[1:] if lines and lines[0].startswith("[") else lines)
    compact = " ".join(body.split())
    return compact if len(compact) <= _SNIPPET_MAX_CHARS else compact[:_SNIPPET_MAX_CHARS] + "…"


def _render_citations(result: AnswerResult) -> None:
    """Menampilkan kartu pasal rujukan: tautan ke sumber resmi dan cuplikan isinya."""
    st.markdown(
        f'<p class="dp-section-label">Berdasarkan {len(result.retrieved)} pasal</p>',
        unsafe_allow_html=True,
    )
    for item in result.retrieved:
        chunk = item.chunk
        st.markdown(
            f'<div class="dp-citation"><a href="{html.escape(chunk.source_url)}" '
            f'target="_blank">{html.escape(chunk.citation_label)}</a>'
            f'<span class="dp-cite-page">hal. {chunk.page_start}</span>'
            f'<p class="dp-cite-snippet">{html.escape(_snippet(chunk.text))}</p></div>',
            unsafe_allow_html=True,
        )


def _render_meta_chips(result: AnswerResult) -> None:
    """Menampilkan chip model penjawab, status jawaban, dan status tulis ulang kueri."""
    status = "Ditemukan di dokumen" if result.is_answer_found else "Tidak ditemukan di dokumen"
    if result.rewrite_error:
        rewrite_status = "Tulis ulang kueri gagal"
    elif result.rewritten_query:
        rewrite_status = "Kueri ditulis ulang"
    else:
        rewrite_status = "Tanpa tulis ulang kueri"
    chips = [f"Dijawab oleh {result.answer_model.label}", status, rewrite_status]
    st.markdown(
        '<div class="dp-meta">'
        + "".join(f'<span class="dp-chip">{html.escape(chip)}</span>' for chip in chips)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_answer(result: AnswerResult) -> None:
    """Menampilkan jawaban lebih dulu, lalu buktinya: konteks, pasal, dan chip meta."""
    st.markdown(result.answer)
    if result.retrieved:
        _render_context_panel(result)
        _render_citations(result)
    _render_meta_chips(result)


def render_composer(
    options: tuple[ModelOption, ...],
    default_key: str,
    on_submit: Callable[[], None],
) -> None:
    """Menampilkan composer: kolom pertanyaan, selector model, dan tombol tanya dalam satu kartu.

    Kartu menempel di bawah layar. Model tanpa API key tetap ditampilkan beserta
    alasannya, bukan disembunyikan, supaya jelas mengapa model itu tidak bisa dipakai.
    ``on_submit`` berjalan sebagai callback tombol, sebelum skrip dijalankan ulang.
    """
    keys = [option.key for option in options]
    options_by_key = {option.key: option for option in options}

    def format_label(key: str) -> str:
        """Mengembalikan label opsi, ditandai bila API key-nya belum diisi."""
        option = options_by_key[key]
        suffix = "" if has_secret(option.secret_name) else " — API key belum diisi"
        return option.label + suffix

    # Pilihan disimpan di session_state agar tombol "coba dengan model lain" bisa
    # memindahkan selector; nilai awal diisi di sini, bukan lewat ``index``, supaya
    # Streamlit tidak memperingatkan dua sumber nilai awal.
    st.session_state.setdefault(MODEL_SELECTOR_KEY, default_key)
    with st.container(key="composer_bar"):
        with st.form("composer", clear_on_submit=False):
            st.text_input(
                "Pertanyaan",
                key=QUESTION_INPUT_KEY,
                placeholder=_COMPOSER_PLACEHOLDER,
                max_chars=500,
                label_visibility="collapsed",
            )
            # Kolom kiri hanya pengisi: selector dan tombol menempel di ujung kanan kartu.
            _, model_column, ask_column = st.columns(
                [4.4, 2.6, 0.5], vertical_alignment="center", gap="small"
            )
            with model_column:
                st.selectbox(
                    "Model penjawab",
                    keys,
                    key=MODEL_SELECTOR_KEY,
                    format_func=format_label,
                    label_visibility="collapsed",
                )
            with ask_column:
                st.form_submit_button(
                    _ASK_BUTTON_LABEL,
                    type="primary",
                    icon=":material/arrow_upward:",
                    help="Kirim pertanyaan",
                    on_click=on_submit,
                )
        # Di dalam composer_bar agar ikut menempel di dasar layar, tepat di bawah kartu.
        st.markdown(f'<p class="dp-copyright">{COPYRIGHT_TEXT}</p>', unsafe_allow_html=True)
