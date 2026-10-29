"""Mengevaluasi pipeline RAG pada set uji: jawab, nilai dengan juri, lalu rangkum.

Empat dimensi CPMK 2 (Bab 7.2): relevansi dan faithfulness (juri Sonnet 5.5),
biaya (jumlah token) dan latency (detik). Ditambah dua ukuran objektif yang tidak
bergantung pada juri: hit rate retrieval dan penolakan yang benar.

Hasil tiap putaran disimpan di ``evals/runs/<run-name>/``. Langkah ``generate`` dan
``judge`` bisa dilanjutkan bila terputus rate limit: pertanyaan yang sudah punya
hasil dilewati.

Contoh:
    python scripts/run-evaluation.py --run-name baseline
    python scripts/run-evaluation.py --run-name top-k-6 --only judge,report
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

from _project_root import add_project_root_to_path

add_project_root_to_path()

from dukcapil_pintar import config  # noqa: E402
from dukcapil_pintar.formatting import format_decimal  # noqa: E402
from dukcapil_pintar.pipeline import AnswerResult, RagPipeline  # noqa: E402
from dukcapil_pintar.prompts import (  # noqa: E402
    ANSWER_PROMPT_VERSION,
    FAITHFULNESS_JUDGE_PROMPT,
    JUDGE_PROMPT_VERSION,
    RELEVANCE_JUDGE_PROMPT,
    REWRITE_PROMPT_VERSION,
)
from dukcapil_pintar.providers import ProviderError, complete  # noqa: E402
from dukcapil_pintar.retrieval import ChunkIndex, read_jsonl  # noqa: E402

OUT_OF_SCOPE_TYPE = "di_luar_cakupan"
_JUDGE_SYSTEM_PROMPT = "Anda adalah juri evaluasi sistem RAG yang teliti dan konsisten."
_FAITHFULNESS_SCORE_PATTERN = re.compile(r"Skor Faithfulness:\s*\**\s*(\d+(?:[.,]\d+)?)")
_RELEVANCE_SCORE_PATTERN = re.compile(r"Skor Relevansi:\s*\**\s*(\d+(?:[.,]\d+)?)")
_LOWEST_SCORE_COUNT = 3
_RESULT_COLUMNS = [
    "question_id",
    "question_type",
    "question",
    "answer_model_id",
    "is_answer_found",
    "is_correct_refusal",
    "retrieval_hit",
    "relevance_score",
    "faithfulness_score",
    "answer_input_tokens",
    "answer_output_tokens",
    "rewrite_input_tokens",
    "rewrite_output_tokens",
    "answer_total_tokens",
    "latency_s",
]


def _run_dir(run_name: str) -> Path:
    """Mengembalikan folder keluaran satu putaran evaluasi, dibuat bila belum ada."""
    run_dir = config.EVAL_RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _read_done_ids(path: Path) -> set[str]:
    """Mengembalikan question_id yang sudah tercatat di berkas JSONL, untuk melanjutkan."""
    if not path.exists():
        return set()
    return {record["question_id"] for record in read_jsonl(path)}


def _append_jsonl(record: dict, path: Path) -> None:
    """Menambahkan satu record ke berkas JSONL; ditulis segera agar aman bila terputus."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_run_config(
    run_dir: Path, answer_model_id: str, frozen_rewrites_from: str | None
) -> None:
    """Menyimpan parameter putaran agar hasilnya dapat direproduksi dan dibandingkan."""
    run_config = {
        "answer_model_id": answer_model_id,
        "frozen_rewrites_from": frozen_rewrites_from,
        "judge_model_id": config.SONNET_OPTION.model_id,
        # API Sonnet 5.5 menolak parameter temperature, jadi suhu juri tidak dapat
        # dipatok ke 0; skor juri bisa bervariasi antarputaran.
        "judge_temperature": "tidak dapat diatur",
        "embedding_model_name": config.EMBEDDING_MODEL_NAME,
        "top_k": config.TOP_K,
        "fusion_method": config.FUSION_METHOD,
        "is_query_rewrite_enabled": config.IS_QUERY_REWRITE_ENABLED,
        "max_chunk_chars": config.MAX_CHUNK_CHARS,
        "chunk_overlap_chars": config.CHUNK_OVERLAP_CHARS,
        "answer_prompt_version": ANSWER_PROMPT_VERSION,
        "rewrite_prompt_version": REWRITE_PROMPT_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
    }
    (run_dir / "run_config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _to_answer_record(test_case: dict, result: AnswerResult) -> dict:
    """Mengubah hasil pipeline menjadi record JSONL yang memuat bukti retrieval."""
    return {
        "question_id": test_case["question_id"],
        "question_type": test_case["question_type"],
        "question": result.question,
        "expected_articles": test_case.get("expected_articles", []),
        "answer": result.answer,
        "answer_model_id": result.answer_model.model_id,
        "is_answer_found": result.is_answer_found,
        "rewritten_query": result.rewritten_query,
        "rewrite_error": result.rewrite_error,
        "retrieved": [
            {
                "chunk_id": item.chunk.chunk_id,
                "document_id": item.chunk.document_id,
                "article_label": item.chunk.article_label,
                "score": item.score,
                "text": item.chunk.text,
            }
            for item in result.retrieved
        ],
        "token_usage": result.token_usage,
        "stage_latency_s": result.stage_latency_s,
        "latency_s": result.total_latency_s,
    }


def _load_frozen_rewrites(run_name: str) -> dict[str, str]:
    """Mengembalikan kueri tulis ulang tiap pertanyaan dari putaran ``run_name``.

    Gagal bila putarannya belum ada: lebih baik berhenti daripada diam-diam memakai
    kueri baru dan mengira perbandingannya sudah bersih.
    """
    answers_path = config.EVAL_RUNS_DIR / run_name / "answers.jsonl"
    if not answers_path.exists():
        raise SystemExit(f"Putaran '{run_name}' belum punya answers.jsonl untuk dibekukan.")
    return {
        record["question_id"]: record["rewritten_query"] or ""
        for record in read_jsonl(answers_path)
    }


def step_generate(args: argparse.Namespace) -> None:
    """Menjawab tiap pertanyaan set uji dan menyimpan jawaban serta buktinya."""
    run_dir = _run_dir(args.run_name)
    answers_path = run_dir / "answers.jsonl"
    answer_model = config.find_answer_model_option(args.model_key)
    frozen_rewrites = (
        _load_frozen_rewrites(args.reuse_rewrites_from) if args.reuse_rewrites_from else None
    )
    _write_run_config(run_dir, answer_model.model_id, args.reuse_rewrites_from)

    index = ChunkIndex.load(config.FAISS_INDEX_PATH, config.CHUNK_METADATA_JSONL_PATH)
    pipeline = RagPipeline(index, config.TOP_K, config.IS_QUERY_REWRITE_ENABLED)
    done_ids = _read_done_ids(answers_path)
    pending = [case for case in read_jsonl(args.test_set) if case["question_id"] not in done_ids]
    print(f"{len(done_ids)} sudah dijawab, {len(pending)} tersisa ({answer_model.label}).")

    for test_case in pending:
        try:
            frozen = None if frozen_rewrites is None else frozen_rewrites[test_case["question_id"]]
            result = pipeline.answer_question(test_case["question"], answer_model, frozen)
        except ProviderError as exc:
            # Berhenti alih-alih melompati: jawaban yang hilang akan membuat rata-rata
            # antarputaran tidak sebanding. Jalankan ulang untuk melanjutkan.
            raise SystemExit(f"{test_case['question_id']}: {exc}") from exc
        _append_jsonl(_to_answer_record(test_case, result), answers_path)
        print(
            f"  {test_case['question_id']} selesai, {format_decimal(result.total_latency_s)} detik"
        )
        # Jeda menjaga pemakaian di bawah batas token per menit Groq tier gratis.
        time.sleep(args.pause_s)


def _parse_score(pattern: re.Pattern[str], judge_text: str) -> float | None:
    """Mengembalikan skor 0-10 dari teks juri, atau None bila formatnya tidak dipatuhi."""
    match = pattern.search(judge_text)
    return float(match.group(1).replace(",", ".")) if match else None


def _judge(prompt: str) -> str:
    """Mengembalikan teks penilaian juri Sonnet untuk satu prompt juri."""
    completion = complete(
        config.SONNET_OPTION,
        _JUDGE_SYSTEM_PROMPT,
        prompt,
        config.JUDGE_MAX_TOKENS,
    )
    return completion.text


def step_judge(args: argparse.Namespace) -> None:
    """Menilai relevansi dan faithfulness tiap jawaban dengan juri Sonnet 5.5."""
    run_dir = _run_dir(args.run_name)
    judgments_path = run_dir / "judgments.jsonl"
    done_ids = _read_done_ids(judgments_path)
    answers = [a for a in read_jsonl(run_dir / "answers.jsonl") if a["question_id"] not in done_ids]
    print(f"{len(done_ids)} sudah dinilai, {len(answers)} tersisa.")

    for answer in answers:
        context = "\n\n".join(item["text"] for item in answer["retrieved"])
        try:
            faithfulness_text = _judge(
                FAITHFULNESS_JUDGE_PROMPT.format(context=context, answer=answer["answer"])
            )
            relevance_text = _judge(
                RELEVANCE_JUDGE_PROMPT.format(question=answer["question"], answer=answer["answer"])
            )
        except ProviderError as exc:
            raise SystemExit(f"{answer['question_id']}: {exc}") from exc
        record = {
            "question_id": answer["question_id"],
            "faithfulness_score": _parse_score(_FAITHFULNESS_SCORE_PATTERN, faithfulness_text),
            "relevance_score": _parse_score(_RELEVANCE_SCORE_PATTERN, relevance_text),
            # Teks lengkap juri disimpan untuk pemeriksaan manual skor terendah.
            "faithfulness_judgment": faithfulness_text,
            "relevance_judgment": relevance_text,
        }
        _append_jsonl(record, judgments_path)
        print(f"  {answer['question_id']} dinilai")


def _is_retrieval_hit(answer: dict) -> bool | None:
    """Mengembalikan True bila minimal satu pasal kunci ada di hasil retrieval.

    ``expected_articles`` berformat ``document_id:Pasal N``. Pertanyaan tanpa pasal
    kunci (di luar cakupan) tidak dihitung, sehingga dikembalikan None.
    """
    expected = set(answer.get("expected_articles") or [])
    if not expected:
        return None
    retrieved = {f"{item['document_id']}:{item['article_label']}" for item in answer["retrieved"]}
    return bool(expected & retrieved)


def _build_result_row(answer: dict, judgment: dict) -> dict:
    """Mengembalikan satu baris hasil evaluasi dari jawaban dan penilaian juri."""
    generation_usage = answer["token_usage"].get("generation", {})
    rewrite_usage = answer["token_usage"].get("rewrite", {})
    answer_input_tokens = generation_usage.get("input_tokens", 0)
    answer_output_tokens = generation_usage.get("output_tokens", 0)
    is_out_of_scope = answer["question_type"] == OUT_OF_SCOPE_TYPE
    return {
        "question_id": answer["question_id"],
        "question_type": answer["question_type"],
        "question": answer["question"],
        "answer_model_id": answer["answer_model_id"],
        "is_answer_found": answer["is_answer_found"],
        "is_correct_refusal": (not answer["is_answer_found"]) if is_out_of_scope else None,
        "retrieval_hit": _is_retrieval_hit(answer),
        "relevance_score": judgment.get("relevance_score"),
        "faithfulness_score": judgment.get("faithfulness_score"),
        "answer_input_tokens": answer_input_tokens,
        "answer_output_tokens": answer_output_tokens,
        "rewrite_input_tokens": rewrite_usage.get("input_tokens", 0),
        "rewrite_output_tokens": rewrite_usage.get("output_tokens", 0),
        # Biaya dihitung sebagai jumlah token per pertanyaan (Bab 7.2), tanpa harga.
        "answer_total_tokens": answer_input_tokens + answer_output_tokens,
        "latency_s": round(answer["latency_s"], 3),
    }


def _mean_of(rows: list[dict], column: str) -> str:
    """Mengembalikan rata-rata kolom (boolean dihitung sebagai proporsi), atau '-'."""
    values = [float(row[column]) for row in rows if row[column] is not None]
    return format_decimal(statistics.mean(values)) if values else "-"


def _summarize_by_type(rows: list[dict]) -> list[str]:
    """Mengembalikan baris tabel Markdown rata-rata metrik per jenis pertanyaan."""
    rows_by_type: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_type[row["question_type"]].append(row)
    rows_by_type["semua"] = rows

    lines = [
        "| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar "
        "| Token jawab (masuk+keluar) | Latency (detik) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for question_type, group in rows_by_type.items():
        lines.append(
            f"| {question_type} | {len(group)} | {_mean_of(group, 'relevance_score')} "
            f"| {_mean_of(group, 'faithfulness_score')} | {_mean_of(group, 'retrieval_hit')} "
            f"| {_mean_of(group, 'is_correct_refusal')} "
            f"| {_mean_of(group, 'answer_total_tokens')} | {_mean_of(group, 'latency_s')} |"
        )
    return lines


def _list_lowest_scores(rows: list[dict]) -> list[str]:
    """Mengembalikan daftar pertanyaan berskor faithfulness terendah untuk dicek manual."""
    scored = [row for row in rows if row["faithfulness_score"] is not None]
    lowest = sorted(scored, key=lambda row: row["faithfulness_score"])[:_LOWEST_SCORE_COUNT]
    return [
        f"- {row['question_id']} (faithfulness {format_decimal(row['faithfulness_score'], 1)}): "
        f"{row['question']}"
        for row in lowest
    ]


def step_report(args: argparse.Namespace) -> None:
    """Menggabungkan jawaban dan penilaian ke CSV hasil serta ringkasan Markdown."""
    run_dir = _run_dir(args.run_name)
    judgments = {j["question_id"]: j for j in read_jsonl(run_dir / "judgments.jsonl")}
    answers = read_jsonl(run_dir / "answers.jsonl")
    rows = [_build_result_row(a, judgments.get(a["question_id"], {})) for a in answers]

    with (run_dir / "evaluation_results.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_RESULT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = [
        f"# Ringkasan evaluasi: {args.run_name}",
        "",
        "Parameter putaran ada di `run_config.json`. Skor juri adalah estimasi; "
        "periksa manual pertanyaan berskor terendah di bawah.",
        "",
        *_summarize_by_type(rows),
        "",
        "## Skor faithfulness terendah (cek manual)",
        "",
        *_list_lowest_scores(rows),
        "",
    ]
    (run_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Hasil → {run_dir / 'evaluation_results.csv'} dan {run_dir / 'summary.md'}")


STEPS = {
    "generate": step_generate,
    "judge": step_judge,
    "report": step_report,
}


def parse_args() -> argparse.Namespace:
    """Mengembalikan argumen CLI evaluasi."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-name", default="baseline", help="Nama folder putaran evaluasi.")
    parser.add_argument(
        "--only",
        default=",".join(STEPS),
        help=f"Langkah yang dijalankan, dipisah koma. Pilihan: {', '.join(STEPS)}.",
    )
    parser.add_argument(
        "--model-key",
        default=config.DEFAULT_ANSWER_MODEL_KEY,
        help="Model penjawab: groq (default) atau haiku.",
    )
    parser.add_argument(
        "--pause-s",
        type=float,
        default=8.0,
        help="Jeda antarpertanyaan dalam detik, untuk batas token per menit Groq.",
    )
    parser.add_argument(
        "--reuse-rewrites-from",
        metavar="RUN_NAME",
        help="Pakai kueri tulis ulang dari putaran ini (bukan memanggil penulis ulang), "
        "supaya retrieval identik dan hanya parameter yang diuji yang berbeda.",
    )
    parser.add_argument(
        "--test-set",
        type=Path,
        default=config.TEST_SET_JSONL_PATH,
        help="Path set uji JSONL.",
    )
    return parser.parse_args()


def main() -> None:
    """Menjalankan langkah evaluasi yang dipilih sesuai urutan baku di ``STEPS``."""
    # Konsol Windows bawaan (cp1252) tidak bisa mencetak "→".
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    selected = {name.strip() for name in args.only.split(",") if name.strip()}
    unknown = selected - STEPS.keys()
    if unknown:
        raise SystemExit(f"Langkah tidak dikenal: {', '.join(sorted(unknown))}")
    for name, step in STEPS.items():
        if name in selected:
            print(f"\n== step_{name} ==")
            step(args)


if __name__ == "__main__":
    main()
