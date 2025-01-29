#!/usr/bin/env python3
import argparse
import sys
import re
import os

# For progress bar:
try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' is required for a progress bar. Install with: pip install tqdm")
    sys.exit(1)

# For spaCy-based filtering:
try:
    import spacy
except ImportError:
    print("Error: spaCy is required. Install with: pip install spacy")
    sys.exit(1)

################################################################
# Filters (fast first, then spaCy/slow filters at the end)
################################################################

def starts_with_capital(sentence: str) -> bool:
    stripped = sentence.lstrip()
    return bool(stripped) and stripped[0].isupper()

def has_no_parentheses(sentence: str) -> bool:
    return '(' not in sentence and ')' not in sentence

def ends_with_punctuation(sentence: str) -> bool:
    stripped = sentence.rstrip()
    return bool(stripped) and stripped[-1] in {'.', '?'}

def only_one_sentence(sentence: str) -> bool:
    """Checks if there's only one end punctuation ('.' or '?') in the string."""
    stripped = sentence.rstrip()
    if not stripped:
        return False
    total_punct = stripped.count('.') + stripped.count('?')
    return total_punct == 1 and stripped[-1] in {'.', '?'}

def has_no_numbers(sentence: str) -> bool:
    return not any(char.isdigit() for char in sentence)

def no_special_characters(sentence: str) -> bool:
    # Allow letters, typical Norwegian chars, whitespace, punctuation
    pattern = r'^[a-zA-ZæøåÆØÅ\s,.!?\'’:;\-]*$'
    return re.fullmatch(pattern, sentence, re.UNICODE) is not None

def reading_time_filter(sentence: str, wpm: int = 100, min_sec: int = 2, max_sec: int = 7) -> bool:
    """
    Accept only sentences that take 7–15 seconds to read,
    assuming 100 wpm. Words over 10 chars count as 2 words.
    """
    words = sentence.split()
    # Count each word; if it has more than 10 characters, count as 2
    effective_word_count = sum(2 if len(w) > 10 else 1 for w in words)
    words_per_second = wpm / 60.0
    reading_time = effective_word_count / words_per_second
    return min_sec <= reading_time <= max_sec

def max_word_count_filter(sentence: str, max_words: int = 14) -> bool:
    """
    Accept only sentences with a maximum number of words.
    """
    return len(sentence.split()) <= max_words

def basic_proper_noun_filter(sentence: str) -> bool:
    """
    Quickly filters out sentences containing words with capital letters 
    (ignoring the first word which starts the sentence).
    """
    words = sentence.split()
    if len(words) > 1:
        for word in words[1:]:
            if word[0].isupper():
                return False
    return True

def create_proper_noun_filter(nlp):
    """
    Return a function that filters out sentences containing proper nouns (PROPN).
    """
    def proper_noun_filter(sentence: str) -> bool:
        doc = nlp(sentence)
        return not any(token.pos_ == 'PROPN' for token in doc)
    return proper_noun_filter

################################################################
# Main logic
################################################################

def main():
    parser = argparse.ArgumentParser(description="Filter Norwegian sentences with spaCy.")
    parser.add_argument('--input_file', required=True, help='Input TSV file.')
    parser.add_argument('--output_folder', required=True, help='Folder where output TSV chunks are saved.')
    parser.add_argument('--single_sentences', action='store_true', help='Process only single sentences. Defaults to False.')
    parser.add_argument('--chunk_size', type=int, default=1000000, help='Number of sentences per output chunk. Defaults to 1,000,000.')
    args = parser.parse_args()

    # Validate input file extension
    if not args.input_file.lower().endswith('.tsv'):
        print("Error: Input must be a .tsv file")
        sys.exit(1)

    # Validate output folder
    if not os.path.isdir(args.output_folder):
        print(f"Error: '{args.output_folder}' is not a directory. Create it or specify an existing directory.")
        sys.exit(1)

    # Load Norwegian NLP model
    try:
        nlp = spacy.load("nb_core_news_sm")
    except OSError:
        print("Model 'nb_core_news_sm' not found. Install with:")
        print("python -m spacy download nb_core_news_sm")
        sys.exit(1)

    # Prepare the slow (spaCy) filter separately
    spaCy_filter_func = create_proper_noun_filter(nlp)

    # Fast filters (applied before spaCy to reduce overhead)
    fast_filters = [
        (starts_with_capital, "starts_with_capital"),
        (has_no_parentheses, "has_no_parentheses"),
        (ends_with_punctuation, "ends_with_punctuation"),
        (only_one_sentence, "only_one_sentence"),
        (has_no_numbers, "has_no_numbers"),
        (no_special_characters, "no_special_characters"),
        (reading_time_filter, "reading_time_filter"),
        (max_word_count_filter, "max_word_count_filter"),
        (basic_proper_noun_filter, "basic_proper_noun_filter")
    ]

    # Track how many sentences each filter kills
    filter_fail_count = {}
    for _, filter_name in fast_filters:
        filter_fail_count[filter_name] = 0
    filter_fail_count["proper_noun_filter"] = 0

    survivors = []
    total_lines = 0

    # First pass: apply fast filters
    with open(args.input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    for line in tqdm(lines, desc="Applying fast filters"):
        line = line.strip()
        if not line:
            continue

        parts = line.split('\t')
        if len(parts) < 2:
            continue

        total_lines += 1
        # We ignore the first column (ID) for final output,
        # only use the second column (sentence).
        sentence = parts[1].strip()

        passed_all_fast = True
        for filter_func, filter_name in fast_filters:
            if not filter_func(sentence):
                filter_fail_count[filter_name] += 1
                passed_all_fast = False
                break

        if passed_all_fast:
            survivors.append(sentence)

    # Second pass: apply the slow spaCy filter to survivors
    final_pass = []
    for sentence in tqdm(survivors, desc="Applying spaCy filter"):
        if spaCy_filter_func(sentence):
            final_pass.append(sentence)
        else:
            filter_fail_count["proper_noun_filter"] += 1

    # Prepare metadata for final output lines
    source = "https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-80/"
    additional_rationale = (
        "This is a CC0 licensed corpus cleared from newspaper text. "
        "The source sentences from a translation corpus is used.  "
        "It is released by Språkbanken."
    )
    domain = "General"

    # Write the final survivors in 1000-line chunks
    CHUNK_SIZE = args.chunk_size
    total_final = len(final_pass)
    chunk_count = 0

    for i in range(0, total_final, CHUNK_SIZE):
        chunk_count += 1
        chunk = final_pass[i : i + CHUNK_SIZE]
        chunk_filename = os.path.join(args.output_folder, f"output_{chunk_count}.tsv")
        
        if args.single_sentences:
            with open(chunk_filename, 'w', encoding='utf-8') as outfile:
                for sentence in chunk:
                    outfile.write(
                        f"{sentence}\n"
                    )

        else:
            with open(chunk_filename, 'w', encoding='utf-8') as outfile:
                for sentence in chunk:
                    outfile.write(
                        f"{sentence}\t"
                        f"{source}\t"
                        f"{additional_rationale}\t"
                        f""  # Sentence Quality Assurance Feedback: blank
                        f"\t"
                        f"{domain}\n"
                    )

    # Print statistics
    print("\n===== Filtering Statistics =====")
    print(f"Total lines processed: {total_lines}")
    for flt in filter_fail_count:
        print(f"Filtered out by {flt}: {filter_fail_count[flt]}")
    print(f"Final lines passed: {total_final}")
    print(f"Output split into {chunk_count} file(s) under '{args.output_folder}'.")

if __name__ == '__main__':
    main()

