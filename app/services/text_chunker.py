import re
from dataclasses import dataclass
from typing import List

TARGET_TOKENS = 500
MAX_TOKENS = 1000
OVERLAP_TOKENS = 100

SENTENCE_SPLITTERS = re.compile(r'(?<=[。！？.!?\n])\s*')


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - cn_chars
    return cn_chars + (other_chars // 4)


def split_sentences(text: str) -> List[str]:
    parts = SENTENCE_SPLITTERS.split(text)
    return [p.strip() for p in parts if p.strip()]


@dataclass
class Chunk:
    content: str
    token_count: int
    metadata: dict


def chunk_text(text: str) -> List[Chunk]:
    if not text or not text.strip():
        return []

    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    raw_chunks = []
    for para in paragraphs:
        if estimate_tokens(para) <= MAX_TOKENS:
            raw_chunks.append(para)
        else:
            sentences = split_sentences(para)
            current = ""
            for sent in sentences:
                if estimate_tokens(current + sent) > MAX_TOKENS:
                    if current:
                        raw_chunks.append(current)
                    current = sent
                else:
                    current = (current + " " + sent).strip() if current else sent
            if current:
                raw_chunks.append(current)

    merged_chunks = []
    buffer = ""
    for chunk in raw_chunks:
        if not buffer:
            buffer = chunk
        elif estimate_tokens(buffer + "\n\n" + chunk) <= TARGET_TOKENS:
            buffer = (buffer + "\n\n" + chunk)
        else:
            merged_chunks.append(buffer)
            if OVERLAP_TOKENS > 0 and merged_chunks:
                overlap_text = _get_tail_tokens(buffer, OVERLAP_TOKENS)
                buffer = (overlap_text + "\n\n" + chunk) if overlap_text else chunk
            else:
                buffer = chunk
    if buffer:
        merged_chunks.append(buffer)

    result = []
    for i, content in enumerate(merged_chunks):
        result.append(Chunk(
            content=content,
            token_count=estimate_tokens(content),
            metadata={"chunk_index": i, "total_chunks": len(merged_chunks)},
        ))

    return result


def _get_tail_tokens(text: str, max_tokens: int) -> str:
    sentences = split_sentences(text)
    tail = ""
    token_sum = 0
    for sent in reversed(sentences):
        sent_tokens = estimate_tokens(sent)
        if token_sum + sent_tokens > max_tokens:
            break
        tail = sent + " " + tail
        token_sum += sent_tokens
    return tail.strip()
