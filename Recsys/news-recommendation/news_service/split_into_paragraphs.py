import kss

# 3줄씩 문장을 잘라 단락 생성


def split_into_paragraphs(article, sentences_per_paragraph=3):
    sentences = kss.split_sentences(article)
    paragraphs = []
    paragraph = []

    for sentence in sentences:
        if len(sentence) > 20:
            # 보통 한 줄에 20자 정도 넘어가야 유의미한 정보가 포함된 문장
            paragraph.append(sentence)
        if len(paragraph) == sentences_per_paragraph:  # 3줄 이상이면
            paragraphs.append(" ".join(paragraph))  # 3줄을 하나로 합치기
            paragraph = []

        # 남아있는 문장들 중 20자가 넘어가면 단락으로 추가
    if paragraph and len(paragraph) > 20:
        paragraphs.append(" ".join(paragraph))

    return paragraphs  # 단락 데이터 반환
