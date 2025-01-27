# Norwegian Bokmål-Nynorsk Translation Filter for Common Voice

This repository contains:

- A **Python script** (`filter.py`) that filters lines from the [Bokmål-Nynorsk-translation set](https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-80/) released by Språkbanken under CC0.  
- The **source data** (in `source/`) and the **generated data** (in `output/`) after filtering.

The resulting data is intended for integration with Mozilla’s [Common Voice](https://commonvoice.mozilla.org/) project, providing Norwegian (Bokmål/Nynorsk) sentences cleared of various undesired attributes.

## Repository Structure

```
.
├── filter.py         # The main filtering script
├── source/           # Directory containing input .tsv files (unfiltered)
├── output/           # Directory where filtered output chunks are written
└── README.md         # This file
```

## What Does the Script Do?

The script reads a `.tsv` input file containing Norwegian sentences (specifically from the Bokmål–Nynorsk translation corpus). It runs these sentences through a series of filters to ensure only “clean” and appropriate sentences remain for Common Voice. The filtering process includes both **fast filters** (for quick pre-validation) and a **spaCy-based filter** for more advanced linguistic checks. The following filters are applied:

1. **starts_with_capital**  
   - Checks if the sentence starts with a capital letter.

2. **has_no_parentheses**  
   - Ensures that the sentence does not contain `(` or `)`.

3. **ends_with_punctuation**  
   - Checks that the sentence ends with either `.` or `?`.

4. **only_one_sentence**  
   - Ensures exactly one end punctuation (`.` or `?`) and that it is at the end.

5. **has_no_numbers**  
   - Discards sentences containing digits (0–9).

6. **no_special_characters**  
   - Allows only typical Norwegian characters and standard punctuation.

7. **reading_time_filter**  
   - Accepts only sentences estimated to take **8–17 seconds** to read at **150 WPM**.  
   - Words with more than **10 characters** count as **2 words** to account for complexity.

8. **basic_proper_noun_filter**
   - Quickly filters out sentences that contain words starting with capital letters within the sentence body (e.g., names or places).

9. **maximum_word_filter**
   -- Filter out sentences with more than 18 words

10. **proper_noun_filter** (spaCy-based)  
   - Uses [spaCy’s Norwegian model](https://spacy.io/models/nb) to discard sentences containing **proper nouns (PROPN)**, i.e., names of people or places.io/models/nb) to discard sentences containing **proper nouns (PROPN)**, i.e. names of people or places.

## Requirements

- **Python 3.7+** recommended.
- Install required dependencies:
  ```bash
  pip install tqdm spacy
  ```
- Install the Norwegian spaCy model:
  ```bash
  python -m spacy download nb_core_news_sm
  ```
- Make sure your environment can run the script with `python filter.py`.

## How to Use

1. **Download the input file** [`npk_2011_2022.tsv`](https://www.nb.no/sbfil/npk-2011-2022/npk_2011_2022.tsv) and place it inside the `source/` folder. Note: This file is not included in the repository and must be downloaded manually.
2. **Create or ensure you have an `output/` folder**.
3. **Run the script** from the command line:
   ```bash
   python filter.py --input_file source/npk_2011_2022.tsv --output_folder output/
   ```
   
   - The script will:
     - Read the file `npk_2011_2022.tsv`.
     - Apply all **fast filters** first.
     - Then apply the **spaCy-based** (slow) filter (`proper_noun_filter`) on the surviving lines.
     - Write final outputs into 1,000-line chunks named `output_1.tsv`, `output_2.tsv`, etc., in the `output/` folder.

4. **Check the resulting files** in the `output/` folder. Each line has this format:

   ```
   Sentence[TAB]Source[TAB]Additional rationale[TAB](blank for QA feedback)[TAB]Domain
   ```

   Where:
   - **Sentence** is the actual Norwegian text.
   - **Source** defaults to [`https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-80/`](https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-80/).
   - **Additional rationale** is a string describing this as a CC0 licensed corpus released by Språkbanken.
   - **Sentence Quality Assurance Feedback** is left blank.
   - **Domain** is set to `General`.

## Output Explanation

- The script prints progress bars (via `tqdm`) for the **fast filters** and **spaCy filter** steps.
- In the end, you’ll see statistics printed to the console, like how many lines were processed, how many were filtered out by each filter, and how many passed overall.
- All sentences that pass all filters are saved in chunks of 1,000 lines each.

## License

The original data from Språkbanken is released under **CC0**. This repository is meant to preserve the same spirit of open licensing. The final sentences are suitable for projects like Mozilla’s Common Voice.

If you have questions or suggestions, feel free to open an issue or fork the repository.

Enjoy building Norwegian language datasets for Common Voice!


